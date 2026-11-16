# CHƯƠNG 2. MERGETREE: TỔ CHỨC DỮ LIỆU, CHỈ MỤC THƯA VÀ CƠ CHẾ MERGE

Phạm vi cập nhật: nghiên cứu MergeTree trên một node ClickHouse với dữ liệu clickstream append-only. Columnar storage, vectorized execution, PostgreSQL, Materialized View và hệ thống phân tán chỉ được giới thiệu ngắn để đặt bối cảnh; không còn là các nhánh thực nghiệm chính. Tên đề tài gợi ý để nhóm thống nhất với giảng viên: “MergeTree Internals in ClickHouse: Evaluating Sorting Keys, Index Granularity and Background Merges on Clickstream Data”. Các phần ngoài chương 2–4 và các thẻ thành viên được giữ nguyên theo yêu cầu; nhóm cần tự rà sự thống nhất tên đề tài và các chương khác khi được phép chỉnh.

Quy cách bản báo cáo cuối: tối đa30 trang toàn bộ, Times New Roman13 (kể cả chú thích/bảng và tiêu đề; tiêu đề phân biệt bằng in đậm), A4; ưu tiên giãn dòng1,15 nếu quy định môn học cho phép. Ngân sách: phần đầu3; chương1:2; chương2:7; chương3:5; chương4:8; chương5:2; tài liệu tham khảo2; dự phòng1. SQL dài, checklist thao tác và log để ở GitHub, không đưa phụ lục dài vào bản30trang. Nếu môn học yêu cầu giãn dòng/lề khác, giữ nguyên trần trang và rút nội dung.

Mục tiêu chương2: giải thích đường đi từ INSERT tạo part, ORDER BY tổ chức dữ liệu, sparse index/marks chọn granule, đến merge nền hợp nhất parts. Viết tối đa7 trang, dành phần lớn dung lượng cho2.2–2.5. Mỗi mục có hình/ví dụ nhỏ cần thiết và liên hệ với chương3. Văn bản dưới đây là kế hoạch/checklist làm việc; bản nộp trình bày nội dung nghiên cứu và kết quả, không chép nguyên checklist vào30trang.

## 2.1. Bối cảnh ClickHouse và vị trí của MergeTree — Hà
### 2.1.1. Clickstream analytics và yêu cầu đọc/ghi
Mô tả ngắn sự kiện website, truy vấn lọc/tổng hợp và nhu cầu cân bằng tốc độ đọc, tốc độ nạp, dung lượng. Phạm vi thực nghiệm là dữ liệu tĩnh lúc SELECT và nạp theo lô lúc INSERT; không đo độ trễ producer-to-dashboard.
### 2.1.2. Tổng quan kiến trúc ở mức tối thiểu
Vẽ một sơ đồ Client → Parser/Planner → Execution → MergeTree → Disk. Giới thiệu hướng cột, vector hóa và nhiều luồng bằng 1–2 câu mỗi khái niệm; không cần phân tích SIMD, CPU cache hay benchmark PostgreSQL. Dùng một đoạn ngắn phân biệt DBMS và storage engine.
Nghiệm thu: khoảng 0,5–1 trang; có sơ đồ và định nghĩa phạm vi. Nguồn đọc: [S1], [S2].

## 2.2. Data parts và đường ghi của MergeTree — Hà
### 2.2.1. Từ block INSERT đến part bất biến
Giải thích parse/convert → chia block và partition → sắp xếp theo ORDER BY → tạo dữ liệu nén, marks và chỉ mục → công bố part. Một INSERT có thể tạo nhiều part tùy block, partition và parallelism; không khẳng định luôn một INSERT tương ứng một part. MergeTree thông thường không tự khử trùng các hàng giống khóa.
### 2.2.2. Cấu trúc vật lý: Wide/Compact, dữ liệu cột và marks
Phân biệt Wide và Compact. Minh họa file dữ liệu nén, primary index và marks bằng tên/file thực tế trên phiên bản đang dùng; đuôi .mrk2/.mrk3 và bố trí file phụ thuộc định dạng, không coi một đuôi cố định là chuẩn mọi bảng. Phân biệt compressed block với granule và vai trò offset trong marks.
### 2.2.3. Tổ chức part trong partition
Phân biệt table/partition/part/granule. Parts thuộc các partition khác nhau không merge với nhau. PARTITION BY hỗ trợ quản lý vòng đời và partition pruning; không thay thế ORDER BY. Dữ liệu hiện tại chủ yếu tháng 7/2013 nên không thiết kế đối chứng partition theo tháng làm thí nghiệm chính.
Nghiệm thu: hình quan hệ table → partition → part → granule; ví dụ SHOW CREATE TABLE và system.parts; một đoạn liên hệ batch INSERT với số part ở E3. Nguồn: [S2], [S3], [S6].

