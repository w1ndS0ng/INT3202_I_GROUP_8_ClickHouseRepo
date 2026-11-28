"""Helper verifier for chapter-5/5.4 (Kiến trúc lai PostgreSQL-ClickHouse và ranh giới áp dụng)."""
import hashlib
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main():
    manifest = json.loads((RESULTS / "files.sha256.json").read_text(encoding="utf-8"))
    print("[chapter-5/5.4] Kiến trúc lai PostgreSQL-ClickHouse và ranh giới áp dụng")
    for rel, expected in sorted(manifest.items()):
        path = RESULTS / rel
        if not path.is_file():
            raise SystemExit(f"Missing result file: {rel}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"SHA-256 mismatch for {rel}: {actual} != {expected}")
        print(f"  - OK {rel} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
