# 5.3 — Kiểm chứng PoC: Compact → Wide Merge, ReplacingMergeTree FINAL và Tải đồng thời

- **Phụ trách:** Hà
- **Mô tả:** Hồ sơ thực đo kiểm chứng Chương 5 trên `clickhouse-server 26.10.4.207` (`laptop1`), gồm:
  - Dữ liệu JSON thô cho kiểm chứng hợp nhất `Compact → Wide Part` (`77,57 MiB` trong `3,991 s`) song song 16 luồng đọc (`8.831` lượt, `p50 = 19,82 ms`, `p95 = 35,67 ms`, `p99 = 46,11 ms`) và chi phí `ReplacingMergeTree FINAL` trên 5% luồng tài chính `1,8M` bản ghi (`page_id = 42`: `8,53 → 9,98 ms`, `+1,45 ms`; toàn bảng `1.799.974` dòng duy nhất: `51,12 ms`).
  - Hình biểu đồ tổng hợp tải đồng thời `C = 1..128` và luồng `500 ms` (Hình 5.2).

## Nội dung

- **Scripts:**
  - [`exp_ch5_compact_wide_and_final.py`](scripts/exp_ch5_compact_wide_and_final.py) *(kịch bản đo đầu-cuối, đồng bộ với [`scripts/exp_ch5_compact_wide_and_final.py`](../../scripts/exp_ch5_compact_wide_and_final.py))*
  - [`verify_5_3_ch5_results.py`](scripts/verify_5_3_ch5_results.py) *(kiểm tra toàn vẹn SHA-256 và in tóm tắt chỉ số thực đo)*
- **Results:** **2 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)):
  - [`ch5_compact_wide_final_ver1.json`](results/ch5_compact_wide_final_ver1.json) *(trích từ `origin/ha/sorting-key:artifacts/addons/laptop1/ch5_compact_wide_final.json`, commit `3f6b6b8`)*
  - [`figure_5_2_ver1.png`](results/figure_5_2_ver1.png) *(trích từ `origin/ha/sorting-key:report/fig5_2.png`, commit `3f6b6b8`)*

## Kiểm tra

```bash
python chapter-5/5.3/scripts/verify_5_3_ch5_results.py
```