## 2.3. Sorting key, primary key và sparse primary index — Tuấn
### 2.3.1. ORDER BY và PRIMARY KEY
Giải thích thứ tự từ điển, cột đầu khóa và prefix; PRIMARY KEY mặc định lấy ORDER BY khi không khai báo riêng, có thể là prefix hợp lệ của sorting key. Khóa chính trong MergeTree không phải ràng buộc duy nhất như trong nhiều hệ quản trị giao dịch.
### 2.3.2. Chỉ mục thưa và lựa chọn khoảng đọc
Dùng 12–20 dòng dữ liệu giả chỉ để minh họa ba khóa K0 tuple(), K1 (CounterID, EventDate), K2 (EventDate, CounterID). Vẽ các khoảng granule có thể được loại bỏ với lọc website, lọc ngày và lọc kết hợp. Phân biệt chỉ mục thưa với B-tree ở mức khái niệm; không triển khai PostgreSQL.
### 2.3.3. Khóa theo workload và hiệu ứng nén
Giải thích khóa phù hợp phụ thuộc bộ lọc/cardinality/phân bố; cùng khóa có thể có lợi cho W1 nhưng kém hơn ở W2. Sorting key cũng có thể thay đổi tỷ lệ nén nên cần đo storage, không quy mọi khác biệt latency hoàn toàn cho chỉ mục.
Nghiệm thu: hình so sánh K1/K2 và bảng filter → khả năng dùng prefix → điều cần kiểm chứng bằng EXPLAIN. Nguồn: [S2], [S4].

## 2.4. Granules, marks và quá trình đọc có chọn lọc — Tuấn
### 2.4.1. index_granularity và adaptive granularity
Giải thích mặc định thường gặp 8192 và giới hạn theo index_granularity_bytes; granule thực tế không luôn đủ 8192 dòng. Thí nghiệm cố định index_granularity_bytes=0 và thay g=2048/8192/32768 để cô lập số dòng/granule. Phân biệt thiết lập thí nghiệm với cấu hình mặc định sản xuất.
### 2.4.2. Đường đọc và granule pruning
Mô tả chọn parts → xét primary index → chọn marks/ranges → đọc/giải nén các cột → lọc/tổng hợp. Minh họa EXPLAIN indexes=1 và EXPLAIN ESTIMATE; hai lệnh cung cấp bằng chứng kế hoạch, không tự trả thời gian milliseconds. Chỉ giới thiệu PREWHERE, skip indexes và projection trong vài câu; thí nghiệm không bật thêm các kỹ thuật này.
### 2.4.3. Đánh đổi độ chính xác pruning và kích thước chỉ mục
Với một part, granule cố định: M≈ceil(N/g); R_est≈min(N, selected_marks×g); I_key≈M×độ rộng khóa. Khóa (Int32,Date) có độ rộng giá trị 6 byte, nhưng công thức chưa gồm metadata, marks của các cột và overhead cấp phát. Granule nhỏ tăng marks, có thể giảm đọc thừa nhưng chưa chắc giảm latency. Dẫn sang E2 và mô hình thời gian ở 3.6.
Nghiệm thu: hình granule nhỏ/lớn, một ví dụ tính tay, SQL giải thích và giới hạn công thức. Nguồn: [S2], [S4], [S7].

## 2.5. Background merges và đánh đổi trong nạp dữ liệu — Tài
### 2.5.1. Tạo nhiều part và hợp nhất nền
Giải thích merge các part cùng partition thành part mới; lựa chọn merge có tính heuristic, không phải luôn gộp hết thành một part sau thời gian cố định. Parts cũ có thể còn tồn tại trước khi dọn dẹp. Không dùng thuật ngữ “tự dọn trùng” cho MergeTree thông thường.
### 2.5.2. Kích thước batch, số request và chi phí merge
Nêu quan hệ batch nhỏ → nhiều request/parts tiềm năng → overhead và công việc merge. Batch lớn cần cân nhắc bộ nhớ và thời gian chờ gom dữ liệu ở producer. Phân biệt ACK INSERT, thời gian quan sát chờ ổn định, tổng duration các merge và dung lượng tạm; chúng không phải một đại lượng.
### 2.5.3. Quan sát bằng system tables
Giới thiệu system.parts, system.merges, system.part_log. Giải thích proxy merge_row_amplification=ΣMergeParts.read_rows/N; không gọi đây là physical SSD write amplification. Đề cập rủi ro too many parts và lý do không ép OPTIMIZE FINAL trong thí nghiệm merge tự nhiên.
Nghiệm thu: sơ đồ merge hai/ba part, bảng metric/nguồn lấy và ví dụ part_log. Nguồn: [S3], [S5], [S6], [S8], [S9].

