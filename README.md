# MergeTree Internals on ClickBench-derived Clickstream Data

Nghiên cứu một node ClickHouse: **sorting key → sparse index/granule pruning → thời gian đọc**;
**granularity → đánh đổi pruning và dung lượng chỉ mục**;
**batch INSERT → data parts/background merges → tốc độ ghi và dung lượng**.

Đây là thực nghiệm tùy biến từ ClickBench, không phải điểm ClickBench chính thức.
Phạm vi mới không triển khai PostgreSQL, vectorization benchmark, MV, Kafka hay cluster.

## Bắt đầu

Chạy trong Ubuntu/WSL2; dữ liệu và repo chạy nên nằm trên filesystem Linux.
ClickHouse server/client/local được ghim **26.10.3.7**. Python >=3.10.
Runner chỉ dùng thư viện chuẩn; matplotlib chỉ dùng để vẽ hình.

```bash
git clone https://github.com/w1ndS0ng/clickhouse-mergetree-study.git
cd clickhouse-mergetree-study
# Trỏ đến cấu hình riêng của bạn, không commit file này.
export CH_CONFIG=/path/to/private/client.xml
python3 scripts/study.py status
python3 -m unittest discover -s tests -v
```

## Cấu hình kết nối ClickHouse

`client.xml` là **file đăng nhập/kết nối**, khác với file cấu hình thí nghiệm
`configs/protocol.json`. Trên máy Tài, file đã có tại:

```text
/home/anhtai06/clickhouse-project/config/client.xml
```

Các thông tin kết nối đã xác minh trên máy Tài:

| Thành phần | Giá trị | Ý nghĩa |
|---|---|---|
| Môi trường | Ubuntu trên WSL2 | Chạy lệnh trong terminal Ubuntu |
| Host trong XML | `127.0.0.1` | ClickHouse trên cùng máy |
| User trong XML | `default` | Tài khoản ClickHouse, không phải user Ubuntu |
| Password trong XML | Mật khẩu riêng đã lưu tại máy | Script đọc trực tiếp từ file |
| Quyền file | `0600`, chủ sở hữu `anhtai06` | Chỉ chủ file được đọc/ghi |
| Cổng native của `clickhouse-client` | `9000` mặc định | XML hiện tại không khai báo riêng trường `port` |
| Cổng HTTP của script Python | `8123` mặc định | Runner dùng HTTP, điều chỉnh bằng `CH_HTTP_PORT` |
| Thư mục repo chạy trên máy Tài | `/home/anhtai06/mergetree-study-v1` | Chứa script và kết quả nghiên cứu mới |

Cấu trúc tối thiểu của file như sau; `YOUR_LOCAL_PASSWORD` chỉ là chỗ giữ chỗ,
không phải mật khẩu của máy Tài:

```xml
<config>
    <host>127.0.0.1</host>
    <user>default</user>
    <password>YOUR_LOCAL_PASSWORD</password>
</config>
```

Máy Tài dùng file hiện có, không cần tạo lại:

```bash
cd /home/anhtai06/mergetree-study-v1
export CH_CONFIG=/home/anhtai06/clickhouse-project/config/client.xml
export CH_HOST=127.0.0.1
export CH_HTTP_PORT=8123
python3 scripts/study.py status
```

Trong phiên bản runner hiện tại, `CH_CONFIG` cung cấp **user/password** từ XML;
host/port HTTP lấy từ `CH_HOST`/`CH_HTTP_PORT`, mặc định `127.0.0.1:8123`.
Trường `host` hoặc `port` trong XML dành cho native client không tự thay host/port
của runner. Cổng `9000` và `8123` thuộc hai giao thức khác nhau.

Có thể kiểm tra native client bằng cùng file, không cần viết mật khẩu vào lệnh:

```bash
clickhouse-client --config-file="$CH_CONFIG" --query "SELECT version(), timezone()"
```

Hà/Tuấn dùng thông tin đăng nhập trên máy của mình. Nếu chưa có file, sao chép
[mẫu không chứa mật khẩu thật](configs/client.example.xml) ra ngoài repo, chỉnh
trực tiếp bằng editor và đặt quyền file:

```bash
mkdir -p ~/.config/mergetree-study
cp configs/client.example.xml ~/.config/mergetree-study/client.xml
chmod 600 ~/.config/mergetree-study/client.xml
nano ~/.config/mergetree-study/client.xml
export CH_CONFIG="$HOME/.config/mergetree-study/client.xml"
python3 scripts/study.py status
```

Thay `YOUR_LOCAL_PASSWORD` trong editor bằng mật khẩu ClickHouse của chính máy đó.
Mật khẩu không cần giống nhau giữa ba thành viên. Không đưa mật khẩu thật vào
lệnh, GitHub, Docs hay file kết quả; chỉ file mẫu ở trên được đưa vào repo.

