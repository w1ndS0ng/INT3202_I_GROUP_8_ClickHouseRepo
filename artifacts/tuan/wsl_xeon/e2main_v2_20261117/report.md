## 3.2. Dữ liệu, môi trường và phương pháp thực nghiệm

### 3.2.1. Nguồn dữ liệu và snapshot nghiên cứu

#### a. Nguồn dữ liệu và khả năng truy vết

Nhóm sử dụng dữ liệu hits của ClickBench do ClickHouse công bố, lấy đúng 30 tệp Parquet theo thứ tự shard 0, 10, …, 90; 1, 11, …, 91; 2, 12, …, 92. Kiểm tra lại từng tệp xác nhận 1.000.000 dòng/tệp, tổng cộng 30.000.000 dòng; quy mô này không được tạo bằng cách nhân bản bản ghi.

Dữ liệu gồm 30 tệp Parquet được tải ngày 16/11/2026, với tổng dung lượng 4.711.867.682 byte. Bản kê manifests/hits30m.sources.json lưu URL, thời điểm tải, dung lượng, số dòng và SHA-256 của từng tệp; checksum của cả 30 tệp khớp bản kê. Schema tham chiếu được ghim tại commit ClickBench b0b7dd8f11a2a719211cc41d8c7ebbada267df66 [S12]. Thời gian tải và xác minh dữ liệu được tách khỏi thời gian thực nghiệm.

#### b. Schema và chuyển đổi dữ liệu

Schema thực nghiệm giữ 12 cột: WatchID, UserID (Int64); CounterID, RegionID, ResponseEndTiming (Int32); AdvEngineID, IsRefresh, ResolutionWidth, ResolutionHeight, DontCountHits (Int16); EventDate (Date); EventTime (DateTime('UTC')). EventDate được chuyển theo số ngày epoch, EventTime theo số giây epoch UTC. Đây là schema rút gọn phục vụ nghiên cứu MergeTree, không phải benchmark ClickBench chuẩn 105 cột.

Quá trình chuyển Parquet sang RowBinary giữ nguyên các bản ghi và được thực hiện trước khi đo. Mỗi dòng RowBinary dài 44 byte; tổng dung lượng của 30 tệp là 1.320.000.000 byte. Kiểm tra 12 cột trên toàn bộ tệp không phát hiện NULL hoặc giá trị vượt miền kiểu đích. Số dòng và fingerprint nguồn–đích khớp ở 30/30 tệp; SHA-256 của các tệp RowBinary khớp bản kê. Kết quả kiểm chứng được lưu tại manifests/hits30m.schema-audit.json.

#### c. Tạo mẫu hệ thống lồng nhau

Trên chuỗi 30 tệp theo thứ tự cố định, nhóm đánh số dòng toàn cục từ 0 và giữ các vị trí có phần dư khi chia 30 nhỏ hơn 1, 3 hoặc 10 để tạo mẫu 1M, 3M và 10M; tập 30M giữ toàn bộ dữ liệu. Kiểm tra lại 30 triệu dòng ở mức byte xác nhận ba mẫu đúng quy tắc, lồng nhau và có số dòng chính xác. SHA-256 của từng mẫu được lưu trong manifests/hits30m.sampling-audit.json.

Đây là lấy mẫu hệ thống có thể tái lập, nhưng có thể chịu ảnh hưởng của chu kỳ và thứ tự tệp. Với mẫu 1M, độ lệch tỷ trọng tuyệt đối lớn nhất so với 30M là 0,001317 điểm phần trăm theo ngày, 0,000157 theo CounterID và 0,045897 theo RegionID. Đối chiếu này chỉ mô tả ba phân bố đã kiểm tra, không chứng minh tính đại diện của mọi thuộc tính.

#### d. Đặc trưng dữ liệu và bản kê dùng chung

