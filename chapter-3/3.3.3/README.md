# 3.3.3 — E1 — Kết quả cắt tỉa chỉ mục, độ trễ và dung lượng lưu trữ

- **Phụ trách:** Hà
- **Mô tả:** Kế hoạch EXPLAIN indexes=1 / EXPLAIN ESTIMATE, bảng tổng hợp queries.csv, storage.csv và biểu đồ E1 ở các quy mô 1M–30M.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`summarize_and_plot_e1.py`](scripts/summarize_and_plot_e1.py)
- `results/`: Chứa **91 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.3.3/scripts/summarize_and_plot_e1.py
```
