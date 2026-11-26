# 4.1 — Cơ sở so sánh MergeTree và PostgreSQL (Heap, BRIN, B-tree)

- **Phụ trách:** Tài
- **Mô tả:** Định nghĩa cấu trúc bảng/chỉ mục thực tế của ClickHouse MergeTree (CH0, CH1) và PostgreSQL 18.6 Heap + BRIN/B-tree (PG0, PG1, PG2).

## Nội dung

- **Scripts:**
  - [`inspect_storage_and_index_defs.py`](scripts/inspect_storage_and_index_defs.py)
- **Results:** **1 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-4/4.1/scripts/inspect_storage_and_index_defs.py
```