Các quy mô 1M/3M/10M/30M đều có dữ liệu ở 17 ngày trong khoảng 02–31/07/2013. Số CounterID phân biệt lần lượt là 1.658/1.696/1.865/2.113; số RegionID phân biệt là 3.419/4.001/5.277/6.834. Phân bố theo ngày, CounterID và RegionID cùng fingerprint của từng quy mô được lưu trong manifests/hits30m.profile.json.

Bản kê manifests/hits30m.lock.json cố định thứ tự shard, schema, số dòng và SHA-256 của Parquet, RowBinary và các mẫu. Fingerprint gồm count(), tổng cityHash64 và XOR cityHash64 trên bộ 12 cột, dùng để kiểm tra tính nhất quán giữa dữ liệu đầu vào và các bảng đối chứng. Bảng thử 1M và ba bảng E2 chính thức 30M đều khớp fingerprint của quy mô tương ứng. Phép kiểm tra hash có khả năng va chạm nên không thay thế chứng minh đồng nhất tuyệt đối. Các bước chuẩn bị và kiểm tra này nằm ngoài thời gian đo truy vấn.

### 3.2.2. Môi trường và các biến giữ cố định

Máy thực nghiệm sử dụng Intel Xeon E-2176M 2,70 GHz, gồm 6 nhân và 12 luồng, chạy Windows 11 Pro for Workstations. Ubuntu 26.04.1 LTS hoạt động qua WSL2 với kernel 6.18.58.1-microsoft-standard-WSL2 và Python 3.14.4. Môi trường WSL2 nhận diện 12 CPU logic và 15,38 GiB RAM; không có tệp .wslconfig tùy chỉnh tại đường dẫn mặc định.

Dữ liệu và ClickHouse được lưu trên hệ thống tệp Linux của WSL2; tệp VHDX Ubuntu nằm trên ổ C thuộc SSD NVMe INTEL SSDPEKKF512G8L 512 GB. Hồ sơ Windows ghi nhận ổ C còn trống 125.223.747.584 byte lúc 23:49:58 ngày 16/11/2026 (UTC+7). Đây là dung lượng trống của ổ vật lý chứa VHDX tại thời điểm ghi nhận. ClickHouse server, client và local đều ở phiên bản 26.10.3.7. Instance nghiên cứu có cấu hình và thư mục dữ liệu riêng, chỉ lắng nghe trên localhost.

Tệp effective_settings.json của run E2 chính thức ghi nhận đủ 20 thiết lập truy vấn có hiệu lực và khớp protocol mergetree-v2. Các giới hạn chính gồm max_threads=4, max_insert_threads=1 và max_memory_usage=2.000.000.000 byte. Cấu hình của từng run được lưu cùng hồ sơ kết quả để phục vụ đối chiếu.

Ba bảng E2 sử dụng MergeTree, 12 cột CODEC(LZ4) và ORDER BY (CounterID, EventDate). PRIMARY KEY mặc định theo sorting key, không áp đặt tính duy nhất [S2]. DDL không khai báo PARTITION BY, materialized view, projection hoặc skip index. SHOW CREATE TABLE thực tế của từng bảng được lưu và đối chiếu với DDL yêu cầu.

Các bảng đối chứng cố định index_granularity_bytes=0, write_final_mark=0 và fsync_after_insert=1. Thiết lập async_insert=0 bảo đảm quy trình nạp đồng bộ; query cache, condition cache, skip index, PREWHERE tự động, tối ưu trivial count và read/aggregation-in-order đều được tắt theo protocol. Các giá trị có hiệu lực đã được kiểm tra trên instance nghiên cứu. Đây là thiết lập kiểm soát thực nghiệm, không phải khuyến nghị cấu hình cho môi trường vận hành.

Theo protocol E1/E2, OPTIMIZE TABLE … FINAL được thực hiện trong giai đoạn chuẩn bị, sau đó chờ ổn định và xác minh đúng một active Wide part. Thời gian OPTIMIZE và thời gian chờ được ghi riêng, không cộng vào thời gian truy vấn. Bảng thử 1M với g8192 có một Wide part, 123 marks và fingerprint khớp dữ liệu đầu vào; ba quan sát cách nhau khoảng 10 giây ghi nhận part không đổi, không có merge hoặc mutation.

