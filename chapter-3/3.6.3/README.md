# 3.6.3 — Kết quả estimated–actual, giải thích sai số và chẩn đoán EXPLAIN

- **Phụ trách:** Tài (ver1 E3) & Hà (ver2 SELECT E1)
- **Mô tả:** Bảng sai số dự báo APE/MAE, chẩn đoán EXPLAIN PLAN / ESTIMATE / ANALYZE trên bảng 5 parts của E3 (ver1) và kết quả holdout 30M của E1 (ver2).

## Nội dung

- **Scripts:**
  - [`evaluate_estimated_vs_actual.py`](scripts/evaluate_estimated_vs_actual.py)
  - [`capture_explain.py`](scripts/capture_explain.py)
- **Results:** **32 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.6.3/scripts/evaluate_estimated_vs_actual.py
```
