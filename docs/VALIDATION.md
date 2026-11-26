# Tổng hợp kiểm chứng mã nguồn và dữ liệu E2

Toàn bộ kết quả và mã kiểm chứng hiện được lập chỉ mục theo từng mục báo cáo tại [`chapter-2/`](../chapter-2/README.md), [`chapter-3/`](../chapter-3/README.md) và [`chapter-4/`](../chapter-4/README.md).

## Kiểm thử tự động

- **Unit tests (`tests/`):** Kiểm tra logic chia lô `RowBinary` giữ đúng biên và thứ tự bản ghi qua ranh giới tệp; kiểm tra quy tắc phân mẫu hệ thống lồng nhau (`ordinal mod 30`); kiểm chứng hồi quy bình phương tối thiểu có ràng buộc ($\alpha, \beta \ge 0$); kiểm tra ánh xạ kiểu dữ liệu và ngữ nghĩa đối chiếu ClickHouse–PostgreSQL.
- **Kiểm tra toàn vẹn dữ liệu đầu vào:** Xác minh SHA-256 trên toàn bộ `30` tệp Parquet nguồn, `30` tệp `RowBinary` (`44` byte/dòng, `1.320.000.000` byte) và các mẫu lồng nhau `1M`, `3M`, `10M`.

## Kiểm chứng thực nghiệm E2 (17/11/2026)

- **Phạm vi đối chiếu:** Pilot 1M (`e2pilot_v2_20261117`) và lần chạy chính thức 30M (`e2main_v2_20261117`) theo protocol `mergetree-v2`, thực hiện trên ba bảng khóa `K1`, `CODEC(LZ4)` với một active Wide part (`index_granularity` lần lượt là `2048`, `8192`, `32768`; commit đo `2e65b9d`).
- **Nội dung đã xác minh:**
  - Khớp SHA-256 của `30` phân đoạn nguồn, đối chiếu từng byte quy tắc phân mẫu `ordinal mod 30` và phân bố `EventDate`, `CounterID`, `RegionID`.
  - Xác minh DDL thực tế, `20` thiết lập truy vấn có hiệu lực và trạng thái `1` active Wide part trước/sau khi đo của cả ba bảng `30M`.
  - Đối chiếu đủ `150` lượt đo chính và `30` lượt làm nóng trong `system.query_log` (`150/150` `QueryFinish`), tính lại độc lập trung vị, `Q1`, `Q3` và `IQR` khớp hoàn toàn với bảng CSV tổng hợp.
- **Hồ sơ lưu trữ:** [`chapter-3/3.4.1/`](../chapter-3/3.4.1/), [`chapter-3/3.4.2/`](../chapter-3/3.4.2/), [`chapter-3/3.4.3/`](../chapter-3/3.4.3/) và [`chapter-3/3.4.4/`](../chapter-3/3.4.4/).
