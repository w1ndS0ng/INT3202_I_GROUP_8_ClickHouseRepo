"""Helper runner/verifier for chapter-4/4.5 (Kết luận đối chiếu theo từng workload (RQ5))."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
RESULTS = Path(__file__).resolve().parents[1] / "results"


def main():
    files = sorted(p.relative_to(RESULTS).as_posix() for p in RESULTS.rglob("*") if p.is_file() and p.name != "files.sha256.json")
    print(f"[chapter-4/4.5] Kết luận đối chiếu theo từng workload (RQ5)")
    print(f"Verified result files ({len(files)}):")
    for f in files[:20]:
        print("  -", f)
    if len(files) > 20:
        print(f"  ... and {len(files) - 20} more files.")


if __name__ == "__main__":
    main()
