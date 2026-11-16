# Protocol MergeTree v2

## 1. Phạm vi và giả thuyết

Single node, append-only, dữ liệu tĩnh lúc đo SELECT. Dataset gồm sự kiện web analytics
thực từ ClickBench; chỉ lấy 12 trường có kiểu cố định. Báo cáo không kết luận về toàn bộ
105 cột, chuỗi dài, JOIN, cluster, OLTP, end-to-end streaming hay ưu thế với PostgreSQL.

1. Khóa phù hợp bộ lọc giảm marks/rows đọc; lợi ích thời gian phụ thuộc độ chọn lọc.
2. Granule nhỏ có thể giảm đọc thừa nhưng làm tăng số marks/chỉ mục; không mặc định nhanh hơn.
3. Batch lớn giảm số request/parts ban đầu, có thể giảm chi phí merge nhưng tăng độ trễ chờ
   gom batch của producer — toolkit chỉ đo từ lúc gửi, không đo thời gian producer chờ.
4. Mô hình thời gian dựa trên lượng đọc có thể dự đoán trong một môi trường cố định;
   sai số tăng khi cache, overhead và phân bố dữ liệu thay đổi.

## 2. Thiết kế đối chứng

| Mã | Người | Biến thay đổi | Quy mô | Giữ cố định |
|---|---|---|---|---|
| E1 | Hà | K0 tuple(); K1 (CounterID,EventDate); K2 đảo thứ tự | 1M,3M,10M hiệu chỉnh; 30M kiểm chứng | g=8192, 1 part, LZ4 |
| E2 | Tuấn | g=2048/8192/32768 | pilot1M; chính30M | K1, 1 part, LZ4 |
| E3 | Tài | batch10k/100k/1M | pilot1M; chính30M | K1, g8192, merge nền tự nhiên |

Mỗi E1/E2: 5 truy vấn × 3 cấu hình × 10 lượt = 150 số đo mỗi quy mô; thêm 2 warmups
mỗi cell, không đưa vào thống kê. E1 gồm 600 số đo chính+calibration, E2 chính150.
E3: 3 cỡ batch × 3 lượt = 9 reload mới; mỗi reload chứa 30M dòng. Nếu đủ thời gian,
chốt 6 lượt từ trước để lặp Latin rotation hai lần; không tăng lặp chỉ vì kết quả xấu.

Workload dùng cùng `SELECT count(), sum(ResolutionWidth)` để buộc đọc dữ liệu:

| Case | Điều kiện | Vai trò |
|---|---|---|
| W0 | Không lọc | Full-scan đối chứng |
| W1 | CounterID=3258 | Phù hợp cột đầu K1 |
| W2 | EventDate trong [15/07,23/07/2013) | Phù hợp cột đầu K2 |
| W3 | Kết hợp W1 và W2 | Key-prefix và lọc kết hợp |
| W4 | RegionID=229 | Đối chứng cột ngoài sorting key |

Pilot 1M trên snapshot 30 shard phát hiện W3 của v1 rỗng và RegionID=225 không xuất hiện.
V2 giữ CounterID=3258, mở rộng cận trên ngày đến 23/07 (loại trừ) để bao gồm ngày 22/07,
là ngày có dữ liệu đầu tiên của website này từ mốc 15/07. W4 chọn RegionID=229,
mã khác 0 có tần suất lớn nhất trong profile pilot. Lựa chọn chỉ dựa trên số dòng và
phân bố, không dựa trên latency. Dùng nguyên literals v2 cho mọi cấu hình/quy mô và
tạo run mới; không gộp kết quả từ v1. Nhật ký kiểm tra literals được giữ trong hồ sơ chuẩn bị.

Kiểm tra số dòng thỏa điều kiện trên pilot. Nếu rỗng hoặc độ chọn lọc không phù hợp,
chọn lại theo profile trước khi đóng băng protocol, ghi lý do và dùng cùng literal cho
mọi cấu hình. Không chọn literal dựa trên latency có lợi. W4 không có nghĩa chắc chắn
không pruning ở mọi phiên bản; phải đọc EXPLAIN, không suy đoán từ tên workload.

## 3. Dữ liệu và môi trường

- Tuấn tải 30 shard được kê trong config; 10 shard đầu là bộ cũ, tiếp 10 shard dư1,
  rồi 10 shard dư2 theo modulo10. Tập30M giữ toàn bộ. Các mẫu1M/3M/10M giữ các dòng
  có vị trí toàn cục modulo30 <1/<3/<10, nên rải trên mọi file và lồng nhau. Đây là
  systematic sample xác định; có thể lệch nếu dữ liệu có tính chu kỳ theo vị trí dòng.
- Script chuẩn hóa Date theo ngày epoch, DateTime theo epoch giây UTC; các số giữ kiểu
  có dấu của schema ghim. Không random LIMIT, không deduplicate, không nhân bản sự kiện.
- Ghi nguồn, ngày tải, SHA Parquet và RowBinary, số hàng, checksum nội dung từng bảng;
  hash fingerprint chỉ là kiểm tra tính nhất quán thực dụng, không thay chứng minh toán học.
