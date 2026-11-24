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

## Cấu trúc theo Chương và Tiểu mục (`chapter-2/`, `chapter-3/`, `chapter-4/`)

Toàn bộ hình vẽ, mã thực thi/kiểm chứng và minh chứng kết quả của cả 3 thành viên (Hà, Tuấn, Tài) đã được tổ chức thống nhất theo từng chương và tiểu mục báo cáo. Mỗi tiểu mục đều gồm `scripts/`, `results/` (kèm `files.sha256.json`) và `README.md`; các đợt đo hoặc phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo đúng trình tự thời điểm đưa vào nghiên cứu:

- **[Chương 2 — Cơ sở lý thuyết MergeTree](chapter-2/README.md):** [`2.3`](chapter-2/2.3/) (Sorting key & sparse primary index), [`2.4`](chapter-2/2.4/) (Granules, marks & công thức kích thước chỉ mục).
- **[Chương 3 — Thực nghiệm MergeTree](chapter-3/README.md):**
  - `3.1` ([RQ1–RQ5](chapter-3/3.1/)); `3.2` ([`3.2.1`](chapter-3/3.2.1/) Dataset/manifest `ver1`–`ver2`, [`3.2.2`](chapter-3/3.2.2/) Môi trường & thiết lập, [`3.2.3`](chapter-3/3.2.3/) Workload W0–W4 `ver1`–`ver2`, [`3.2.4`](chapter-3/3.2.4/) Lịch lặp & ổn định).
  - `3.3` — Thực nghiệm E1 của Hà: [`3.3.1`](chapter-3/3.3.1/), [`3.3.2`](chapter-3/3.3.2/), [`3.3.3`](chapter-3/3.3.3/), [`3.3.4`](chapter-3/3.3.4/).
  - `3.4` — Thực nghiệm E2 của Tuấn (`ver1` pilot 1M, `ver2` chính thức 30M): [`3.4.1`](chapter-3/3.4.1/), [`3.4.2`](chapter-3/3.4.2/), [`3.4.3`](chapter-3/3.4.3/), [`3.4.4`](chapter-3/3.4.4/).
  - `3.5` — Thực nghiệm E3 của Tài (`ver1` 1 đợt, `ver2` 3 đợt = 27 lượt nạp): [`3.5.1`](chapter-3/3.5.1/), [`3.5.2`](chapter-3/3.5.2/), [`3.5.3`](chapter-3/3.5.3/), [`3.5.4`](chapter-3/3.5.4/).
  - `3.6` — Mô hình thời gian & nghiệm thu (`ver1` E3 hồi cứu, `ver2` E1 SELECT holdout): [`3.6.1`](chapter-3/3.6.1/), [`3.6.2`](chapter-3/3.6.2/), [`3.6.3`](chapter-3/3.6.3/), [`3.6.4`](chapter-3/3.6.4/), [`3.6.5`](chapter-3/3.6.5/).
- **[Chương 4 — Đối chiếu MergeTree với PostgreSQL](chapter-4/README.md):** [`4.1`](chapter-4/4.1/), [`4.2`](chapter-4/4.2/) (`ver1` Xeon pilot 1M, `ver2` Core i5 pilot 1M), [`4.3.1`](chapter-4/4.3.1/) (Query latency Bảng 4.3), [`4.3.2`](chapter-4/4.3.2/) (Pruning & EXPLAIN Bảng 4.4–4.5), [`4.3.3`](chapter-4/4.3.3/) (Dung lượng: `ver1` Xeon, `ver2` Core i5 Bảng 4.6), [`4.3.4`](chapter-4/4.3.4/) (Chi phí chuẩn bị: `ver1` Xeon, `ver2` Core i5 Bảng 4.7), [`4.4`](chapter-4/4.4/), [`4.5`](chapter-4/4.5/).

Thư mục chạy nháp cục bộ tại gốc (`/results/<member>/<machine>/<run>/`) vẫn được `.gitignore` bỏ qua để không đẩy nhầm dữ liệu thô chưa rà soát:

```bash
# Thay bộ ba nhãn bằng đúng run cục bộ của bạn khi chạy mới:
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/study.py plot --member ha --machine laptop1 --run main01
python3 scripts/study.py package --member ha --machine laptop1 --run main01
```

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

Hồ sơ đối chiếu đã công bố của nhóm (CSV từng lượt, QueryFinish, SQL/DDL/EXPLAIN, cấu hình,
kiểm dữ liệu, dung lượng, thời gian chuẩn bị và SHA-256; không chứa dataset):

- [Pilot 1M Xeon (`ver1`, `crossdb-v2`)](chapter-4/4.2/results/ver1_xeon_pilot_1m/) và [Pilot 1M Core i5 (`ver2`)](chapter-4/4.2/results/ver2_i5_pilot_1m/): kiểm tra quy trình ở mục 4.2.
- [Formal 30M Xeon (`ver1`, `crossdb-v3`)](chapter-4/README.md): độ trễ ở [`4.3.1`](chapter-4/4.3.1/results/), kế hoạch thực thi & pruning ở [`4.3.2`](chapter-4/4.3.2/results/), bảng tổng hợp & kiểm toán ở [`4.5`](chapter-4/4.5/results/).
- [Formal 30M Core i5 (`ver2`)](chapter-4/4.3.3/results/ver2_i5_30m/): dung lượng đối tượng ở [`4.3.3`](chapter-4/4.3.3/results/) và thời gian chuẩn bị ở [`4.3.4`](chapter-4/4.3.4/results/).

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