## Cấu hình thực nghiệm dùng chung

Nguồn cấu hình là [`configs/protocol.json`](configs/protocol.json); runner lưu
bản chụp vào `results/<member>/<machine>/<run>/config.json`. Không đặt các tham số
benchmark dưới đây vào file đăng nhập `client.xml`.

| Tham số | Giá trị trong protocol hiện tại |
|---|---|
| ClickHouse server/client/local | `26.10.3.7` |
| Dataset chính | `30.000.000` sự kiện, `12` cột, RowBinary `44` byte/dòng |
| Tập hiệu chỉnh | `1M`, `3M`, `10M`; mẫu lồng nhau trên toàn bộ 30 shard |
| Engine / codec / part type | `MergeTree` / `LZ4` / `Wide` |
| Partition | Không khai báo `PARTITION BY` |
| Primary key | Mặc định theo `ORDER BY`, không phải ràng buộc duy nhất |
| Khóa E1 | `tuple()`, `(CounterID, EventDate)`, `(EventDate, CounterID)` |
| `max_threads` | `4` luồng truy vấn |
| `max_insert_threads` | `1` luồng nạp |
| `max_memory_usage` | `2.000.000.000` byte cho mỗi query, khoảng `1,86 GiB` |
| `index_granularity` | E1/E3: `8192`; E2: `2048`, `8192`, `32768` |
| `index_granularity_bytes` / `write_final_mark` | `0` / `0`, đặt trong DDL |
| `async_insert` / `fsync_after_insert` | `0` / `1`; `fsync_after_insert` đặt trong DDL |
| Query cache / query condition cache | Tắt: `use_query_cache=0`, `use_query_condition_cache=0` |
| Tối ưu đọc bổ sung | Tắt skip indexes, tự động PREWHERE, read/aggregation-in-order trong đối chứng |
| Batch E3 | `10.000`, `100.000`, `1.000.000` dòng/request |
| Lặp query | `2` warmups + `10` lượt đo/cell |
| Lặp ingestion | `3` vòng cho mỗi batch, luân phiên thứ tự |
| Kiểm tra ổn định | `3` quan sát, cách `10s`, tối đa `1200s` |
| Seed đảo thứ tự query | `20261116` |
| Lưu thời gian sự kiện | `EventTime DateTime('UTC')` trong schema |

Hà/Tuấn/Tài giữ chung protocol nhưng mỗi máy có host, tài khoản và đường dẫn riêng.
Kết quả luôn tách theo thành viên/máy/run; mọi đối chứng và speedup được tính trên
cùng máy. Đây là thiết lập nghiên cứu có kiểm soát; thay đổi sau pilot phải được
ghi vào protocol chung trước khi bắt đầu run chính mới.

## Dữ liệu chung

Giữ **30 triệu sự kiện**, chọn **12 cột số/ngày/giờ** từ 105 cột gốc; 44 byte/dòng
trong RowBinary chưa nén. Không tạo thêm dòng bằng nhân bản hay sinh dữ liệu giả.
30 shard được cố định trong `configs/protocol.json`; 10 shard đầu trùng bộ 10M cũ.
Các tập 1M/3M/10M là mẫu hệ thống lồng nhau rải trên toàn bộ 30 file: giữ vị trí dòng
toàn cục modulo30 <1/<3/<10. Đây là cách lấy mẫu xác định, không phải mẫu ngẫu nhiên.

Tuấn chuẩn bị và commit manifest khóa trước; ba người sử dụng cùng manifest:

```bash
# Tuấn: bỏ --reuse-dir nếu chưa có các file cũ.
python3 scripts/study.py dataset --shards 30 \
  --reuse-dir /path/to/old/data \
  --publish-lock manifests/hits30m.lock.json

# Hà/Tài: sau khi git pull có manifest chung.
python3 scripts/study.py dataset --shards 30 \
  --lock manifests/hits30m.lock.json \
  --reuse-dir /path/to/old/data
```

Nguồn chuẩn: `https://datasets.clickhouse.com/hits_compatible/athena_partitioned/`.
Quá trình tải/chuyển định dạng/checksum **nằm ngoài thời gian đo**. Script xác minh
mỗi shard có 1M dòng; số dòng sai hoặc hash khác sẽ dừng, không tự cắt/nhân bản.
Tuấn tạo `manifests/hits30m.lock.json` sau khi tải đủ30 shard và kiểm tra các mẫu;
cả ba dùng cùng file khóa. Không tự điền checksum khi chưa tải/kiểm tra dữ liệu.

