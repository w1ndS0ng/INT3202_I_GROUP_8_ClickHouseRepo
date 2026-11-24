# 4.1 — Cơ sở so sánh MergeTree và PostgreSQL (Heap, BRIN, B-tree)

- **Phụ trách:** Tài
- **Mô tả:** Định nghĩa cấu trúc bảng/chỉ mục thực tế của ClickHouse MergeTree (CH0, CH1) và PostgreSQL 18.6 Heap + BRIN/B-tree (PG0, PG1, PG2).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`inspect_storage_and_index_defs.py`](scripts/inspect_storage_and_index_defs.py)
- `results/`: Chứa **1 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-4/4.1/scripts/inspect_storage_and_index_defs.py
```
