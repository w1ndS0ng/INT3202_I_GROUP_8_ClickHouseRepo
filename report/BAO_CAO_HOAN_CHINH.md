# BÁO CÁO NGHIÊN CỨU HỆ QUẢN TRỊ CƠ SỞ DỮ LIỆU

**ĐỀ TÀI:**  
**KIẾN TRÚC LƯU TRỮ MERGETREE TRONG CLICKHOUSE: GIẢI PHẪU CƠ CHẾ, ĐỐI CHỨNG ĐA HỆ QUẢN TRỊ VÀ ỨNG DỤNG PHÂN TÍCH CLICKSTREAM THỜI GIAN THỰC**

*(MergeTree Storage Engine in ClickHouse: Internals, Cross-DBMS Benchmarking and Real-time Clickstream Analytics)*

**Nhóm thực hiện:** INT3202\_I\_GROUP\_8 (Hà – Tuấn – Tài)  
**Học phần:** Hệ quản trị Cơ sở dữ liệu (DBMS)  
**Thời gian hoàn thiện:** Tháng 11 / 2026

---

## TÓM TẮT BÁO CÁO (ABSTRACT)

Báo cáo này thực hiện nghiên cứu toàn diện về **ClickHouse** — hệ quản trị cơ sở dữ liệu phân tích hướng cột (Columnar OLAP DBMS) mã nguồn mở hiệu năng cao — tập trung vào ba trụ cột: (1) định vị triết lý kiến trúc hướng phần cứng (*hardware-sympathetic*) và vị thế của ClickHouse so với các họ DBMS hiện đại (RDBMS hướng dòng, kho dữ liệu cột nhúng, hệ tìm kiếm chỉ mục đảo và hệ thống LSM-tree); (2) giải phẫu và thực nghiệm kiểm chứng động cơ lưu trữ lõi **MergeTree** — điểm sáng công nghệ tạo nên tốc độ quét và khả năng nén vượt trội của ClickHouse; và (3) thiết kế cùng kiểm chứng thực tế kiến trúc ứng dụng ClickHouse giải quyết bài toán phân tích luồng nhấp chuột (*clickstream*) cường độ 10.000 sự kiện/giây.

Trên tập dữ liệu chuẩn **ClickBench `hits` (30 triệu bản ghi, 12 cột)**, chuỗi ba thực nghiệm nội tại có kiểm soát (`E1–E3`) chứng minh: (i) đặt đúng cột tiền tố trong `ORDER BY` cho phép cắt tỉa tới `99,95%` hạt dữ liệu và tăng tốc truy vấn đến `7,76×`, trong khi kích thước chỉ mục chính thưa trong RAM chỉ tốn đúng `21.978 byte` (`~21,46 KiB`, khớp tuyệt đối `0,00%` sai số với công thức lý thuyết); (ii) kích thước hạt mặc định `index_granularity = 8192` giữ điểm cân bằng tối ưu trước chi phí duyệt mốc cố định (`g = 2.048` giảm dòng đọc nhưng không giảm độ trễ); và (iii) gom lô nạp `1.000.000` dòng giúp giảm `71,3%` thời gian nạp và triệt tiêu hệ số khuếch đại dòng đọc gộp nền (`Σr / N` giảm từ `4,517` xuống `1,000`). Trong đối chứng trực diện với **PostgreSQL 18.6** (Heap, BRIN và B-tree) trên cùng 30 triệu dòng và 4 CPU logic, ClickHouse `CH1` nhanh hơn PostgreSQL B-tree (`PG2`) từ `13,42×` đến `36,00×` ở các tải quét tổng hợp, tiết kiệm `80,96%` dung lượng đĩa (`498,20 MiB` so với `2.616,27 MiB`) và rút ngắn thời gian chuẩn bị dữ liệu tới `6,19×`; chỉ riêng truy vấn điểm siêu chọn lọc `W3` (`0,013%` bảng) thì B-tree của PostgreSQL nhanh hơn `4,79×` (`1,16 ms` so với `5,56 ms`), nhưng cần tới `20.089` lượt truy vấn `W3` trên bảng tĩnh để hoàn vốn chi phí chuẩn bị ban đầu.

Ở phần ứng dụng thực tế (Chương 5), báo cáo thiết kế đường ống 3 tầng nội tại (`Kafka Engine → Streaming Materialized View → AggregatingMergeTree`) kết hợp phác thảo HyperLogLog (`uniqHLL12`) và mô hình lai `PostgreSQL (OLTP) + Debezium CDC + ClickHouse (OLAP)`. Kết quả kiểm chứng PoC trên **36 triệu sự kiện tổng hợp (1 giờ tải 10.000 sự kiện/giây, `clickhouse-local 26.10.4.207`)** cho thấy việc đảo khóa sắp xếp từ `ORDER BY (minute, page_id)` sang `ORDER BY (page_id, minute)` giúp độ trễ truy vấn Dashboard giảm từ `180,83 ms` (vi phạm ngưỡng `< 50 ms`) xuống còn **`11,50 ms`** (nhanh hơn `26,59×` so với quét bảng thô `305,67 ms`) và nén dung lượng lưu trữ xuống chỉ còn **`1,455 MiB/giờ`** (gọn hơn `191,4×` so với bảng thô 5 cột và `27,3×` so với khóa sắp xếp theo phút đứng trước).

---

## MỤC LỤC TỔNG QUAN

* **Danh mục từ viết tắt**
* **Danh mục hình ảnh (13 hình)**
* **Danh mục bảng biểu (29 bảng)**
* **CHƯƠNG 1. TỔNG QUAN VỀ CLICKHOUSE VÀ ĐỊNH VỊ TRONG HỆ SINH THÁI DBMS**
* **CHƯƠNG 2. MERGETREE: TỔ CHỨC DỮ LIỆU, CHỈ MỤC THƯA VÀ CƠ CHẾ MERGE**
* **CHƯƠNG 3. THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỘNG CƠ MERGETREE (E1–E3)**
* **CHƯƠNG 4. ĐỐI CHIẾU TRỰC DIỆN MERGETREE VỚI POSTGRESQL (HEAP + B-TREE / BRIN)**
* **CHƯƠNG 5. ỨNG DỤNG GIẢI QUYẾT BÀI TOÁN CLICKSTREAM THỜI GIAN THỰC VÀ KIỂM CHỨNG PoC**
* **KẾT LUẬN CHUNG**
* **TÀI LIỆU THAM KHẢO**
* **PHỤ LỤC A. BẢNG GIẢI THÍCH NGUỒN GỐC HÌNH ẢNH VÀ ĐỐI CHIẾU TÁI LẬP**

---

## DANH MỤC TỪ VIẾT TẮT

| Thuật ngữ viết tắt | Nghĩa đầy đủ | Ý nghĩa trong báo cáo |
| :--- | :--- | :--- |
| **ACID** | Atomicity, Consistency, Isolation, Durability | Bộ tính chất bảo đảm giao dịch của RDBMS (OLTP) |
| **APE / MAE / MAPE** | Absolute Percentage Error / Mean Absolute (Percentage) Error | Các chỉ số đánh giá sai số dự báo mô hình thời gian |
| **AST** | Abstract Syntax Tree | Cây cú pháp trừu tượng sau pha phân tích SQL |
| **BRIN** | Block Range Index | Chỉ mục tóm tắt khoảng khối trang của PostgreSQL |
| **CDC** | Change Data Capture | Cơ chế bắt thay đổi dữ liệu từ nhật ký WAL |
| **DDL / SQL** | Data Definition Language / Structured Query Language | Ngôn ngữ định nghĩa cấu trúc và truy vấn dữ liệu |
| **HLL** | HyperLogLog | Thuật toán phác thảo xác suất đếm phần tử phân biệt |
| **IQR** | Interquartile Range (`Q3 − Q1`) | Khoảng tứ phân vị đo độ phân tán dữ liệu thực nghiệm |
| **LSM-Tree** | Log-Structured Merge-Tree | Cấu trúc cây ghép nối nhật ký tối ưu hóa ghi nối tiếp |
| **MV** | Materialized View | Khung nhìn vật lý (dạng trigger gia tăng trong ClickHouse) |
| **OLAP / OLTP** | Online Analytical / Transaction Processing | Xử lý phân tích trực tuyến / Xử lý giao dịch trực tuyến |
| **PoC** | Proof of Concept | Thực nghiệm kiểm chứng tính khả thi kỹ thuật |
| **RDBMS** | Relational Database Management System | Hệ quản trị cơ sở dữ liệu quan hệ |
| **SIMD** | Single Instruction, Multiple Data | Tập lệnh xử lý vector hóa dữ liệu trên CPU |
| **SLO** | Service Level Objective | Mục tiêu cam kết chất lượng dịch vụ (độ trễ, độ tươi mới) |
| **TID** | Tuple Identifier | Con trỏ định danh vị trí vật lý `(trang, offset)` trong PostgreSQL |
| **TTL** | Time To Live | Cơ chế tự động hết hạn và dọn dữ liệu theo thời gian |
| **WAL** | Write-Ahead Log | Nhật ký tiền ghi bảo đảm bền vững dữ liệu |

