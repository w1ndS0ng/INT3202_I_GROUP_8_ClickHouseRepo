# 3.5.2 — E3 — Đo thời gian ACK, số parts và công việc background merge

- **Phụ trách:** Tài
- **Mô tả:** Nhật ký nạp từng lượt, kiểm chứng 30M, gói log đầy đủ (ZIP đánh số ver1, ver2 theo thời điểm thêm vào) cho 1 đợt (ver1) và 3 đợt 27 lượt (ver2).

## Nội dung

- **Scripts:**
  - [`run_e3_ingest_and_verify.py`](scripts/run_e3_ingest_and_verify.py)
  - [`e3_check_results.py`](scripts/e3_check_results.py)
- **Results:** **17 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-3/3.5.2/scripts/run_e3_ingest_and_verify.py
```
