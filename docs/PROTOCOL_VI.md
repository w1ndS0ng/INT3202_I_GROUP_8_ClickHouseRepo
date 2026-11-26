# Đặc tả Protocol Thực nghiệm MergeTree (`mergetree-v2`)

Tài liệu này mô tả thiết kế đối chứng, tập dữ liệu, các thiết lập hệ thống cố định và định nghĩa chỉ số đo cho các thực nghiệm **E1–E3** ở Chương 3. Phần đối chiếu với PostgreSQL ở Chương 4 sử dụng cấu hình riêng tại [`configs/comparison.json`](../configs/comparison.json) và được dẫn trong [mục lục Chương 4](../chapter-4/README.md).

## 1. Phạm vi thực nghiệm

Các thực nghiệm được triển khai trên một nút máy chủ ClickHouse đơn lẻ với dữ liệu sự kiện web *clickstream* trích xuất từ ClickBench (`12` cột kiểu cố định, dạng *append-only*). Để cô lập từng cơ chế của MergeTree, quá trình đo tách biệt trạng thái dữ liệu tĩnh khi chạy `SELECT` (`E1`, `E2`) và trạng thái nạp nối tiếp theo lô khi chạy `INSERT` (`E3`).

## 2. Ma trận đối chứng và bộ truy vấn

| Thí nghiệm | Biến thay đổi | Quy mô dữ liệu | Tham số giữ cố định |
|---|---|---|---|
| **E1** (Sorting key) | `K0 = tuple()`, `K1 = (CounterID, EventDate)`, `K2 = (EventDate, CounterID)` | Hiệu chỉnh `1M, 3M, 10M`; Kiểm chứng `30M` | `index_granularity = 8192`, `1` active Wide part, `LZ4` |
| **E2** (Granularity) | `index_granularity = 2048, 8192, 32768` | Pilot `1M`; Chính thức `30M` | Khóa `K1`, `1` active Wide part, `LZ4`, `index_granularity_bytes = 0` |
| **E3** (Batch INSERT) | Cỡ lô `10.000`, `100.000`, `1.000.000` dòng | Pilot `1M`; Chính thức `30M` (`3` đợt × `3` vòng) | Khóa `K1`, `g = 8192`, `LZ4`, hợp nhất nền tự nhiên |

- Với **E1** và **E2**: mỗi tổ hợp cấu hình × truy vấn chạy `2` lượt làm nóng (*warmup*) và `10` lượt đo chính thức (`150` lượt đo cho mỗi mức quy mô) với thứ tự đảo ngẫu nhiên theo seed cố định; hai lượt làm nóng không đưa vào thống kê.
- Với **E3**: thực hiện `3` đợt đo độc lập, mỗi đợt gồm `3` vòng luân phiên cho ba cỡ lô (`27` lượt nạp mới `30M` dòng), giữ hợp nhất nền tự nhiên (không gọi `OPTIMIZE FINAL` hoặc `STOP MERGES`).

Năm truy vấn chuẩn dùng chung phép tổng hợp `SELECT count(), sum(ResolutionWidth)` để buộc đọc và giải nén dữ liệu cột:

| Truy vấn | Điều kiện `WHERE` | Vai trò kiểm chứng |
|---|---|---|
| **W0** | Không lọc | Quét toàn bảng đối chứng (*full scan*) |
| **W1** | `CounterID = 3258` | Lọc theo cột đứng đầu của `K1` |
| **W2** | `EventDate >= '2013-07-15' AND EventDate < '2013-07-23'` | Lọc theo cột đứng đầu của `K2` (cột thứ hai của `K1`) |
| **W3** | `CounterID = 3258 AND EventDate >= '2013-07-15' AND EventDate < '2013-07-23'` | Lọc kết hợp tiền tố khóa và dải thời gian |
| **W4** | `RegionID = 229` | Đối chứng lọc theo cột nằm ngoài sorting key |

## 3. Dữ liệu và thiết lập cố định

- **Dữ liệu nguồn:** `30` tệp Parquet (`1.000.000` dòng/tệp, tổng `30.000.000` dòng) theo danh sách shard cố định `0, 10, ..., 90; 1, 11, ..., 91; 2, 12, ..., 92` từ ClickBench. Dữ liệu được chuyển đổi sang định dạng `RowBinary` (`44` byte/dòng) và khóa toàn vẹn SHA-256 trong [`manifests/`](../manifests/).
- **Phân mẫu hệ thống lồng nhau:** Trên chuỗi `30M` bản ghi đánh số liên tiếp từ `0`, các mẫu `1M`, `3M` và `10M` giữ các dòng có vị trí toàn cục chia lấy dư cho `30` lần lượt nhỏ hơn `1`, `3` và `10`.
- **Phiên bản và tham số ClickHouse (`26.10.3.7`):**
  - `max_threads = 4`, `max_insert_threads = 1`, `max_memory_usage = 2000000000`.
  - `CODEC(LZ4)`, `fsync_after_insert = 1`, `async_insert = 0`, `index_granularity_bytes = 0`.
  - Tắt *query cache*, *query condition cache*, `PREWHERE` tự động, *skip index*, *projection*, *trivial count* và *read/aggregation-in-order* để cô lập hành vi của chỉ mục thưa.