---

## DANH MỤC HÌNH ẢNH (13 HÌNH)

* **Hình 2.1.** Luồng xử lý truy vấn tối thiểu trong ClickHouse và vị trí của động cơ MergeTree [S1, S2].
* **Hình 2.2.** Đường ghi bất biến của MergeTree từ khối dữ liệu trong RAM đến tệp phân đoạn trên đĩa [S1, S3, S4].
* **Hình 2.3.** Quan hệ phân cấp giữa Table, Partition, Data Part và Granule trong động cơ MergeTree [S2, S3].
* **Hình 2.4.** Phân bố granule chứa hàng khớp bộ lọc với K0, K1 và K2 trên 16 bản ghi giả định; dấu ✓ không phải kết quả chọn marks của ClickHouse [S2, S4].
* **Hình 2.5.** So sánh granule nhỏ/lớn trên 16 hàng giả định: xanh đậm là hàng 5–6 thỏa lọc, xanh nhạt là các hàng khác cùng granule phải đọc [S2, S4].
* **Hình 2.6.** Minh họa do nhóm vẽ: A, B, C cùng partition được hợp nhất thành D (không phải số đo thực nghiệm; cơ chế theo [S3, S5]).
* **Hình 2.7.** Các bước xử lý một yêu cầu INSERT đồng bộ để tạo data part (Nguồn: ClickHouse Docs, *Selecting an insert strategy* [S9] · CC BY-NC-SA 4.0).
* **Hình 2.8.** Hợp nhất các part của ReplacingMergeTree và giữ lại hàng theo khóa sắp xếp (Nguồn: ClickHouse Docs, *Replacing merges* [S5, V1] · CC BY-NC-SA 4.0).
* **Hình 3.1.** Biểu đồ so sánh độ trễ (Median và khoảng tứ phân vị IQR) cùng khối lượng dòng đọc (`read_rows`) giữa K0, K1, K2 trên các truy vấn W0–W4 ở quy mô 30M.
* **Hình 3.2.** Biểu đồ 4 ô kết quả E2 trên máy `wsl_xeon`; `N = 30M, n = 10`: (a) Trung vị `client_ms` và khoảng `Q1–Q3` (cho W1–W3); (b–c) Tỷ lệ Pruning; (d) Dung lượng Primary index RAM và Marks đĩa.
* **Hình 3.3.** Đối chiếu Ước tính và Thực đo (*Estimate vs. Actual*) tại quy mô 30 triệu dòng: (a) Holdout E1 SELECT (`laptop1`); (b) Hồi cứu E3 Batch INSERT (`laptop_i5`).
* **Hình 5.1.** Sơ đồ kiến trúc luồng dữ liệu 3 tầng xử lý Clickstream thời gian thực nội tại trong ClickHouse *(ghi chú: DDL tối ưu hóa trong báo cáo sử dụng `ORDER BY (page_id, minute)` cho truy vấn lọc theo trang)*.
* **Hình 5.2.** Mô hình kiến trúc lai hiện đại kết hợp giữa PostgreSQL (OLTP) và ClickHouse (OLAP).

*(Nguồn gốc, công cụ tạo lập và tập dữ liệu đầu vào của toàn bộ 13 hình được trình bày chi tiết tại **Phụ lục A** cuối báo cáo).*

---

## DANH MỤC BẢNG BIỂU (29 BẢNG)

* **Chương 1 (2 bảng):** Bảng 1.1 (Đối chiếu Heap PostgreSQL vs Columnar MergeTree), Bảng 1.2 (Định vị ClickHouse MergeTree cạnh các họ DBMS phân tích và lưu trữ hiện đại).
* **Chương 2 (3 bảng):** Bảng 2.1 (Cấu trúc tệp Data Part Wide), Bảng 2.2 (Khả năng tận dụng tiền tố khóa), Bảng 2.3 (Đại lượng phục vụ E3).
* **Chương 3 (13 bảng):** Bảng 3.1 (Ánh xạ RQ–giả thuyết–thực nghiệm), Bảng 3.2 (Cấu hình phần cứng/phần mềm), Bảng 3.3 (Thiết lập cố định MergeTree), Bảng 3.4 (Bộ truy vấn W0–W4), Bảng 3.5 (Kết quả E1 trên 30M), Bảng 3.6 (Dung lượng lưu trữ và nén E1), Bảng 3.7 (Thời gian nạp & OPTIMIZE E2), Bảng 3.8 (Kết quả E2 với 3 mức granularity), Bảng 3.9 (Dung lượng index & marks E2), Bảng 3.10 (Kết quả nạp & merge nền E3), Bảng 3.11 (Đối chiếu Estimate vs. Actual E1 holdout), Bảng 3.12 (Đối chiếu hồi cứu E3), Bảng 3.13 (Tổng hợp đối chứng lý thuyết E3).
* **Chương 4 (9 bảng):** Bảng 4.1 (Tổ chức vật lý MergeTree vs PostgreSQL Heap), Bảng 4.2 (Ma trận 5 cấu hình đối chứng), Bảng 4.3 (Độ trễ `client_ms` trên `wsl_xeon`), Bảng 4.4 (Hệ số tăng tốc `S` và `ΔT%`), Bảng 4.5 (Pruning của CH1), Bảng 4.6 (Kế hoạch thực thi PostgreSQL), Bảng 4.7 (Dung lượng đĩa 5 cấu hình trên `laptop_i5`), Bảng 4.8 (Thời gian chuẩn bị trên `laptop_i5`), Bảng 4.9 (Thời gian chuẩn bị trên `wsl_xeon`).
* **Chương 5 (2 bảng):** Bảng 5.1 (Kết quả PoC thực đo 36 triệu sự kiện trên `clickhouse-local 26.10.4.207`: Bảng thô vs `ORDER BY (minute, page_id)` vs `ORDER BY (page_id, minute)`), Bảng 5.2 (Chi tiết dung lượng nén theo từng cột trong `clickstream_1m_state` và kiểm chứng sai số/lũy đẳng).

---

# CHƯƠNG 1. TỔNG QUAN VỀ CLICKHOUSE VÀ ĐỊNH VỊ TRONG HỆ SINH THÁI DBMS

## 1.1. Giới thiệu chung và Triết lý thiết kế hướng phần cứng (Hardware-Sympathetic)

Sự gia tăng theo cấp số nhân của dữ liệu sinh ra từ máy (*machine-generated data*) như nhật ký sự kiện, luồng nhấp chuột (*clickstream*) và dữ liệu viễn đo (*telemetry*) đặt các hệ quản trị cơ sở dữ liệu quan hệ truyền thống (RDBMS) trước giới hạn vật lý của kiến trúc phần cứng. Việc thực thi các truy vấn tổng hợp trên quy mô hàng chục triệu đến hàng tỷ bản ghi với yêu cầu độ trễ dưới một giây đòi hỏi một sự chuyển dịch mô hình: từ lưu trữ hướng dòng sang lưu trữ hướng cột thuần túy kết hợp xử lý vector hóa [A1, A2].

**ClickHouse** là hệ quản trị cơ sở dữ liệu phân tích hướng cột mã nguồn mở hiệu năng cao, được phát triển bằng ngôn ngữ C++ [A1]. Khác với các hệ thống phân tích dựa trên máy ảo Java (JVM) hay động cơ lưu trữ lai, ClickHouse là hệ thống hướng cột thuần túy (*true column-oriented*). Dữ liệu được tổ chức thành các mảng giá trị đồng nhất (`ColumnVector`) xuyên suốt từ đĩa cứng, bộ nhớ RAM đến các tầng bộ nhớ đệm CPU (L1/L2/L3), loại bỏ hoàn toàn siêu dữ liệu cấp dòng (*row headers*). Triết lý thiết kế cốt lõi của ClickHouse là thiết kế từ dưới lên, khai thác tối đa năng lực phần cứng (*hardware-sympathetic design*):

