# 4.2 — Thiết kế đối chứng CH0/CH1 – PG0/PG1/PG2, cấu hình và chạy thử Pilot 1M

- **Phụ trách:** Tuấn (ver1 Xeon) & Tài (ver2 Core i5)
- **Mô tả:** DDL 5 cấu hình, thiết lập thực thi 30M, cùng toàn bộ hồ sơ Pilot 1M kiểm chứng quy trình trên máy Xeon (ver1) và máy Core i5 (ver2).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`run_comparison_design_and_pilot.py`](scripts/run_comparison_design_and_pilot.py)
  - [`compare_databases.py`](scripts/compare_databases.py)
- `results/`: Chứa **76 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-4/4.2/scripts/run_comparison_design_and_pilot.py
```
