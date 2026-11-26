# Hướng dẫn Biên dịch Báo cáo LaTeX

Thư mục này chứa toàn bộ bản thảo báo cáo nghiên cứu bằng LaTeX, được thiết kế tuân thủ nghiêm ngặt quy định tại `docs/PAGE_BUDGET_VI.md`:
- **Độ dài**: Trần 30 trang (toàn bộ bản nộp).
- **Phông chữ**: Times New Roman 13pt.
- **Khổ giấy & Căn lề**: A4 (Trái 30mm, Phải 20mm, Trên 20mm, Dưới 20mm).
- **Giãn dòng**: 1.15.
- **Cấu trúc**: 5 chương theo `docs/REPORT_PLAN_VI.md`.

## 1. Biên dịch trên máy cục bộ (Windows / Linux / macOS)

Yêu cầu đã cài đặt **TeX Live** hoặc **MiKTeX**. Nên sử dụng **XeLaTeX** để hiển thị đúng font Times New Roman và tiếng Việt.

Chạy các lệnh sau trong terminal tại thư mục `report/`:

```bash
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

File PDF đầu ra là `main.pdf`.

## 2. Biên dịch trên Overleaf

1. Nén toàn bộ thư mục `report/` thành file ZIP.
2. Truy cập [Overleaf](https://www.overleaf.com) > **New Project** > **Upload Project** và tải file ZIP lên.
3. Trong menu Overleaf góc trái trên: **Menu > Compiler**, chọn **XeLaTeX**.
4. Nhấn **Recompile** để xem trước và tải PDF.

## 3. Tự động xuất số liệu từ Python vào Báo cáo

Trước khi biên dịch báo cáo, bạn có thể chạy lệnh sau để tự động trích xuất các bảng thực nghiệm (`.tex`) từ dữ liệu benchmark:

```bash
python scripts/study.py export-latex --member ha --machine laptop1 --run main01
```

Lệnh trên sẽ tự động cập nhật các bảng số liệu trong `report/tables/`, giúp số liệu trong báo cáo luôn đồng bộ tuyệt đối với kết quả thực nghiệm.
