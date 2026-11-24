# Chương 3 — Thực nghiệm và đánh giá MergeTree (E1, E2, E3 & Time Model)

| Mục | Nội dung | Phụ trách | Scripts | Results |
|---|---|---|---|---|
| [`3.1`](3.1/) | Mục tiêu, câu hỏi nghiên cứu (RQ1–RQ5) và giả thuyết | Hà | [`scripts/`](3.1/scripts/) | [`results/`](3.1/results/) |
| [`3.2.1`](3.2.1/) | Nguồn dữ liệu, schema 12 cột, lấy mẫu hệ thống và khóa snapshot 30M | Tuấn (ver1) & Tài (ver2 đối chiếu nguồn E3) | [`scripts/`](3.2.1/scripts/) | [`results/`](3.2.1/results/) |
| [`3.2.2`](3.2.2/) | Môi trường phần cứng, phần mềm và các biến giữ cố định | Tuấn | [`scripts/`](3.2.2/scripts/) | [`results/`](3.2.2/results/) |
| [`3.2.3`](3.2.3/) | Bộ truy vấn W0–W4 và các chỉ số đo lường | Tuấn | [`scripts/`](3.2.3/scripts/) | [`results/`](3.2.3/results/) |
| [`3.2.4`](3.2.4/) | Quy trình lặp, tính đúng đắn, cửa sổ ổn định và tái lập | Tuấn | [`scripts/`](3.2.4/scripts/) | [`results/`](3.2.4/results/) |
| [`3.3.1`](3.3.1/) | E1 — Thiết kế đối chứng K0/K1/K2 và chuẩn bị bảng (1M, 3M, 10M, 30M) | Hà | [`scripts/`](3.3.1/scripts/) | [`results/`](3.3.1/results/) |
| [`3.3.2`](3.3.2/) | E1 — Quy trình thực thi truy vấn và thu thập nhật ký (1M, 3M, 10M, 30M) | Hà | [`scripts/`](3.3.2/scripts/) | [`results/`](3.3.2/results/) |
| [`3.3.3`](3.3.3/) | E1 — Kết quả cắt tỉa chỉ mục, độ trễ và dung lượng lưu trữ | Hà | [`scripts/`](3.3.3/scripts/) | [`results/`](3.3.3/results/) |
| [`3.3.4`](3.3.4/) | E1 — Phân tích theo workload và trả lời RQ1 | Hà | [`scripts/`](3.3.4/scripts/) | [`results/`](3.3.4/results/) |
| [`3.4.1`](3.4.1/) | E2 — Cấu hình g2048/g8192/g32768 và kiểm chứng đối chứng | Tuấn | [`scripts/`](3.4.1/scripts/) | [`results/`](3.4.1/results/) |
| [`3.4.2`](3.4.2/) | E2 — Chạy đo 150 lượt và kiểm tra công thức marks / primary index | Tuấn | [`scripts/`](3.4.2/scripts/) | [`results/`](3.4.2/results/) |
| [`3.4.3`](3.4.3/) | E2 — Kết quả loại bỏ granule, thời gian truy vấn và dung lượng chỉ mục | Tuấn | [`scripts/`](3.4.3/scripts/) | [`results/`](3.4.3/results/) |
| [`3.4.4`](3.4.4/) | E2 — Phân tích điểm cân bằng và trả lời RQ2 | Tuấn | [`scripts/`](3.4.4/scripts/) | [`results/`](3.4.4/results/) |
| [`3.5.1`](3.5.1/) | E3 — Đối chứng lô 10k/100k/1M và chuẩn bị dữ liệu nạp | Tài | [`scripts/`](3.5.1/scripts/) | [`results/`](3.5.1/results/) |
| [`3.5.2`](3.5.2/) | E3 — Đo thời gian ACK, số parts và công việc background merge | Tài | [`scripts/`](3.5.2/scripts/) | [`results/`](3.5.2/results/) |
| [`3.5.3`](3.5.3/) | E3 — Kết quả thông lượng nạp, timeline số part và dung lượng | Tài | [`scripts/`](3.5.3/scripts/) | [`results/`](3.5.3/results/) |
| [`3.5.4`](3.5.4/) | E3 — Phân tích kết quả, quy luật lợi ích giảm dần và trả lời RQ3 | Tài | [`scripts/`](3.5.4/scripts/) | [`results/`](3.5.4/results/) |
| [`3.6.1`](3.6.1/) | Mô hình ước lượng thời gian và giả định | Tài (ver1 E3) & Hà (ver2 SELECT E1) | [`scripts/`](3.6.1/scripts/) | [`results/`](3.6.1/results/) |
| [`3.6.2`](3.6.2/) | Đóng băng dự đoán và kiểm chứng holdout | Tài (ver1 E3) & Hà (ver2 SELECT E1) | [`scripts/`](3.6.2/scripts/) | [`results/`](3.6.2/results/) |
| [`3.6.3`](3.6.3/) | Kết quả estimated–actual, giải thích sai số và chẩn đoán EXPLAIN | Tài (ver1 E3) & Hà (ver2 SELECT E1) | [`scripts/`](3.6.3/scripts/) | [`results/`](3.6.3/results/) |
| [`3.6.4`](3.6.4/) | Tổng hợp ba thực nghiệm E1–E3 và các yếu tố hạn chế tính tin cậy | Tài, Hà & Tuấn | [`scripts/`](3.6.4/scripts/) | [`results/`](3.6.4/results/) |
| [`3.6.5`](3.6.5/) | Hồ sơ tái lập và nghiệm thu Chương 3 | Tuấn, Hà & Tài | [`scripts/`](3.6.5/scripts/) | [`results/`](3.6.5/results/) |