* **Tối ưu hóa tính cục bộ bộ nhớ đệm (Cache Locality):** Sắp xếp dữ liệu của từng cột liên tiếp trong RAM, giảm thiểu tối đa hiện tượng trượt bộ nhớ đệm (*CPU cache misses*) và tối ưu hóa bộ dự đoán nhánh (*branch predictor*).
* **Thực thi mã máy gốc không chi phí trừu tượng (Zero-cost Abstractions):** Biên dịch C++ với kỹ thuật chuyên biệt hóa mẫu (*template specialization*), loại bỏ chi phí gọi hàm ảo trên từng bản ghi và triệt tiêu hoàn toàn hiện tượng dừng hệ thống để thu gom rác (*Garbage Collection pauses*).
* **Đánh đổi chu kỳ CPU lấy băng thông I/O:** Tận dụng năng lực tính toán đa nhân của CPU hiện đại để giải nén dữ liệu tốc độ cao (với các thuật toán như LZ4, ZSTD), biến băng thông đĩa cứng và bus truyền thông trở thành nút thắt ít bị quá tải nhất [A1].

Dự án khởi nguồn từ năm 2009 tại Yandex nhằm phục vụ nền tảng phân tích lưu lượng web Yandex.Metrica [A1, A4], chính thức mở mã nguồn năm 2016 theo giấy phép Apache 2.0 và được cộng đồng học thuật quốc tế đúc kết toàn diện tại hội nghị VLDB 2024 [A1].

## 1.2. Phân loại và định vị kiến trúc trên bản đồ các họ DBMS

ClickHouse được thiết kế chuyên biệt cho tải **xử lý phân tích trực tuyến (OLAP)**, nơi các thao tác đọc quét dải rộng chiếm ưu thế, chỉ chiếu trên một tập con nhỏ các thuộc tính và tính toán các hàm tổng hợp (`COUNT`, `SUM`, `AVG`, `uniq`).

Để làm rõ định vị kiến trúc giữa hệ thống lưu trữ hàng truyền thống (đại diện là PostgreSQL) và hệ thống lưu trữ cột phân tích (ClickHouse), **Bảng 1.1** đối chiếu các cơ chế vật lý nền tảng. Cần nhấn mạnh rằng sự phân định này xuất phát từ bản chất cấu trúc dữ liệu, không mang ý nghĩa áp đặt cứng nhắc *"PostgreSQL chỉ chạy được OLTP"*. Trên thực tế, PostgreSQL vẫn có thể thực thi truy vấn phân tích thông qua quét tuần tự song song hoặc chỉ mục BRIN; tuy nhiên, cấu trúc bảng Heap hướng dòng tạo ra giới hạn vật lý nội tại về dung lượng đọc thừa khi chỉ cần tính toán trên một vài cột.

**Bảng 1.1.** Đối chiếu cơ chế kỹ thuật giữa kiến trúc Heap (PostgreSQL) và Columnar MergeTree (ClickHouse)

| Tiêu chí kỹ thuật | Kiến trúc Heap + B-tree/BRIN (PostgreSQL) | Kiến trúc Columnar MergeTree (ClickHouse) |
| :--- | :--- | :--- |
| **Tổ chức lưu trữ vật lý** | Hướng dòng (Heap file, trang 8 KiB). Mọi thuộc tính của một tuple nằm liền kề nhau trên đĩa [P1]. | Hướng cột thuần túy. Mỗi thuộc tính được lưu thành các tệp dữ liệu nén độc lập (`.bin`) [S2, S3]. |
| **Độ rộng đọc dữ liệu (I/O)** | Đọc toàn bộ trang chứa tuple (phát sinh đọc thừa các thuộc tính không có trong câu truy vấn). | Chỉ mở và đọc đúng các tệp của những cột có mặt trong câu lệnh SQL [A1, A2]. |
| **Tổ chức thứ tự vật lý** | Dữ liệu chèn tự do vào trang trống; lệnh `CLUSTER` chỉ sắp xếp 1 lần, không tự duy trì khi ghi mới [P5]. | Dữ liệu luôn được sắp xếp theo `ORDER BY` trong từng part; duy trì liên tục qua tiến trình merge nền [S2, S5]. |
| **Cơ chế đánh chỉ mục** | Chỉ mục dày (B-tree) trỏ qua con trỏ dòng (TID) hoặc chỉ mục tóm tắt dải trang (BRIN) [P2, P3]. | Chỉ mục chính thưa (`primary.idx`) gắn liền với part, nạp thường trực vào RAM [S4]. |
| **Đặc tính nén dữ liệu** | Thấp đến trung bình do dữ liệu dị loại nằm xen kẽ trên trang đĩa. | Rất cao: từ 2×–3× với số nguyên entropy cao đến trên 10× với chuỗi văn bản lặp lại [A1]. |
| **Mô hình thực thi CPU** | Duyệt từng bộ dữ liệu (*tuple-at-a-time* / Volcano Iterator). | Thực thi vector hóa theo khối (*vectorized block execution*, kích hoạt SIMD) [A1, A2]. |
| **Mô hình ghi dữ liệu** | Ghi nhận từng dòng vào WAL và trang đệm, hỗ trợ cập nhật tại chỗ (*in-place update*) [P8]. | Ghi nối tiếp theo lô (*batch append-only*), các phân đoạn dữ liệu tạo ra là bất biến [S3, S9]. |

### Định vị ClickHouse (MergeTree) cạnh các họ DBMS phân tích và lưu trữ khác

Ngoài RDBMS hướng dòng truyền thống, để hiểu đúng giá trị của **MergeTree** (điểm sáng kiến trúc được mổ xẻ xuyên suốt Chương 2–4), cần đặt ClickHouse cạnh các DBMS phân tích và lưu trữ hiệu năng cao khác trên thị trường (**Bảng 1.2**):

**Bảng 1.2.** Định vị ClickHouse MergeTree trong hệ sinh thái các DBMS hiện đại

| Hệ quản trị / Họ DBMS | Kiến trúc lưu trữ & chỉ mục đặc trưng | Điểm mạnh nổi bật | Đánh đổi / Giới hạn so với ClickHouse MergeTree |
| :--- | :--- | :--- | :--- |
| **ClickHouse** *(MergeTree)* | Hướng cột thuần túy; phân đoạn bất biến sắp xếp theo `ORDER BY`; chỉ mục chính thưa (`primary.idx`) + tọa độ `marks`; merge nền bất đồng bộ [S1–S5]. | Nén cực tốt, tốc độ quét & tổng hợp thời gian thực rất cao, chi phí RAM chỉ mục siêu nhỏ (~0,004% dung lượng đĩa). | Cập nhật/xóa điểm tốn kém (Mutations); JOIN bảng lớn dễ tràn RAM; không hỗ trợ ACID đa dòng. |
| **PostgreSQL** *(Heap + B-tree/BRIN)* | Hướng dòng trên trang 8 KiB; chỉ mục tách rời (`B-tree` dày hoặc `BRIN` dải khối) [P1–P3]. | Giao dịch ACID đầy đủ, khóa mức dòng, tra cứu điểm 1 dòng dưới 1 ms, hệ sinh thái OLTP trưởng thành. | Đọc thừa cột khi phân tích quét rộng; dung lượng đĩa và B-tree phình lớn; không tự duy trì thứ tự Heap khi ghi nối tiếp. |
| **Apache Druid / Pinot** *(Real-time OLAP)* | Hướng cột chia phân đoạn theo thời gian; kết hợp **chỉ mục đảo (Inverted Index)** & **Roaring Bitmap** trên JVM/C++ [A1]. | Xuất sắc với truy vấn lọc đa điều kiện phức tạp trên cột phân loại (high-filter ad-hoc) và tích hợp luồng thời gian thực. | Chỉ mục đảo tiêu tốn nhiều RAM/đĩa hơn chỉ mục thưa; vận hành cụm nhiều thành phần (Broker, Historical, Coordinator) phức tạp hơn; JVM chịu áp lực GC (Druid). |
| **Elasticsearch / OpenSearch** | Tài liệu JSON + **Chỉ mục đảo Lucene** (Inverted Index + DocValues) trên JVM [B2]. | Tìm kiếm toàn văn (*full-text search*) và khớp mẫu văn bản linh hoạt. | Chi phí lưu trữ chỉ mục đảo rất lớn; tổng hợp số học trên hàng trăm triệu dòng chậm và ngốn bộ nhớ heap JVM hơn hẳn vector hóa C++ [B2]. |
| **DuckDB** *(Embedded Columnar)* | Vector hóa C++, lưu trữ khối cột nén + **Zone Maps (Min/Max)** trên từng Row Group. | Nhúng trực tiếp vào ứng dụng (in-process), đọc Parquet/CSV cực nhanh, không cần dựng server. | Không phải máy chủ dịch vụ phân tán phục vụ tải ghi/đọc đồng thời cao từ nhiều người dùng và luồng sự kiện liên tục như MergeTree. |
| **RocksDB / Cassandra** *(LSM-tree K-V / Wide-column)* | **LSM-tree** (MemTable trên RAM + WAL + SSTable bất biến phân tầng + Bloom Filter). | Chịu tải ghi ngẫu nhiên từng dòng rất cao và tra cứu điểm theo khóa (*key-value lookup*) nhanh. | Tối ưu cho truy xuất theo khóa từng bản ghi chứ không nén theo từng cột độc lập và không tối ưu cho thực thi vector hóa SIMD quét hàng trăm triệu dòng. |

