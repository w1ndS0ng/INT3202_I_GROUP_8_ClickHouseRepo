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
