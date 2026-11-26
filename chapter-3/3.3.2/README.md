# 3.3.2 — E1 — Quy trình thực thi truy vấn và thu thập nhật ký (1M, 3M, 10M, 30M)

- **Phụ trách:** Hà
- **Mô tả:** Thời gian nạp/OPTIMIZE chuẩn bị (setup), câu lệnh SQL từng tổ hợp và nhật ký thực thi 150 lượt đo mỗi quy mô (tổng 600 lượt chính).

## Nội dung

- **Scripts:**
  - [`run_e1_queries.py`](scripts/run_e1_queries.py)
- **Results:** **84 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.3.2/scripts/run_e1_queries.py
```
