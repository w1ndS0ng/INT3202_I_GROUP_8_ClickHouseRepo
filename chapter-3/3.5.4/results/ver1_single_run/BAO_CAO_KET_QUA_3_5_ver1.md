# Kết quả E3 — batch INSERT và background merge

Run: e3main_v2_20261117; máy wsl_i5; ClickHouse26.10.3.7; protocol mergetree-v2-e3-r1; commit 0c360382b07c584f11957782079b144cee13cb75.
Dataset 30,000,000 dòng/lượt, 12cột; 3batch×3vòng. Tổng 9,990request; mọi fingerprint khớp nguồn độc lập.
Thiết lập: K1(CounterID,EventDate), g8192, Wide, LZ4, fsync1, async0, insert1thread; merge tự nhiên.

| Batch | ACK trung vị (s) | ACK IQR(s) | Throughput trung vị (dòng/s) | Active storage trung vị(MiB) | Merge row amplification trung vị |
|---:|---:|---:|---:|---:|---:|
|10,000|317.246|74.879|94,564|498.834|4.511|
|100,000|86.051|35.711|348,631|499.763|2.483|
|1,000,000|48.053|22.686|624,316|499.949|1.000|

## Chi tiết9lượt

|Vòng|Vị trí|Batch|ACK(s)|Throughput(dòng/s)|Parts sauACK|Parts ổn định|Merge events|
|---:|---:|---:|---:|---:|---:|---:|---:|
|1|1|10,000|196.162|152,935|10|10|604|
|1|2|100,000|57.543|521,351|9|9|55|
|1|3|1,000,000|74.411|403,167|10|5|5|
|2|1|100,000|128.966|232,620|9|9|55|
|2|2|1,000,000|48.053|624,316|10|5|5|
|2|3|10,000|317.246|94,564|12|12|610|
|3|1|1,000,000|29.038|1,033,122|10|5|5|
|3|2|10,000|345.919|86,726|11|11|608|
|3|3|100,000|86.051|348,631|9|9|55|

## Giới hạn và truy vết

Median/Q1/Q3/IQR chỉ mô tả3lượt; không phải khoảng tin cậy hay kết luận nhân quả cho mọi hệ thống.
ACK elapsed gồm HTTP và xử lý input/journal giữa batch; không gồm tải mạng/chuyển Parquet hoặc thời gian producer gom batch.
Snapshot gần sauACK: độ trễ hoàn thành từ 0.0073s đến 0.1444s; không phải snapshot nguyên tử tạiACK.
Merge events được tính theo UUID bảng đến mốc server observation_end sau snapshot ổn định; tổngduration có thể chồng thời gian.
Ổn định được quan sát3lần cách10s, không có merge/mutation; không bảo đảm không phát sinh merge tương lai.
Active storage không gồm mọi inactive/tạm; merge row amplification là proxy đọc lại, không phải physical SSD write amplification.
Nguồn đã kiểm độc lập đủ30file; các workload counts30M khớp báo cáo Tuấn. Mẫu1M tự tạo có một số thống kê khác pilot trong Docs; chỉ dùng để kiểm tra pipeline E3. Chưa có curator hash-lock/code2e65b9d để khẳng định cùng chính xác bản khóa của máy E2.
Phầncứng/memory/kernel/Python thực tế trong environment.json; không dùng thời gian tuyệt đối đối chiếu máy Xeon.

Dữ liệu gốc trong ingest/, checks/, ddl/; summary/ chứa tóm tắt và figures/ chứa hình. Pilot không thay kết quả30M.
