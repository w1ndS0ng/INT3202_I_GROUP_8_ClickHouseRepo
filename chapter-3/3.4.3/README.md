# 3.4.3 — E2 — Kết quả loại bỏ granule, thời gian truy vấn và dung lượng chỉ mục

- **Phụ trách:** Tuấn
- **Mô tả:** EXPLAIN 15 tổ hợp, bảng tổng hợp `queries.csv`, `storage.csv`, `granularity_cost.csv` và Hình E2 (`ver1`: 1M, `ver2`: 30M `v5`, `ver3`: `v6` 450 DPI chú giải dùng chung bên ngoài, `ver4`: `v7` 450 DPI với trục tung ngắt đoạn và thanh chặn `Q1–Q3` có nắp ngang).

## Nội dung

- **Scripts:**
  - [`summarize_and_plot_e2.py`](scripts/summarize_and_plot_e2.py) (`--plot` để tái tạo hình `v7_ver4` 450 DPI từ dữ liệu `summary/`)
- **Results:** **54 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.4.3/scripts/summarize_and_plot_e2.py
```
