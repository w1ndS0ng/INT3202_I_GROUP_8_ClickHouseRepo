#!/usr/bin/env python3
"""Measure Ch5 Compact->Wide streaming transition under 16 concurrent readers and 5% ReplacingMergeTree FINAL cost."""
import json
import random
import statistics
import sys
import threading
import time
import urllib.parse
import http.client
import base64
import xml.etree.ElementTree as ET
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mtstudy.common import Client, quote, read, save, utc

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "artifacts" / "addons" / "laptop1" / "ch5_compact_wide_final.json"
DB = "mtr_ch5_ext"


def percentile(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    idx = (len(s) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def reader_worker(stop_event, lat_list, lock, auth_hdr, host, port):
    conn = http.client.HTTPConnection(host, port, timeout=30)
    sql = (
        f"SELECT minute, sum(total_views) AS v, sum(total_checkouts) AS c, "
        f"uniqHLL12Merge(unique_users) AS uu FROM {DB}.clickstream_state "
        "WHERE page_id = 42 GROUP BY minute ORDER BY minute FORMAT JSONEachRow"
    )
    url = "/?" + urllib.parse.urlencode({"query": sql, "max_threads": 2, "use_query_cache": 0})
    headers = {"Authorization": auth_hdr}
    rng = random.Random()
    while not stop_event.is_set():
        pid = rng.randint(1, 500)
        q_sql = sql.replace("page_id = 42", f"page_id = {pid}")
        q_url = "/?" + urllib.parse.urlencode({"query": q_sql, "max_threads": 2, "use_query_cache": 0})
        t0 = time.perf_counter()
        conn.request("GET", q_url, headers=headers)
        resp = conn.getresponse()
        _ = resp.read()
        ms = (time.perf_counter() - t0) * 1000.0
        if resp.status == 200:
            with lock:
                lat_list.append(ms)
    conn.close()


def main():
    protocol = read(ROOT / "configs" / "protocol.json")
    xml_path = os.environ.get("CH_CONFIG") or str(Path("~/.config/mergetree-study/client.xml").expanduser())
    client = Client(protocol["settings"], xml=xml_path)
    root = ET.parse(Path(xml_path).expanduser()).getroot()
    user = root.findtext("user", "default")
    pw = root.findtext("password", "")
    auth_hdr = "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()
    host = os.environ.get("CH_HOST", "127.0.0.1")
    port = int(os.environ.get("CH_HTTP_PORT", "8123"))

    client.execute(f"DROP DATABASE IF EXISTS {DB}")
    client.execute(f"CREATE DATABASE {DB}")

    out = {"recorded_at": utc(), "compact_to_wide_stream": {}, "financial_final_5pct": {}}
    try:
        # 1. Live Compact -> Wide under Streaming MV + 16 concurrent readers
        # Keep default min_bytes_for_wide_part = 10 MiB (10485760). Insert ~25 micro-batches
        # across 250 distinct page_id * 16 distinct minutes = 4000 distinct groups per batch
        # (~2.5 MiB per batch -> crosses 10 MiB into Wide part naturally via background merges!)
        client.execute(f"""
            CREATE TABLE {DB}.clickstream_null (
                event_time DateTime, user_id UInt64, page_id UInt32,
                event_type Enum8('view'=1,'add_to_cart'=2,'checkout'=3,'refund'=4),
                revenue Decimal(18, 2)
            ) ENGINE = Null
        """)
        client.execute(f"""
            CREATE TABLE {DB}.clickstream_state (
                minute DateTime CODEC(DoubleDelta, ZSTD(1)),
                page_id UInt32 CODEC(T64, ZSTD(1)),
                total_views SimpleAggregateFunction(sum, UInt64),
                total_checkouts SimpleAggregateFunction(sum, Int64),
                total_revenue SimpleAggregateFunction(sum, Decimal(38, 2)),
                unique_users AggregateFunction(uniqHLL12, UInt64)
            ) ENGINE = AggregatingMergeTree()
            PARTITION BY toYYYYMM(minute)
            ORDER BY (page_id, minute)
            SETTINGS index_granularity = 256
        """)
        client.execute(f"""
            CREATE MATERIALIZED VIEW {DB}.clickstream_mv TO {DB}.clickstream_state AS
            SELECT toStartOfMinute(event_time) AS minute, page_id,
                countIf(event_type='view') AS total_views,
                sumIf(toInt64(1), event_type='checkout') + sumIf(toInt64(-1), event_type='refund') AS total_checkouts,
                sum(revenue) AS total_revenue, uniqHLL12State(user_id) AS unique_users
            FROM {DB}.clickstream_null GROUP BY minute, page_id
        """)

        # Seed 5 small Compact history chunks (~2.1 MiB each via HLL ~50 users/bucket => ~10.5 MiB total so live merges cross 10 MiB Compact->Wide!)
        for h in range(5):
            client.execute(f"""
                INSERT INTO {DB}.clickstream_null
                SELECT
                    toDateTime('2026-11-26 05:00:00') + (h * 3600) + ((number % 60) * 60),
                    (number % 250000) + (h * 1000000) + 1 AS user_id,
                    (cityHash64(number, 9) % 1000) + 1 AS page_id,
                    'view' AS event_type,
                    toDecimal64(0.00, 2) AS revenue
                FROM numbers(3000000)
                SETTINGS min_insert_block_size_rows = 3000000
            """.replace("h * 3600", f"{h * 3600}").replace("h * 1000000", f"{h * 1000000}"))

        # Build 20 distinct JSONEachRow micro-batches (5,000 events each = 10k events/s pace at 500ms interval)
        batches = []
        for b in range(20):
            lines = []
            for j in range(5000):
                uid = 90000000 + b * 10000 + j
                pid = (j % 1000) + 1
                sec = j % 60
                minute = b % 60
                lines.append(
                    f'{{"event_time":"2026-11-26 10:{minute:02d}:{sec:02d}","user_id":{uid},"page_id":{pid},"event_type":"view","revenue":"0.00"}}'
                )
            batches.append("\n".join(lines).encode())

        stop_ev = threading.Event()
        read_lats = []
        lock = threading.Lock()
        workers = [
            threading.Thread(target=reader_worker, args=(stop_ev, read_lats, lock, auth_hdr, host, port), daemon=True)
            for _ in range(16)
        ]
        for w in workers:
            w.start()

        ingest_ms = []
        part_snapshots = []
        t_start = time.perf_counter()
        for b_idx, payload in enumerate(batches):
            _, ms = client.execute(f"INSERT INTO {DB}.clickstream_null FORMAT JSONEachRow", payload=payload)
            ingest_ms.append(ms)
            snap = client.rows(
                f"SELECT count() AS n_parts, countIf(part_type='Wide') AS wide_parts, "
                f"countIf(part_type='Compact') AS compact_parts, sum(bytes_on_disk) AS disk_bytes "
                f"FROM system.parts WHERE database={quote(DB)} AND table='clickstream_state' AND active=1"
            )[0]
            part_snapshots.append({"batch": b_idx + 1, **snap})
            time.sleep(0.35)

        # Keep readers running for 4s after last insert so final Compact->Wide background merge executes during live reads
        time.sleep(4.0)
        stop_ev.set()
        for w in workers:
            w.join(timeout=5)
        total_stream_s = time.perf_counter() - t_start

        client.execute("SYSTEM FLUSH LOGS")
        part_log = client.rows(
            f"SELECT event_type, part_type, count() AS cnt, sum(rows) AS sum_rows, sum(read_rows) AS sum_read_rows, "
            f"max(size_in_bytes) AS max_bytes, sum(duration_ms) AS sum_dur_ms "
            f"FROM system.part_log WHERE database={quote(DB)} AND table='clickstream_state' "
            f"GROUP BY event_type, part_type ORDER BY event_type, part_type"
        )
        final_parts = client.rows(
            f"SELECT name, part_type, rows, bytes_on_disk FROM system.parts "
            f"WHERE database={quote(DB)} AND table='clickstream_state' AND active=1 ORDER BY name"
        )

        out["compact_to_wide_stream"] = {
            "total_stream_s": total_stream_s,
            "batches": len(batches),
            "raw_events": len(batches) * 5000,
            "seed_events": 15000000,
            "concurrent_readers": 16,
            "total_reads": len(read_lats),
            "read_ms_p50": percentile(read_lats, 0.50),
            "read_ms_p95": percentile(read_lats, 0.95),
            "read_ms_p99": percentile(read_lats, 0.99),
            "ingest_commit_ms_p50": percentile(ingest_ms, 0.50),
            "ingest_commit_ms_p95": percentile(ingest_ms, 0.95),
            "part_log_summary": part_log,
            "final_parts": final_parts,
            "timeline": part_snapshots,
        }

        # 2. ReplacingMergeTree FINAL overhead on 5% financial stream (1.8M rows)
        client.execute(f"""
            CREATE TABLE {DB}.financial_events_dedup (
                event_id UUID, event_time DateTime, page_id UInt32, user_id UInt64,
                event_type Enum8('checkout'=3, 'refund'=4), revenue Decimal(18, 2),
                ingest_ver UInt64
            ) ENGINE = ReplacingMergeTree(ingest_ver)
            PARTITION BY toYYYYMM(event_time)
            ORDER BY (toDate(event_time), page_id, event_id)
        """)
        # Load 1.8M rows in 2 batches (keeping 2 unmerged parts to make FINAL do real dedup work!)
        client.execute(f"""
            INSERT INTO {DB}.financial_events_dedup
            SELECT
                reinterpretAsUUID(MD5(toString(number % 1764000))) AS event_id,
                toDateTime('2026-11-26 10:00:00') + (number % 3600),
                (cityHash64(number, 7) % 1000) + 1 AS page_id,
                (number % 200000) + 1 AS user_id,
                if(number % 25 = 0, 'refund', 'checkout') AS event_type,
                if(number % 25 = 0, -50.00, 100.00) AS revenue,
                number DIV 1764000 + 1 AS ingest_ver
            FROM numbers(900000)
        """)
        client.execute(f"""
            INSERT INTO {DB}.financial_events_dedup
            SELECT
                reinterpretAsUUID(MD5(toString((number + 900000) % 1764000))) AS event_id,
                toDateTime('2026-11-26 10:00:00') + ((number + 900000) % 3600),
                (cityHash64(number + 900000, 7) % 1000) + 1 AS page_id,
                ((number + 900000) % 200000) + 1 AS user_id,
                if((number + 900000) % 25 = 0, 'refund', 'checkout') AS event_type,
                if((number + 900000) % 25 = 0, -50.00, 100.00) AS revenue,
                (number + 900000) DIV 1764000 + 1 AS ingest_ver
            FROM numbers(900000)
        """)
        fin_parts = client.rows(
            f"SELECT count() AS parts, sum(rows) AS total_rows, sum(bytes_on_disk) AS disk_bytes "
            f"FROM system.parts WHERE database={quote(DB)} AND table='financial_events_dedup' AND active=1"
        )[0]
        q_page_nofinal = f"SELECT page_id, sum(revenue) AS rev FROM {DB}.financial_events_dedup WHERE page_id = 42 GROUP BY page_id"
        q_page_final = f"SELECT page_id, sum(revenue) AS rev FROM {DB}.financial_events_dedup FINAL WHERE page_id = 42 GROUP BY page_id"
        q_all_final = f"SELECT count(), sum(revenue) FROM {DB}.financial_events_dedup FINAL"

        ans_nofinal = client.rows(q_page_nofinal)[0]
        ans_final = client.rows(q_page_final)[0]
        ans_all = client.rows(q_all_final)[0]

        def bench(sql_q, n=10):
            vals = []
            for r in range(-2, n):
                _, ms = client.execute(sql_q + " FORMAT JSONEachRow", overrides={"max_threads": 4, "use_query_cache": 0})
                if r >= 0:
                    vals.append(ms)
            return sorted(vals), statistics.median(vals), percentile(vals, 0.95)

        _, med_nf, p95_nf = bench(q_page_nofinal)
        _, med_f, p95_f = bench(q_page_final)
        _, med_all, p95_all = bench(q_all_final, n=5)

        out["financial_final_5pct"] = {
            "parts": fin_parts,
            "page42_no_final": {"ans": ans_nofinal, "median_ms": med_nf, "p95_ms": p95_nf},
            "page42_final": {"ans": ans_final, "median_ms": med_f, "p95_ms": p95_f},
            "full_1_8m_final": {"ans": ans_all, "median_ms": med_all, "p95_ms": p95_all},
        }
    finally:
        client.execute(f"DROP DATABASE IF EXISTS {DB}")

    save(OUT_PATH, out)
    print(f"Saved {OUT_PATH}", flush=True)
    print("  Compact->Wide part_log:", out["compact_to_wide_stream"]["part_log_summary"])
    print("  16-reader reads:", out["compact_to_wide_stream"]["total_reads"],
          "p50=", round(out["compact_to_wide_stream"]["read_ms_p50"], 2),
          "p95=", round(out["compact_to_wide_stream"]["read_ms_p95"], 2))
    print("  Financial 1.8M FINAL vs no-FINAL page42 med_ms:",
          round(out["financial_final_5pct"]["page42_final"]["median_ms"], 2), "vs",
          round(out["financial_final_5pct"]["page42_no_final"]["median_ms"], 2),
          "| full 1.8M FINAL med_ms:", round(out["financial_final_5pct"]["full_1_8m_final"]["median_ms"], 2))


if __name__ == "__main__":
    main()