## 2.6. Phạm vi áp dụng và liên hệ thiết kế thực nghiệm — Tài
### 2.6.1. Các biến thể MergeTree và kỹ thuật liên quan
Liệt kê ReplacingMergeTree, SummingMergeTree, AggregatingMergeTree, ReplicatedMergeTree; mỗi loại 1–2 câu kèm điều kiện cơ bản. MV, TTL, codec, sharding và replication chỉ được liệt kê vai trò; không tạo phần thực nghiệm bổ sung. Nếu nhắc ReplacingMergeTree, nêu loại trùng trong quá trình merge không đồng nghĩa kết quả đọc luôn tức thời đã loại trùng.
### 2.6.2. Ánh xạ cơ chế sang nghiên cứu
Lập bảng: sorting key/sparse index → E1; granule/index size → E2; data parts/merge → E3; lượng đọc và overhead cố định → mô hình estimated time. Kết chương bằng các dự đoán định tính cần kiểm chứng, không đưa số tốc độ từ tài liệu khác vào kết quả nhóm.
Nghiệm thu chương 2: thuật ngữ nhất quán; mỗi mô tả cơ chế có nguồn chính thức/paper; có ít nhất ba hình tự vẽ, một ví dụ tính granule/index, và liên kết rõ với chương 3.

# CHƯƠNG 3. THIẾT KẾ VÀ TRIỂN KHAI THỰC NGHIỆM MERGETREE

Quyết định chung: tiếp tục dùng ClickBench hits, lấy đúng khoảng 30 triệu sự kiện từ 30 file cố định và giữ 12 cột dùng trong nghiên cứu: WatchID, UserID, CounterID, EventDate, EventTime, RegionID, AdvEngineID, IsRefresh, ResolutionWidth, ResolutionHeight, DontCountHits, ResponseEndTiming. Dữ liệu RowBinary có 44 byte/dòng chưa nén. Đây là tập cột rút gọn của hits, không còn workload/schema ClickBench chuẩn để so điểm leaderboard. Chọn phương án này để ba máy cá nhân đủ tài nguyên và nhóm tập trung vào MergeTree.

Repo dùng chung: https://github.com/w1ndS0ng/clickhouse-mergetree-study. README hướng dẫn chạy; docs/PROTOCOL_VI.md mô tả đầy đủ phương pháp; configs/protocol.json là cấu hình đóng băng; scripts/run_member.sh chạy theo thành viên; scripts/study.py cho từng bước. Các ô dưới đây chỉ đánh dấu hoàn tất khi có file bằng chứng và người kiểm tra chéo; chưa có số đo chính thức thì giữ nhãn “chưa thực nghiệm”.

## 3.1. Mục tiêu, câu hỏi và giả thuyết — Hà
☐ H31-01 — Viết phạm vi single-node, append-only, cùng dữ liệu và truy vấn giữa các đối chứng. Giải thích dữ liệu tĩnh khi đo SELECT, nạp theo batch khi đo INSERT; không suy ra hiệu năng production hay độ trễ streaming đầu-cuối.
☐ H31-02 — Câu hỏi 1: Thứ tự sorting key ảnh hưởng thế nào đến marks được chọn, read_rows, thời gian và dung lượng khi workload lọc theo website, ngày hoặc cả hai?
☐ H31-03 — Câu hỏi 2: Giảm granularity đem lại lợi ích pruning nào và làm tăng kích thước chỉ mục/marks ra sao; mức nào cân bằng trong môi trường đã đo?
☐ H31-04 — Câu hỏi 3: Batch INSERT ảnh hưởng thế nào đến throughput, số part, chi phí merge và dung lượng ở trạng thái quan sát ổn định?
☐ H31-05 — Câu hỏi 4: Mô hình T_est=α+β×R_est hiệu chỉnh trên tập nhỏ dự đoán latency ở 30M tốt đến đâu; sai số xuất hiện ở trường hợp nào?
☐ H31-06 — Lập bảng câu hỏi → giả thuyết → biến độc lập → đối chứng → metric → kết luận có thể chấp nhận/bác bỏ. Không coi khóa, granule hay batch lớn hơn là luôn tốt hơn trước khi đo.
Đầu ra: 0,5–1 trang và bảng ánh xạ bốn câu hỏi. Tuấn kiểm tra thiết kế; Tài kiểm tra các chi phí đọc/ghi/storage đã được bao quát.

