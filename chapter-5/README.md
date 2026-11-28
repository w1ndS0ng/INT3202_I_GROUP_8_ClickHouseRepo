# Chương 5 — Case Study nâng cao: Xử lý Clickstream thời gian thực bằng MergeTree

Tích hợp từ nhánh `origin/ha/sorting-key` (commit `3f6b6b8`) theo cấu trúc theo chương/tiểu mục của nhánh `main`.

| Mục | Nội dung | Phụ trách | Scripts | Results |
|---|---|---|---|---|
| [`5.2`](5.2/) | Thiết kế giải pháp luồng 3 tầng gắn với 3 cơ chế MergeTree (Hình 5.1) | Hà | [`scripts/`](5.2/scripts/) | [`results/`](5.2/results/) |
| [`5.3`](5.3/) | Kiểm chứng PoC: Chuyển đổi Compact → Wide song song 16 luồng đọc, `ReplacingMergeTree FINAL` 5% tài chính và Hình 5.2 | Hà | [`scripts/`](5.3/scripts/) | [`results/`](5.3/results/) |
| [`5.4`](5.4/) | Kiến trúc lai PostgreSQL–ClickHouse và ranh giới áp dụng (Hình 5.3) | Hà | [`scripts/`](5.4/scripts/) | [`results/`](5.4/results/) |

> **Ghi chú phạm vi hồ sơ tái lập:** Nhánh `origin/ha/sorting-key` hiện cung cấp đầy đủ log JSON thô và kịch bản tái lập cho kiểm chứng **Compact → Wide Merge (77,57 MiB song song 16 luồng đọc)** và **`ReplacingMergeTree FINAL` trên 5% luồng tài chính (1,8M dòng)** ([`ch5_compact_wide_final_ver1.json`](5.3/results/ch5_compact_wide_final_ver1.json)), kèm 3 hình chính thức (`figure_5_1_ver1.png`–`figure_5_3_ver1.png`). Log JSON/CSV thô của giai đoạn PoC 36M sơ bộ (Bảng `tab:ch5_36m`, `tab:ch5_concurrent`, `tab:ch5_stream`, `tab:ch5_columns`) chưa được đẩy lên nhánh `origin/ha/sorting-key` và có thể bổ sung trực tiếp vào `5.3/results/` với hậu tố `_ver2` khi có sẵn.
