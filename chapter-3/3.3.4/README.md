# 3.3.4 — E1 — Phân tích theo workload và trả lời RQ1

- **Phụ trách:** Hà
- **Mô tả:** Tổng hợp tỷ số cắt tỉa granule và hệ số tăng tốc (speedup so với K0) trên 30M dòng cho W0–W4.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`analyze_rq1_workload.py`](scripts/analyze_rq1_workload.py)
- `results/`: Chứa **1 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.3.4/scripts/analyze_rq1_workload.py
```
