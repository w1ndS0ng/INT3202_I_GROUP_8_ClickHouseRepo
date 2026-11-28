#!/usr/bin/env python3
"""Measure non-prefix W4 (Skipping Index vs Projection) and External Spill on 30M ClickBench rows (laptop1)."""
import json
import random
import statistics
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mtstudy.common import Client, distribution, quote, read, save, utc

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "chapter-3" / "3.6.6" / "results" / "mergetree_features_ver1.json"
SRC_30M = "mtr_ha_laptop1_main01.keys_30m_k1"
SRC_10M = "mtr_ha_laptop1_main01.keys_10m_k1"
DB = "mtr_addon_exp"


def main():
    protocol = read(ROOT / "configs" / "protocol.json")
    default_xml = Path("~/.config/mergetree-study/client.xml").expanduser()
    cfg = str(default_xml) if ("CH_CONFIG" not in __import__("os").environ and default_xml.exists()) else None
    client = Client(protocol["settings"], xml=cfg)
    server = client.rows("SELECT version() AS version")[0]["version"]

    # Pick a rare RegionID (50-200 rows) deterministically for positive control on skipping index
    rare_row = client.rows(
        f"SELECT RegionID, count() AS c FROM {SRC_30M} GROUP BY RegionID "
        "HAVING c BETWEEN 50 AND 200 ORDER BY c DESC, RegionID ASC LIMIT 1"
    )[0]
    rare_region = int(rare_row["RegionID"])
    rare_count = int(rare_row["c"])

    client.execute(f"DROP DATABASE IF EXISTS {DB}")
    client.execute(f"CREATE DATABASE {DB}")
    results = {
        "recorded_at": utc(),
        "server_version": server,
        "source_30m": SRC_30M,
        "rare_region": {"RegionID": rare_region, "rows": rare_count},
        "w4_variants": [],
        "memory_spill": {},
    }

    try:
        cols_ddl = ",\n  ".join(f"`{name}` {typ} CODEC(LZ4)" for name, typ, _ in protocol["schema"])
        common_settings = (
            "index_granularity=8192, index_granularity_bytes=0, "
            "min_bytes_for_wide_part=0, min_rows_for_wide_part=0, write_final_mark=0"
        )

        # 1. Base table + Skipping Indexes (minmax + bloom_filter)
        t_skip = f"{DB}.hits_skip"
        client.execute(
            f"CREATE TABLE {t_skip} (\n  {cols_ddl},\n"
            "  INDEX idx_reg_mm RegionID TYPE minmax GRANULARITY 4,\n"
            "  INDEX idx_reg_bf RegionID TYPE bloom_filter(0.01) GRANULARITY 1\n"
            f") ENGINE=MergeTree ORDER BY (CounterID, EventDate) SETTINGS {common_settings}"
        )
        t0 = time.perf_counter()
        client.execute(
            f"INSERT INTO {t_skip} SELECT * FROM {SRC_30M}",
            overrides={"max_insert_threads": 4, "max_memory_usage": 4000000000},
        )
        client.execute(f"OPTIMIZE TABLE {t_skip} FINAL", overrides={"max_memory_usage": 4000000000})
        skip_build_s = time.perf_counter() - t0

        # 2. Order Projection table (SELECT * ORDER BY RegionID)
        t_pord = f"{DB}.hits_proj_order"
        client.execute(
            f"CREATE TABLE {t_pord} (\n  {cols_ddl},\n"
            "  PROJECTION p_reg_order (SELECT * ORDER BY RegionID)\n"
            f") ENGINE=MergeTree ORDER BY (CounterID, EventDate) SETTINGS {common_settings}"
        )
        t0 = time.perf_counter()
        client.execute(
            f"INSERT INTO {t_pord} SELECT * FROM {SRC_30M}",
            overrides={"max_insert_threads": 4, "max_memory_usage": 4000000000},
        )
        client.execute(f"OPTIMIZE TABLE {t_pord} FINAL", overrides={"max_memory_usage": 4000000000})
        pord_build_s = time.perf_counter() - t0

        # 3. Aggregate Projection table (SELECT RegionID, count(), sum(ResolutionWidth) GROUP BY RegionID)
        t_pagg = f"{DB}.hits_proj_agg"
        client.execute(
            f"CREATE TABLE {t_pagg} (\n  {cols_ddl},\n"
            "  PROJECTION p_reg_agg (SELECT RegionID, count(), sum(ResolutionWidth) GROUP BY RegionID)\n"
            f") ENGINE=MergeTree ORDER BY (CounterID, EventDate) SETTINGS {common_settings}"
        )
        t0 = time.perf_counter()
        client.execute(
            f"INSERT INTO {t_pagg} SELECT * FROM {SRC_30M}",
            overrides={"max_insert_threads": 4, "max_memory_usage": 4000000000},
        )
        client.execute(f"OPTIMIZE TABLE {t_pagg} FINAL", overrides={"max_memory_usage": 4000000000})
        pagg_build_s = time.perf_counter() - t0

        skip_idx_info = client.rows(
            f"SELECT name, type_full, marks_bytes, data_compressed_bytes, data_uncompressed_bytes "
            f"FROM system.data_skipping_indices WHERE database={quote(DB)}"
        )
        proj_info = client.rows(
            f"SELECT table, name, rows, bytes_on_disk, data_compressed_bytes, marks_bytes "
            f"FROM system.projection_parts WHERE database={quote(DB)} AND active=1"
        )
        parts_info = client.rows(
            f"SELECT table, rows, marks, bytes_on_disk, data_compressed_bytes, part_type "
            f"FROM system.parts WHERE database={quote(DB)} AND active=1 ORDER BY table"
        )
        results["storage"] = {
            "parts": parts_info,
            "skip_indices": skip_idx_info,
            "projections": proj_info,
            "build_s": {"t_skip": skip_build_s, "t_proj_order": pord_build_s, "t_proj_agg": pagg_build_s},
        }

        configs = [
            ("k1_baseline", SRC_30M, 229, "W4 (RegionID=229, 20.6%)", {"use_skip_indexes": 0, "optimize_use_projections": 0}),
            ("skip_w4_scattered", t_skip, 229, "W4 (RegionID=229, 20.6%)", {"use_skip_indexes": 1, "use_skip_indexes_on_data_read": 1, "optimize_use_projections": 0}),
            ("k1_rare_noskip", SRC_30M, rare_region, f"Rare RegionID={rare_region} ({rare_count} rows)", {"use_skip_indexes": 0, "optimize_use_projections": 0}),
            ("skip_rare_region", t_skip, rare_region, f"Rare RegionID={rare_region} ({rare_count} rows)", {"use_skip_indexes": 1, "use_skip_indexes_on_data_read": 1, "optimize_use_projections": 0}),
            ("proj_order_w4", t_pord, 229, "W4 (RegionID=229, 20.6%)", {"optimize_use_projections": 1, "optimize_use_implicit_projections": 1}),
            ("proj_agg_w4", t_pagg, 229, "W4 (RegionID=229, 20.6%)", {"optimize_use_projections": 1, "optimize_use_implicit_projections": 1}),
        ]

        # Collect EXPLAIN and verify answers first
        cases = []
        explains = {}
        for label, tbl, reg, desc, ov in configs:
            sql = f"SELECT count() AS matched, sum(ResolutionWidth) AS checksum FROM {tbl} WHERE RegionID = {reg}"
            ans = client.rows(sql, overrides=ov)[0]
            exp_txt, _ = client.execute(f"EXPLAIN indexes=1, projections=1 {sql}", overrides=ov)
            explains[label] = {"answer": ans, "explain": exp_txt}
            cases.append((label, sql, ov, desc, tbl, reg))

        rng = random.Random(20261116)
        qids = []
        raw = {label: [] for label, _, _, _, _, _ in cases}
        for r_idx in range(-2, 10):
            order = list(cases)
            rng.shuffle(order)
            for label, sql, ov, _, _, _ in order:
                qid = "addon_w4_" + uuid.uuid4().hex
                _, ms = client.execute(sql + " FORMAT Null", query_id=qid, overrides=ov)
                if r_idx >= 0:
                    raw[label].append((qid, ms))
                    qids.append(qid)

        client.execute("SYSTEM FLUSH LOGS")
        in_list = ",".join(quote(q) for q in qids)
        logs = {
            r["query_id"]: r
            for r in client.rows(
                "SELECT query_id, query_duration_ms, read_rows, read_bytes, memory_usage, ProfileEvents "
                f"FROM system.query_log WHERE type='QueryFinish' AND query_id IN ({in_list})"
            )
        }

        for label, tbl, reg, desc, ov in configs:
            entries = raw[label]
            c_ms = [ms for _, ms in entries]
            s_ms = [float(logs[q]["query_duration_ms"]) for q, _ in entries]
            r_rows = [int(logs[q]["read_rows"]) for q, _ in entries]
            r_bytes = [int(logs[q]["read_bytes"]) for q, _ in entries]
            m_bytes = [int(logs[q]["memory_usage"]) for q, _ in entries]
            results["w4_variants"].append({
                "label": label,
                "table": tbl,
                "region_id": reg,
                "desc": desc,
                "answer": explains[label]["answer"],
                "explain": explains[label]["explain"],
                "client_ms": distribution(c_ms),
                "server_ms": distribution(s_ms),
                "read_rows_median": statistics.median(r_rows),
                "read_bytes_median": statistics.median(r_bytes),
                "memory_bytes_median": statistics.median(m_bytes),
                "raw_client_ms": c_ms,
            })

        # Part B: Memory Guard vs External Spill on 10M rows
        heavy_sql = f"SELECT WatchID, any(UserID) AS u, count() AS c FROM {SRC_10M} GROUP BY WatchID FORMAT Null"
        guard_qid = "addon_guard_" + uuid.uuid4().hex
        try:
            client.execute(
                heavy_sql,
                query_id=guard_qid,
                overrides={"max_memory_usage": 80_000_000, "max_bytes_before_external_group_by": 0, "max_threads": 4},
            )
            results["memory_spill"]["guard"] = {"blocked": False}
        except RuntimeError as exc:
            results["memory_spill"]["guard"] = {"blocked": True, "error": str(exc)[:500]}

        spill_qid = "addon_spill_" + uuid.uuid4().hex
        t0 = time.perf_counter()
        _, spill_ms = client.execute(
            heavy_sql,
            query_id=spill_qid,
            overrides={"max_memory_usage": 350_000_000, "max_bytes_before_external_group_by": 60_000_000, "max_threads": 4},
        )
        client.execute("SYSTEM FLUSH LOGS")
        slog = client.rows(
            "SELECT query_duration_ms, read_rows, read_bytes, memory_usage, ProfileEvents "
            f"FROM system.query_log WHERE type='QueryFinish' AND query_id={quote(spill_qid)}"
        )[0]
        pe = {k: v for k, v in slog.get("ProfileEvents", {}).items() if "ExternalAggregation" in k or "TemporaryFiles" in k}
        results["memory_spill"]["spill"] = {
            "completed": True,
            "client_ms": spill_ms,
            "server_ms": slog["query_duration_ms"],
            "read_rows": slog["read_rows"],
            "memory_usage_bytes": slog["memory_usage"],
            "external_events": pe,
        }
    finally:
        client.execute(f"DROP DATABASE IF EXISTS {DB}")

    save(OUT_PATH, results)
    print(f"Saved {OUT_PATH}", flush=True)
    for row in results["w4_variants"]:
        print(f"  {row['label']:18s} | rows={int(row['read_rows_median']):>10,d} | client_med={row['client_ms']['median']:.2f}ms | server_med={row['server_ms']['median']:.1f}ms")
    print("  Guard blocked:", results["memory_spill"]["guard"].get("blocked"))
    print("  Spill result :", results["memory_spill"]["spill"])


if __name__ == "__main__":
    main()