## 3.2. Dataset, môi trường và protocol chung — Tuấn
### 3.2.1. Tải dữ liệu, khóa snapshot và tạo tập hiệu chỉnh
☐ T32-01 — Dùng 30 shard trong configs/protocol.json: 0,10,…,90; 1,11,…,91; 2,12,…,92. Mỗi file dự kiến 1M dòng, script kiểm tra đúng số dòng. Ghim commit ClickBench b0b7dd8f11a2a719211cc41d8c7ebbada267df66; ghi URL, ngày tải, điều kiện ghi nguồn và SHA-256 Parquet/RowBinary vào manifest chung.
☐ T32-02 — Chuyển đúng 12 cột, giữ kiểu có dấu theo schema ghim; Date theo epoch ngày, DateTime UTC theo epoch giây. Không nhân bản dữ liệu, không tự bỏ trùng và không tạo LIMIT riêng cho từng bảng. Thời gian tải/chuyển đổi nằm ngoài benchmark.
☐ T32-03 — Tạo mẫu lồng nhau từ chuỗi 30 file cố định bằng vị trí dòng toàn cục modulo30: giữ phần dư <1 cho1M, <3 cho3M, <10 cho10M; 30M giữ toàn bộ. Cách này rải mẫu trên mọi file, là lấy mẫu hệ thống xác định, không tuyên bố mẫu ngẫu nhiên hay hoàn toàn không thiên lệch. Lưu rule, số dòng và hash từng mẫu.
☐ T32-04 — Profile min/max ngày, phân bố theo ngày/CounterID/RegionID và cardinality ở các quy mô. Kiểm tra W1/W2/W3/W4 đều có dòng phù hợp; nếu sửa literal, sửa protocol trước formal run và dùng thống nhất. Giải thích giới hạn do chỉ chọn 30 shard và 12 cột.
☐ T32-05 — Bàn giao manifests/hits30m.lock.json đã kiểm tra; Hà/Tài chạy dataset với --lock để đối chiếu. Mọi bảng đối chứng phải có cùng N và fingerprint count/hash_sum/hash_xor; hash là kiểm tra nhất quán thực dụng, không chứng minh tuyệt đối không va chạm.
### 3.2.2. Phần cứng, phần mềm và thiết lập
☐ T32-06 — Mỗi người ghi CPU/luồng cấp cho WSL, RAM/giới hạn WSL, SSD, dung lượng trống ổ vật lý chứa VHDX, Ubuntu/kernel/Python và ClickHouse server/client/local. Đề xuất ghim 26.10.3.7, query4threads, insert1thread, memory2GB; nếu một máy không đáp ứng, thống nhất lại trước khi đo.
☐ T32-07 — Lưu SHOW CREATE TABLE và effective settings: MergeTree, LZ4, Wide, không partition key, không MV/projection/skip index; PRIMARY KEY mặc định theo ORDER BY; fsync_after_insert=1, async_insert=0. Tắt query/condition cache, PREWHERE tự động và tối ưu aggregation/read-in-order trong đối chứng để thu hẹp cơ chế nghiên cứu. Ghi rõ đây là thiết lập kiểm soát, không phải tuning production.
☐ T32-08 — Với E1/E2, cố định index_granularity_bytes=0, write_final_mark=0; chuẩn hóa về một active Wide part bằng OPTIMIZE FINAL trong giai đoạn chuẩn bị, không tính vào latency. Xác minh một part và chờ ổn định. E3 giữ merge nền tự nhiên, không OPTIMIZE FINAL hay STOP MERGES.
### 3.2.3. Workload, metrics và phương pháp lặp
☐ T32-09 — Workload W0 full scan; W1 CounterID=3258; W2 EventDate trong [2013-07-15,2013-07-22); W3 kết hợp W1/W2; W4 RegionID=225 ngoài khóa. Cùng SELECT count(),sum(ResolutionWidth) để buộc đọc dữ liệu; không dùng SELECT * LIMIT hoặc count() metadata làm bằng chứng pruning. Chốt literal sau profile/pilot.
☐ T32-10 — Đo query: client elapsed_ms, server query_duration_ms, read_rows, read_bytes, memory_usage; lấy QueryFinish theo query_id. Đo pruning: estimated rows/selected marks/parts từ EXPLAIN ESTIMATE và kế hoạch EXPLAIN indexes=1. Đo storage: bytes_on_disk, data_compressed/uncompressed_bytes, marks_bytes, primary_key_bytes_in_memory trên active parts.
☐ T32-11 — Đo ingestion: N/ACK time, số request/parts, NewPart/MergeParts, tổng duration và read_rows của merge theo table_uuid; giữ snapshots tại ACK và sau ổn định. read_bytes là lượng đọc logic; active bytes không phải toàn bộ dung lượng VHDX; tổng duration merge không phải elapsed time hay CPU time.
☐ T32-12 — E1/E2: mỗi cell 2 warmups +10 lượt đo, đảo thứ tự case/cấu hình với seed cố định. Báo median/Q1/Q3/IQR, giữ log lỗi và mọi lượt, không tùy ý xóa outlier. E3: 3 vòng cho mỗi batch, luân phiên thứ tự ba cấu hình. Nếu tăng lặp, quyết định trước formal run.
☐ T32-13 — Chờ 3 lần quan sát cách10s, không merge/mutation và parts không đổi; giới hạn chờ1200s. Đây là ổn định quan sát, có tối thiểu20s xác nhận, không bảo đảm merge tương lai không xảy ra. Không gọi thời gian chờ này là chi phí merge thực tế. Không xóa OS cache; mô tả warm-repeat sau warmups.
☐ T32-14 — Một máy chỉ chạy một thí nghiệm tại một thời điểm. Ba người có thể chạy trên ba máy nhưng mọi đối chứng/speedup phải tính nội bộ cùng máy; công bố môi trường từng máy, không lấy ms của Hà chia ms của Tuấn. Tái lập chéo ít nhất một đối chứng ở máy thứ hai.
Đầu ra: manifest30M+mẫu, profile, environment ba máy, schema/DDL/settings, workload và protocol đóng băng. Hà/Tài kiểm tra tải, hash và một pilot trước khi đo chính thức.

