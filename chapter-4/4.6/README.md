# 4.6 — Đối chứng bổ sung cùng hệ cột: ClickHouse MergeTree vs DuckDB 2.0.1

- **Phụ trách:** Hà
- **Mô tả:** Đối chứng cùng hệ lưu trữ hướng cột trên `laptop1` (30M dòng ClickBench, 4 luồng, giới hạn RAM 2 GB, 2 warmup + 10 lượt xáo trộn, kiểm định Mann–Whitney U 50.000 hoán vị; tương ứng Mục 4.5 và Bảng 4.8 `tab:ch4_duckdb` trong báo cáo hoàn chỉnh):
  - **Dung lượng đĩa:** `CH1 = 498,20 MiB` gọn hơn `DUCK1 = 571,76 MiB` (`−12,9%`) và `DUCK0 = 599,26 MiB` (`−16,9%`).
  - **Độ trễ W0–W4 (`CH1 HTTP` vs `DUCK1 Sort`):** `W0` chưa có khác biệt có ý nghĩa thống kê (`27,04` vs `25,23 ms`, `p = 0,123`); DuckDB nội tiến trình thấp hơn ở `W1–W3` (không tốn `~2,6 ms` HTTP và tối ưu Zone Maps); tại `W4`, `CH1 + PROJECTION p_reg_order` (`14,39 ms`) nhanh hơn `DUCK1` (`33,13 ms`) `2,30×`.

## Nội dung

- **Scripts:**
  - [`exp_duckdb_vs_clickhouse.py`](scripts/exp_duckdb_vs_clickhouse.py) *(đồng bộ với [`scripts/exp_duckdb_vs_clickhouse.py`](../../../scripts/exp_duckdb_vs_clickhouse.py))*
  - [`verify_4_6_duckdb_comparison.py`](scripts/verify_4_6_duckdb_comparison.py) *(kiểm tra toàn vẹn SHA-256 và in tóm tắt bảng so sánh)*
- **Results:** **1 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)):
  - [`duckdb_vs_clickhouse_ver1.json`](results/duckdb_vs_clickhouse_ver1.json) *(trích từ `origin/ha/sorting-key:artifacts/addons/laptop1/duckdb_vs_clickhouse.json`, commit `3f6b6b8`)*

## Kiểm tra

```bash
python chapter-4/4.6/scripts/verify_4_6_duckdb_comparison.py
```
