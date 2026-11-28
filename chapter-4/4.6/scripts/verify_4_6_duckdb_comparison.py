"""Helper verifier for chapter-4/4.6 (Đối chứng cùng hệ cột ClickHouse vs DuckDB 2.0.1)."""
import hashlib
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main():
    manifest = json.loads((RESULTS / "files.sha256.json").read_text(encoding="utf-8"))
    print("[chapter-4/4.6] Đối chứng cùng hệ cột: ClickHouse MergeTree vs DuckDB 2.0.1")
    for rel, expected in sorted(manifest.items()):
        path = RESULTS / rel
        if not path.is_file():
            raise SystemExit(f"Missing result file: {rel}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"SHA-256 mismatch for {rel}: {actual} != {expected}")
        print(f"  - OK {rel} ({path.stat().st_size} bytes)")

    data = json.loads((RESULTS / "duckdb_vs_clickhouse_ver1.json").read_text(encoding="utf-8"))
    sb = data["storage_bytes"]
    ch1_mib = sb["CH1"] / (1024 ** 2)
    d1_mib = sb["DUCK1"] / (1024 ** 2)
    d0_mib = sb["DUCK0"] / (1024 ** 2)
    print(
        f"  - DuckDB {data['duckdb_version']} storage: CH1={ch1_mib:.2f} MiB, "
        f"DUCK1={d1_mib:.2f} MiB (CH1 -{(1 - ch1_mib/d1_mib)*100:.1f}%), "
        f"DUCK0={d0_mib:.2f} MiB (CH1 -{(1 - ch1_mib/d0_mib)*100:.1f}%)"
    )
    mwu_map = {m["case"]: m for m in data["mann_whitney_u"]}
    for row in data["summary"]:
        c = row["case"]
        p_val = mwu_map[c]["ch1_vs_duck1_p"]
        print(
            f"  - {c.upper()}: CH1={row['CH1']['median']:.2f} ms (srv={row['CH1_server']['median']:.1f} ms) "
            f"vs DUCK1={row['DUCK1']['median']:.2f} ms | MWU p={p_val:.5f}"
        )


if __name__ == "__main__":
    main()
