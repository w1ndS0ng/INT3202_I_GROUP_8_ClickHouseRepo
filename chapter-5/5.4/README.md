# 5.4 — Kiến trúc lai PostgreSQL–ClickHouse và ranh giới áp dụng

- **Phụ trách:** Hà
- **Mô tả:** Sơ đồ kiến trúc lai đề xuất (`PostgreSQL → Debezium CDC → Kafka → ClickHouse`, Hình 5.3) cùng ranh giới phân tách giữa phần đã kiểm chứng trên 1 nút WSL2 và phần mở rộng đa máy đề xuất.

## Nội dung

- **Scripts:**
  - [`verify_5_4_hybrid_architecture.py`](scripts/verify_5_4_hybrid_architecture.py)
- **Results:** **1 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)):
  - [`figure_5_3_ver1.png`](results/figure_5_3_ver1.png) *(trích từ `origin/ha/sorting-key:report/fig5_3.png`, commit `3f6b6b8`)*

## Kiểm tra

```bash
python chapter-5/5.4/scripts/verify_5_4_hybrid_architecture.py
```
