# 3.4.2 — E2 — Chạy đo 150 lượt và kiểm tra công thức marks / primary index

- **Phụ trách:** Tuấn
- **Mô tả:** Thời gian nạp/OPTIMIZE chuẩn bị, câu lệnh SQL, nhật ký 150 lượt đo và kiểm chứng công thức M_est, I_key_est (ver1: 1M, ver2: 30M).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`run_e2_queries_and_formulas.py`](scripts/run_e2_queries_and_formulas.py)
- `results/`: Chứa **48 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.4.2/scripts/run_e2_queries_and_formulas.py
```