Đối với E3, quy trình nạp để merge nền diễn ra tự nhiên, không gọi OPTIMIZE FINAL hoặc STOP MERGES. Trong E2 chính thức, cả ba bảng 30M đều được xác minh có một active Wide part trước và sau đo. Kết quả E2 được trình bày tại mục 3.4; số liệu thử nghiệm thu thập chỉ số nạp không được sử dụng thay cho kết quả E3 chính thức.

### 3.2.3. Bộ truy vấn và các chỉ số đo lường

Năm workload sử dụng cùng biểu thức SELECT count(), sum(ResolutionWidth) để thực thi phép tổng hợp trên dữ liệu. W0 không lọc; W1 lọc CounterID=3258; W2 lọc EventDate thuộc [2013-07-15, 2013-07-23); W3 kết hợp W1 và W2; W4 lọc RegionID=229, là cột ngoài sorting key.

Pilot 1M xác nhận bộ literal ban đầu làm W3 và W4 không có bản ghi thỏa điều kiện. Trước khi tạo run chính thức, protocol mergetree-v2 mở rộng cận trên ngày đến 23/07/2013 và chọn RegionID=229 dựa trên phân bố dữ liệu, không dựa trên thời gian truy vấn. Số bản ghi thỏa điều kiện của W0–W4 trên pilot lần lượt là 1.000.000, 1.294, 382.135, 134 và 205.725. Bộ literal đã điều chỉnh được giữ thống nhất giữa các cấu hình và quy mô.

client_ms là thời gian từ lúc gửi yêu cầu HTTP đến khi nhận đầy đủ phản hồi. Các trường query_duration_ms, read_rows, read_bytes và memory_usage được lấy từ QueryFinish theo query_id [S10]. EXPLAIN ESTIMATE cung cấp số dòng, marks và parts ước tính cần đọc; total marks lấy từ system.parts, kèm kế hoạch EXPLAIN indexes=1 [S7]. Tỷ lệ loại bỏ granule được tính bằng pruning=1−selected_marks/total_marks. Số bản ghi thỏa điều kiện, số dòng đọc thực tế và số dòng ước tính được trình bày như các đại lượng riêng biệt.

Các chỉ số dung lượng được tổng hợp từ system.parts với active=1, gồm bytes_on_disk, data_compressed_bytes, data_uncompressed_bytes, marks_bytes và primary_key_bytes_in_memory [S6]. bytes_on_disk phản ánh dung lượng các part đang hoạt động; marks_bytes phản ánh dung lượng marks trên đĩa, còn primary_key_bytes_in_memory phản ánh bộ nhớ chứa giá trị khóa chính. read_bytes là lượng đọc logic do ClickHouse ghi nhận, không phải lượng I/O vật lý của SSD.

Phép đo nạp ghi từng batch và query_id, tính throughput=N/ingest_ack_s với ingest_ack_s đo từ lần gửi đầu đến ACK cuối, bao gồm xử lý cục bộ giữa các batch. Snapshot dung lượng và số part được lấy ngay sau ACK cuối và sau khi đạt điều kiện ổn định; đây không phải snapshot nguyên tử tại thời điểm ACK. Các sự kiện NewPart và MergeParts được đối chiếu theo table_uuid. Pilot 1M gồm 10 batch × 100.000 dòng ghi nhận 10 NewPart, một MergeParts và năm active part ở cả hai snapshot. Tổng duration và read_rows của merge được tính riêng; chúng không đồng nghĩa với thời gian ACK, thời gian chờ hoặc CPU time.

### 3.2.4. Quy trình lặp, tính đúng đắn và tái lập

