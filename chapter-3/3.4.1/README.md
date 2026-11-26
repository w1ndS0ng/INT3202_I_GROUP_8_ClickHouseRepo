# 3.4.1 — E2 — Cấu hình g2048/g8192/g32768 và kiểm chứng đối chứng

- **Phụ trách:** Tuấn
- **Mô tả:** Cấu hình, DDL và kiểm chứng 1 active Wide part + fingerprint cho pilot 1M (ver1) và thực nghiệm chính thức 30M (ver2).

## Nội dung

- **Scripts:**
  - [`run_e2_build_and_checks.py`](scripts/run_e2_build_and_checks.py)
- **Results:** **40 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.4.1/scripts/run_e2_build_and_checks.py
```
