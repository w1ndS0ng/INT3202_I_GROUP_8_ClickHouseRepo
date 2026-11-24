# 2.3 — Sorting key, primary key và sparse primary index

- **Phụ trách:** Tuấn
- **Mô tả:** Minh họa phân bố granule trên 16 bản ghi giả định với K0 = tuple(), K1 = (CounterID, EventDate), K2 = (EventDate, CounterID).

## Cấu trúc thư mục

- `scripts/`: Mã nguồn thực thi / kiểm chứng của mục này:
  - [`verify_2_3_example.py`](scripts/verify_2_3_example.py)
- `results/`: Chứa **2 tệp** kết quả/minh chứng (kèm [`files.sha256.json`](results/files.sha256.json)).
  - Các tệp/phiên bản bổ sung theo thời gian được gắn hậu tố `_ver1`, `_ver2` theo thứ tự thời điểm đưa vào nghiên cứu.

## Chạy kiểm tra nhanh từ thư mục gốc repo

```bash
python chapter-2/2.3/scripts/verify_2_3_example.py
```
