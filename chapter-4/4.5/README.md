# 4.5 — Kết luận đối chiếu theo từng workload và trả lời RQ5

- **Phụ trách:** Tuấn
- **Mô tả:** Bảng tổng hợp báo cáo Chương 4 (report_tables), kết quả kiểm toán độc lập (audit.json), xác nhận PASS_FORMAL và danh mục SHA-256.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`verify_4_5_conclusions.py`](scripts/verify_4_5_conclusions.py)
- `results/`: Chứa **4 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-4/4.5/scripts/verify_4_5_conclusions.py
```