Mỗi tổ hợp E1/E2 được quy định hai lượt khởi động (warmup) và 10 lượt đo; thứ tự các tổ hợp được đảo bằng seed 20261116. Ma trận E2 gồm 3 cấu hình × 5 workload, tương ứng 30 warmup và 150 lượt đo chính. Kết quả count() và sum() được kiểm tra riêng; lượt đo sử dụng FORMAT Null. Nhật ký giữ toàn bộ lượt đo, query_id và lỗi hoặc timeout; không loại bỏ ngoại lệ tùy ý. Đối với E3, protocol quy định ba vòng cho mỗi kích thước batch, với thứ tự luân phiên.

Thống kê sử dụng trung vị và các tứ phân vị tính theo phương pháp inclusive. Q1 và Q3 lần lượt là phân vị 25% và 75%; khoảng tứ phân vị có độ rộng IQR=Q3−Q1. Khoảng Q1–Q3 mô tả độ phân tán của phần giữa phân bố, không phải khoảng tin cậy của trung vị. Với 10 lượt đo mỗi tổ hợp, p95 không được sử dụng làm căn cứ kết luận chính. Điều kiện ổn định gồm ba quan sát cách nhau 10 giây, part không đổi và không có merge/mutation, với timeout 1.200 giây. Khoảng xác nhận tối thiểu 20 giây không phải thời gian merge thực và không bảo đảm không phát sinh merge về sau. OS cache không được xóa; kết quả thuộc chế độ lặp sau warmup (warm-repeat).

Trước từng truy vấn E2, chương trình kiểm tra không có merge, mutation chưa hoàn tất hoặc truy vấn khác đang chạy trên instance nghiên cứu. Phép kiểm tra này không loại trừ tác động của các ứng dụng nền khác trong Windows hoặc WSL2. Các phép đối chứng và tỷ số thời gian chỉ được so sánh trong cùng máy, quy mô, workload và protocol. Run chính thức e2main_v2_20261117 được tạo sau pilot e2pilot_v2_20261117, sử dụng mã nguồn đo tại commit 2e65b9d. Hồ sơ tách theo member/machine/run và lưu protocol hash, manifest hash cùng trạng thái Git. Mã xuất Hình 3.1 ở commit c47338a.

Hồ sơ E2 đã rà soát được lưu tại artifacts/tuan/wsl_xeon/e2main_v2_20261117/; gói log đầy đủ được giữ trong results/tuan/wsl_xeon/e2main_v2_20261117/share_results_figure31_v5.zip. Hồ sơ gồm số đo gốc, QueryFinish, DDL, SQL, EXPLAIN, snapshot dung lượng và hình. Việc tái lập ít nhất một cặp đối chứng bởi người kiểm tra độc lập trên máy thứ hai chưa được thực hiện; vì vậy yêu cầu review của T32-15 chưa hoàn tất.

Bảng 3.1. Thiết lập và ma trận thực nghiệm E2.

| Thành phần | Thiết lập E2 |
| --- | --- |
| Dữ liệu | Bộ dữ liệu đã khóa: 30M dòng, 12 cột; các biến thể khớp fingerprint và đáp án. |
| Bảng và khóa | MergeTree; K1 (CounterID, EventDate); LZ4; một active Wide part. |
| Biến đối chứng | g=2048/8192/32768; index_granularity_bytes=0; write_final_mark=0. |
| Tài nguyên | ClickHouse 26.10.3.7; max_threads=4; max_insert_threads=1; giới hạn bộ nhớ 2.000.000.000 byte. |
| Ma trận đo | 3 cấu hình g × 5 workload × 10 lượt = 150 lượt chính; 2 warmup/tổ hợp; seed 20261116. |

Quy trình E2 gồm khóa dữ liệu, chạy pilot 1M, tạo run chính mới, nạp và chuẩn hóa part, kiểm fingerprint và đáp án, thực hiện warmup và đo, sau đó tổng hợp kết quả. Bước tái lập đối chứng trên máy thứ hai đang chờ thực hiện.

