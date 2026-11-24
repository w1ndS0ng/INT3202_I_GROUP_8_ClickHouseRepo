# 3.2.1 — Nguồn dữ liệu, schema 12 cột, lấy mẫu hệ thống và khóa snapshot 30M

- **Phụ trách:** Tuấn (ver1) & Tài (ver2 đối chiếu nguồn E3)
- **Mô tả:** Bản kê 30 shard ClickBench hits, kiểm tra schema 12 cột, mẫu lồng nhau mod 30 (1M/3M/10M) và đối chiếu nguồn độc lập.

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`prepare_and_verify_dataset.py`](scripts/prepare_and_verify_dataset.py)
  - [`check_sample.py`](scripts/check_sample.py)
  - [`prefetch_e3.py`](scripts/prefetch_e3.py)
  - [`audit_e3_sources.py`](scripts/audit_e3_sources.py)
- `results/`: Chứa **8 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-3/3.2.1/scripts/prepare_and_verify_dataset.py
```
