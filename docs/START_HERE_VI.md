# Bắt đầu theo đúng thứ tự

## 1. Chốt protocol và chuẩn bị dữ liệu — Tuấn

Tải/cài cùng server/client/local26.10.3.7; cả ba xác minh `study.py status`.
Tuấn dùng README chuẩn bị30shard và tạo `manifests/hits30m.lock.json`; commit qua PR.
Hà/Tài dùng `dataset --lock` với file khóa đó. Không dùng manifest10M cũ thay cho manifest30M.

Máy Tài đã có repo chạy ở `/home/anhtai06/mergetree-study-v1`, 11shard đã chuyển đổi,
một file tiếp theo đang tải dở. Có thể tiếp tục chuẩn bị bằng:

```bash
cd /home/anhtai06/mergetree-study-v1
export CH_CONFIG=/home/anhtai06/clickhouse-project/config/client.xml
python3 scripts/study.py dataset --shards 30 \
  --reuse-dir /home/anhtai06/clickhouse-project/data
```

Nếu Tuấn đã commit manifest chung, git pull và thêm
`--lock manifests/hits30m.lock.json` vào lệnh. Script tiếp tục file tải dở, kiểm tra
lại hash của file đã có, không tải/nạp trùng vào bảng. Thư mục mới chỉ là nơi chạy
nghiên cứu MergeTree; dự án MV cũ nằm nguyên ở `clickhouse-project`.

## 2. Pilot riêng — cả ba

Sau khi đủ30shard và mẫu, tạo run `pilot01` trên từng máy. Ví dụ cho Tuấn:

```bash
python3 scripts/study.py init --member tuan --machine laptop2 --run pilot01
python3 scripts/study.py build --member tuan --machine laptop2 --run pilot01 --experiment granularity --scale 1m
python3 scripts/study.py queries --member tuan --machine laptop2 --run pilot01 --experiment granularity --scale 1m
python3 scripts/study.py summarize --member tuan --machine laptop2 --run pilot01
```

Hà thay member/machine, dùng `--experiment keys`; Tài dùng init rồi
`ingest --member tai --machine laptop3 --run pilot01 --scale 1m`.
Pilot phải qua count/fingerprint, kết quả query khớp, literals có dữ liệu và máy không thiếu
RAM/đĩa. Nếu thay protocol, cập nhật đồng nhất trước run chính. Không chép số pilot thành30M.

## 3. Chạy chính — mỗi người một lệnh

README có ba lệnh `run_member.sh`. Sử dụng run ID mới `main01`; mỗi lệnh tự thực hiện
đúng pipeline của người đó và giữ hồ sơ. Máy Hà phải đóng băng model/forecast trước đo30M.
Một máy chỉ chạy một thí nghiệm tại một thời điểm; không dùng chung database/results giữa người.

## 4. Viết bản30trang

Vẽ hình, package ZIP, review chéo rồi viết theo [Outline Báo cáo hiện hành](https://docs.google.com/document/d/1eA1XSvGx-8YbP02ilUgHmPeRKYKhRwCHg_8KZZysm3o/edit?tab=t.le5tjknhw5zq) và [PAGE_BUDGET_VI.md](PAGE_BUDGET_VI.md).
Phân công: Hà sorting key; Tuấn granularity và dataset/protocol; Tài batch/merge và tổng hợp.
Ngân sách30trang là cho bản nộp có nội dung, không phải yêu cầu chép nguyên checklist/script.
Sau khi có các kết quả, cần export PDF kiểm tra số trang thật và bảng/hình ở Times New Roman13.
