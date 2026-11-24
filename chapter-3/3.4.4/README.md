# 3.4.4 — E2 — Phân tích điểm cân bằng và trả lời RQ2

- **Phụ trách:** Tuấn
- **Mô tả:** Đối chiếu tỷ lệ giảm read_rows / read_bytes với mức tăng primary_key_bytes_in_memory và marks_bytes giữa g2048, g8192 và g32768.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`analyze_rq2_granularity_tradeoff.py`](scripts/analyze_rq2_granularity_tradeoff.py)
- `results/`: Chứa **1 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.4.4/scripts/analyze_rq2_granularity_tradeoff.py
```
