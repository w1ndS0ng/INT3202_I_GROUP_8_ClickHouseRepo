# 3.6.5 — Hồ sơ tái lập và nghiệm thu Chương 3

- **Phụ trách:** Tuấn, Hà & Tài
- **Mô tả:** Danh mục mã băm SHA-256 nghiệm thu của Chương 3 theo trình tự bổ sung: E2 (ver1), E3 follow-up (ver2) và kiểm tra toàn vẹn.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`verify_chapter3_provenance.py`](scripts/verify_chapter3_provenance.py)
- `results/`: Chứa **2 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.6.5/scripts/verify_chapter3_provenance.py
```
