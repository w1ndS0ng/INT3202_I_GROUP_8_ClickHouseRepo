# 4.3.2 — Granule pruning, heap blocks và bằng chứng kế hoạch thực thi (Bảng 4.4–4.5)

- **Phụ trách:** Tuấn
- **Mô tả:** Kế hoạch EXPLAIN indexes=1 (ClickHouse) và EXPLAIN (ANALYZE, BUFFERS) (PostgreSQL), số marks, exact/lossy heap blocks và pg_stats.correlation.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`extract_4_3_2_plans.py`](scripts/extract_4_3_2_plans.py)
- `results/`: Chứa **6 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-4/4.3.2/scripts/extract_4_3_2_plans.py
```
