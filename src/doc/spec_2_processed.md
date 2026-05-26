# SPEC 2 Processed - Cập nhật tài liệu thực hành WEKA 3.8.7 K=5

Original spec path: `src/doc/spec_2.md`

Date/time processed: 2026-05-26 23:58 Asia/Bangkok

## 1. Tóm tắt

Đã viết lại `src/doc/spec_2.md` theo yêu cầu: tài liệu hiện tập trung vào thực hành phân cụm và khai phá luật trên **WEKA 3.8.7** với cấu hình phân cụm chính **SimpleKMeans K=5**.

Phạm vi xử lý trong lượt này là cập nhật tài liệu spec, chưa chạy lại thí nghiệm WEKA GUI vì thao tác này cần môi trường WEKA tương tác và output thực nghiệm thủ công.

## 2. Checklist theo yêu cầu

- [x] Đọc PRD trước khi chỉnh spec.
- [x] Đọc `repomix-output.xml` sau PRD để nắm cấu trúc repo.
- [x] Đọc spec gốc `src/doc/spec_2.md`.
- [x] Đọc `src/doc/Kmean.md` để lấy kết quả tham chiếu KMeans K=5 đã có.
- [x] Viết lại SPEC 2 thành hướng dẫn thực hành WEKA 3.8.7 chi tiết.
- [x] Cố định cấu hình chính `SimpleKMeans K=5`.
- [x] Bổ sung quy trình chuẩn bị ARFF, `Remove`, `Standardize`, train/test trong WEKA Explorer.
- [x] Bổ sung phần per-cell KMeans K=5.
- [x] Bổ sung phần rời rạc hóa và Apriori.
- [x] Bổ sung cấu trúc output, mẫu log, checklist và tiêu chí hoàn thành.
- [x] Chạy kiểm tra markdown sau khi lưu file.
- [x] Refresh `repomix-output.xml` sau khi verification hoàn tất.

## 3. File đã thay đổi

- `src/doc/spec_2.md`: viết lại toàn bộ nội dung.
- `src/doc/spec_2_processed.md`: tạo mới file processed để ghi vết theo workflow.

## 4. Verification

- [x] `git diff --check -- src/doc/spec_2.md src/doc/spec_2_processed.md`
- [x] Kiểm tra nhanh heading và số liệu tài liệu bằng PowerShell.
- [x] `repomix.cmd`

Kết quả: không phát hiện lỗi whitespace trong diff. Git chỉ cảnh báo line ending `LF` sẽ được chuyển thành `CRLF` khi Git chạm file trên Windows.

`repomix.cmd` chạy thành công từ repo root và ghi lại `repomix-output.xml`.

## 5. Ghi chú còn lại

- SPEC 2 mới là tài liệu thực hành, không tự động tạo output WEKA.
- Các thao tác WEKA GUI cần được người thực hành chạy sau theo checklist trong spec.
- Kết quả KMeans K=5 tham chiếu được lấy từ `src/doc/Kmean.md`.
