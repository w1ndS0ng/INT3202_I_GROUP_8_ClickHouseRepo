# 3.6.3 — Kết quả estimated–actual, giải thích sai số và chẩn đoán EXPLAIN

- **Phụ trách:** Tài (ver1 E3) & Hà (ver2 SELECT E1)
- **Mô tả:** Bảng sai số dự báo APE/MAE, chẩn đoán EXPLAIN PLAN / ESTIMATE / ANALYZE trên bảng 5 parts của E3 (ver1) và kết quả holdout 30M của E1 (ver2).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`evaluate_estimated_vs_actual.py`](scripts/evaluate_estimated_vs_actual.py)
  - [`capture_explain.py`](scripts/capture_explain.py)
- `results/`: Chứa **32 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.6.3/scripts/evaluate_estimated_vs_actual.py
```