`dataset --shards 1` chỉ kiểm tra tải/chuyển đổi. Sau khi chuẩn bị đủ30 shard và mẫu,
tạo **run pilot riêng**, rồi `build/queries --scale 1m` với thí nghiệm của mình.
Tạo **run chính mới** sau pilot; manifest của một run là bất biến.
Không tiếp tục run đã lỗi bằng cách nạp lại hoặc ghi đè journal.

## Phân công và lệnh chạy chính

| Thành viên | Thí nghiệm | Chương 2 | Chương 3 | Chương 4 |
|---|---|---|---|---|
| Hà | Sorting key, hiệu chỉnh/dự đoán thời gian | 2.1–2.2 | 3.1, 3.3 | 4.1 |
| Tuấn | Dataset chung, granularity/index size | 2.3–2.4 | 3.2, 3.4 | 4.2 |
| Tài | Batch INSERT, parts và background merge | 2.5–2.6 | 3.5–3.6 | 4.3–4.5 |

Sau pilot và chốt protocol, mỗi người dùng **một trong** các lệnh sau, thay nhãn máy/run:

```bash
bash scripts/run_member.sh ha laptop1 main01
bash scripts/run_member.sh tuan laptop2 main01
bash scripts/run_member.sh tai laptop3 main01
```

Không chạy cả ba lệnh đồng thời trên một máy. Script Hà tự đóng băng model và dự đoán
trước khi đo 30M. Script Tuấn chạy 3 granularity; Tài chạy 9 lần nạp 30M
(3 batch size × 3 lặp, thứ tự luân phiên). `run_member.sh` tạo run một lần;
không chạy lại toàn bộ lệnh với cùng run ID.

Xem từng bước, SQL, số liệu, công thức và tiêu chí nghiệm thu trong
[hướng dẫn thực nghiệm](docs/PROTOCOL_VI.md) và [kế hoạch báo cáo](docs/REPORT_PLAN_VI.md).
Bản nộp tối đa30trang toàn bộ, Times New Roman13; xem
[ngân sách từng chương](docs/PAGE_BUDGET_VI.md). Checklist/SQL/log đầy đủ nằm trong repo,
không chép nguyên vào bản nộp. Script vẽ hình dùng Times New Roman13 từ font có trên máy.

## Kết quả

```text
results/<member>/<machine>/<run>/
  config.json, environment.json, effective_settings.json, input_manifest.json
  ddl/ sql/ explain/ checks/ setup/
  queries/           # journal, CSV từng lượt, system.query_log
  ingest/            # từng batch, 9 lượt nạp, part_log, timeline, storage
  model/             # hệ số + dự đoán có timestamp và hash
  summary/           # median, Q1, Q3, IQR; estimated_vs_actual.csv
  figures/           # PNG + SVG
```

```bash
# Thay bộ ba nhãn bằng đúng run của bạn.
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/study.py plot --member ha --machine laptop1 --run main01
python3 scripts/study.py package --member ha --machine laptop1 --run main01
```

`share_results.zip` chứa hồ sơ thực nghiệm, không chứa dataset hay cấu hình mật khẩu.
Thư mục `results/` mặc định không được Git theo dõi. Chỉ đưa bộ kết quả đã rà soát
vào `artifacts/<member>/<machine>/<run>/`; giữ ZIP lớn ở Release nếu cần.

## Cộng tác

Mỗi người dùng nhánh `ha/sorting-key`, `tuan/granularity`, `tai/batch-merge`.
Sửa protocol/schema/workload chung phải qua PR và tăng phiên bản protocol **trước khi đo**.
Review vòng: Hà → Tuấn → Tài → Hà. Một người tái lập ít nhất một đối chứng của người khác.
Không lấy thời gian máy Hà chia cho thời gian máy Tuấn để tính speedup.
Kết quả khác máy chỉ đối chiếu xu hướng/tỷ lệ nội bộ và công bố đầy đủ môi trường.

## Kiểm tra và tài nguyên

```bash
python3 scripts/smoke_test.py
```

Smoke test sinh tối đa 30 nghìn dòng, kiểm tra pipeline và ghi `SMOKE_ONLY.json`;
**không được dùng các số này trong báo cáo**. Script không tự xóa database nào.
Các database mới có tiền tố `mtr_<member>_<machine>_<run>`; dữ liệu cũ `ch3`, `exp35`
và chương trình MV cũ được giữ nguyên.

Dự trù khoảng 15–25 GiB trống cho nguồn, binary, bảng đối chứng và merge; đây là ngân sách
thận trọng, cần điều chỉnh sau pilot. Trên WSL kiểm tra cả ổ vật lý Windows chứa VHDX,
không dựa riêng vào dung lượng đĩa ảo do `df` báo. Repo không tự tải/chạy 30M khi clone.

Nguồn và giới hạn được nêu trong [PROTOCOL_VI.md](docs/PROTOCOL_VI.md).
