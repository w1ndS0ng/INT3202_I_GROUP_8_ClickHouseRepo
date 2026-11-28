# 3.6.6 — Giải quyết lọc ngoài khóa W4 (Skipping Index, Projection) và Bảo vệ RAM / External Spill

- **Phụ trách:** Hà
- **Mô tả:** Kiểm chứng mở rộng trên `mtr_addon_exp` (`clickhouse-server 26.10.4.207`, `laptop1`, 30M dòng cho W4/giá trị hiếm và 10M dòng cho `GROUP BY WatchID`; tương ứng Mục 3.6.2 và Bảng 3.9 trong báo cáo hoàn chỉnh):
  - **Skipping Index (`minmax` + `bloom_filter`, +1,09 MiB):** Không hiệu quả với `W4` mật độ phân tán 20,6% (`50,39 → 60,62 ms`, `0,83×`), nhưng cắt tỉa `97,41%` hạt với giá trị hiếm `RegionID = 106539` (`200` dòng: `47,01 → 15,04 ms`, `3,13×`).
  - **Projection tự đồng bộ:** `p_reg_order` (+407,1 MiB) đạt `14,39 ms` (`3,50×`); `p_reg_agg` (+45,4 KiB) đạt `7,30 ms` (`6,91×`).
  - **Memory Guard & External Spill (10M `GROUP BY WatchID`):** Chặn OOM ở `77,62 MiB` khi tắt spill; hoàn tất trong `1.334,9 ms` ở đỉnh `144,7 MiB RAM` (33 tệp tạm, `169,1 MB` nén) khi bật spill `60 MB`.

## Nội dung

- **Scripts:**
  - [`exp_mergetree_features.py`](scripts/exp_mergetree_features.py) *(đồng bộ với [`scripts/exp_mergetree_features.py`](../../../scripts/exp_mergetree_features.py))*
  - [`verify_3_6_6_mergetree_features.py`](scripts/verify_3_6_6_mergetree_features.py) *(kiểm tra toàn vẹn SHA-256 và in tóm tắt chỉ số thực đo)*
- **Results:** **1 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)):
  - [`mergetree_features_ver1.json`](results/mergetree_features_ver1.json) *(trích từ `origin/ha/sorting-key:artifacts/addons/laptop1/mergetree_features.json`, commit `3f6b6b8`)*

## Kiểm tra

```bash
python chapter-3/3.6.6/scripts/verify_3_6_6_mergetree_features.py
```
