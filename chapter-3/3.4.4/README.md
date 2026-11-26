# 3.4.4 — E2 — Phân tích điểm cân bằng và trả lời RQ2

- **Phụ trách:** Tuấn
- **Mô tả:** Đối chiếu tỷ lệ giảm read_rows / read_bytes với mức tăng primary_key_bytes_in_memory và marks_bytes giữa g2048, g8192 và g32768.

## Nội dung

- **Scripts:**
  - [`analyze_rq2_granularity_tradeoff.py`](scripts/analyze_rq2_granularity_tradeoff.py)
- **Results:** **1 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.4.4/scripts/analyze_rq2_granularity_tradeoff.py
```
