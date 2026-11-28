# 5.2 — Thiết kế giải pháp luồng 3 tầng gắn với 3 điểm sáng MergeTree

- **Phụ trách:** Hà
- **Mô tả:** Sơ đồ kiến trúc luồng 3 tầng nội tại (`Kafka Engine → Streaming Materialized View → AggregatingMergeTree`, Hình 5.1) kết hợp micro-batch 500 ms (`Compact Part`), khóa `ORDER BY (page_id, minute)`, kiểu `Int64`/`uniqHLL12` và `index_granularity = 256`.

## Nội dung

- **Scripts:**
  - [`verify_5_2_architecture.py`](scripts/verify_5_2_architecture.py)
- **Results:** **1 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)):
  - [`figure_5_1_ver1.png`](results/figure_5_1_ver1.png) *(trích từ `origin/ha/sorting-key:report/fig5_1.png`, commit `3f6b6b8`)*

## Kiểm tra

```bash
python chapter-5/5.2/scripts/verify_5_2_architecture.py
```
