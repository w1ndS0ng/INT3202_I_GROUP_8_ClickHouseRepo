# 3.3.1 — E1 — Thiết kế đối chứng K0/K1/K2 và chuẩn bị bảng (1M, 3M, 10M, 30M)

- **Phụ trách:** Hà
- **Mô tả:** DDL thực tế, cấu hình chạy, kiểm chứng toàn vẹn fingerprint, đáp án COUNT/SUM và trạng thái 1 active part cho K0, K1, K2.

## Nội dung

- **Scripts:**
  - [`run_e1_build_and_checks.py`](scripts/run_e1_build_and_checks.py)
- **Results:** **60 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.3.1/scripts/run_e1_build_and_checks.py
```
