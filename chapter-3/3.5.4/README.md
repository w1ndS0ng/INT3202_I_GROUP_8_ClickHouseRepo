# 3.5.4 — E3 — Phân tích kết quả, quy luật lợi ích giảm dần và trả lời RQ3

- **Phụ trách:** Tài
- **Mô tả:** Báo cáo phân tích kết quả E3 qua các phiên bản (ver1: 1 đợt; ver2: trung bình 3 đợt) và tài liệu hướng dẫn chạy E3.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`analyze_rq3_batch_merge.py`](scripts/analyze_rq3_batch_merge.py)
- `results/`: Chứa **3 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.5.4/scripts/analyze_rq3_batch_merge.py
```