## 3.3. E1 — Sorting key và granule pruning — Hà
### 3.3.1. Ma trận cấu hình và tính đúng đắn
☐ H33-01 — Dựng K0 ORDER BY tuple(), K1 ORDER BY (CounterID,EventDate), K2 ORDER BY (EventDate,CounterID); giữ g8192 và mọi thiết lập khác. Chuẩn bị 1M/3M/10M để hiệu chỉnh mô hình, 30M để kiểm chứng. Fingerprint và kết quả count/sum của W0–W4 phải khớp giữa ba bảng cùng quy mô.
☐ H33-02 — Kiểm tra EXPLAIN cho mỗi key/case; lưu selected_marks/total_marks, estimated rows và full plan. Phân biệt số dòng khớp điều kiện với số dòng cần đọc; không mặc định mọi truy vấn hưởng lợi từ khóa.
### 3.3.2. Chạy calibration, đóng băng dự đoán rồi đo30M
☐ H33-03 — Chạy build→queries cho1M,3M,10M; mỗi quy mô150 lượt đo chính. Sau đó fit model; dựng các bảng30M và lấy EXPLAIN; chạy forecast để lưu dự đoán có timestamp/hash trước khi chạy queries30M. Không hiệu chỉnh lại mô hình bằng kết quả30M.
☐ H33-04 — Chạy150 lượt đo30M, so sánh lượng đọc/time/storage; kiểm tra parts không thay đổi trong quá trình đo. Nếu lỗi/parts đổi, giữ nguyên journal, điều tra và tạo run mới theo quy trình; không chọn vài lần chạy có lợi để thay thế.
### 3.3.3. Hồ sơ bàn giao
☐ H33-05 — Xuất summary/queries.csv, summary/storage.csv, model/model.json, model/forecast.json, estimated_vs_actual.csv, DDL/SQL/EXPLAIN và hình PNG/SVG. Viết ghi chú W1 ưu tiênK1, W2 ưu tiênK2 có đúng hay không, dựa trên số liệu.
Lệnh thuận tiện sau khi có dữ liệu/protocol: bash scripts/run_member.sh ha laptop1 main01. Dùng nhãn máy/run thực tế; mỗi run chỉ init một lần. Tuấn review E1 và mô hình; kết quả phân tích đưa vào4.1, mô hình đối chiếu ở4.4.

## 3.4. E2 — Index granularity và chi phí chỉ mục — Tuấn
### 3.4.1. Cấu hình g2048/g8192/g32768
☐ T34-01 — Giữ khóa K1, cùng30M/12cột/LZ4/một active Wide part; chỉ thay index_granularity=2048/8192/32768, cố định granularity_bytes=0. Chạy pilot1M trên run riêng trước.
☐ T34-02 — Kiểm tra cùng dữ liệu và kết quả W0–W4; lưu EXPLAIN và actual DDL. G8192 là baseline nội bộ; không dùng số ms K1 từ máy Hà làm baseline của Tuấn.
### 3.4.2. Đo pruning, query time và index size
☐ T34-03 — Thu150 lượt đo chính30M; tính pruning và latency median/IQR. Tách marks_bytes và primary_key_bytes_in_memory; đo dung lượng dữ liệu nén và bytes_on_disk để tránh gọi mọi byte tăng thêm là primary index.
☐ T34-04 — So số marks thực tế với ceil(N/g), và I_key≈ceil(N/g)×6byte với kích thước index ghi nhận. Nêu overhead và khác biệt cấp phát; công thức không dự đoán toàn dung lượng bảng hay mọi file marks.
### 3.4.3. Hồ sơ bàn giao
☐ T34-05 — Xuất CSV/log/EXPLAIN/storage và đồ thị latency/read_rows/pruning; thêm hình index/marks size theo g. Viết trường hợp g nhỏ không cải thiện hoặc overhead lấn át; không tuyên bố g2048 luôn tối ưu.
Lệnh thuận tiện: bash scripts/run_member.sh tuan laptop2 main01. Tài review và tái lập một cặp g trên máy khác; phân tích chính ở4.2.