- Lập profile theo ngày, CounterID, RegionID; so phân bố 1M/10M/30M và nêu thiên lệch
  lấy tập con theo file. Dữ liệu tháng 7 nên không lấy partition theo tháng làm đối chứng chính.
- Mỗi người lưu CPU/RAM/WSL/kernel/SSD/ClickHouse/disk path và giới hạn tài nguyên.
  Bổ sung cấu hình Windows `.wslconfig`/ổ vật lý thủ công nếu runner không quan sát được.

Chốt ClickHouse26.10.3.7, max_threads4, max_insert_threads1, memory2GB; dùng cùng
schema, LZ4, fsync_after_insert1, async_insert0. Không MV, projection, skip index,
partition key; PRIMARY KEY mặc định trùng ORDER BY. Tắt query cache/condition cache,
PREWHERE tự động, read/aggregation-in-order để tập trung vào sparse index. Những thiết lập
này là lựa chọn thí nghiệm có kiểm soát, không phải khuyến nghị tối ưu cho production.

`index_granularity_bytes=0` cố định số dòng/granule, `write_final_mark=0` bỏ mark cuối,
Wide parts để dễ giải thích. Thực tế adaptive granularity/Compact cũng tồn tại và chỉ
được giới thiệu ngắn ở lý thuyết; không suy kết luận định lượng sang mọi cấu hình mặc định.

E1/E2 dùng OPTIMIZE FINAL **trong chuẩn bị**, xác minh một active part trước đo; ghi thời gian
chuẩn bị riêng. Đây là cách loại biến số part count trên dataset nhỏ, không khuyến nghị
ép merge toàn bảng trong sản xuất. E3 tuyệt đối không OPTIMIZE hoặc STOP MERGES.

Chờ 3 lần quan sát cách10s, không merge/mutation và parts không đổi. Đây chỉ là trạng thái
ổn định quan sát được, không bảo đảm mọi merge tương lai hoàn tất. 20s tối thiểu xác nhận
không được gọi là CPU time hay chi phí merge thực tế. Không xóa cache OS; phép đo là warm
repeat sau2 warmups, có thể vẫn đọc đĩa nếu working set lớn. Máy không chạy tác vụ nặng khác.

## 4. Metrics và ý nghĩa

| Metric | Cách lấy | Kết luận được phép |
|---|---|---|
| client_ms | perf_counter, request→response | Latency tại client; có overhead HTTP/local |
| server_ms | QueryFinish.query_duration_ms | Thời gian server, độ phân giải ms |
| read_rows / read_bytes | QueryFinish | Lượng đọc logic; read_bytes không phải SSD I/O |
| memory_bytes | QueryFinish.memory_usage | Bộ nhớ query được ClickHouse ghi nhận |
| selected/total marks | EXPLAIN ESTIMATE + system.parts | Mức pruning; giữ cả EXPLAIN indexes |
| bytes_on_disk active | system.parts active=1 | Dung lượng bảng đang hoạt động, không phải toàn VHDX |
| compressed/uncompressed bytes | system.parts | Tỷ lệ nén phần dữ liệu, không cộng lẫn metadata |
| primary_key_bytes_in_memory, marks_bytes | system.parts | Chi phí sparse index và marks riêng biệt |
| ingest_ack_s | first send→last ACK | Nạp đồng bộ từ file local; gồm đọc file giữa các batch |
| throughput=N/ingest_ack_s | N đầu vào đã xác minh | Tốc độ toàn pipeline nạp được định nghĩa |
| parts/new_part_events | parts + part_log | Phân mảnh; không mặc định 1 INSERT=1 part |
| merge_events/duration/read_rows | part_log theo table_uuid | Công việc merge, không đồng nhất với wall time |

Giữ số đo từng lượt, median, Q1, Q3, IQR. Không dùng p95 làm kết luận chính với n10.
`pruning=1-selected_marks/total_marks`; `speedup=median(T_baseline)/median(T_variant)`
chỉ trong cùng máy/quy mô/case/protocol. Nếu server median0ms: không chia cho0;
client_ms vẫn có độ phân giải cao nhưng phải gọi đúng là thời gian client.

`merge_row_amplification=sum(part_log.MergeParts.read_rows)/N` là proxy lượng dòng
được đọc lại do merge, không phải physical write amplification của SSD. Tổng duration
của các merge có thể chồng thời gian; không cộng với ACK để suy ra tổng thời gian hệ thống.
Active bytes không bao gồm tất cả inactive/tạm khi merge; timeline lấy mỗi1s có overhead
và không đo được đỉnh dung lượng vật lý tuyệt đối. Giữ log lỗi/timeout, không loại outlier tùy ý.

## 5. Dự đoán trước và kiểm chứng

Với một part, granule cố định g, N dòng:

```text
M ≈ ceil(N/g)
R_est ≈ min(N, selected_marks*g)       # xấp xỉ, granule cuối có thể ngắn
I_key_est ≈ M * key_width_bytes       # K1/K2: 4+2=6 byte; chưa gồm metadata/marks
T_est_ms = alpha_ms + beta_ms_per_row * EXPLAIN_ESTIMATE.rows
```

