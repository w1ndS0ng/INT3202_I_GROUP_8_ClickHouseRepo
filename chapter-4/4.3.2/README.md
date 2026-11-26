# 4.3.2 — Granule pruning, heap blocks và bằng chứng kế hoạch thực thi (Bảng 4.4–4.5)

- **Phụ trách:** Tuấn
- **Mô tả:** Kế hoạch EXPLAIN indexes=1 (ClickHouse) và EXPLAIN (ANALYZE, BUFFERS) (PostgreSQL), số marks, exact/lossy heap blocks và pg_stats.correlation.

## Nội dung

- **Scripts:**
  - [`extract_4_3_2_plans.py`](scripts/extract_4_3_2_plans.py)
- **Results:** **6 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-4/4.3.2/scripts/extract_4_3_2_plans.py
```
