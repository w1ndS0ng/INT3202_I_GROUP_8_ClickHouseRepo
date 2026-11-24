# Minh chứng dùng trong báo cáo của Tuấn

Nội dung báo cáo hiện hành nằm trong các tab Tuấn của [Google Docs](https://docs.google.com/document/d/1eA1XSvGx-8YbP02ilUgHmPeRKYKhRwCHg_8KZZysm3o).
Các đường dẫn dưới đây chứa dữ liệu để kiểm chứng số liệu và hình, không chứa dataset hits.

| Phần báo cáo | Minh chứng | Phạm vi |
|---|---|---|
| 2.3 | [Hình 2.3](theory/figures/figure_2_3.png) | Ví dụ giả định 16 dòng, ba cách sắp xếp K0/K1/K2. Dấu ✓ chỉ granule chứa hàng khớp, không phải kết quả chọn marks thực tế của ClickHouse. |
| 2.4 | [Hình 2.4](theory/figures/figure_2_4.png) | Minh họa g=2/g=8, không phải số đo benchmark. Hai PNG được lấy từ hình đang nhúng trong Docs, không tạo lại hình. |
| 3.2 — nguồn/schema/mẫu | [Manifest](../../manifests/) | Khóa 30 shard, SHA-256, audit schema/lấy mẫu và profile 1M/3M/10M/30M. Không đưa Parquet/RowBinary lên Git. |
| 3.2 — môi trường/công cụ đo | [preparation_20261116](wsl_xeon/preparation_20261116/) | Môi trường Windows/Linux, probe schema/settings/query/storage, điều kiện ổn định và phép thử journal lỗi có chủ đích. |
| 3.2 — pilot công cụ | [pilot_v2_20261117](wsl_xeon/pilot_v2_20261117/) | Probe nạp/parts, fingerprint, DDL và journal. Không dùng làm kết quả hiệu năng chính thức. |
| 3.2/3.4 — pilot E2 | [e2pilot_v2_20261117](wsl_xeon/e2pilot_v2_20261117/) | 1M dòng, ba granularity, 150 số đo chính sau 30 warmup. |
| 3.4 — kết quả E2 | [e2main_v2_20261117](wsl_xeon/e2main_v2_20261117/) | 30M dòng, 150 số đo, QueryFinish, EXPLAIN, storage và Hình 3.1 v5. |
| 4.2 — pilot đối chiếu | [pilot42_v2_20261123](wsl_xeon/pilot42_v2_20261123/) | 1M dòng, crossdb-v2; 250 số đo và 50 warmup. Không dùng kết luận hiệu năng 30M. |
| 4.3.1–4.3.2, 4.5 | [formal43_v3_20261123](wsl_xeon/formal43_v3_20261123/) | 30M dòng, crossdb-v3; 250 số đo và 50 warmup, năm cấu hình CH0/CH1/PG0/PG1/PG2. |

## Đọc và tái lập số liệu

- E2: `queries/` chứa CSV từng lượt, journal và QueryFinish; `summary/` chứa thống kê truy vấn/dung lượng; `explain/`, `ddl/`, `sql/` chứa điều kiện thực thi. `checks/` lưu fingerprint, trạng thái ổn định và đối chiếu sau đo.
- Hình 3.1 dùng `e2main_v2_20261117/figures/e2_granularity_tradeoff_v5.png` hoặc SVG cùng tên. Các tệp audit hình trong thư mục này là hồ sơ lúc tạo v5.
- Chương 4: `queries.csv`, `summary.csv`, `report_tables.json`, `ch_pruning.csv`, `pg_scans.csv` và `plans.json` là nguồn Bảng 4.3–4.5.
- Dung lượng Chương 4: `ch_storage.json`, `pg_storage.json`; chi phí chuẩn bị: `setup.json`. Thời gian chuẩn bị chỉ có một lần mỗi cấu hình, không phải trung vị của các lượt SELECT.
- Nguồn xử lý E2 được truy vết bằng `measurement_commit` và `figure_processing_commit` trong `e2main_v2_20261117/validation.json`; mã ở các commit đó còn trong lịch sử Git. Chương 4 giữ bản chụp mã/cấu hình trong `source/` và `source_hashes.json` của từng run.
- Mỗi thư mục minh chứng có `files.sha256.json`. Khóa là đường dẫn tương đối; giá trị là SHA-256 của toàn bộ byte tệp. `.gitattributes` giữ nguyên byte khi checkout trên hệ điều hành khác.

## Trạng thái và lịch sử

`validation.json` của E2 là bản kiểm tra có thời điểm và revision Docs riêng. Những trường về cỡ chữ, số trang, số bảng trong tệp này mô tả bản Docs lúc kiểm tra, không đại diện cho định dạng hiện tại. Số liệu gốc vẫn được giữ nguyên. Review/tái lập độc lập còn chờ.

Bản `report.md`/`report.pdf` E2 cũ và kế hoạch báo cáo cũ đã được bỏ khỏi cây hiện hành vì khác bản Docs hiện tại; có thể tra lịch sử Git khi cần. ZIP chia sẻ E2 cũ chứa nhiều hình v1–v4 và ZIP lồng nhau; dùng cây minh chứng hiện hành và checksum thay cho ZIP này. Pilot đối chiếu crossdb-v1 đã bị crossdb-v2 thay thế và không được dùng trong báo cáo.

File probe workload ban đầu ở `preparation_20261116/` được giữ để giải thích việc đổi literal trước lần chạy v2. Lượt lỗi cố ý kiểm tra journal được giữ cùng nhãn rõ ràng, không phải số đo benchmark và không bị loại để làm đẹp kết quả.

## Minh chứng của các thành viên khác

Các thư mục sau đã hiện diện trên nhánh remote khi rà soát; việc này xác nhận vị trí file, không thay thế review hoặc tái lập kết quả của người thực hiện:

- [E1 của Hà trên nhánh main](https://github.com/w1ndS0ng/clickhouse-mergetree-study/tree/main/artifacts/ha/laptop1/main01).
- [Ba đợt E3 của Tài](https://github.com/w1ndS0ng/clickhouse-mergetree-study/tree/f141aac6efb168a69a05d1ebf0fdba39da36d18d/artifacts/tai/wsl_i5/e3_three_runs_20261117).
- [Phân tích E3 hồi cứu và EXPLAIN của Tài](https://github.com/w1ndS0ng/clickhouse-mergetree-study/tree/5cde904a51dfe7b0f4db1f327b17b1412ba86b3e/artifacts/tai/wsl_i5/e3_followup_20261117).

Không sao chép hoặc sửa số liệu Hà/Tài vào thư mục Tuấn. Minh chứng Chương 4 trên máy Xeon không có nghĩa đã tái lập trên máy i5 của Tài.
