# E3: đối chiếu hồi cứu và chẩn đoán SELECT

Phân tích này bổ sung hồ sơ E3, không thay thế hoặc sửa số liệu gốc của ba run 30M.

## Estimated–actual ingestion

Baseline do nhóm tự xây dựng: `T_est(N,B)=(N/N0)*mean(T_ACK(N0,B))`, N0=1M.
Giả định chi phí trung bình theo dòng/request không đổi khi giữ B và các biến kiểm soát.
Đây là phép ngoại suy tuyến tính thô, không phải công thức gốc của tác giả hoặc cost model ClickHouse.
Các ước lượng được lập sau khi xem kết quả 30M, nên phải gọi là phân tích hồi cứu;
không có forecast được đóng băng trước actual hoặc validation holdout.

Pilot dùng ba lượt/batch; actual dùng chín lượt/batch từ ba formal run.
Giữ mọi số đo, kể cả lượt pilot 10k đầu tiên 17,993 giây. Pilot khác commit và git_dirty=true
do các manifest audit chưa được theo dõi lúc init. So protocol cho thấy chỉ khác mô tả nguồn gốc;
schema/settings/seed và manifest hash giống formal. Các giới hạn này vẫn phải được công bố.

Tái tính từ thư mục repo:

```sh
python scripts/compare_e3_estimate.py --pilot artifacts/tai/wsl_i5/e3_followup_20261117/pilot_1m.csv --formal artifacts/tai/wsl_i5/e3_followup_20261117/formal_27_cases.csv --out /tmp/e3_retrospective_recomputed
```

## EXPLAIN / EXPLAIN ANALYZE

Đã kiểm tra tính năng trên ClickHouse 26.10.3.7 thực tế, không suy từ phiên bản tài liệu.
Hai SELECT `sum(ResolutionWidth)` quét toàn bộ và lọc CounterID=3258 dùng cùng bảng E3 30M/5 parts,
g8192/K1; parts trước/sau giống nhau. Đây là hai chẩn đoán đơn lẻ sau formal run,
không phải benchmark E1 hoặc dữ liệu calibration của mô hình query ở mục 3.6.

EXPLAIN ESTIMATE cho 30.000.000 và 73.728 dòng, khớp read_rows của SELECT thường.
EXPLAIN ANALYZE thực thi query và in thời gian theo bước, không tự cung cấp predicted milliseconds.
Query summary Time là 58,37/11,48ms; query_duration_ms của SELECT thường là 25/3ms.
Thứ tự chạy và instrumentation/cache khác nhau nên không dùng tỷ số này để kết luận overhead nhân quả.
QueryFinish của wrapper EXPLAIN ANALYZE ghi read_rows tăng thêm 42/51 dòng, đúng bằng
result_rows báo cáo plan trong lần đo này; không dùng trực tiếp trường đó làm read_rows của SELECT gốc.

Script `capture_explain.py` chỉ chạy SELECT/EXPLAIN và flush log, không sửa bảng.
Thông tin kết nối được cung cấp qua `--client-config`; không xuất nội dung file đăng nhập.
SQL, plan, analyze, QueryFinish và query_id riêng nằm trong `explain_diagnostics/`.

Nguồn cơ chế:
- https://clickhouse.com/docs/reference/statements/explain
- https://clickhouse.com/docs/reference/system-tables/query_log
- https://www.postgresql.org/docs/18/using-explain.html

PostgreSQL EXPLAIN cost là đơn vị chi phí planner, không phải milliseconds; EXPLAIN ANALYZE
thực thi query và cho số liệu runtime. Chưa chạy benchmark PostgreSQL.
