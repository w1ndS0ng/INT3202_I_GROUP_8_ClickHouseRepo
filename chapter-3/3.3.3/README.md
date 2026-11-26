# 3.3.3 — E1 — Kết quả cắt tỉa chỉ mục, độ trễ và dung lượng lưu trữ

- **Phụ trách:** Hà
- **Mô tả:** Kế hoạch EXPLAIN indexes=1 / EXPLAIN ESTIMATE, bảng tổng hợp queries.csv, storage.csv và biểu đồ E1 ở các quy mô 1M–30M.

## Nội dung

- **Scripts:**
  - [`summarize_and_plot_e1.py`](scripts/summarize_and_plot_e1.py)
- **Results:** **91 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.3.3/scripts/summarize_and_plot_e1.py
```