Từ Bảng 1.2 có thể thấy rõ **lý do lựa chọn đối chứng trong báo cáo này**: điểm sáng lớn nhất của ClickHouse nằm ở **động cơ MergeTree** — một biến thể lấy cảm hứng từ LSM-Tree nhưng bỏ qua tầng MemTable truyền thống, tổ chức dữ liệu theo cột nén độc lập và dùng **chỉ mục thưa kết hợp sắp xếp vật lý liên tục**. Trong báo cáo, Chương 4 sử dụng **PostgreSQL 18.6** (với cả chỉ mục dày `B-tree` lẫn chỉ mục dải khối `BRIN` vốn có triết lý gần với *sparse index*) làm đối trọng thực nghiệm trực diện trên cùng phần cứng để định lượng ranh giới giao cắt hiệu năng giữa kiến trúc Heap truyền thống và MergeTree.

### Các bài toán trọng tâm và Giới hạn thiết kế của ClickHouse

* **Bài toán trọng tâm:** (i) Phân tích dữ liệu lớn quy mô Terabyte–Petabyte với chi phí phần cứng tối ưu [A1]; (ii) Truy vấn tổng hợp đa chiều tùy biến (*ad-hoc aggregation*) trên trường có lực lượng lớn (*high cardinality*) qua thuật toán xác suất HyperLogLog; (iii) Giám sát hạ tầng, Log, Clickstream và IoT Telemetry [B1, B2]; (iv) Bảng điều khiển thời gian thực qua `Materialized Views` tính toán gia tăng [S16].
* **Đánh đổi thiết kế & Phản mẫu (Anti-patterns):** Không phù hợp làm cơ sở dữ liệu giao dịch OLTP (chèn từng dòng gây lỗi `Too many parts`); cập nhật/xóa điểm (`ALTER TABLE ... UPDATE/DELETE`) rất nặng do tính bất biến của phân đoạn; phép `JOIN` hai bảng lớn dễ gây tràn RAM (Hash Join mặc định) [A1, S2].

## 1.3. Khái quát các đặc điểm nổi bật (6 trụ cột kiến trúc)

Hiệu năng của ClickHouse được định hình bởi 6 trụ cột kỹ thuật cốt lõi [A1, S1]:

1. **Lưu trữ hướng cột thuần túy (True Column-oriented Storage):** Mỗi cột được tách thành tệp vật lý độc lập (`.bin`), loại bỏ hoàn toàn chi phí đọc I/O của các cột không xuất hiện trong câu lệnh SQL [A2].
2. **Nén dữ liệu chuyên biệt (Advanced Data Compression):** Miền giá trị đồng nhất cho phép kết hợp các thuật toán nén đa dụng (`LZ4`, `ZSTD`) cùng bộ mã hóa chuyên biệt (`Delta`, `DoubleDelta`, `T64`). Tỷ lệ nén thực tế phụ thuộc vào kiểu dữ liệu: chuỗi văn bản lặp lại có thể đạt trên `10×–20×`, trong khi các cột số nguyên có entropy cao đạt khoảng `2×–3×` (phù hợp với số đo thực nghiệm `2,31×` tại Chương 3) [A1, S18].
3. **Xử lý truy vấn song song đa luồng (Multi-core Parallel Processing):** Tự động phân chia khối dữ liệu cho toàn bộ các nhân CPU vật lý để xử lý đồng thời trên đồ thị luồng thực thi (*execution pipeline*).
4. **Thực thi vector hóa (Vectorized Query Execution & SIMD):** Dữ liệu được nạp vào bộ nhớ đệm L1/L2 theo từng khối mảng cột liền kề, kích hoạt tập lệnh SIMD (`AVX2`, `AVX-512`) để tính toán trên nhiều phần tử trong một chu kỳ lệnh [A1, A2].
5. **Động cơ lưu trữ họ MergeTree (MergeTree Engine Family):** Dữ liệu ghi theo lô thành các phân đoạn bất biến đã sắp xếp theo `ORDER BY`, kết hợp chỉ mục chính thưa (`primary.idx`) nạp thường trực trong RAM và tiến trình hợp nhất nền (*background merges*) bất đồng bộ [S1, S2]. *(Đây là trọng tâm giải phẫu tại Chương 2–4).*
6. **Khả năng mở rộng phân tán (Distributed Scalability):** Hỗ trợ mở rộng ngang theo kiến trúc *Shared-Nothing* qua cơ chế phân mảnh (*Sharding*) và nhân bản (*Replication*) điều phối bởi **ClickHouse Keeper** (thuật toán đồng thuận Raft viết bằng C++) [A1, S19].

## 1.4. Hệ sinh thái và ứng dụng công nghiệp

ClickHouse hỗ trợ giao tiếp qua giao thức **Native TCP** nhị phân tốc độ cao và **HTTP RESTful API**, tích hợp tự nhiên với các công cụ trực quan hóa (`Grafana`, `Superset`, `Metabase`) và hệ sinh thái đường ống dữ liệu (`Kafka`, `Flink`, `Spark`, `Debezium CDC`) [S1]. Trong công nghiệp, nhiều tổ chức lớn đã chuyển dịch các hệ thống dữ liệu lớn sang ClickHouse:

* **Cloudflare (Phân tích lưu lượng mạng):** Chuyển đổi nền tảng phân tích log HTTP/DNS quy mô hàng triệu yêu cầu mỗi giây sang `ReplicatedMergeTree`, cải thiện mạnh độ trễ và năng lực phát hiện tấn công DDoS [B1].
* **Uber (Nền tảng giám sát Log):** Thay thế cụm chỉ mục đảo Lucene bằng ClickHouse, tận dụng lưu trữ cột và nén dữ liệu để cắt giảm đáng kể tài nguyên phần cứng lưu trữ log tập trung [B2].
* **Bloomberg (Dữ liệu thị trường tài chính):** Quản lý hàng nghìn tỷ bản ghi biến động giá, tận dụng xử lý vector hóa SQL để tính toán chỉ số thị trường với độ trễ dưới một giây [B3].

## 1.5. Tổng kết Chương 1

Chương 1 đã định vị triết lý thiết kế, ưu/nhược điểm và vị thế của ClickHouse cạnh các DBMS khác. Thay vì dừng ở giới thiệu bề nổi, Chương 2 sẽ giải phẫu sâu điểm sáng quyết định năng lực lưu trữ của ClickHouse — **động cơ MergeTree** — trước khi đưa toàn bộ cơ chế này vào kiểm chứng định lượng tại Chương 3 và đối chứng trực diện với PostgreSQL 18.6 tại Chương 4.

---

# CHƯƠNG 2. MERGETREE: TỔ CHỨC DỮ LIỆU, CHỈ MỤC THƯA VÀ CƠ CHẾ MERGE

Nếu Chương 1 đã định vị ClickHouse trên bản đồ các hệ quản trị cơ sở dữ liệu, thì Chương 2 tập trung giải phẫu thành phần cốt lõi tạo nên năng lực lưu trữ và truy xuất của hệ thống: **động cơ lưu trữ MergeTree** [S1, S2]. Phạm vi nghiên cứu lý thuyết và thực nghiệm ở Chương 2–3 được giới hạn chặt chẽ trên kiến trúc một nút máy chủ đơn lẻ (*single-node ClickHouse*) với tập dữ liệu luồng sự kiện web (*clickstream*) chỉ ghi nối tiếp (*append-only*).

## 2.1. Bối cảnh và vị trí của MergeTree

### 2.1.1. Đặc trưng tải công việc Clickstream và Yêu cầu đối với tầng lưu trữ

