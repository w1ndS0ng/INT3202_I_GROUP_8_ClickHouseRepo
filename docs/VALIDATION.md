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
- Bước chuẩn bị đã xác minh10shard cũ và một shard bổ sung. Tải đủ30shard, khóa manifest
  và chạy pilot1M với literals hiện tại là cổng bắt buộc trước formal run; chưa gọi các kết quả
  synthetic hoặc thao tác cài đặt là kết quả nghiên cứu30M.

Ngày bàn giao16/11/2026. Chưa chạy benchmark chính thức30M trên ba máy; độ ổn định/tài nguyên
và thời gian chạy thực tế phải được pilot xác minh. Kết quả plot/package được kiểm tra riêng
trên smoke run; không đẩy smoke CSV thành số liệu report.
