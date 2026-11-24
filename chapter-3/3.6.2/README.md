# 3.6.2 — Đóng băng dự đoán và kiểm chứng holdout

- **Phụ trách:** Tài (ver1 E3) & Hà (ver2 SELECT E1)
- **Mô tả:** Hồ sơ đối chiếu khả năng so sánh pilot 1M – 30M của E3 (ver1) và tệp dự đoán đóng băng forecast.json trước khi chạy holdout 30M của E1 (ver2).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`freeze_and_verify_forecast.py`](scripts/freeze_and_verify_forecast.py)
- `results/`: Chứa **4 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.6.2/scripts/freeze_and_verify_forecast.py
```
