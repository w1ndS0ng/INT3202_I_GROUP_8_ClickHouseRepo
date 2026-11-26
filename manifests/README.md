# Bản kê dữ liệu và khóa kiểm toàn vẹn (`manifests/`)

Thư mục này lưu các tệp kiểm toán dữ liệu đầu vào và mã băm SHA-256 dùng chung cho `30` phân đoạn ClickBench `hits` (`30.000.000` dòng, `12` cột, `44` byte/dòng ở định dạng `RowBinary`):

- [`hits30m.sources.json`](hits30m.sources.json): Danh sách URL, kích thước, số dòng và SHA-256 của `30` tệp Parquet gốc.
- [`hits30m.schema-audit.json`](hits30m.schema-audit.json) & [`hits30m.e3.schema-audit.json`](hits30m.e3.schema-audit.json): Kết quả kiểm tra kiểu dữ liệu `12` cột, biên giá trị và fingerprint nguồn–đích.
- [`hits30m.sampling-audit.json`](hits30m.sampling-audit.json): Kiểm chứng phân mẫu hệ thống lồng nhau (`1M`, `3M`, `10M`, `30M`) theo quy tắc `ordinal mod 30`.
- [`hits30m.profile.json`](hits30m.profile.json) & [`hits30m.e3.profile.json`](hits30m.e3.profile.json): Thống kê phân bố `EventDate`, `CounterID`, `RegionID` và đáp án đối chứng.
- [`hits30m.lock.json`](hits30m.lock.json) & [`hits30m.e3.lock.json`](hits30m.e3.lock.json): Tệp khóa SHA-256 cố định thứ tự shard và tệp `RowBinary` giữa các máy thực nghiệm.
