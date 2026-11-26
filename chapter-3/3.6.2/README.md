# 3.6.2 — Đóng băng dự đoán và kiểm chứng holdout

- **Phụ trách:** Tài (ver1 E3) & Hà (ver2 SELECT E1)
- **Mô tả:** Hồ sơ đối chiếu khả năng so sánh pilot 1M – 30M của E3 (ver1) và tệp dự đoán đóng băng forecast.json trước khi chạy holdout 30M của E1 (ver2).

## Nội dung

- **Scripts:**
  - [`freeze_and_verify_forecast.py`](scripts/freeze_and_verify_forecast.py)
- **Results:** **4 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.6.2/scripts/freeze_and_verify_forecast.py
```
