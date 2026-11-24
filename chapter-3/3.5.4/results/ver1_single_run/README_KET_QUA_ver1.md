# Hồ sơ thực nghiệm3.5 — 17/11/2026

Đã hoàn tất9case30M: batch10k/100k/1M, mỗi batch3vòng;9.990request;270M dòng
được nạp qua các lần lặp. Dataset gốc vẫn30M dòng/12cột, không nhân bản để tăng quy mô.

- Bang_9_luot_30M.csv: số đo từng case; Tong_hop_3_batch.csv: median/Q1/Q3/IQR.
- BAO_CAO_KET_QUA_3_5.md: bảng và định nghĩa/giới hạn để viết báo cáo.
- hinh/: PNG/SVG, Times New Roman13. Các chấm là3lượt riêng, errorbars làQ1–Q3.
- Ket_qua_3_5_day_du.zip: raw logs, DDL, checks, protocol, môi trường, fingerprint,
  source audit và bản code đã khóa. Không chứa dataset payload hoặc cấu hình đăng nhập thật.
- pilot_1M/: dữ liệu kiểm tra pipeline, không gộp vào bảng30M.
- SHA256SUMS.txt: checksum mọi file trong bộ bàn giao.

Nguồn chạy: protocol mergetree-v2-e3-r1, commit0c360382b07c584f11957782079b144cee13cb75.
Thông số lấy theo mô tả v2 trong Docs; code/manifest được tái tạo và audit độc lập.
30M có profile/workload counts khớp báo cáo E2; mẫu1M có một số thống kê khác pilot Tuấn.
Chưa có curator hash-lock để xác nhận byte-for-byte cùng bản khóa của máy E2.

Raw DB và kết quả vẫn được giữ trong Ubuntu:
/home/anhtai06/mergetree-study-v1/results/tai/wsl_i5/e3main_v2_20261117/
Các bảng có tiền tố mtr_tai_wsl_i5_e3main_v2_20261117; merge tương lai có thể làm đổi
trạng thái bảng, nên dùng snapshot đã lưu khi đọc kết quả thực nghiệm.

ACK time là first HTTP send→last complete response, gồm input/journal giữa batch.
Observed stable wait có cửa sổ xác nhận tối thiểu20s, không phải merge duration hayCPUtime.
Merge row amplification là proxy read_rows của các MergeParts trong cửa sổ quan sát.
Active storage không phản ánh mọi inactivepart/filetạm hay toàn bộ VHDX.
Không chia time khác máy, không coi3lượt là kiểm định thống kê cho mọi workload.
