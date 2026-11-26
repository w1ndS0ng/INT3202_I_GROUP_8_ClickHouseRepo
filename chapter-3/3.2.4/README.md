# 3.2.4 — Quy trình lặp, tính đúng đắn, cửa sổ ổn định và tái lập

- **Phụ trách:** Tuấn
- **Mô tả:** Kiểm chứng lịch đảo thứ tự (seed 20261116), cửa sổ ổn định 3x10s, kiểm tra bắt lỗi journal có chủ đích và baseline pilot 1M.

## Nội dung

- **Scripts:**
  - [`verify_repeat_and_stability.py`](scripts/verify_repeat_and_stability.py)
  - [`smoke_test.py`](scripts/smoke_test.py)
- **Results:** **16 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.2.4/scripts/verify_repeat_and_stability.py
```
