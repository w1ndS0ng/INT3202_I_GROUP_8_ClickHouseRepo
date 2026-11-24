# 3.5.1 — E3 — Đối chứng lô 10k/100k/1M và chuẩn bị dữ liệu nạp

- **Phụ trách:** Tài
- **Mô tả:** Cấu hình E3, môi trường máy Core i5-11400H (5,65 GiB RAM), pilot 1M (ver1) và cấu hình 3 đợt chạy chính thức 30M (ver2).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`prepare_e3_configs.py`](scripts/prepare_e3_configs.py)
- `results/`: Chứa **18 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.5.1/scripts/prepare_e3_configs.py
```