`EXPLAIN ESTIMATE` trả rows/marks/parts, **không trả milliseconds**. Dùng chính rows của
EXPLAIN trong fit, không dùng số nhóm đầu ra hay actual read_rows của30M làm biến dự đoán.
α đại diện overhead cố định; β là chi phí trung bình thực nghiệm mỗi dòng trên máy/case/layout.
Fit riêng15 mô hình (3 keys × 5 cases) với3 median ở1M/3M/10M; least squares ràng buộc
α,β≥0. Nếu số dòng ước lượng không biến thiên: đánh dấu không nhận diện được, không bịa hệ số.
β=0/α=0 và R² kém phải được báo cáo; chỉ3 điểm nên mô hình có tính khám phá, không phải
bộ cost model tổng quát của ClickHouse. Có thể thêm scale calibration trước khi đo holdout
bằng protocol mới, nhưng không điều chỉnh hệ số sau khi đã nhìn kết quả30M.

```bash
python3 scripts/study.py fit --member ha --machine laptop1 --run main01
python3 scripts/study.py build --member ha --machine laptop1 --run main01 --experiment keys --scale 30m
python3 scripts/study.py forecast --member ha --machine laptop1 --run main01
# Commit model/forecast trước bước tiếp theo để có mốc độc lập, nếu quy trình nhóm cho phép.
python3 scripts/study.py queries --member ha --machine laptop1 --run main01 --experiment keys --scale 30m
python3 scripts/study.py compare --member ha --machine laptop1 --run main01
```

Runner lưu timestamp, hash file model, calibration và target EXPLAIN; từ chối chạy measured30M
trước forecast. Fit không đọc30M timings. Baseline đơn giản `T10 * R30_est/R10_est` giả định
overhead không đáng kể; báo cáo lỗi của baseline để thấy mô hình α+βR có thực sự tốt hơn.

Bảng cuối: key/case, estimated rows, actual read_rows, predicted ms, actual median/Q1/Q3,
absolute error(ms), signed error, APE(%), naive error. `APE=|estimated-actual|/actual*100`,
`MAE=mean(|estimated-actual|)`; percentage không có nghĩa khi actual0. Đồ thị predicted-vs-actual
có đường y=x, ghi máy và protocol. Sai số lớn là kết quả nghiên cứu cần giải thích, không cần
sửa mô hình cho khớp rồi gọi là dự đoán. Dự đoán storage/ingestion là phần mở rộng; toolkit
hiện thực hóa dự đoán **query client time** cho E1, không giả vờ dự đoán mọi metric.

## 6. Các bước hoàn thành và nghiệm thu

1. Chốt phạm vi, phân công, schema12cột, literals và protocol; Tuấn commit manifest30M.
2. Chạy status và pilot1M mỗi máy, kiểm tra kết quả đối chứng, tài nguyên, duration đủ phân giải.
3. Tạo run chính mới, Hà chạy calibration→fit→build30M→forecast→query30M; Tuấn E2, Tài E3.
4. Dùng summarize, compare, plot. Mọi con số trong hình truy về CSV/query_id hoặc table_uuid.
5. Viết theo mạch câu hỏi→giả thuyết→thiết lập→số liệu→cơ chế→giới hạn. Không điền số dự kiến
   vào ô kết quả. Bác bỏ giả thuyết cũng là kết quả hợp lệ.
6. Người review khác tái lập một case, kiểm tra fingerprint, DDL/settings, phân vị/công thức;
   gắn tên reviewer và commit trong PR. Không gộp tuyệt đối số ms từ ba máy.
7. Package ZIP; đưa bản đã rà soát vào artifacts, giữ dataset và password ngoài Git.

## Nguồn chính thức để đọc/trích dẫn

- [ClickBench và quy tắc](https://github.com/ClickHouse/ClickBench)
- [Schema ghim](https://github.com/ClickHouse/ClickBench/blob/b0b7dd8f11a2a719211cc41d8c7ebbada267df66/clickhouse/create.sql)
- [MergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree)
- [Data parts](https://clickhouse.com/docs/parts)
- [Primary indexes](https://clickhouse.com/docs/primary-indexes)
- [Part merges](https://clickhouse.com/docs/merges)
- [Partitions](https://clickhouse.com/docs/partitions)
- [EXPLAIN](https://clickhouse.com/docs/reference/statements/explain)
- [Query log](https://clickhouse.com/docs/reference/system-tables/query_log)
- [Parts metrics](https://clickhouse.com/docs/reference/system-tables/parts)
- [Part log](https://clickhouse.com/docs/reference/system-tables/part_log)
- [Insert strategy](https://clickhouse.com/docs/concepts/best-practices/selecting-an-insert-strategy)
- [RowBinary](https://clickhouse.com/docs/reference/formats/RowBinary/RowBinary)

Ngày thiết kế16/11/2026. Tài liệu web có thể mới hơn server26.10; đối chiếu SHOW CREATE,
system.settings, EXPLAIN và kết quả smoke test trên phiên bản thực tế. Các ngưỡng, số lượt,
ma trận và mô hình trên là thiết kế của nhóm, không phải quy tắc chính thức của ClickBench.
