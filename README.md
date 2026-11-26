# Nghiên cứu cơ chế MergeTree trên ClickHouse (INT3202 — Nhóm 8)

Kho lưu trữ mã nguồn, cấu hình thực nghiệm, bộ kiểm chứng và dữ liệu kết quả cho nghiên cứu về động cơ lưu trữ **MergeTree** trên nút đơn ClickHouse với bài toán dữ liệu luồng nhấp chuột (*clickstream* dạng *append-only*).

Các nội dung thực nghiệm gồm:
- **E1 (`3.3`):** Thứ tự khóa sắp xếp (`ORDER BY`) và khả năng cắt tỉa của chỉ mục chính thưa (*sparse primary index*).
- **E2 (`3.4`):** Độ mịn chỉ mục (`index_granularity`) và đánh đổi giữa lượng dữ liệu đọc, độ trễ và kích thước chỉ mục/marks.
- **E3 (`3.5`):** Kích thước lô `Batch INSERT`, tốc độ nạp và áp lực hợp nhất nền (*background merges*).
- **Mô hình ước lượng (`3.6`):** Đánh giá sai số dự đoán thời gian thực thi theo quy mô dữ liệu và đối chiếu hồi cứu.
- **Đối chiếu PostgreSQL (`Chương 4`):** So sánh trực diện MergeTree với PostgreSQL Heap kết hợp chỉ mục BRIN và B-tree trên cùng tập dữ liệu và tải truy vấn.

## Môi trường và bộ dữ liệu

- **Phần mềm:** ClickHouse `26.10.3.7`, PostgreSQL `18.6`, Python `>= 3.10` (môi trường Ubuntu/WSL2).
- **Bộ dữ liệu chuẩn hóa:** `30` phân đoạn (*shard*) từ tập `hits` của [ClickBench](https://github.com/ClickHouse/ClickBench) (schema cố định tại commit [`b0b7dd8f`](https://github.com/ClickHouse/ClickBench/blob/b0b7dd8f11a2a719211cc41d8c7ebbada267df66/clickhouse/create.sql)), tổng cộng `30.000.000` bản ghi và `12` cột định kiểu cố định (`44` byte/dòng ở định dạng `RowBinary`).
- **Phân mẫu hệ thống lồng nhau:** Các tập `1M`, `3M`, `10M` và `30M` được trích xác định theo chỉ số vị trí dòng toàn cục (`ordinal mod 30`), khóa toàn vẹn bằng mã băm SHA-256 trong [`manifests/`](manifests/).

## Cấu trúc kho mã nguồn

- [`chapter-2/`](chapter-2/README.md), [`chapter-3/`](chapter-3/README.md), [`chapter-4/`](chapter-4/README.md): Cấu trúc lưu trữ hình vẽ, mã kiểm chứng (`scripts/`) và kết quả đo (`results/` kèm `files.sha256.json`) tương ứng với từng mục báo cáo. Các đợt đo hoặc bản cập nhật bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2`, ...
- [`src/mtstudy/`](src/mtstudy/): Thư viện lõi chạy thực nghiệm MergeTree, đối chiếu PostgreSQL, tính thống kê và xuất đồ thị.
- [`scripts/`](scripts/): Kịch bản chạy đầu cuối (`study.py`, `run_member.sh`, `compare_databases.py`, `audit_comparison.py`, `audit_e3_sources.py`, ...).
- [`configs/`](configs/): Cấu hình protocol (`protocol.json`, `protocol.e3.v2.json`, `comparison.json`).
- [`manifests/`](manifests/): Danh sách nguồn Parquet/RowBinary, kiểm toán schema, phân bố mẫu và tệp khóa SHA-256.
- [`tests/`](tests/): Bộ kiểm thử đơn vị (*unit tests*).
- [`docs/`](docs/PROTOCOL_VI.md): Đặc tả protocol (`PROTOCOL_VI.md`), tổng hợp kiểm chứng (`VALIDATION.md`, `E3_RUN_20261117.md`) và hình vẽ báo cáo chất lượng cao ([`docs/figures/`](docs/figures/)).

## Phân công và mục lục kết quả

| Thành viên | Phạm vi phụ trách | Mục lục chi tiết |
|---|---|---|
| **Hà** | Cơ sở lý thuyết `2.1–2.2`; Thực nghiệm **E1** (`3.1`, `3.3`); Mô hình SELECT (`3.6`); Chương 5 | [`chapter-3/3.3.3`](chapter-3/3.3.3/), [`chapter-3/3.6.3`](chapter-3/3.6.3/) |
| **Tuấn** | Dataset chung & cơ sở lý thuyết `2.3–2.4`; Thiết lập chung & **E2** (`3.2`, `3.4`); Đối chiếu PG (`4.2`, `4.3.1–4.3.2`, `4.5`) | [`chapter-2/`](chapter-2/README.md), [`chapter-3/3.4.3`](chapter-3/3.4.3/), [`chapter-4/`](chapter-4/README.md) |
| **Tài** | Cơ sở lý thuyết `2.5–2.6`; Thực nghiệm **E3** (`3.5`); Mô hình nạp (`3.6`); Dung lượng & chi phí PG (`4.1`, `4.3.3–4.3.4`, `4.4`) | [`chapter-3/3.5.3`](chapter-3/3.5.3/), [`chapter-4/4.3.3`](chapter-4/4.3.3/), [`chapter-4/4.3.4`](chapter-4/4.3.4/) |

Chi tiết toàn bộ các tiểu mục được lập chỉ mục tại:
- [Mục lục Chương 2](chapter-2/README.md)
- [Mục lục Chương 3](chapter-3/README.md)
- [Mục lục Chương 4](chapter-4/README.md)

## Kiểm tra nhanh

```bash
git clone https://github.com/w1ndS0ng/INT3202_I_GROUP_8_ClickHouseRepo.git
cd INT3202_I_GROUP_8_ClickHouseRepo

python -m unittest discover -s tests -v
python -m compileall -q src scripts chapter-2 chapter-3 chapter-4
python chapter-3/3.4.3/scripts/summarize_and_plot_e2.py
```

Các thông số thiết lập và giới hạn thực nghiệm được mô tả chi tiết trong [PROTOCOL_VI.md](docs/PROTOCOL_VI.md).
