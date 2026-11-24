# 4.4 — Phân tích đánh đổi giữa tốc độ truy vấn, dung lượng và chi phí chuẩn bị

- **Phụ trách:** Tài
- **Mô tả:** Tổng hợp đa chiều đặt độ trễ (W0–W4), dung lượng lưu trữ/chỉ mục và chi phí chuẩn bị cạnh nhau để phân tích đánh đổi.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`synthesize_4_4_tradeoffs.py`](scripts/synthesize_4_4_tradeoffs.py)
  - [`analysis_audit_comparison_ver1.py`](scripts/analysis_audit_comparison_ver1.py)
- `results/`: Chứa **1 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-4/4.4/scripts/synthesize_4_4_tradeoffs.py
```