## 3.5. E3 — Batch INSERT, data parts và background merge — Tài
### 3.5.1. Đối chứng nạp dữ liệu
☐ A35-01 — Thay kế hoạch MV cũ bằng batch10k/100k/1M; dùng cùng30M/12cột, thứ tự dòng/file và format RowBinary. Giữ K1,g8192,LZ4,fsync1,async0,insert1thread. Các file được chuẩn bị trước, không tính tải mạng/chuyển Parquet vào phép đo.
☐ A35-02 — Mỗi case dùng bảng mới rỗng;3batch×3vòng=9lượt nạp30M. Luân phiên vị trí ba cấu hình qua3vòng. Merge nền hoạt động tự nhiên; không OPTIMIZE FINAL, không STOP MERGES, không trộn SELECT benchmark vào lúc nạp.
### 3.5.2. ACK time, throughput và quan sát merge
☐ A35-03 — Đo từ request đầu đến ACK cuối; numerator là N dòng đầu vào đã kiểm chứng. Ghi elapsed từng batch/query_id; tổng pipeline có đọc file giữa các batch và overhead client, phải nêu rõ định nghĩa.
☐ A35-04 — Theo dõi parts/active bytes mỗi1s, snapshot ngay sau ACK và sau trạng thái ổn định. Thu part_log theo table_uuid, NewPart/MergeParts/error; kiểm tra count/hash sau mỗi lượt. Nếu part_log chưa bật, dùng configs/server/part_log.xml và restart trước run chính; không thay cấu hình giữa các case.
☐ A35-05 — Tính merge_row_amplification=ΣMergeParts.read_rows/N; tách tổng merge duration, observed stable wait và ACK. Merge có thể chạy song song; không cộng chúng để suy ra thời gian CPU hoặc elapsed tổng. Timeline active bytes không đo đỉnh dung lượng vật lý tuyệt đối; dung lượng inactive/tạm được nêu là hạn chế.
### 3.5.3. Storage và hồ sơ bàn giao
☐ A35-06 — Lưu ingestion9lượt, từng batch, fingerprints, storage và part_log; summary theo batch gồm median/Q1/Q3/IQR của throughput/time/storage/merge. Vẽ throughput và storage, timeline số part, chi phí merge; kết luận cả lợi ích lẫn chi phí.
Lệnh thuận tiện: bash scripts/run_member.sh tai laptop3 main01. Hà review; phân tích ở4.3. Toolkit giữ các bảng thí nghiệm để audit, không tự xóa bảng dữ liệu cũ.

## 3.6. Mô hình ước lượng thời gian và hồ sơ tái lập — Tài tổng hợp, Hà chạy model
### 3.6.1. Công thức và giả định
☐ A36-01 — Giới thiệu T_est_ms=α_ms+β_ms_per_row×R_est; R_est lấy EXPLAIN ESTIMATE của chính query/setting. Fit riêng cho mỗi key/case bằng median client_ms trên1M/3M/10M, ràng buộc α,β≥0. α mô tả overhead, β mô tả chi phí trung bình thực nghiệm; không coi đây là cost model chính thức của ClickHouse.
☐ A36-02 — Lưu cả baseline T_naive=T10M×R30M_est/R10M_est, giả định overhead không đáng kể. Với ít nhất3điểm và đủ biến thiên rows mới fit; nếu không nhận diện được hoặc fit biên/R² kém, ghi rõ. Chỉ3điểm nên đây là mô hình khám phá; kết quả30M là holdout, không dùng sửa hệ số rồi vẫn gọi là dự đoán.
### 3.6.2. Quy trình đóng băng và xử lý sai số
☐ A36-03 — Lưu model trước đo30M, forecast sau khi có EXPLAIN nhưng trước measured query30M; giữ timestamp và hash calibration/model/EXPLAIN. Khuyến khích commit forecast trước đo để có mốc kiểm chứng độc lập. Runner từ chối đo30M khi thiếu forecast; không tạo predictions từ actual read_rows30M.
☐ A36-04 — Định nghĩa actual cho mô hình là client elapsed_ms cùng giao thức; server_ms báo song song. Absolute error=|predicted−actual|; APE=absolute_error/actual×100 khi actual>0; MAE=trung bình absolute_error. Không chia0, không dùng “real time” để ám chỉ độ trễ hệ thống streaming. Đánh giá cả mô hình α+βR và baseline naive.
### 3.6.3. Repo và thứ tự thực hiện chung
☐ A36-05 — Repo: configs/ chung+members; src/mtstudy/ dùng chung; scripts/ runner/data/check; tests/; docs/; manifests/; artifacts/<member>/<machine>/<run>/. Kết quả local nằm results/<member>/<machine>/<run>/ và mặc định gitignore. Nhánh ha/sorting-key, tuan/granularity, tai/batch-merge; thay protocol qua PR trước formal run.
☐ A36-06 — Thứ tự: chốt scope → chuẩn bị/khóa30M → pilot1M ba máy → khóa protocol → Hà calibration/model/holdout, TuấnE2, TàiE3 → summarize/compare/plot → review chéo → viếtch4 → package/archive. Mỗi người chỉ chạy script nhiệm vụ của mình; thay đổi môi trường phải tạo run mới.
☐ A36-07 — Mỗi hình/bảng có member/machine/run/protocol, N, metric, đơn vị và số lượt; truy về CSV/query_id hoặc table_uuid. Chỉ commit kết quả đã rà soát vào artifacts; ZIP log lớn có thể đưa GitHub Release. Không đẩy client.xml, password, .env, Parquet/RowBinary hay synthetic smoke results thành kết quả báo cáo.
Đầu ra chương3: đầy đủ schema/manifest/environment/protocol, ba ma trận thực nghiệm, forecast trước holdout, README tái lập và hồ sơ kiểm tra chéo. Chi tiết lệnh và output theo từng bước ở docs/PROTOCOL_VI.md.