Trong các hệ thống phân tích lưu lượng web (như tập dữ liệu chuẩn ClickBench trích xuất từ môi trường sản xuất của Yandex.Metrica [B4, B5]), mỗi hành vi tương tác của người dùng được ghi nhận dưới dạng một bản ghi bất biến theo thời gian. Tải công việc này đặt ra bài toán tối ưu hóa đa mục tiêu cho tầng lưu trữ:

* **Thông lượng nạp cao (High Ingestion Throughput):** Tiếp nhận hàng trăm nghìn dòng mỗi giây mà không làm nghẽn luồng đọc.
* **Độ trễ truy vấn đọc thấp (Low Read Latency):** Quét hàng chục triệu bản ghi nhưng chỉ chiếu trên một số cột, kết hợp các bộ lọc phạm vi trên website (`CounterID`) và thời gian (`EventDate`).
* **Hiệu quả nén vật lý (Storage Efficiency):** Giảm thiểu chi phí đĩa cứng mà không làm suy giảm tốc độ giải nén dữ liệu trong bộ nhớ đệm CPU.

**Giới hạn phạm vi nghiên cứu Chương 2–3:** Để cô lập chính xác hành vi nội tại của động cơ MergeTree, hai trạng thái tải được khảo sát tách biệt: (i) truy vấn đọc (`SELECT`) trên tập dữ liệu tĩnh đã chuẩn hóa cấu trúc phân đoạn; và (ii) nạp dữ liệu theo lô (`Batch INSERT`) để quan sát chi phí sinh phân đoạn và hợp nhất nền tự nhiên. Bài toán luồng đầu-cuối (*producer-to-dashboard*) được giải quyết chuyên sâu tại Chương 5.

### 2.1.2. Tổng quan kiến trúc thực thi tối thiểu

Cần phân biệt rõ giữa **Hệ quản trị cơ sở dữ liệu (DBMS)** và **Động cơ lưu trữ (Storage Engine)**. ClickHouse là một hệ thống DBMS hoàn chỉnh đảm nhận giao tiếp mạng, phân tích cú pháp SQL, lập kế hoạch truy vấn và điều phối tài nguyên; trong khi đó, MergeTree là động cơ lưu trữ tầng dưới cùng, chịu trách nhiệm trực tiếp về định dạng bố trí tệp vật lý trên đĩa, cấu trúc chỉ mục thưa, cơ chế tạo phân đoạn khi ghi và cắt tỉa dữ liệu khi đọc [S1, S2].

Khác với PostgreSQL nơi chỉ mục (`B-tree`, `BRIN`) là các cấu trúc dữ liệu phụ trợ tách rời trỏ vào tệp Heap qua định danh dòng (`TID`), MergeTree tích hợp chặt chẽ thứ tự sắp xếp vật lý, chỉ mục thưa và tệp nén thành một thể thống nhất trong từng phân đoạn. Khi một truy vấn đi từ trình khách vào máy chủ ClickHouse, nó đi qua chuỗi xử lý năm tầng (**Hình 2.1**):

1. **Tầng Giao tiếp & Phân tích (Client & Parser/Analyzer):** Tiếp nhận chuỗi truy vấn qua giao thức Native TCP hoặc HTTP, phân tích cú pháp thành Cây cú pháp trừu tượng (AST).
2. **Tầng Lập kế hoạch (Planner/Optimizer):** Biến đổi AST thành kế hoạch thực thi logic và vật lý (`QueryPlan`), đẩy các bộ lọc xuống tầng lưu trữ (*predicate pushdown*).
3. **Tầng Thực thi (Execution Engine):** Xây dựng đồ thị luồng thực thi (`QueryPipeline`) dựa trên lưu trữ hướng cột, thực thi vector hóa theo khối khớp bộ nhớ đệm L1/L2 để kích hoạt SIMD, và xử lý đa luồng song song trên các nhân vật lý [S1].
4. **Động cơ lưu trữ MergeTree:** Luồng đọc sử dụng chỉ mục chính thưa (`primary.idx`) và tệp đánh dấu (`marks`) để định vị hạt dữ liệu (`granules`). Luồng ghi sắp xếp dữ liệu theo `ORDER BY`, nén và ghi thành các phân đoạn bất biến (`Data Parts`), đồng thời kích hoạt bể luồng nền để hợp nhất các phân đoạn nhỏ thành lớn.
5. **Tầng Lưu trữ vật lý (Disk Storage):** Hệ thống tệp chứa các thư mục phân đoạn, tệp cột nén (`.bin`), tệp đánh dấu (`.mrk2`/`.mrk3`) và tệp chỉ mục.

*(Hình 2.1. Luồng xử lý truy vấn tối thiểu trong ClickHouse và vị trí của động cơ MergeTree [S1, S2]).*

## 2.2. Data parts và đường ghi (Write Path) của MergeTree

Khác biệt căn bản nhất giữa MergeTree và các động cơ lưu trữ B-Tree truyền thống nằm ở cách thức xử lý luồng ghi dữ liệu. Thay vì cập nhật trực tiếp vào một cấu trúc tệp toàn cục thông qua bộ đệm trang (*page buffer pool*) và nhật ký tiền ghi (*Write-Ahead Log – WAL*), MergeTree áp dụng kiến trúc phân đoạn bất biến lấy cảm hứng từ cấu trúc cây ghép nối nhật ký (LSM-Tree), nhưng loại bỏ hoàn toàn cấu trúc MemTable trên RAM trong luồng ghi mặc định [S1, S3].

### 2.2.1. Từ khối dữ liệu trong RAM đến phân đoạn bất biến

Khi câu lệnh `INSERT` gửi tới ClickHouse, dữ liệu được xử lý tuần tự qua năm bước trong RAM trước khi chạm xuống đĩa (**Hình 2.2**):

1. **Phân khối (Block Parsing & Conversion):** Luồng byte đầu vào được chuyển thành các khối mảng cột (`Block`). Kích thước tối đa của mỗi khối được kiểm soát bởi tham số `max_insert_block_size` (mặc định `1.048.576` dòng) [S9].
2. **Tách khối theo Khóa phân vùng (Partition Splitting):** Nếu bảng có khai báo `PARTITION BY expr`, khối dữ liệu được tách thành các khối con độc lập sao cho mỗi khối con chỉ chứa các bản ghi thuộc về duy nhất một giá trị phân vùng (`partition_id`) [S2, S3].
3. **Sắp xếp vật lý theo `ORDER BY`:** Trong phạm vi từng khối con, các dòng dữ liệu được sắp xếp trong RAM theo thứ tự từ điển của biểu thức `ORDER BY`. Đối với động cơ `MergeTree` tiêu chuẩn, quá trình này không tự động khử trùng lặp các dòng có cùng khóa; mọi dòng trùng khóa vẫn được giữ nguyên và xếp liền kề nhau [S2].
4. **Phân cắt Granule, Nén cột và Sinh chỉ mục:** Dữ liệu sắp xếp của từng cột được cắt thành các hạt logic (`granules`, mặc định `8.192` dòng). Hệ thống trích xuất giá trị khóa của dòng đầu tiên mỗi granule để ghi vào tệp chỉ mục thưa (`primary.idx`), đồng thời nén dữ liệu từng cột thành các khối nén (*compressed blocks*) ghi xuống tệp `.bin`, và lưu tọa độ giải nén vào tệp đánh dấu (`marks`) [S3, S4].
5. **Công bố phân đoạn nguyên tử (Atomic Part Publication):** Dữ liệu được ghi vào thư mục tạm `tmp_insert_...`. Khi hoàn tất, thư mục được đổi tên nguyên tử thành `<partition_id>_<min_block_num>_<max_block_num>_<level>` (ví dụ: `201307_1_1_0`) và kích hoạt trạng thái hoạt động (`active = 1`) trong bộ nhớ máy chủ [S3, S6].

*(Hình 2.2. Đường ghi bất biến của MergeTree từ khối dữ liệu trong RAM đến tệp phân đoạn trên đĩa [S1, S3, S4]).*

**Lưu ý kỹ thuật về số lượng Part sinh ra từ một lệnh `INSERT`:** Số lượng Data Part vật lý được tạo ra bởi một câu lệnh `INSERT` đơn lẻ có thể lớn hơn `1` và phụ thuộc vào ba yếu tố [S3, S9]: (i) số lượng khối đầu vào vượt ngưỡng `max_insert_block_size` hoặc `min_insert_block_size_rows`/`bytes`; (ii) độ phân tán của khóa phân vùng (`k` giá trị phân vùng sinh tối thiểu `k` thư mục Part riêng); và (iii) mức độ song song khi nạp (`max_insert_threads > 1`).

