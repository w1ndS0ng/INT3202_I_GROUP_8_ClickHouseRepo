# 3.2.2 — Môi trường phần cứng, phần mềm và các biến giữ cố định

- **Phụ trách:** Tuấn
- **Mô tả:** Hồ sơ môi trường WSL2/Windows, probe schema/DDL, effective_settings.json (20 thiết lập cố định) và cấu hình protocol.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`inspect_environments.py`](scripts/inspect_environments.py)
- `results/`: Chứa **15 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.2.2/scripts/inspect_environments.py
```
