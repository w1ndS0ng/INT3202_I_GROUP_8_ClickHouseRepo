# Kết quả E3 — batch INSERT và background merge

Run: e3pilot_v2_20261117; máy wsl_i5; ClickHouse26.10.3.7; protocol mergetree-v2-e3-r1; commit 6b433b626382e80333a0d8c72cf47c1ec228e056.
Dataset 1,000,000 dòng/lượt, 12cột; 3batch×3vòng. Tổng 333request; mọi fingerprint khớp nguồn độc lập.
Thiết lập: K1(CounterID,EventDate), g8192, Wide, LZ4, fsync1, async0, insert1thread; merge tự nhiên.

| Batch | ACK trung vị (s) | ACK IQR(s) | Throughput trung vị (dòng/s) | Active storage trung vị(MiB) | Merge row amplification trung vị |
|---:|---:|---:|---:|---:|---:|
|10,000|2.906|7.588|344,148|24.229|2.590|
|100,000|2.981|1.830|335,410|24.176|0.600|
|1,000,000|1.041|0.579|960,571|24.153|0.000|

## Chi tiết9lượt

|Vòng|Vị trí|Batch|ACK(s)|Throughput(dòng/s)|Parts sauACK|Parts ổn định|Merge events|
|---:|---:|---:|---:|---:|---:|---:|---:|
|1|1|10,000|17.993|55,578|8|3|18|
|1|2|100,000|2.981|335,410|5|5|1|
|1|3|1,000,000|1.736|576,134|1|1|0|
|2|1|100,000|4.444|225,003|5|5|1|
|2|2|1,000,000|0.577|1,731,711|1|1|0|
|2|3|10,000|2.906|344,148|8|3|18|
|3|1|1,000,000|1.041|960,571|1|1|0|
|3|2|10,000|2.816|355,094|8|3|18|
|3|3|100,000|0.784|1,275,652|5|5|1|

## Giới hạn và truy vết

Median/Q1/Q3/IQR chỉ mô tả3lượt; không phải khoảng tin cậy hay kết luận nhân quả cho mọi hệ thống.
ACK elapsed gồm HTTP và xử lý input/journal giữa batch; không gồm tải mạng/chuyển Parquet hoặc thời gian producer gom batch.
Snapshot gần sauACK: độ trễ hoàn thành từ 0.0036s đến 0.0137s; không phải snapshot nguyên tử tạiACK.
Merge events được tính theo UUID bảng đến mốc server observation_end sau snapshot ổn định; tổngduration có thể chồng thời gian.
Ổn định được quan sát3lần cách10s, không có merge/mutation; không bảo đảm không phát sinh merge tương lai.
Active storage không gồm mọi inactive/tạm; merge row amplification là proxy đọc lại, không phải physical SSD write amplification.
Nguồn đã kiểm độc lập đủ30file; các workload counts30M khớp báo cáo Tuấn. Mẫu1M tự tạo có một số thống kê khác pilot trong Docs; chỉ dùng để kiểm tra pipeline E3. Chưa có curator hash-lock/code2e65b9d để khẳng định cùng chính xác bản khóa của máy E2.
Phầncứng/memory/kernel/Python thực tế trong environment.json; không dùng thời gian tuyệt đối đối chiếu máy Xeon.

Dữ liệu gốc trong ingest/, checks/, ddl/; summary/ chứa tóm tắt và figures/ chứa hình. Pilot không thay kết quả30M.