### 2.2.2. Cấu trúc vật lý của Data Part: Định dạng Wide/Compact, Dữ liệu cột và Marks

Tùy thuộc vào kích thước dữ liệu so với ngưỡng `min_bytes_for_wide_part` (mặc định `10 MiB`) và `min_rows_for_wide_part`, MergeTree tự động lựa chọn một trong hai định dạng vật lý:

* **Compact Part:** Toàn bộ dữ liệu của tất cả các cột được ghi chung vào một tệp `data.bin`, và toàn bộ dấu vị trí lưu trong `data.mrk3`. Áp dụng cho các phân đoạn nhỏ nhằm tiết kiệm inode hệ thống tệp.
* **Wide Part:** Mỗi cột được tách thành tệp dữ liệu nén riêng `<column>.bin` và tệp đánh dấu tương ứng `<column>.mrk2` (hoặc `.mrk3`). Đây là định dạng tối ưu cho đọc quét cột độc lập.

**Bảng 2.1.** Cấu trúc tệp tiêu biểu trong thư mục Data Part (định dạng Wide)

| Tên tệp vật lý | Vai trò trong kiến trúc lưu trữ và truy xuất |
| :--- | :--- |
| `<column>.bin` | Chứa dữ liệu của cột `<column>` chia thành các khối nén liên tiếp (*Compressed Blocks*, mặc định bằng thuật toán LZ4) [S3]. |
| `<column>.mrk2` / `.mrk3` / `.cmrk2` | Tệp đánh dấu (*Marks file*) đóng vai trò cầu nối định vị giữa chỉ mục logic (Granule) và vị trí byte vật lý trong tệp `<column>.bin` [S4]. |
| `primary.idx` / `primary.cidx` | Tệp lưu trữ Chỉ mục chính thưa (*Sparse Primary Index*), chứa giá trị của biểu thức `PRIMARY KEY` tại dòng đầu tiên của mỗi Granule [S4]. |
| `count.txt` | Lưu tổng số bản ghi hiện có bên trong Data Part (hỗ trợ trả về tức thì các truy vấn `SELECT count()`) [S3]. |
| `columns.txt` | Danh sách tên và kiểu dữ liệu chính xác của mọi cột tại thời điểm Data Part được tạo ra (hỗ trợ tiến hóa lược đồ) [S3]. |
| `checksums.txt` | Bảng tổng kiểm tra (*hash checksums*) và kích thước của mọi tệp trong thư mục nhằm bảo đảm toàn vẹn dữ liệu trên đĩa [S3]. |
| `minmax_<col>.idx` | Lưu giá trị nhỏ nhất (Min) và lớn nhất (Max) của các cột tham gia vào biểu thức khóa phân vùng (`PARTITION BY`) [S2]. |

*(Lưu ý học thuật: Phần mở rộng của tệp đánh dấu và tệp chỉ mục như `.mrk2`, `.mrk3`, `.cmrk2` hay `primary.idx` / `primary.cidx` phụ thuộc vào phiên bản máy chủ ClickHouse, định dạng Wide/Compact, cấu hình `adaptive_granularity` và việc bật/tắt nén marks).*

**Phân biệt giữa Granule, Compressed Block và cơ chế trỏ hai tầng của Marks:**
* **Granule (Hạt dữ liệu logic):** Là đơn vị dữ liệu nhỏ nhất và không thể chia cắt mà ClickHouse đọc khi sử dụng chỉ mục, được định nghĩa theo số lượng hàng thông qua tham số `index_granularity` (mặc định `8.192` hàng) [S1, S4].
* **Compressed Block (Khối nén vật lý):** Tệp `<column>.bin` không nén từng Granule riêng lẻ mà gom dữ liệu thành từng khối nén theo số byte chưa nén (`min_compress_block_size` mặc định `65.536 bytes = 64 KiB`, `max_compress_block_size` mặc định `1.048.576 bytes = 1 MiB`). Một Compressed Block có thể chứa nhiều Granule (với cột hẹp như `UInt8`), hoặc ngược lại, một Granule có thể trải dài qua nhiều Compressed Block (với cột chứa chuỗi URL dài).

Do các khối nén có độ dài biến thiên, tệp đánh dấu (`Marks file`) lưu trữ bộ ba tọa độ cho mỗi Granule thứ `i` (**Hình 2.2**): (1) `offset_in_compressed_file` (độ lệch byte từ đầu `.bin` tới khối nén chứa Granule `i`); (2) `offset_in_decompressed_block` (độ lệch byte bên trong khối đã giải nén trên RAM); và (3) `rows_num` (số hàng thực tế trong Granule đó). Nhờ tọa độ hai tầng này, ClickHouse chỉ việc gọi `lseek` tới đúng khối `64 KiB–1 MiB` cần thiết, giải nén duy nhất khối đó vào RAM và trích xuất đúng hạt dữ liệu mục tiêu [S4].

### 2.2.3. Tổ chức phân cấp Table – Partition – Part – Granule

Để quản lý vòng đời dữ liệu và tối ưu hóa phạm vi quét, MergeTree tổ chức dữ liệu theo mô hình phân cấp 4 tầng chặt chẽ (**Hình 2.3**): **Table** (bảng logic) → **Partition** (tập hợp các part cùng giá trị `PARTITION BY`) → **Data Part** (thư mục vật lý bất biến) → **Granule** (lát cắt 8.192 hàng sắp xếp theo `ORDER BY`). Quy tắc bất biến quan trọng: **các Data Part thuộc hai Partition khác nhau không bao giờ được gộp chung với nhau bởi tiến trình nền** [S3, S5].

*(Hình 2.3. Quan hệ phân cấp giữa Table, Partition, Data Part và Granule trong động cơ MergeTree [S2, S3]).*

Trên đĩa, siêu dữ liệu lược đồ bảng nằm tại `metadata/<database>/<table>.sql`, còn toàn bộ dữ liệu thực lưu tách biệt trong cây thư mục nguyên tử `store/<table_uuid>/<partition_id>_<min_block_num>_<max_block_num>_<level>/` [S2, S3].

**Vai trò thực sự của `PARTITION BY` và lý do không thay thế được `ORDER BY`:** Mệnh đề `PARTITION BY` không phải chỉ mục tìm kiếm chi tiết mà phục vụ hai mục đích: (1) quản trị vòng đời dữ liệu cấp độ vĩ mô (`DROP PARTITION`, `TTL`, di chuyển đĩa nóng/lạnh); và (2) cắt tỉa phân vùng (*Partition Pruning*) qua tệp `minmax_<col>.idx`. Nếu chọn khóa `PARTITION BY` có độ phân tán cao (*high cardinality* như `UserID` hoặc theo phút), một lệnh `INSERT` sẽ bị xé lẻ thành hàng trăm part thuộc các phân vùng khác nhau và không thể gộp chung, trực tiếp gây lỗi `Too many parts` [S2, S9].

**Phân biệt minh họa ClickBench gốc và Lược đồ thực nghiệm Chương 3–4:** Trong lược đồ ClickBench `hits` gốc (105 cột, có `PARTITION BY toYYYYMM(EventDate)` [B5]), câu lệnh kiểm tra bảng hệ thống `system.parts` giúp quan sát trực tiếp từng phân đoạn theo phân vùng tháng:

```sql
-- Truy vấn kiểm tra trạng thái vật lý của các phân đoạn trong system.parts [S6]
SELECT
    partition,
    name AS part_name,
    part_type,
    active,
    marks,
    rows,
    formatReadableSize(bytes_on_disk) AS size_on_disk,
    formatReadableSize(data_uncompressed_bytes) AS uncompressed_size,
    round(data_uncompressed_bytes / bytes_on_disk, 2) AS compression_ratio
FROM system.parts
WHERE (database = 'default') AND (table = 'hits') AND (active = 1)
ORDER BY name ASC;
```

Tuy nhiên, do toàn bộ dữ liệu ClickBench thực tế đều tập trung trong duy nhất một tháng (`201307`), việc phân vùng theo tháng không tạo ra khác biệt khi cắt tỉa truy vấn. Nhằm cô lập tuyệt đối tác động của khóa sắp xếp `ORDER BY`, độ mịn `index_granularity` và tiến trình hợp nhất nền trên máy tính nghiên cứu, toàn bộ các thực nghiệm tại **Chương 3 và Chương 4** sử dụng **lược đồ rút gọn 12 cột** và **không khai báo `PARTITION BY`** (tất cả dữ liệu nằm trong một phân vùng mặc định `tuple()`) [B5, M6].

