# 3.2.3 — Bộ truy vấn W0–W4 và các chỉ số đo lường

- **Phụ trách:** Tuấn
- **Mô tả:** Kiểm tra độ chọn lọc W0–W4 trên pilot 1M (ver1 bộ lọc ban đầu rỗng W3/W4 -> ver2 điều chỉnh mergetree-v2) và probe chỉ số query/storage/ingest.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`verify_workloads_v1_v2.py`](scripts/verify_workloads_v1_v2.py)
- `results/`: Chứa **5 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.2.3/scripts/verify_workloads_v1_v2.py
```
