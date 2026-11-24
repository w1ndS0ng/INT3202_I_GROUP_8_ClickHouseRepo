# 3.4.3 — E2 — Kết quả loại bỏ granule, thời gian truy vấn và dung lượng chỉ mục

- **Phụ trách:** Tuấn
- **Mô tả:** EXPLAIN 15 tổ hợp, bảng tổng hợp `queries.csv`, `storage.csv`, `granularity_cost.csv` và Hình E2 (`ver1`: 1M, `ver2`: 30M `v5`, `ver3`: bản vẽ lại `v6` 450 DPI với chú giải dùng chung đặt bên ngoài).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng và vẽ hình của mục này:
  - [`summarize_and_plot_e2.py`](scripts/summarize_and_plot_e2.py) (`--plot` để tái tạo hình `v6_ver3` 450 DPI từ dữ liệu `summary/`)
- `results/`: Chứa **50 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2`, `_ver3` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.4.3/scripts/summarize_and_plot_e2.py
```