*(Liên hệ Thực nghiệm E3: Cơ chế sinh phân đoạn ở Mục 2.2.1 giải thích trực tiếp hiện tượng ở Thực nghiệm E3: khi giữ nguyên tổng khối lượng dữ liệu nạp 30M dòng nhưng giảm kích thước lô `Batch INSERT`, số lượng Data Part cấp 0 sinh ra tăng tỷ lệ nghịch với kích thước lô, kéo theo áp lực hợp nhất nền được ghi nhận qua `system.part_log` [S8]).*

## 2.3. Khóa sắp xếp (`ORDER BY`), Khóa chính và Chỉ mục chính thưa

### 2.3.1. Phân biệt vai trò của `ORDER BY` và `PRIMARY KEY`

Trong MergeTree, `ORDER BY` và `PRIMARY KEY` đảm nhận hai vai trò kỹ thuật tách biệt [S2, S4]:

* **Khóa sắp xếp (`ORDER BY`):** Xác định thứ tự sắp xếp vật lý thực tế (theo thứ tự từ điển) của các dòng dữ liệu bên trong từng Data Part và thứ tự trộn dữ liệu khi hợp nhất nền.
* **Khóa chính (`PRIMARY KEY`):** Xác định biểu thức khóa được trích xuất giá trị tại dòng đầu tiên của mỗi Granule để ghi vào tệp chỉ mục thưa `primary.idx` (nạp thường trực vào RAM). Nếu không khai báo riêng, ClickHouse mặc định gán `PRIMARY KEY` trùng với `ORDER BY`; nhưng kỹ sư dữ liệu có thể khai báo `PRIMARY KEY` là tiền tố ngắn hơn của `ORDER BY` để giữ tệp chỉ mục RAM nhỏ gọn. **Khẳng định cốt lõi:** Khóa chính trong MergeTree **không phải ràng buộc duy nhất (*unique constraint*)** như trong RDBMS truyền thống [S2, S4].

Trong Thực nghiệm E1 (Chương 3), ba phương án sắp xếp được đưa vào đối chứng: `K0 = tuple()` (không sắp xếp theo cột dữ liệu), `K1 = (CounterID, EventDate)` (ưu tiên website) và `K2 = (EventDate, CounterID)` (ưu tiên thời gian).

### 2.3.2. Chỉ mục thưa và lựa chọn khoảng đọc

Mỗi data part sở hữu một chỉ mục chính thưa lưu giá trị `PRIMARY KEY` của hàng đầu tiên trong mỗi granule thay vì lập mục cho từng hàng. Để minh họa cơ chế, **Hình 2.4** xét 16 bản ghi giả định gồm hai `CounterID` (100, 200), bốn ngày (15–18) với `4` hàng/granule và ba bộ lọc: `W1` (`CounterID = 100`), `W2` (ngày 17–18) và `W3` (kết hợp hai điều kiện). Dấu `✓` chỉ granule thực sự chứa hàng khớp điều kiện lọc (trong thực tế, chỉ mục thưa chỉ lưu các mốc biên nên có thể chọn thêm granule kề biên không chứa kết quả, được xác minh bằng `EXPLAIN`) [S2, S4, S4a].

*(Hình 2.4. Phân bố granule chứa hàng khớp bộ lọc với K0, K1 và K2 trên 16 bản ghi giả định; dấu ✓ không phải kết quả chọn marks của ClickHouse. Nguồn: Nhóm xây dựng theo [S2, S4]).*

Từ cấu trúc trên, ClickHouse kích hoạt hai giải thuật tìm kiếm khác biệt [S4a]:

1. **Tìm kiếm nhị phân liên tục (Binary Search):** Khi điều kiện lọc chứa cột **đứng đầu** khóa sắp xếp (ví dụ `W1` trên `K1` hoặc `W2` trên `K2`). Do toàn bộ tệp chỉ mục được sắp xếp đơn điệu theo tiền tố, ClickHouse thực hiện tìm kiếm nhị phân với độ phức tạp $O(\log_2 M)$ (với $M$ là tổng số Marks), thu gọn vùng đọc về đúng `1` dải hạt liên tục.
2. **Tìm kiếm loại trừ tổng quát (Generic Exclusion Search):** Khi truy vấn chỉ lọc trên cột **đứng sau** của khóa phức hợp mà khuyết cột tiền tố (ví dụ `W1` lọc `CounterID = 100` trên cấu hình `K2` có `EventDate` đứng trước). Do `CounterID` lặp lại theo từng ngày, thứ tự toàn cục bị phá vỡ. ClickHouse duyệt qua từng cặp mốc liên tiếp $[K_i, K_{i+1}]$ trong RAM: nếu khoảng giá trị không giao cắt với điều kiện lọc, hạt đó bị loại trừ. Nếu cột đứng trước có lực lượng phân biệt (*cardinality*) thấp (ví dụ 17 ngày trong tập thực nghiệm), giải thuật vẫn cắt tỉa được phần lớn bảng; ngược lại, nếu cột đứng trước có *cardinality* quá cao, chỉ mục trở nên vô hiệu [S4, S4a].

**Bảng 2.2.** Khả năng tận dụng tiền tố khóa theo nhóm bộ lọc khảo sát (đánh giá định tính theo [S4, S4a])

| Bộ lọc | K1: `(CounterID, EventDate)` | K2: `(EventDate, CounterID)` | Nội dung kiểm chứng |
| :--- | :--- | :--- | :--- |
| **W1: `CounterID`** | Có tiền tố trực tiếp (Binary Search) | Không có tiền tố (Generic Exclusion) | Granules (`EXPLAIN`) |
| **W2: `EventDate`** | Không có tiền tố (Generic Exclusion) | Có tiền tố trực tiếp (Binary Search) | Granules (`EXPLAIN`) |
| **W3: Kết hợp** | Tiền tố `CounterID` | Tiền tố `EventDate` | Granules; độ trễ |
| **W4: `RegionID`** | Không thuộc khóa | Không thuộc khóa | Granules; `read_rows` |

### 2.3.3. Khóa sắp xếp theo Workload và Hiệu ứng nén dữ liệu

Việc lựa chọn khóa sắp xếp phụ thuộc trực tiếp vào mẫu truy vấn chiếm ưu thế (*workload*), *cardinality* và phân bố dữ liệu. Thứ tự sắp xếp cũng ảnh hưởng đến khả năng nén do các giá trị giống nhau được đặt liền kề nhau. Vì vậy, Thực nghiệm E1 đồng thời đo số granule được chọn, `read_rows`, `read_bytes`, độ trễ truy vấn và dung lượng nén trên đĩa [S2, S4].

## 2.4. Granules, Marks và Quá trình đọc có chọn lọc

### 2.4.1. `index_granularity` và Tính đại diện của cấu hình thực nghiệm

Tham số `index_granularity` quy định số dòng tối đa trong một hạt (mặc định `8.192`). Cơ chế thích ứng (*adaptive granularity*) còn xét thêm giới hạn dung lượng `index_granularity_bytes` (mặc định `10 MiB`). Trong Thực nghiệm E2 (Mục 3.4), nhóm cố định `index_granularity_bytes = 0` để vô hiệu hóa giới hạn byte và cô lập biến số `g ∈ {2.048, 8.192, 32.768}`. Với lược đồ 12 cột hẹp (`44 byte/dòng`), một hạt `8.192` dòng chỉ chiếm `8.192 × 44 B ≈ 360 KiB ≪ 10 MiB`; do đó thiết lập này hoàn toàn đại diện cho hành vi mặc định thực tế trên lược đồ hẹp [S2]. *(Ngược lại, như sẽ kiểm chứng ở Chương 5, khi bảng chứa cột trạng thái `AggregateFunction` nặng vài KiB/dòng, ngưỡng `10 MiB` sẽ tự động kích hoạt adaptive granularity).*

### 2.4.2. Đường đọc và Công cụ kiểm chứng kế hoạch (`EXPLAIN`)

Với truy vấn `SELECT`, MergeTree xác định các data part phù hợp, dùng `primary.idx` để chọn khoảng granule (*mark ranges*), đọc tọa độ từ tệp marks, giải nén các khối cột cần thiết rồi lọc và tổng hợp. Để cô lập tác động thuần túy của chỉ mục thưa trong E1/E2, nhóm tắt `PREWHERE` tự động, không tạo skip index hay projection và tắt cache. Hai câu lệnh sau minh họa cách lấy bằng chứng kế hoạch trước khi đối chiếu với `system.query_log` [S7, S10]:

