# 4.3.1 — Kết quả so sánh — Query latency theo workload (Bảng 4.3)

- **Phụ trách:** Tuấn
- **Mô tả:** Số đo gốc 250 lượt chính + 50 warmup trên 30M dòng (Xeon), nhật ký client_ms, QueryFinish, đáp án COUNT/SUM và thống kê trung vị/IQR.

## Nội dung

- **Scripts:**
  - [`audit_4_3_1_latency.py`](scripts/audit_4_3_1_latency.py)
  - [`audit_comparison.py`](scripts/audit_comparison.py)
- **Results:** **7 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-4/4.3.1/scripts/audit_4_3_1_latency.py
```