## 3.4. E2 — Index granularity: thiết kế, kết quả và chi phí chỉ mục

### 3.4.1. Cấu hình và kiểm chứng đối chứng

E2 giữ cố định khóa K1 (CounterID, EventDate), bộ dữ liệu 30M dòng với 12 cột, LZ4, một active Wide part và các thiết lập tại mục 3.2; biến thay đổi là index_granularity=2048/8192/32768. Cấu hình g8192 được dùng làm mốc đối chứng trên cùng máy. Pilot 1M được thực hiện ở run riêng trước run chính 30M. Ba bảng chính thức khớp count/hash_sum/hash_xor của dữ liệu đầu vào và có cùng kết quả count(), sum(ResolutionWidth) cho W0–W4. Số bản ghi thỏa điều kiện lần lượt là 30.000.000, 38.841, 11.464.429, 4.012 và 6.185.519. DDL thực tế và EXPLAIN của đủ 15 tổ hợp được lưu trong hồ sơ.

### 3.4.2. Chạy đo và kiểm tra công thức

Run chính thu đủ 150 lượt đo và 30 warmup; mỗi tổ hợp có 10 số đo, với 150/150 query_id khớp QueryFinish. Nhật ký đo không ghi nhận lỗi truy vấn. Part và fingerprint kiểm lại sau đo khớp trước đo. Snapshot dung lượng được lấy sau khi đạt điều kiện ổn định. Thời gian OPTIMIZE chuẩn bị của g2048/g8192/g32768 lần lượt là 7.983,681/7.514,693/7.245,069 ms và không tính vào thời gian truy vấn.

Với N=30.000.000, một part và write_final_mark=0, công thức M_est=ceil(N/g) cho 14.649/3.663/916 marks, khớp số thực tế. Giá trị khóa Int32+Date rộng 6 byte, nên I_key_est=M_est×6 bằng 87.894/21.978/5.496 byte và khớp primary_key_bytes_in_memory ở cả ba bảng. Sự khớp này chỉ phản ánh trường bộ nhớ đã đo, không bao gồm marks của các cột, metadata hoặc bộ nhớ dự phòng do cấp phát. Lượng dòng ước tính R_est≈min(N, selected_marks×g) vẫn là xấp xỉ vì granule cuối có thể ngắn.

### 3.4.3. Kết quả loại bỏ granule, thời gian truy vấn và dung lượng chỉ mục

Bảng 3.2. Kết quả E2 trên 30M dòng, máy wsl_xeon, run e2main_v2_20261117, protocol mergetree-v2. Mỗi ô ghi lần lượt read_rows; selected/total marks; pruning (%); trung vị client_ms/IQR (ms), với 10 lượt đo mỗi tổ hợp. read_rows là trung vị, còn marks lấy từ EXPLAIN và system.parts.

| Case | g2048 | g8192 | g32768 |
| --- | --- | --- | --- |
| W0 | 30.000.000<br>14.649/14.649<br>0,000%<br>34,776 / 12,937 | 30.000.000<br>3.663/3.663<br>0,000%<br>38,757 / 13,210 | 30.000.000<br>916/916<br>0,000%<br>33,449 / 6,590 |
| W1 | 40.960<br>20/14.649<br>99,863%<br>3,750 / 1,002 | 49.152<br>6/3.663<br>99,836%<br>3,149 / 1,000 | 98.304<br>3/916<br>99,672%<br>3,342 / 0,709 |
| W2 | 12.780.416<br>6.241/14.649<br>57,396%<br>35,083 / 8,434 | 14.377.856<br>1.756/3.663<br>52,061%<br>35,850 / 9,918 | 16.827.264<br>514/916<br>43,886%<br>36,704 / 6,435 |
| W3 | 6.144<br>3/14.649<br>99,980%<br>3,598 / 0,192 | 16.384<br>2/3.663<br>99,945%<br>3,347 / 0,627 | 32.768<br>1/916<br>99,891%<br>3,613 / 1,220 |
| W4 | 30.000.000<br>14.649/14.649<br>0,000%<br>86,235 / 19,474 | 30.000.000<br>3.663/3.663<br>0,000%<br>87,399 / 13,883 | 30.000.000<br>916/916<br>0,000%<br>79,283 / 24,830 |

