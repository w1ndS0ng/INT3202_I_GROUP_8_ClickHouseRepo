# 3.2.4 — Quy trình lặp, tính đúng đắn, cửa sổ ổn định và tái lập

- **Phụ trách:** Tuấn
- **Mô tả:** Kiểm chứng lịch đảo thứ tự (seed 20261116), cửa sổ ổn định 3x10s, kiểm tra bắt lỗi journal có chủ đích và baseline pilot 1M.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`verify_repeat_and_stability.py`](scripts/verify_repeat_and_stability.py)
  - [`smoke_test.py`](scripts/smoke_test.py)
- `results/`: Chứa **16 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.2.4/scripts/verify_repeat_and_stability.py
```
