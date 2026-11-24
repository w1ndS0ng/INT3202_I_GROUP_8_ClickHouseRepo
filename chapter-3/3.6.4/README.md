# 3.6.4 — Tổng hợp ba thực nghiệm E1–E3 và các yếu tố hạn chế tính tin cậy

- **Phụ trách:** Tài, Hà & Tuấn
- **Mô tả:** Tổng hợp kết quả kiểm chứng xuyên suốt E1 (sorting key), E2 (granularity), E3 (batch merge) và mô hình thời gian.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`synthesize_chapter3_findings.py`](scripts/synthesize_chapter3_findings.py)
- `results/`: Chứa **1 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.6.4/scripts/synthesize_chapter3_findings.py
```
