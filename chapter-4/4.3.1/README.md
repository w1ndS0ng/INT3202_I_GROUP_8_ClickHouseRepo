# 4.3.1 — Kết quả so sánh — Query latency theo workload (Bảng 4.3)

- **Phụ trách:** Tuấn
- **Mô tả:** Số đo gốc 250 lượt chính + 50 warmup trên 30M dòng (Xeon), nhật ký client_ms, QueryFinish, đáp án COUNT/SUM và thống kê trung vị/IQR.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`audit_4_3_1_latency.py`](scripts/audit_4_3_1_latency.py)
  - [`audit_comparison.py`](scripts/audit_comparison.py)
- `results/`: Chứa **7 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-4/4.3.1/scripts/audit_4_3_1_latency.py
```
