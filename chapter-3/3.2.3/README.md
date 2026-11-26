# 3.2.3 — Bộ truy vấn W0–W4 và các chỉ số đo lường

- **Phụ trách:** Tuấn
- **Mô tả:** Kiểm tra độ chọn lọc W0–W4 trên pilot 1M (ver1 bộ lọc ban đầu rỗng W3/W4 -> ver2 điều chỉnh mergetree-v2) và probe chỉ số query/storage/ingest.

## Nội dung

- **Scripts:**
  - [`verify_workloads_v1_v2.py`](scripts/verify_workloads_v1_v2.py)
- **Results:** **5 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.2.3/scripts/verify_workloads_v1_v2.py
```
