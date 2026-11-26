# 4.3.4 — Chi phí nạp, tạo chỉ mục và sắp xếp vật lý / bảo trì (ver1: Xeon; ver2: Core i5 — Bảng 4.7)

- **Phụ trách:** Tài (Bảng 4.7 i5 — ver2) & Tuấn (hồ sơ Xeon đối chiếu — ver1)
- **Mô tả:** Thời gian INSERT/COPY BINARY, OPTIMIZE FINAL, CREATE INDEX (BRIN/B-tree) và VACUUM (ANALYZE) trên máy Xeon (ver1) và máy Core i5 (ver2).

## Nội dung

- **Scripts:**
  - [`compare_4_3_4_setup_costs.py`](scripts/compare_4_3_4_setup_costs.py)
- **Results:** **11 tệp** minh chứng ([`files.sha256.json`](results/files.sha256.json)).

## Kiểm tra

```bash
python chapter-4/4.3.4/scripts/compare_4_3_4_setup_costs.py
```
