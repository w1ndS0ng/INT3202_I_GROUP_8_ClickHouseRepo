# 3.4.3 — E2 — Kết quả loại bỏ granule, thời gian truy vấn và dung lượng chỉ mục

- **Phụ trách:** Tuấn
- **Mô tả:** EXPLAIN 15 tổ hợp, bảng tổng hợp queries.csv, storage.csv, granularity_cost.csv và Hình 3.1 v5 (ver1: 1M, ver2: 30M).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`summarize_and_plot_e2.py`](scripts/summarize_and_plot_e2.py)
- `results/`: Chứa **46 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.4.3/scripts/summarize_and_plot_e2.py
```
