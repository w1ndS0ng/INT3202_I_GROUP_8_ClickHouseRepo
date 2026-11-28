"""Helper verifier for chapter-3/3.6.6 (Skipping Index, Projection và External Spill)."""
import hashlib
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main():
    manifest = json.loads((RESULTS / "files.sha256.json").read_text(encoding="utf-8"))
    print("[chapter-3/3.6.6] Lọc ngoài khóa W4 (Skipping Index, Projection) & External Spill")
    for rel, expected in sorted(manifest.items()):
        path = RESULTS / rel
        if not path.is_file():
            raise SystemExit(f"Missing result file: {rel}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"SHA-256 mismatch for {rel}: {actual} != {expected}")
        print(f"  - OK {rel} ({path.stat().st_size} bytes)")

    data = json.loads((RESULTS / "mergetree_features_ver1.json").read_text(encoding="utf-8"))
    for row in data["w4_variants"]:
        print(
            f"  - {row['label']:18s}: med={row['client_ms']['median']:.2f} ms, "
            f"read_rows={int(row['read_rows_median']):,}"
        )
    guard = data["memory_spill"]["guard"]
    spill = data["memory_spill"]["spill"]
    ext = spill["external_events"]
    print(
        f"  - Memory Guard blocked={guard['blocked']} | External Spill: {spill['client_ms']:.1f} ms, "
        f"peak RAM={spill['memory_usage_bytes'] / (1024**2):.1f} MiB, "
        f"parts={ext['ExternalAggregationWritePart']}, "
        f"compressed={ext['ExternalAggregationCompressedBytes'] / 1e6:.1f} MB"
    )


if __name__ == "__main__":
    main()
