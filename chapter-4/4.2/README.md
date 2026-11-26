# 4.2 — Thiết kế đối chứng CH0/CH1 – PG0/PG1/PG2, cấu hình và chạy thử Pilot 1M

- **Phụ trách:** Tuấn (ver1 Xeon) & Tài (ver2 Core i5)
- **Mô tả:** DDL 5 cấu hình, thiết lập thực thi 30M, cùng toàn bộ hồ sơ Pilot 1M kiểm chứng quy trình trên máy Xeon (ver1) và máy Core i5 (ver2).

## Nội dung

- **Scripts:**
  - [`run_comparison_design_and_pilot.py`](scripts/run_comparison_design_and_pilot.py)
  - [`compare_databases.py`](scripts/compare_databases.py)
- **Results:** **76 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-4/4.2/scripts/run_comparison_design_and_pilot.py
```
