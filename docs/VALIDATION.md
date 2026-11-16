# Kiểm tra trước bàn giao

- Unit tests: chia batch giữ đúng byte/thứ tự qua ranh giới file; mẫu hệ thống lồng nhau;
  fit hồi phục được α/β đã biết, không sinh thời gian âm khi dữ liệu không phù hợp;
  phát hiện trường hợp không đủ biến thiên để fit; kiểm tra schema44byte/dòng.
- Integration trên ClickHouse26.10.3.7: pipeline keys ở4scale, fit→forecast→holdout,
  granularity3cấu hình, ingestion9case, correctness và summary. Dữ liệu synthetic tối đa
  30.000dòng, marker SMOKE_ONLY; các nhãn1m/30m chỉ là test label trong smoke test.
- Dữ liệu thật: chuyển shard0 đủ1.000.000dòng, fingerprint12cột của Parquet và RowBinary
  khớp; kiểm tra định dạng Date/DateTime và độ rộng44byte. Shard0 chỉ có một ngày và các
  literal3258/225 không xuất hiện, nên calibration dùng mẫu rải trên cả30shard, không lấy
  các shard đầu làm sample. Runner kiểm tra workload không rỗng trước measured queries.
- Dữ liệu dùng cho E2 của Tuấn gồm đủ 30 shard tải ngày 16/11/2026. SHA-256 của
  Parquet, RowBinary và ba mẫu lồng nhau khớp bản kê đã khóa; tổng cộng 30M dòng,
  12 cột, 44 byte/dòng. Các tệp synthetic không được dùng làm kết quả báo cáo.

## Rà soát E2 của Tuấn ngày 17/11/2026

Run pilot `e2pilot_v2_20261117` và run chính `e2main_v2_20261117` sử dụng protocol
`mergetree-v2`. Run chính có ba bảng 30M dòng, khóa K1, LZ4 và một active Wide part;
DDL chỉ khác `index_granularity`. Mã nguồn đo ở commit `2e65b9d`; mã xuất Hình 3.1
ở commit `c47338a`. Không sử dụng số đo pilot thay cho kết quả chính thức.

Đợt rà soát đã thực hiện:

- Kiểm lại checksum của 30 Parquet, 30 RowBinary và ba mẫu; đối chiếu từng byte mẫu
  với quy tắc vị trí toàn cục modulo 30 trên đủ 30M dòng. Tính lại phân bố ngày,
  CounterID và RegionID ở cả bốn quy mô, cùng sai lệch tỷ trọng lấy mẫu.
- Kiểm tra trực tiếp ba bảng E2: part, fingerprint và DDL khớp hồ sơ đã lưu;
  20 thiết lập truy vấn có hiệu lực khớp protocol.
- Đối chiếu đủ 150 lượt đo và 30 warmup của từng run pilot/chính với lịch seed;
  150 QueryFinish mỗi run khớp query_id và các chỉ số. Tính lại độc lập trung vị,
  Q1, Q3 và IQR; các giá trị số trong bảng kết quả khớp CSV ở độ làm tròn công bố.
- Kiểm tra trace ổn định, phép thử lưu journal lỗi, chỉ số nạp pilot và hồ sơ gói
  kết quả. Lỗi thiếu matplotlib khi xuất hình đã được khắc phục; nhật ký vẫn được giữ.
- Chạy lại `python -m unittest discover -s tests -v`: cả 5 test đạt. Việc kiểm tra
  báo cáo không tạo thêm lượt benchmark hoặc sửa số đo gốc.

Bản báo cáo và hồ sơ đã rà soát nằm tại
[`artifacts/tuan/wsl_xeon/e2main_v2_20261117/`](../artifacts/tuan/wsl_xeon/e2main_v2_20261117/).
T32-15 còn bước tái lập ít nhất một cặp đối chứng trên máy thứ hai. Trạng thái review
độc lập là **chưa thực hiện**; kiểm tra nội bộ không thay thế bước này. Tài liệu này
không xác nhận đã hoàn tất E1, E3 hoặc benchmark chính thức trên cả ba máy.
