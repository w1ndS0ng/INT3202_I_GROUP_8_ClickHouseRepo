# MergeTree Internals on ClickBench-derived Clickstream Data

Nghiên cứu một node ClickHouse: **sorting key → sparse index/granule pruning → thời gian đọc**;
**granularity → đánh đổi pruning và dung lượng chỉ mục**;
**batch INSERT → data parts/background merges → tốc độ ghi và dung lượng**.

Đây là thực nghiệm tùy biến từ ClickBench, không phải điểm ClickBench chính thức.
Các thí nghiệm chương 3 không triển khai PostgreSQL, vectorization benchmark, MV, Kafka hay cluster.
Đối chiếu PostgreSQL ở mục 4.2–4.3 được tách riêng trong `configs/comparison.json` và
`scripts/compare_databases.py`, với run pilot 1M và run chính thức 30M độc lập.

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

Máy Tài đã có cấu hình tại `/home/anhtai06/clickhouse-project/config/client.xml`.
Không đưa mật khẩu vào lệnh, GitHub, Docs hay file kết quả.

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
| Hà | Sorting key, hiệu chỉnh/dự đoán thời gian | 2.1–2.2 | 3.1, 3.3 | — |
| Tuấn | Dataset chung, granularity/index size | 2.3–2.4 | 3.2, 3.4 | 4.2, 4.3.1–4.3.2, 4.5 |
| Tài | Batch INSERT, parts và background merge | 2.5–2.6 | 3.5–3.6 | 4.1, 4.3.3–4.3.4, 4.4 |

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
[hướng dẫn thực nghiệm](docs/PROTOCOL_VI.md) và [Outline Báo cáo hiện hành](https://docs.google.com/document/d/1eA1XSvGx-8YbP02ilUgHmPeRKYKhRwCHg_8KZZysm3o/edit?tab=t.le5tjknhw5zq).
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
Tra cứu [minh chứng theo từng phần báo cáo của Tuấn](artifacts/tuan/README.md),
gồm hình Chương 2, dữ liệu/kiểm tra Chương 3 và đối chiếu Chương 4.

## Cộng tác

### Đối chiếu PostgreSQL (mục 4.2–4.3)

Workflow này dùng hai instance nghiên cứu riêng, ClickHouse 26.10.3.7 và PostgreSQL
18.6; không dùng lại các bảng/kết quả chương 3 làm baseline thời gian. Cài dependency
tùy chọn bằng `pip install -r requirements-comparison.txt`. Trên Linux, client và
server đều dùng CPU affinity 0–3; cấu hình PostgreSQL và chính sách RAM/cache được
ghi trong hồ sơ chạy. Các tham số RAM hai hệ không phải hai giới hạn tổng tương đương.
Instance ClickHouse dành riêng đặt `keep_alive_timeout=3600` để kết nối HTTP không
đóng trong lúc các cấu hình PostgreSQL đang được đo; runner kiểm thiết lập này.

```bash
CH_HTTP_PORT=18124 taskset -c 0-3 python scripts/compare_databases.py \
  --data /path/to/locked/dataset --derived /path/to/derived-input \
  --pg-socket /path/to/private/pgsocket --pg-port 55432 \
  --machine wsl_xeon --run pilot42_new --scale 1m
```

Lệnh trên chạy pilot 1M: giữ nguồn gốc, chuyển sang PostgreSQL COPY BINARY ngoài
thời gian đo, dựng CH0/CH1/PG0/PG1/PG2, kiểm toàn bộ 12 cột và COUNT/SUM, lưu
DDL/EXPLAIN/settings, 50 warmup và 250 lượt SELECT. Kết quả mang nhãn
`PASS_PILOT_ONLY`; không dùng làm kết luận hiệu năng 30M. Đo chính thức bằng
`--scale 30m` với một run ID mới; runner kiểm SHA-256 cả 30 shard trước nạp và chỉ
ghi `PASS_FORMAL` khi kiểm dữ liệu, đáp án, QueryFinish và trạng thái parts đạt.
Dùng `python scripts/audit_comparison.py results/tuan/<machine>/<run>` để tính lại
thống kê và sinh bảng đối chiếu từ số đo gốc, không truy vấn lại database. Dùng run ID mới mỗi lần;
runner không tự xóa hoặc ghi đè database/schema/thư mục kết quả đã tồn tại.

Hồ sơ đã công bố của Tuấn (CSV từng lượt, QueryFinish, SQL/DDL/EXPLAIN, cấu hình,
kiểm dữ liệu, dung lượng, thời gian chuẩn bị và SHA-256; không chứa dataset):

- [Pilot 1M, crossdb-v2](artifacts/tuan/wsl_xeon/pilot42_v2_20261123/): kiểm tra quy trình, không dùng kết luận hiệu năng 30M.
- [Formal 30M, crossdb-v3](artifacts/tuan/wsl_xeon/formal43_v3_20261123/): 250 lượt đo và 50 warmup; bảng kết quả ở `report_tables.json`, chi phí chuẩn bị ở `setup.json`, dung lượng ở `ch_storage.json` và `pg_storage.json`.

`files.sha256.json` kiểm tra toàn vẹn tệp; `audit.json` ghi kết quả đối chiếu tự động.
Trạng thái này không thay thế tái lập độc lập, hiện vẫn chưa thực hiện.

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
