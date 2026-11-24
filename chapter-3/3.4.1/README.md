# 3.4.1 — E2 — Cấu hình g2048/g8192/g32768 và kiểm chứng đối chứng

- **Phụ trách:** Tuấn
- **Mô tả:** Cấu hình, DDL và kiểm chứng 1 active Wide part + fingerprint cho pilot 1M (ver1) và thực nghiệm chính thức 30M (ver2).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`run_e2_build_and_checks.py`](scripts/run_e2_build_and_checks.py)
- `results/`: Chứa **40 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.4.1/scripts/run_e2_build_and_checks.py
```