Bảng 3.3. Chi phí E2, N=30M, một Wide part. Primary index thực tế: primary_key_bytes_in_memory; cặp số: ước tính/thực tế; MiB=2²⁰ byte.

| g | Marks<br>ước tính / thực tế | Primary index<br>ước tính / thực tế (byte) | marks_bytes<br>(byte) | Dữ liệu nén /<br>active table (MiB) |
| --- | --- | --- | --- | --- |
| 2048 | 14.649 /<br>14.649 | 87.894 /<br>87.894 | 251.092 | 498,164 /<br>498,408 |
| 8192 | 3.663 /<br>3.663 | 21.978 /<br>21.978 | 103.008 | 498,103 /<br>498,204 |
| 32768 | 916 /<br>916 | 5.496 /<br>5.496 | 33.161 | 488,362 /<br>488,396 |

Hình 3.1. E2 (Tuấn, wsl_xeon, e2main_v2_20261117, mergetree-v2); N=30M, n=10. (a) Trung vị client_ms và Q1–Q3 (nét xám), trục log; điểm dịch ngang để tránh chồng lấp. (b–c) Pruning (%), ô (b) phóng đại từ 99,6%. (d) Primary index (RAM) và marks (đĩa), KiB=2¹⁰ byte.

![Hình 3.1](figures/e2_granularity_tradeoff_v5.png)

### 3.4.4. Phân tích điểm cân bằng

So với g8192, g2048 giảm read_rows khoảng 16,7% ở W1, 11,1% ở W2 và 62,5% ở W3; đồng thời bộ nhớ chứa giá trị khóa chính tăng gần 4 lần và marks_bytes tăng 2,44 lần. Trung vị client_ms của W1/W3 tăng từ 3,149/3,347 lên 3,750/3,598 ms, còn W2 giảm từ 35,850 xuống 35,083 ms. Như vậy, mức giảm lượng dòng đọc không đi kèm mức cải thiện thời gian tương xứng trong run này. Thiết kế chưa tách riêng overhead, cache và biến động thực thi nên chưa thể quy toàn bộ chênh lệch thời gian cho kích thước granule.

W0 và W4 đọc toàn bộ 30M dòng, với pruning bằng 0 ở cả ba cấu hình. Cấu hình g32768 giảm dung lượng primary index và marks nhưng tăng lượng đọc ở W1–W3. Dung lượng dữ liệu nén cũng thay đổi theo g, nên chênh lệch bytes_on_disk không thể được quy hoàn toàn cho primary index. Trong run này, g8192 có trung vị client_ms thấp nhất ở W1 và W3; tuy nhiên, các khoảng Q1–Q3 giữa các cấu hình chồng lấp và chưa có kiểm định thống kê để xác nhận khác biệt thời gian. Chưa có cơ sở xác định một g tối ưu chung cho mọi workload. Kết luận giới hạn ở K1, LZ4, một Wide part, index_granularity_bytes=0 và chế độ warm-repeat trên máy đã đo; phần tái lập độc lập trên máy thứ hai vẫn đang chờ thực hiện.

[S2]: https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree
[S6]: https://clickhouse.com/docs/reference/system-tables/parts
[S7]: https://clickhouse.com/docs/reference/statements/explain
[S10]: https://clickhouse.com/docs/reference/system-tables/query_log
[S12]: https://github.com/ClickHouse/ClickBench/blob/b0b7dd8f11a2a719211cc41d8c7ebbada267df66/clickhouse/create.sql
