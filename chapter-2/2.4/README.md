# 2.4 — Granules, marks và quá trình đọc có chọn lọc

- **Phụ trách:** Tuấn
- **Mô tả:** Minh họa đánh đổi granule nhỏ (g=2) và granule lớn (g=8) cùng kiểm chứng công thức M = ceil(N/g), I_key = M * 6 byte.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`verify_2_4_formulas.py`](scripts/verify_2_4_formulas.py)
- `results/`: Chứa **2 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-2/2.4/scripts/verify_2_4_formulas.py
```
