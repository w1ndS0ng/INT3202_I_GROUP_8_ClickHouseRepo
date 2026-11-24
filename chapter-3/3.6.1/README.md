# 3.6.1 — Mô hình ước lượng thời gian và giả định

- **Phụ trách:** Tài (ver1 E3) & Hà (ver2 SELECT E1)
- **Mô tả:** Tham số mô hình ước lượng thời gian: đối chiếu tuyến tính E3 (ver1) và mô hình T_est = alpha + beta * R_est trên 1M/3M/10M (ver2).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`fit_time_models.py`](scripts/fit_time_models.py)
  - [`compare_e3_estimate.py`](scripts/compare_e3_estimate.py)
- `results/`: Chứa **2 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.6.1/scripts/fit_time_models.py
```
