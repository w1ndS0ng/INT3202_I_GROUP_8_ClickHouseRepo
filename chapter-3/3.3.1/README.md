# 3.3.1 — E1 — Thiết kế đối chứng K0/K1/K2 và chuẩn bị bảng (1M, 3M, 10M, 30M)

- **Phụ trách:** Hà
- **Mô tả:** DDL thực tế, cấu hình chạy, kiểm chứng toàn vẹn fingerprint, đáp án COUNT/SUM và trạng thái 1 active part cho K0, K1, K2.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`run_e1_build_and_checks.py`](scripts/run_e1_build_and_checks.py)
- `results/`: Chứa **60 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.3.1/scripts/run_e1_build_and_checks.py
```
