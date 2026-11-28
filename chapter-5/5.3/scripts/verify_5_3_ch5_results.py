"""Helper verifier for chapter-5/5.3 (Kiểm chứng Compact->Wide Merge và ReplacingMergeTree FINAL)."""
import hashlib
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main():
    manifest = json.loads((RESULTS / "files.sha256.json").read_text(encoding="utf-8"))
    print("[chapter-5/5.3] Kiểm chứng Chương 5 (Compact->Wide Merge & ReplacingMergeTree FINAL)")
    for rel, expected in sorted(manifest.items()):
        path = RESULTS / rel
        if not path.is_file():
            raise SystemExit(f"Missing result file: {rel}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"SHA-256 mismatch for {rel}: {actual} != {expected}")
        print(f"  - OK {rel} ({path.stat().st_size} bytes)")

    data = json.loads((RESULTS / "ch5_compact_wide_final_ver1.json").read_text(encoding="utf-8"))
    stream = data["compact_to_wide_stream"]
    fin = data["financial_final_5pct"]
    wide_merges = [
        e for e in stream["part_log_summary"]
        if e.get("event_type") == "MergeParts" and e.get("part_type") == "Wide"
    ]
    wide_mib = wide_merges[0]["max_bytes"] / (1024 ** 2) if wide_merges else 0.0
    wide_dur_s = wide_merges[0]["sum_dur_ms"] / 1000.0 if wide_merges else 0.0
    delta_final = fin["page42_final"]["median_ms"] - fin["page42_no_final"]["median_ms"]

    print(
        f"  - Compact->Wide ({stream['concurrent_readers']} readers, {stream['total_reads']} reads): "
        f"p50={stream['read_ms_p50']:.2f} ms, p95={stream['read_ms_p95']:.2f} ms, p99={stream['read_ms_p99']:.2f} ms; "
        f"Wide merge={wide_mib:.2f} MiB in {wide_dur_s:.2f} s"
    )
    print(
        f"  - ReplacingMergeTree FINAL (1.8M -> {fin['full_1_8m_final']['ans']['count()']} unique): "
        f"page42 {fin['page42_no_final']['median_ms']:.2f} -> {fin['page42_final']['median_ms']:.2f} ms "
        f"(+{delta_final:.2f} ms); full={fin['full_1_8m_final']['median_ms']:.2f} ms"
    )


if __name__ == "__main__":
    main()
