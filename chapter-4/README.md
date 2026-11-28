# Chương 4 — Đối chiếu MergeTree với PostgreSQL Heap + BRIN/B-tree

| Mục | Nội dung | Phụ trách | Scripts | Results |
|---|---|---|---|---|
| [`4.1`](4.1/) | Cơ sở so sánh MergeTree và PostgreSQL (Heap, BRIN, B-tree) | Tài | [`scripts/`](4.1/scripts/) | [`results/`](4.1/results/) |
| [`4.2`](4.2/) | Thiết kế đối chứng CH0/CH1 – PG0/PG1/PG2, cấu hình và chạy thử Pilot 1M | Tuấn (ver1 Xeon) & Tài (ver2 Core i5) | [`scripts/`](4.2/scripts/) | [`results/`](4.2/results/) |
| [`4.3.1`](4.3.1/) | Kết quả so sánh — Query latency theo workload (Bảng 4.3) | Tuấn | [`scripts/`](4.3.1/scripts/) | [`results/`](4.3.1/results/) |
| [`4.3.2`](4.3.2/) | Granule pruning, heap blocks và bằng chứng kế hoạch thực thi (Bảng 4.4–4.5) | Tuấn | [`scripts/`](4.3.2/scripts/) | [`results/`](4.3.2/results/) |
| [`4.3.3`](4.3.3/) | Dung lượng dữ liệu và chỉ mục (ver1: Xeon; ver2: Core i5 — Bảng 4.6) | Tài (Bảng 4.6 i5 — ver2) & Tuấn (hồ sơ Xeon đối chiếu — ver1) | [`scripts/`](4.3.3/scripts/) | [`results/`](4.3.3/results/) |
| [`4.3.4`](4.3.4/) | Chi phí nạp, tạo chỉ mục và sắp xếp vật lý / bảo trì (ver1: Xeon; ver2: Core i5 — Bảng 4.7) | Tài (Bảng 4.7 i5 — ver2) & Tuấn (hồ sơ Xeon đối chiếu — ver1) | [`scripts/`](4.3.4/scripts/) | [`results/`](4.3.4/results/) |
| [`4.4`](4.4/) | Phân tích đánh đổi giữa tốc độ truy vấn, dung lượng và chi phí chuẩn bị | Tài | [`scripts/`](4.4/scripts/) | [`results/`](4.4/results/) |
| [`4.5`](4.5/) | Kết luận đối chiếu theo từng workload và trả lời RQ5 | Tuấn | [`scripts/`](4.5/scripts/) | [`results/`](4.5/results/) |
| [`4.6`](4.6/) | Đối chứng bổ sung cùng hệ cột: ClickHouse MergeTree vs DuckDB 2.0.1 | Hà | [`scripts/`](4.6/scripts/) | [`results/`](4.6/results/) |
