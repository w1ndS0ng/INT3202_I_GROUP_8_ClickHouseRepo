# Hồ sơ kết quả được duyệt

Mỗi thành viên đặt bản đã rà soát vào `artifacts/<member>/<machine>/<run>/`.
Ưu tiên commit summary CSV, model/forecast JSON, manifest, cấu hình, DDL, SQL,
EXPLAIN và hình SVG/PNG. Đính kèm ZIP đầy đủ bằng GitHub Release nếu log lớn.

Không commit dữ liệu hits, mật khẩu/client.xml, file `.env`, hay kết quả synthetic
smoke test như số liệu thực nghiệm. Không đổi hoặc ghi đè thư mục của thành viên khác.
Mọi kết quả phải có commit code, protocol hash, fingerprint/manifest và reviewer.
