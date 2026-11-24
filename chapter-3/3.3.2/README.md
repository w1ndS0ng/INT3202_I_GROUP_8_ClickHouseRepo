# 3.3.2 — E1 — Quy trình thực thi truy vấn và thu thập nhật ký (1M, 3M, 10M, 30M)

- **Phụ trách:** Hà
- **Mô tả:** Thời gian nạp/OPTIMIZE chuẩn bị (setup), câu lệnh SQL từng tổ hợp và nhật ký thực thi 150 lượt đo mỗi quy mô (tổng 600 lượt chính).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`run_e1_queries.py`](scripts/run_e1_queries.py)
- `results/`: Chứa **84 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.3.2/scripts/run_e1_queries.py
```
