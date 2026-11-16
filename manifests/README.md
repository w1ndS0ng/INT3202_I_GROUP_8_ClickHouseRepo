# Manifest chung

Tuấn chuẩn bị 30 shard đầu tiên bằng `dataset --publish-lock manifests/hits30m.lock.json`.
Commit file khóa này qua PR trước khi Hà/Tài chạy chính thức. Hai người dùng
`dataset --lock manifests/hits30m.lock.json` để đối chiếu SHA-256 của Parquet và
RowBinary; không tự tạo snapshot khác. Danh sách 10 shard cũ đã có hash ghim trong code.
20 shard bổ sung chỉ được khóa sau khi tải/kiểm tra; repo không bịa checksum.