- **Điều kiện ổn định bảng:** Sau bước chuẩn bị ở `E1`/`E2` (hoặc sau khi nhận phản hồi cuối ở `E3`), hệ thống kiểm tra trạng thái qua `3` lần quan sát liên tiếp cách nhau `10` giây ghi nhận số part không đổi và không còn tác vụ merge/mutation đang chạy. Các phép đo `SELECT` thực hiện trong chế độ *warm-repeat* (không xóa OS page cache).

## 4. Định nghĩa chỉ số đo lường

| Chỉ số | Nguồn trích xuất | Ý nghĩa kỹ thuật |
|---|---|---|
| `client_ms` | Đồng hồ `perf_counter` phía client | Thời gian phản hồi đầu–cuối từ khi gửi HTTP request tới khi nhận đủ kết quả |
| `server_ms` | `system.query_log` (`query_duration_ms`) | Thời gian xử lý phía máy chủ ClickHouse (độ phân giải `ms`) |
| `read_rows`, `read_bytes` | `system.query_log` (`QueryFinish`) | Lượng dòng và byte logic được ClickHouse đọc từ cột (khác I/O vật lý ổ đĩa) |
| `selected_marks`, `total_marks` | `EXPLAIN ESTIMATE` & `system.parts` | Số marks được chỉ mục chọn và tổng marks của part (`pruning = 1 - selected/total`) |
| `bytes_on_disk`, `data_compressed_bytes` | `system.parts` (`active = 1`) | Dung lượng các part đang hoạt động trên đĩa và dữ liệu cột sau nén |
| `primary_key_bytes_in_memory`, `marks_bytes` | `system.parts` (`active = 1`) | Bộ nhớ RAM cho khóa chính thưa và dung lượng tệp `.mrk2` trên đĩa |
| `ingest_ack_s`, `throughput` | Chương trình nạp (`N / ingest_ack_s`) | Tổng thời gian nạp đồng bộ `30M` dòng từ tệp `RowBinary` cục bộ và tốc độ nạp |
| `parts_stable`, `Σr / N` | `system.parts` & `system.part_log` | Số part ở trạng thái ổn định và hệ số lặp đọc bản ghi do hợp nhất nền |

Các kết quả tổng hợp báo cáo bằng **trung vị (median)**, tứ phân vị **Q1–Q3** và khoảng tứ phân vị **IQR = Q3 − Q1**. Hệ số tăng tốc tính theo tỷ số trung vị `speedup = median(T_baseline) / median(T_variant)` trong cùng máy và cùng workload.

## 5. Mô hình ước lượng và công thức kiểm chứng

Với một active Wide part gồm $N$ dòng, kích thước granule cố định $g$ (`index_granularity_bytes = 0`) và tổng độ rộng cột khóa $s_{\text{key}}$ ($6$ byte đối với `CounterID Int32 + EventDate Date`):

```text
M_est     = ceil(N / g)
R_est     ≈ min(N, selected_marks * g)
I_key_est = M_est * s_key
T_est_ms  = alpha_ms + beta_ms_per_row * EXPLAIN_ESTIMATE.rows   (alpha, beta >= 0)
```

- Với **E1**, `15` mô hình tuyến tính (tương ứng `3` khóa × `5` truy vấn) được hiệu chỉnh một lần trên trung vị của ba quy mô `1M`, `3M`, `10M` và đóng băng trước khi chạy kiểm chứng *holdout* trên tập `30M`, kèm đối chiếu sai số tuyệt đối (`MAE`), sai số phần trăm tuyệt đối (`APE`) và mô hình tuyến tính tỷ lệ đơn giản `T10 * (R30_est / R10_est)`.

## 6. Tài liệu tham chiếu kỹ thuật

- [ClickBench](https://github.com/ClickHouse/ClickBench) và [Schema tham chiếu `hits`](https://github.com/ClickHouse/ClickBench/blob/b0b7dd8f11a2a719211cc41d8c7ebbada267df66/clickhouse/create.sql)
- ClickHouse Documentation: [MergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree), [Data Parts](https://clickhouse.com/docs/parts), [Primary Indexes](https://clickhouse.com/docs/primary-indexes), [Part Merges](https://clickhouse.com/docs/merges)
- ClickHouse Reference: [EXPLAIN Statement](https://clickhouse.com/docs/reference/statements/explain), [`system.query_log`](https://clickhouse.com/docs/reference/system-tables/query_log), [`system.parts`](https://clickhouse.com/docs/reference/system-tables/parts), [`system.part_log`](https://clickhouse.com/docs/reference/system-tables/part_log)