# CHƯƠNG 4. KẾT QUẢ, KIỂM CHỨNG ƯỚC LƯỢNG VÀ THẢO LUẬN MERGETREE

Mục tiêu: trình bày số đo của nhóm và giải thích bằng cơ chế ở chương2. Không tiếp tục chương so sánh PostgreSQL trong phạm vi này. Mỗi phần viết theo câu hỏi → bảng/hình → phân tích cơ chế → giới hạn. Các ô kết quả chưa có bằng chứng phải ghi “chưa thực nghiệm”; không đưa số illustrative/smoke vào bảng chính.

## 4.1. Kết quả sorting key và sparse index — Hà
### 4.1.1. Mức pruning và lượng dữ liệu đọc
☐ H41-01 — Lập bảng W0–W4 × K0/K1/K2 ở30M: estimated rows, actual read_rows/read_bytes, selected/total marks và pruning. Đính một EXPLAIN tiêu biểu cho W1/W2/W3; chỉ rõ prefix nào đã được dùng.
### 4.1.2. Query latency và dung lượng
☐ H41-02 — Hình latency median/IQR và read_rows theo case/key, bảng speedup soK0 trên cùng máy. Bổ sung storage/nén để đánh giá ảnh hưởng thứ tự sắp xếp; server_ms0 thì để trống tỷ lệ server, trình bày client_ms đúng tên.
### 4.1.3. Diễn giải theo workload
☐ H41-03 — Trả lời câu hỏi1; bàn trường hợp fullscan/cột ngoài khóa/ít chọn lọc không hưởng lợi, và trường hợp giảm rows nhưng time không giảm tương ứng. Không chọn khóa tốt nhất bằng một truy vấn duy nhất hoặc trung bình speedup tùy ý.

## 4.2. Kết quả granularity và chi phí chỉ mục — Tuấn
### 4.2.1. Granule size, pruning và query time
☐ T42-01 — So ba mứcg trên cùng30M/K1; báo median/IQR choW0–W4. Hình latency/read_rows theo g, ghi cùngmáy/thiết lập để tách khỏi kết quả E1.
### 4.2.2. Index/marks size và độ khớp công thức
☐ T42-02 — Bảng g, ceil(N/g), marks thực tế, I_key_est, primary_key_bytes_in_memory, marks_bytes và active table bytes. Vẽ index/marks theo g; tách phần dự đoán lý thuyết6byte/mark với metadata/cấp phát thực tế.
### 4.2.3. Điểm cân bằng có điều kiện
☐ T42-03 — Trả lời câu hỏi2; chọn cấu hình phù hợp cho workload đã đo, giải thích chi phí chỉ mục và đọc thừa. Nêu rõ index_granularity_bytes=0/Wide/mộtpart làm giới hạn khả năng khái quát.

## 4.3. Kết quả batch INSERT và background merges — Tài
### 4.3.1. Ingestion time và throughput
☐ A43-01 — Bảng3batch×3vòng, hình median/IQR và điểm đo từng vòng; ghi N30M/lượt, ACKtime và throughput. Nêu định nghĩa gồm pipeline local, không đo thời gian chờ gom batch ở producer.
### 4.3.2. Part timeline, merge work và storage
☐ A43-02 — Hình sốpart theo thời gian và bảng parts_at_ACK/parts_stable, NewPart/MergeParts, Σmerge duration, merge_row_amplification và activebytes. Giữ mốc quan sát ổn định, không giả định parts_stable=1 hoặc không còn merge sau đó.
### 4.3.3. Đánh đổi và khuyến nghị
☐ A43-03 — Trả lời câu hỏi3; giải thích quan hệ batch/request/parts/merge, trường hợp overhead/durability lấn át. Dung lượng hoạt động và proxy merge không đủ để kết luận write amplification vật lý hoặc chi phí vận hành production.

## 4.4. Estimated time so với actual time — Tài viết, Hà cung cấp model
### 4.4.1. Hiệu chỉnh và bằng chứng dự đoán trước
☐ A44-01 — Trình bày công thức, α/β theo case/key, ba điểm calibration, R²/boundary-fit và giả định. Dẫn commit/timestamp/hash forecast trước đo30M; loại kết quả synthetic. Nếu đã nhìn30M trước khi fit ngoài quy trình, ghi “phân tích hồi cứu” thay vì dự đoán trước.
### 4.4.2. Sai số trên30M và baseline đơn giản
☐ A44-02 — Bảng predicted_client_ms, actual median/Q1/Q3, server_ms, absolute error, signed error, APE và naive error; hình predicted-vs-actual với đườngy=x. Tổng hợp MAE và medianAPE, giữ cả case sai số lớn, case không nhận diện được để trống có lý do.
### 4.4.3. Vì sao sai khác và giới hạn mô hình
☐ A44-03 — Đối chiếu estimated rows với actual read_rows trước khi lý giải latency; phân tích cache/working set, granule biên, fixed overhead, độ chọn lọc, phân bố file và thay đổi tốc độ xử lý. Không gọi β là tốc độ vật lý SSD hoặc suy mô hình một máy sang máy khác. Nếu mô hình không tốt hơnnaive, kết luận thẳng.

