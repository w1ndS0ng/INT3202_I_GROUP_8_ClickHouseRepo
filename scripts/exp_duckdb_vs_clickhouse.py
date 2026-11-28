#!/usr/bin/env python3
"""Direct multi-DBMS columnar comparison on laptop1: ClickHouse MergeTree vs DuckDB 2.0.1 (30M ClickBench hits, 4 threads)."""
import json
import os
import random
import statistics
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mtstudy.common import Client, distribution, quote, read, save, utc

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "chapter-4" / "4.6" / "results" / "duckdb_vs_clickhouse_ver1.json"
TMP_DIR = Path("/tmp/duckdb_ch_exp")


def perm_mwu(x, y, n_perm=50000, seed=20261116):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n1, n2 = len(x), len(y)
    # Exact rank sum U (handles ties cleanly via scipy-like average ranks)
    combined = np.concatenate([x, y])
    order = np.argsort(combined, kind="mergesort")
    ranks = np.empty(len(combined), dtype=float)
    sorted_vals = combined[order]
    i = 0
    while i < len(sorted_vals):
        j = i + 1
        while j < len(sorted_vals) and sorted_vals[j] == sorted_vals[i]:
            j += 1
        avg_rank = 0.5 * (i + 1 + j)
        ranks[order[i:j]] = avg_rank
        i = j
    u1 = float(np.sum(ranks[:n1]) - n1 * (n1 + 1) / 2.0)
    u2 = n1 * n2 - u1
    u_obs = min(u1, u2)
    diff_obs = abs(float(np.sum(ranks[:n1])) - float(np.mean(ranks)) * n1)
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(ranks)
        diff_p = abs(float(np.sum(perm[:n1])) - float(np.mean(ranks)) * n1)
        if diff_p >= diff_obs - 1e-12:
            count += 1
    return float(u_obs), float((count + 1) / (n_perm + 1))


