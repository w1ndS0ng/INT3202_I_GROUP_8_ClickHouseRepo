# 3.6.1 — Mô hình ước lượng thời gian và giả định

- **Phụ trách:** Tài (ver1 E3) & Hà (ver2 SELECT E1)
- **Mô tả:** Tham số mô hình ước lượng thời gian: đối chiếu tuyến tính E3 (ver1) và mô hình T_est = alpha + beta * R_est trên 1M/3M/10M (ver2).

## Nội dung

- **Scripts:**
  - [`fit_time_models.py`](scripts/fit_time_models.py)
  - [`compare_e3_estimate.py`](scripts/compare_e3_estimate.py)
- **Results:** **2 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.6.1/scripts/fit_time_models.py
```
