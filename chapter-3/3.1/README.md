# 3.1 — Mục tiêu, câu hỏi nghiên cứu (RQ1–RQ5) và giả thuyết

- **Phụ trách:** Hà
- **Mô tả:** Ma trận ánh xạ 5 câu hỏi nghiên cứu (RQ1–RQ5) sang các thực nghiệm E1, E2, E3, mô hình thời gian và đối chiếu Chương 4.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`export_rq_matrix.py`](scripts/export_rq_matrix.py)
- `results/`: Chứa **1 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.1/scripts/export_rq_matrix.py
```