def export_parquet_from_ch(client, out_parquet):
    # Export 30M rows cleanly via HTTP stream from mtr_ha_laptop1_main01.keys_30m_k0
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    host = os.environ.get("CH_HOST", "127.0.0.1")
    port = int(os.environ.get("CH_HTTP_PORT", "8123"))
    params = {"query": "SELECT * FROM mtr_ha_laptop1_main01.keys_30m_k0 FORMAT Parquet"}
    url = f"http://{host}:{port}/?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=client.headers)
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=1800) as resp, out_parquet.open("wb") as f:
        while True:
            chunk = resp.read(4 * 1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return time.perf_counter() - t0, out_parquet.stat().st_size


def duck_sql(table, p):
    sel = f"SELECT COUNT(*)::BIGINT AS matched, COALESCE(SUM(ResolutionWidth), 0)::BIGINT AS checksum FROM {table}"
    dates = f"EventDate >= DATE '{p['date_start']}' AND EventDate < DATE '{p['date_end']}'"
    return {
        "w0": sel,
        "w1": sel + f" WHERE CounterID = {int(p['counter_id'])}",
        "w2": sel + " WHERE " + dates,
        "w3": sel + f" WHERE CounterID = {int(p['counter_id'])} AND " + dates,
        "w4": sel + f" WHERE RegionID = {int(p['region_id'])}",
    }


def ch_sql(table, p):
    sel = f"SELECT count() AS matched, sum(ResolutionWidth) AS checksum FROM {table}"
    dates = f"EventDate >= toDate('{p['date_start']}') AND EventDate < toDate('{p['date_end']}')"
    return {
        "w0": sel,
        "w1": sel + f" WHERE CounterID = {int(p['counter_id'])}",
        "w2": sel + " WHERE " + dates,
        "w3": sel + f" WHERE CounterID = {int(p['counter_id'])} AND " + dates,
        "w4": sel + f" WHERE RegionID = {int(p['region_id'])}",
    }


def main():
    protocol = read(ROOT / "configs" / "protocol.json")
    expected_ans = read(ROOT / "chapter-3" / "3.3.1" / "results" / "checks" / "keys_30m_answers_ver1.json")
    default_xml = Path("~/.config/mergetree-study/client.xml").expanduser()
    cfg = str(default_xml) if ("CH_CONFIG" not in os.environ and default_xml.exists()) else None
    client = Client(protocol["settings"], xml=cfg)
    p = protocol["parameters"]

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = TMP_DIR / "hits_30m.parquet"
    duck0_path = TMP_DIR / "duck0.duckdb"
    duck1_path = TMP_DIR / "duck1.duckdb"
    for f in (parquet_path, duck0_path, duck1_path):
        if f.exists():
            f.unlink()

    try:
        exp_s, pq_bytes = export_parquet_from_ch(client, parquet_path)

        # Build DUCK0 (unsorted native columnar)
        t0 = time.perf_counter()
        c0 = duckdb.connect(str(duck0_path))
        c0.execute("SET threads=4; SET memory_limit='2GB';")
        c0.execute(f"CREATE TABLE hits_k0 AS SELECT * FROM read_parquet('{parquet_path}'); CHECKPOINT;")
        duck0_build_s = time.perf_counter() - t0
        c0.close()

        # Build DUCK1 (sorted by CounterID, EventDate matching CH1)
        t0 = time.perf_counter()
        c1 = duckdb.connect(str(duck1_path))
        c1.execute("SET threads=4; SET memory_limit='2GB';")
        c1.execute(f"CREATE TABLE hits_k1 AS SELECT * FROM read_parquet('{parquet_path}') ORDER BY CounterID, EventDate; CHECKPOINT;")
        duck1_build_s = time.perf_counter() - t0
        c1.close()

        c0 = duckdb.connect(str(duck0_path), read_only=True)
        c0.execute("SET threads=4; SET memory_limit='2GB';")
        c1 = duckdb.connect(str(duck1_path), read_only=True)
        c1.execute("SET threads=4; SET memory_limit='2GB';")

        duck_tables = {"DUCK0": (c0, duck_sql("hits_k0", p)), "DUCK1": (c1, duck_sql("hits_k1", p))}
        ch_tables = {
            "CH0": ch_sql("mtr_ha_laptop1_main01.keys_30m_k0", p),
            "CH1": ch_sql("mtr_ha_laptop1_main01.keys_30m_k1", p),
        }

        # Verify bit-identical W0-W4 answers across CH0, CH1, DUCK0, DUCK1
        for case in ["w0", "w1", "w2", "w3", "w4"]:
            ref = expected_ans[case]
            for eng, sql_map in ch_tables.items():
                ans = client.rows(sql_map[case])[0]
                assert int(ans["matched"]) == int(ref["matched"]) and int(ans["checksum"]) == int(ref["checksum"]), (eng, case, ans, ref)
            for eng, (conn, sql_map) in duck_tables.items():
                row = conn.execute(sql_map[case]).fetchone()
                assert int(row[0]) == int(ref["matched"]) and int(row[1]) == int(ref["checksum"]), (eng, case, row, ref)

        cases = []
        for case in ["w0", "w1", "w2", "w3", "w4"]:
            for eng in ["CH0", "CH1", "DUCK0", "DUCK1"]:
                cases.append((eng, case))

        rng = random.Random(protocol["seed"])
        raw_client = {(eng, c): [] for eng, c in cases}
        ch_qids = []
        ch_qid_map = {}

        # Interleaved warm-repeat rounds (2 warmups + 10 measured rounds), returning exact 2-column tuple
        for r_idx in range(-2, 10):
            order = list(cases)
            rng.shuffle(order)
            for eng, case in order:
                if eng in ch_tables:
                    qid = "duck_ch_" + uuid.uuid4().hex
                    txt, ms = client.execute(ch_tables[eng][case] + " FORMAT JSONEachRow", query_id=qid)
                    _ = json.loads(txt.strip())
                    if r_idx >= 0:
                        raw_client[(eng, case)].append(ms)
                        ch_qids.append(qid)
                        ch_qid_map[qid] = (eng, case)
                else:
                    conn, sql_map = duck_tables[eng]
                    t0 = time.perf_counter()
                    _ = conn.execute(sql_map[case]).fetchall()
                    ms = (time.perf_counter() - t0) * 1000.0
                    if r_idx >= 0:
                        raw_client[(eng, case)].append(ms)

        c0.close()
        c1.close()

        client.execute("SYSTEM FLUSH LOGS")
        in_list = ",".join(quote(q) for q in ch_qids)
        logs = {
            r["query_id"]: r
            for r in client.rows(
                "SELECT query_id, query_duration_ms, read_rows, read_bytes, memory_usage "
                f"FROM system.query_log WHERE type='QueryFinish' AND query_id IN ({in_list})"
            )
        }
        ch_server_raw = {(eng, c): [] for eng in ["CH0", "CH1"] for c in ["w0", "w1", "w2", "w3", "w4"]}
        ch_read_rows = {k: [] for k in ch_server_raw}
        for qid, key in ch_qid_map.items():
            ch_server_raw[key].append(float(logs[qid]["query_duration_ms"]))
            ch_read_rows[key].append(int(logs[qid]["read_rows"]))

        ch_disk = client.rows(
            "SELECT table, sum(bytes_on_disk) AS disk_bytes, sum(marks_bytes) AS marks_bytes, "
            "sum(primary_key_bytes_in_memory) AS pk_mem FROM system.parts "
            "WHERE database='mtr_ha_laptop1_main01' AND table IN ('keys_30m_k0','keys_30m_k1') AND active=1 GROUP BY table"
        )
        ch_disk_map = {r["table"]: r for r in ch_disk}

        summary = []
        mwu = []
        for case in ["w0", "w1", "w2", "w3", "w4"]:
            row = {"case": case}
            for eng in ["CH0", "CH1", "DUCK0", "DUCK1"]:
                row[eng] = distribution(raw_client[(eng, case)])
                if eng in ch_tables:
                    row[eng + "_server"] = distribution(ch_server_raw[(eng, case)])
                    row[eng + "_read_rows"] = int(statistics.median(ch_read_rows[(eng, case)]))
            summary.append(row)
            u1, p1 = perm_mwu(raw_client[("CH1", case)], raw_client[("DUCK1", case)])
            u0, p0 = perm_mwu(raw_client[("CH1", case)], raw_client[("DUCK0", case)])
            mwu.append({"case": case, "ch1_vs_duck1_U": u1, "ch1_vs_duck1_p": p1, "ch1_vs_duck0_U": u0, "ch1_vs_duck0_p": p0})

        out = {
            "recorded_at": utc(),
            "duckdb_version": duckdb.__version__,
            "parquet_bytes": pq_bytes,
            "duck_build_s": {"DUCK0": duck0_build_s, "DUCK1": duck1_build_s},
            "storage_bytes": {
                "CH0": int(ch_disk_map["keys_30m_k0"]["disk_bytes"]),
                "CH1": int(ch_disk_map["keys_30m_k1"]["disk_bytes"]),
                "DUCK0": duck0_path.stat().st_size,
                "DUCK1": duck1_path.stat().st_size,
                "parquet_12col": pq_bytes,
            },
            "summary": summary,
            "mann_whitney_u": mwu,
        }
        save(OUT_PATH, out)
        print(f"Saved {OUT_PATH}", flush=True)
        print("Storage MiB:", {k: round(v / 2**20, 3) for k, v in out["storage_bytes"].items()})
        print("Build s:", out["duck_build_s"])
        for r, m in zip(summary, mwu):
            print(
                f"  {r['case']}: CH0={r['CH0']['median']:.2f}ms | CH1={r['CH1']['median']:.2f}ms (srv={r['CH1_server']['median']:.1f}ms) | "
                f"DUCK0={r['DUCK0']['median']:.2f}ms | DUCK1={r['DUCK1']['median']:.2f}ms | p(CH1 vs DUCK1)={m['ch1_vs_duck1_p']:.5f}"
            )
    finally:
        for f in (parquet_path, duck0_path, duck1_path):
            if f.exists():
                f.unlink()
        if TMP_DIR.exists():
            try:
                TMP_DIR.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    main()