## 4.5. Tổng hợp, threats to validity và kết luận — Tài, cả nhóm rà soát
### 4.5.1. Trả lời bốn câu hỏi nghiên cứu
☐ A45-01 — Bảng câu hỏi → kết quả chính → bằng chứng → điều kiện áp dụng. Tách nhận định có số liệu, diễn giải cơ chế và giả thuyết chưa kiểm chứng. Không tuyên bố MergeTree nhanh hơn PostgreSQL khi không có phép so sánh tương ứng.
### 4.5.2. Giới hạn và kiểm chứng chéo
☐ A45-02 — Nêu WSL/ứng dụng nền/cache; ba máy khác cấu hình; chỉ30shard/12cột; systematic sample có thể lệch; literals; n10query/n3ingest; fsync1/Wide/granularity_bytes0; mộtpart ởE1/E2; merge heuristic; metric logic khác physical I/O; ba điểm calibration và holdout một quy mô. Ghi biện pháp áp dụng và điều chưa giải quyết.
☐ A45-03 — Review vòng Hà→Tuấn→Tài→Hà; một case đối chứng được chạy lại trên máy khác và so xu hướng/pruning/tỷ lệ nội bộ. Không gộp ms tuyệt đối hoặc kết quả lỗi vào bảng chính mà không gắn nhãn.
### 4.5.3. Kết luận thực dụng và hồ sơ bàn giao
☐ A45-04 — Viết khuyến nghị có điều kiện về key theoworkload, granule theo đánh đổi index/đọc, batch theo throughput/merge. Hướng phát triển chỉ liệt kê adaptive granularity, phân vùng nhiều tháng, rộng105cột, cập nhật/biến thểMergeTree và môi trường production.
☐ DONE-01 — Có đầy đủ source/commit/manifest/config/DDL/SQL, log gốc, model/forecast, CSVsummary và hình; từng con số truy về run/case. Đủ ma trận hoặc nêu rõ ô thiếu và nguyên nhân.
☐ DONE-02 — Mọi hình có caption/đơn vị/N/sốlượt/median-IQR; công thức không chia0; thời gianACK,server,client,merge và chờổnđịnh được gọi đúng. Các số dự kiến không bị trình bày như kết quả.
☐ DONE-03 — GitHub có hướng dẫn từngngười, nhánh/review và kết quả cáchly; secrets/dataset không nằm trong Git. Thành viên khác thực hiện lại được ít nhất một đối chứng bằng tài liệu đi kèm.

## Nguồn đọc và trích dẫn cho chương2–4
[S1] Schulze và cộng sự, “ClickHouse — Lightning Fast Analytics for Everyone”, PVLDB17(12),2024,3731–3744. https://www.vldb.org/pvldb/vol17/p3731-schulze.pdf
[S2] ClickHouse — MergeTree. https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree
[S3] ClickHouse — Table parts. https://clickhouse.com/docs/concepts/core-concepts/parts
[S4] ClickHouse — Primary indexes. https://clickhouse.com/docs/concepts/core-concepts/primary-indexes
[S5] ClickHouse — Part merges. https://clickhouse.com/docs/concepts/core-concepts/merges
[S6] ClickHouse — system.parts. https://clickhouse.com/docs/reference/system-tables/parts
[S7] ClickHouse — EXPLAIN. https://clickhouse.com/docs/reference/statements/explain
[S8] ClickHouse — system.part_log. https://clickhouse.com/docs/reference/system-tables/part_log
[S9] ClickHouse — Selecting an insert strategy. https://clickhouse.com/docs/concepts/best-practices/selecting-an-insert-strategy
[S10] ClickHouse — system.query_log. https://clickhouse.com/docs/reference/system-tables/query_log
[S11] ClickBench và quy tắc benchmark. https://github.com/ClickHouse/ClickBench
[S12] Schema ClickBench ghim. https://github.com/ClickHouse/ClickBench/blob/b0b7dd8f11a2a719211cc41d8c7ebbada267df66/clickhouse/create.sql
Lưu ý học thuật: số trang, ma trận, sampling, số lượt và mô hình dự đoán trên là thiết kế của nhóm. Nội dung web có thể mới hơn server ghim; đối chiếu với DDL/settings/EXPLAIN thực tế. Dẫn nguồn cho cơ chế, dẫn kết quả tự đo cho các nhận định định lượng.
