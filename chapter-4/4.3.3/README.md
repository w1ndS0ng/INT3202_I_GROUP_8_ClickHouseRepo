# 4.3.3 — Dung lượng dữ liệu và chỉ mục (ver1: Xeon; ver2: Core i5 — Bảng 4.6)

- **Phụ trách:** Tài (Bảng 4.6 i5 — ver2) & Tuấn (hồ sơ Xeon đối chiếu — ver1)
- **Mô tả:** Số đo dung lượng bảng nén, marks, chỉ mục trên đĩa và RAM cho 5 cấu hình trên máy Xeon (ver1) và máy Core i5 (ver2).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`compare_4_3_3_storage.py`](scripts/compare_4_3_3_storage.py)
- `results/`: Chứa **7 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-4/4.3.3/scripts/compare_4_3_3_storage.py
```
