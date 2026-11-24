# 3.5.3 — E3 — Kết quả thông lượng nạp, timeline số part và dung lượng

- **Phụ trách:** Tài
- **Mô tả:** Bảng tổng hợp trung bình/phân vị theo cỡ lô và biểu đồ timeline số active parts (ver1: 1 đợt 9 lượt; ver2: 3 đợt 27 lượt).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`summarize_and_plot_e3.py`](scripts/summarize_and_plot_e3.py)
- `results/`: Chứa **87 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.5.3/scripts/summarize_and_plot_e3.py
```
