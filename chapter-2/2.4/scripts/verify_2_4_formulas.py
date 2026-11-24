"""Verify granule & sparse primary index size formulas for Section 2.4."""
import math

def verify():
    n = 30_000_000
    for g, expected_m, expected_bytes in [(2048, 14649, 87894), (8192, 3663, 21978), (32768, 916, 5496)]:
        m = math.ceil(n / g)
        i_key = m * 6
        assert m == expected_m and i_key == expected_bytes
        print(f"g={g}: M={m} marks, I_key={i_key} bytes")

if __name__ == "__main__":
    verify()