```sql
EXPLAIN indexes = 1 SELECT count(), sum(ResolutionWidth)
FROM hits_k1
WHERE CounterID = 3258 AND EventDate >= toDate('2013-07-15') AND EventDate < toDate('2013-07-23')
SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0;

EXPLAIN ESTIMATE SELECT count(), sum(ResolutionWidth)
FROM hits_k1
WHERE CounterID = 3258 AND EventDate >= toDate('2013-07-15') AND EventDate < toDate('2013-07-23')
SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0;
```

### 2.4.3. Mô hình giải tích kích thước chỉ mục và Đánh đổi tài nguyên

Xét một active part gồm $N$ hàng với kích thước hạt cố định $g$ (`index_granularity_bytes = 0`). Số lượng granule/marks ước lượng là $M \approx \lceil N / g \rceil$. Nếu chỉ mục chọn $k$ granule, phạm vi hàng cần đọc xấp xỉ $R_{\text{est}} \approx \min(N, k \times g)$. Với $s_{\text{key}}$ là tổng độ rộng byte của một bộ khóa trong mỗi mục chỉ mục, kích thước phần giá trị khóa trên RAM là $I_{\text{key}} \approx M \times s_{\text{key}}$ [S2, S4].

*(Hình 2.5. So sánh granule nhỏ/lớn trên 16 hàng giả định: xanh đậm là hàng 5–6 thỏa lọc, xanh nhạt là các hàng khác cùng granule phải đọc [S2, S4]).*

**Ví dụ tính toán:** Với $N = 30.000.000$ và $g = 8.192$, ta có $M = \lceil 30.000.000 / 8.192 \rceil = 3.663$ marks. Khóa `K1 = (CounterID Int32, EventDate Date)` có độ rộng $s_{\text{key}} = 4 + 2 = 6$ byte, suy ra $I_{\text{key}} = 3.663 \times 6 = 21.978$ byte (`~21,46 KiB`). Công thức này chỉ tính phần giá trị khóa, chưa gồm metadata, tệp marks của từng cột và chi phí cấp phát phụ trợ. Các thông số thực tế được thu thập từ `system.parts` (`marks`, `marks_bytes`, `primary_key_bytes_in_memory`) [S6].

## 2.5. Tiến trình Hợp nhất nền (Background Merges) và Đánh đổi trong Nạp dữ liệu

### 2.5.1. Tạo nhiều part và Background merges

MergeTree lưu bảng thành các data part bất biến. **Background merge** là tiến trình nền đọc các part trong cùng partition, trộn dữ liệu theo thứ tự khóa (`k-way merge sort`), tạo lại chỉ mục và ghi part mới ở trạng thái `active`, đồng thời đánh dấu các part nguồn là `inactive` để dọn dẹp về sau (**Hình 2.6**) [S3, S5]. Động cơ `MergeTree` tiêu chuẩn **không** áp đặt khóa duy nhất và **không** tự khử trùng khi merge.

*(Hình 2.6. Minh họa do nhóm vẽ: A, B, C cùng partition được hợp nhất thành D. Sơ đồ không phải số đo thực nghiệm; cơ chế theo [S3, S5]).*

### 2.5.2. Kích thước batch, số request và chi phí merge

Với $N$ dòng đầu vào và tối đa $B$ dòng/lô, chương trình gửi nối tiếp cần $\lceil N / B \rceil$ yêu cầu `INSERT` (**Hình 2.7**) [S9]. Lô nhỏ tạo nhiều part nhỏ, tăng chi phí xử lý yêu cầu (`fsync`, giao thức) và áp lực hợp nhất nền. Lô lớn phân bổ chi phí này trên nhiều dòng hơn nhưng đòi hỏi bộ nhớ đệm và độ trễ gom lô lớn hơn tại phía ứng dụng phát sự kiện. Cần tách biệt rạch ròi thời gian nhận phản hồi nạp ($T_{\text{ACK}}$), thời gian chờ ổn định và tổng thời lượng các thao tác merge (`Σduration_ms` có thể chạy song song và chồng lấn lên $T_{\text{ACK}}$) [S5, S8].

*(Hình 2.7. Các bước xử lý một yêu cầu INSERT đồng bộ để tạo data part. Nguồn: ClickHouse Docs, "Selecting an insert strategy" [S9] · CC BY-NC-SA 4.0).*

### 2.5.3. Quan sát bằng system tables

ClickHouse cung cấp ba bảng hệ thống cốt lõi để giám sát vòng đời part: `system.parts` (trạng thái part hiện tại), `system.merges` (merge đang chạy) và `system.part_log` (lịch sử sự kiện `NewPart` và `MergeParts`) [S6, S8, S13].

**Bảng 2.3.** Đại lượng phục vụ Thực nghiệm E3 và nguồn trích xuất ($N$: số dòng đầu vào; $r$: `read_rows` của một sự kiện `MergeParts` thành công)

| Đại lượng | Nguồn lấy | Ý nghĩa và giới hạn |
| :--- | :--- | :--- |
| $T_{\text{ACK}}$ (s); $N / T_{\text{ACK}}$ (dòng/s) | Đồng hồ chương trình nạp | Thời gian từ request đầu đến ACK cuối; tốc độ nạp. Không đo chờ gom lô ở producer. |
| Số active part; $\Sigma\text{bytes\_on\_disk}$ | `system.parts` (`active = 1`) | Trạng thái tại thời điểm lấy mẫu; chưa phản ánh đỉnh dung lượng đĩa tạm lúc merge. |
| Merge đang chạy; `elapsed`/`progress` | `system.merges` | Quan sát tức thời; không thay thế nhật ký lịch sử. |
| $\Sigma\text{duration\_ms}$; $\Sigma\text{read\_rows}$ | `system.part_log` (`MergeParts`) | Tổng thời gian/lượt dòng đọc ở các lượt merge thành công (`error = 0`). |
| $\Sigma r / N$; chờ ổn định (s) | Nhóm tính từ log/đồng hồ | Chỉ số dẫn xuất (hệ số đọc lặp gộp) do nhóm định nghĩa; không phải write amplification vật lý của SSD. |

Nếu part nhỏ tích tụ nhanh hơn năng lực hợp nhất nền, ClickHouse sẽ từ chối lệnh ghi với lỗi `"Too many parts"` [S15]. Thực nghiệm E3 giữ merge tự nhiên thay vì ép `OPTIMIZE TABLE ... FINAL` [S14].

## 2.6. Phạm vi áp dụng: Các biến thể họ MergeTree và Cầu nối sang Chương 3

Bên cạnh `MergeTree` tiêu chuẩn, ClickHouse cung cấp các biến thể chuyên dụng cho các bài toán đặc thù:

* **`ReplacingMergeTree(ver)` (**Hình 2.8**):** Khi merge, giữ lại một hàng cho mỗi khóa `ORDER BY` (ưu tiên `ver` lớn nhất). Do merge chạy bất đồng bộ, truy vấn tức thời vẫn có thể đọc thấy bản cũ nếu không dùng `SELECT ... FINAL` [V1].
* **`SummingMergeTree`:** Cộng gộp các cột số theo cùng khóa `ORDER BY` khi merge; khi đọc vẫn cần `sum()` và `GROUP BY` [V2].
* **`AggregatingMergeTree`:** Hợp nhất trạng thái trung gian (`AggregateFunction`, `SimpleAggregateFunction`) qua cặp hậu tố `-State` / `-Merge` [V3] *(ứng dụng chủ chốt tại Chương 5)*.
* **`ReplicatedMergeTree`:** Duy trì bản sao đa nút qua ClickHouse Keeper (sao chép mặc định bất đồng bộ) [V4].

*(Hình 2.8. Hợp nhất các part của ReplacingMergeTree và giữ lại hàng theo khóa sắp xếp. Nguồn: ClickHouse Docs, "Replacing merges" [S5, V1] · CC BY-NC-SA 4.0).*

**Cầu nối sang Chương 3:** Toàn bộ ba cơ chế cốt lõi ở Chương 2 — khóa sắp xếp `ORDER BY` (Mục 2.3), độ mịn hạt `index_granularity` (Mục 2.4) và kích thước lô nạp cùng hợp nhất nền (Mục 2.5) — được đưa vào kiểm chứng định lượng qua chuỗi thực nghiệm **E1, E2, E3** trên 30 triệu dòng tại Chương 3.
