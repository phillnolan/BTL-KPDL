# SPEC 1 Processed - Trạng thái triển khai tiền xử lý UCSD và CUHK Avenue

Tài liệu này đánh dấu các mục đã thực hiện từ `doc/spec_1.md`.

Ngày cập nhật: 2026-05-26

## 1. Tóm tắt trạng thái

Đã tạo thư mục `src/` và triển khai pipeline tiền xử lý theo SPEC 1 ở mức MVP:

- đọc UCSD Ped1/Ped2 dạng chuỗi frame `.tif`;
- đọc CUHK Avenue dạng video `.avi`;
- resize, grayscale, Gaussian blur tùy config;
- tạo grid cố định;
- tạo spatio-temporal cube;
- trích xuất feature baseline bằng frame differencing;
- xuất manifest, grid, feature CSV, stats JSON;
- xuất ARFF cho WEKA;
- tách entrypoint riêng cho UCSD và CUHK Avenue trong `src/tool/`;
- đưa dataset SPEC 1 vào `src/dataset/`;
- đưa output tiền xử lý mặc định vào `src/outputs/`;
- chạy smoke test trên UCSD Ped1, UCSD Ped2 và CUHK Avenue;
- thêm `.gitignore` để không commit dataset, output, archive và paper PDF ở root.

Chưa chạy full preprocess toàn bộ UCSD Ped2 và toàn bộ Avenue trong bước này. Đã kiểm thử bằng giới hạn `1` video/sequence và `10-20` frame để xác nhận pipeline, schema và output.

## 2. Output đã có

Code chính:

- [X] `src/preprocess.py`
- [X] `src/csv_to_arff.py`
- [X] `src/tool/preprocess_ucsd.py`
- [X] `src/tool/preprocess_avenue.py`
- [X] `src/kpdl_preprocess/`
- [X] `src/configs/ucsd_ped2.yaml`
- [X] `src/configs/ucsd_ped1.yaml`
- [X] `src/configs/avenue.yaml`
- [X] `src/requirements.txt`
- [X] `src/README.md`
- [X] `.gitignore`

Dataset nội bộ `src`:

- [X] `src/dataset/UCSD_Anomaly_Dataset.v1p2/`
- [X] `src/dataset/CUHK-avenue/`

Output smoke test:

- [X] `src/outputs/preprocessed/ucsd_ped2/`
- [X] `src/outputs/preprocessed/avenue/`
- [X] `src/outputs/weka/ucsd_ped2_features_train.arff`
- [X] `src/outputs/weka/ucsd_ped2_features_test.arff`
- [X] `src/outputs/weka/avenue_features_train.arff`
- [X] `src/outputs/weka/avenue_features_test.arff`

Output cũ từng sinh ở project root đã được chuyển vào:

- [X] `src/outputs/legacy_root_outputs/`

## 3. Đánh dấu theo phạm vi SPEC 1

### 3.1. Nằm trong phạm vi

- [X] Đọc frame `.tif` của UCSD Ped1/Ped2.
- [X] Đọc video `.avi` của CUHK Avenue.
- [X] Resize frame về kích thước cấu hình.
- [X] Chuyển grayscale.
- [X] Làm trơn nhẹ bằng Gaussian blur nếu cấu hình bật.
- [X] Chuẩn hóa độ sáng nhẹ nếu cấu hình bật.
- [X] Chia frame thành grid cố định.
- [X] Tạo spatio-temporal cube.
- [X] Trích xuất feature chuyển động và ngữ cảnh cơ bản.
- [X] Lưu feature và metadata.
- [X] Kiểm tra số lượng frame, cube, cell và feature qua `preprocess_stats.json`.

### 3.2. Ngoài phạm vi

Các mục này chưa triển khai vì SPEC 1 xác định là ngoài phạm vi:

- [ ] Train model phân cụm.
- [ ] Tính anomaly score.
- [ ] Khai phá association rules.
- [ ] Vẽ heatmap kết quả bất thường.
- [ ] Đánh giá ROC-AUC/EER.
- [ ] Xử lý semantic object detection.

## 4. Đánh dấu theo cấu hình đề xuất

### 4.1. UCSD Ped2 baseline

- [X] `data.dataset = ucsd_ped2`
- [X] `data.root = src/dataset/UCSD_Anomaly_Dataset.v1p2/UCSDped2`
- [X] `video.input_type = frame_sequence`
- [X] `resize_width = 320`
- [X] `resize_height = 240`
- [X] `grayscale = true`
- [X] `blur.enabled = true`
- [X] `blur.kernel_size = 3`
- [X] `brightness_normalization.enabled = false`
- [X] `grid.rows = 12`
- [X] `grid.cols = 16`
- [X] `cube.length = 5`
- [X] `cube.stride = 1`
- [X] `motion_method = frame_diff`
- [X] `frame_diff_threshold = 15`
- [X] `direction_bins = 8`
- [X] `use_brightness = true`
- [X] `output.root = src/outputs/preprocessed`
- [X] `output.weka_root = src/outputs/weka`

File: `src/configs/ucsd_ped2.yaml`

### 4.2. CUHK Avenue baseline

- [X] `data.dataset = avenue`
- [X] `data.root = src/dataset/CUHK-avenue`
- [X] `video.input_type = video`
- [X] `resize_width = 320`
- [X] `resize_height = 240`
- [X] `grayscale = true`
- [X] `blur.enabled = true`
- [X] `blur.kernel_size = 3`
- [X] `brightness_normalization.enabled = false`
- [X] `grid.rows = 12`
- [X] `grid.cols = 16`
- [X] `cube.length = 5`
- [X] `cube.stride = 1`
- [X] `motion_method = frame_diff`
- [X] `frame_diff_threshold = 15`
- [X] `direction_bins = 8`
- [X] `use_brightness = true`
- [X] `output.root = src/outputs/preprocessed`
- [X] `output.weka_root = src/outputs/weka`

File: `src/configs/avenue.yaml`

## 5. Đánh dấu theo pipeline chung

### Bước 1 - Quét dataset

- [X] Tạo danh sách `dataset, split, video_id, source_path, input_type`.
- [X] UCSD: mỗi thư mục `TrainXXX` hoặc `TestXXX` là một sequence.
- [X] Avenue: mỗi file `.avi` là một video.
- [X] Bỏ qua thư mục ground truth `_gt` khi trích xuất feature.

Module: `src/kpdl_preprocess/datasets.py`

### Bước 2 - Đọc frame

UCSD:

- [X] Đọc ảnh `.tif` theo thứ tự tăng dần.
- [X] `frame_id` lấy từ tên file.
- [X] `timestamp` gán theo thứ tự frame khi không có FPS.

Avenue:

- [X] Đọc `.avi` bằng `cv2.VideoCapture`.
- [X] `frame_id` bắt đầu từ 1.
- [X] `timestamp = frame_id / fps` nếu đọc được FPS, ngược lại để trống.

Module: `src/kpdl_preprocess/readers.py`

### Bước 3 - Chuẩn hóa frame

- [X] Đọc frame RGB/BGR hoặc grayscale.
- [X] Resize theo config.
- [X] Chuyển grayscale.
- [X] Blur nhẹ nếu bật.
- [X] Chuẩn hóa độ sáng nếu bật.
- [X] Lưu kích thước gốc và kích thước resize trong manifest.

Module: `src/kpdl_preprocess/readers.py`

### Bước 4 - Tạo grid

- [X] Grid mặc định `rows = 12`, `cols = 16`.
- [X] Với `320x240`, tạo `192` cell.
- [X] Lưu `cell_id` dạng `row_col`, ví dụ `08_05`.
- [X] Xuất `grid.json`.

Module: `src/kpdl_preprocess/grid.py`

### Bước 5 - Tạo cube

- [X] Cube sliding window với `length = 5`, `stride = 1`.
- [X] Công thức số cube đúng: `floor((N - length) / stride) + 1`.
- [X] Không lưu ảnh cube ra đĩa.
- [X] Lưu metadata cube trong từng dòng feature.

Module: `src/kpdl_preprocess/pipeline.py`

### Bước 6 - Trích xuất feature

- [X] Tính chênh lệch tuyệt đối giữa các frame liên tiếp trong cube.
- [X] Threshold để tạo motion mask.
- [X] Tính feature theo từng cell.
- [X] `foreground_ratio`
- [X] `motion_magnitude_mean`
- [X] `motion_magnitude_std`
- [X] `motion_density`
- [X] `direction_hist_0..7`
- [X] `brightness_mean`
- [X] `brightness_delta`

Ghi chú: với `motion_method = frame_diff`, các cột `direction_hist_0..7` hiện được tạo và gán `0.0`, đúng với ghi chú trong SPEC 1 rằng direction histogram chưa đáng tin cậy nếu chưa dùng optical flow.

Module: `src/kpdl_preprocess/features.py`

### Bước 7 - Lưu feature

- [X] `frames_manifest.csv`
- [X] `videos_manifest.csv`
- [X] `grid.json`
- [X] `features_train.csv`
- [X] `features_test.csv`
- [X] `preprocess_stats.json`

Đã xác nhận bằng smoke test tại:

- `src/outputs/preprocessed/ucsd_ped2/`
- `src/outputs/preprocessed/avenue/`

ARFF mặc định lưu tại:

- `src/outputs/weka/`

### Bước 8 - Xuất ARFF cho WEKA

- [X] Convert feature CSV sang ARFF.
- [X] Giữ `cell_id` dạng nominal.
- [X] Cột numeric giữ dạng numeric.
- [X] Cột text dài như `dataset`, `split`, `video_id`, `cube_id` để dạng string.

Module:

- `src/kpdl_preprocess/arff.py`
- `src/csv_to_arff.py`

## 6. Đánh dấu theo kế hoạch riêng cho UCSD

- [X] Ưu tiên UCSD Ped2 trước.
- [X] Có script riêng `src/tool/preprocess_ucsd.py`.
- [X] Hỗ trợ `--ped ped2` và `--ped ped1`.
- [X] Dataset UCSD đã nằm trong `src/dataset/UCSD_Anomaly_Dataset.v1p2/`.
- [X] Đọc các file `.tif` theo thứ tự tên file.
- [X] Tên sequence là tên thư mục, ví dụ `Train001`, `Test001`.
- [X] Không đọc thư mục `*_gt` trong tiền xử lý feature.
- [X] Ground truth mask chưa dùng, đúng phạm vi SPEC 1.
- [X] Lưu `videos_manifest.csv`.
- [X] Lưu `frames_manifest.csv`.
- [X] Không hard-code kích thước frame gốc.
- [X] Smoke test UCSD Ped1 train với `1` sequence và `10` frame.
- [X] Smoke test UCSD Ped2 train/test với `1` sequence mỗi split và `10` frame.
- [X] Chạy full preprocess toàn bộ UCSD Ped2.
- [ ] Mở rộng/chạy full UCSD Ped1.

## 7. Đánh dấu theo kế hoạch riêng cho CUHK Avenue

- [X] Có script riêng `src/tool/preprocess_avenue.py`.
- [X] Dataset Avenue đã nằm trong `src/dataset/CUHK-avenue/`.
- [X] Đọc `training_videos/*.avi`.
- [X] Đọc `testing_videos/*.avi`.
- [X] Bỏ qua `training_vol` và `testing_vol` trong MVP.
- [X] Dùng OpenCV đọc từng frame.
- [X] Lấy FPS, width, height từ `VideoCapture`.
- [X] `video_id` lấy từ tên file không có đuôi, ví dụ `01`.
- [X] Lưu `videos_manifest.csv`.
- [X] Lưu `frames_manifest.csv`.
- [X] Smoke test Avenue train/test với `1` video mỗi split và `10` frame.
- [ ] Chạy full preprocess toàn bộ Avenue.
- [ ] Nghiên cứu file `.mat` để lấy annotation sau.

## 8. Kiểm tra chất lượng đầu ra

Đã có các trường thống kê trong `preprocess_stats.json`:

- [X] `dataset`
- [X] `split`
- [X] `num_videos`
- [X] `num_frames`
- [X] `num_cubes`
- [X] `num_cells`
- [X] `num_feature_rows`
- [X] `missing_frames`
- [X] `failed_videos`
- [X] `avg_motion_density`
- [X] `avg_brightness`

Kết quả smoke test:

- [X] UCSD Ped2 train/test đọc được `1` sequence mỗi split.
- [X] UCSD Ped1 train đọc được `1` sequence.
- [X] Avenue train/test đọc được `1` video mỗi split.
- [X] Với `10` frame, `cube.length = 5`, `stride = 1`: mỗi split có `6` cube.
- [X] Với `12 x 16 = 192` cell: mỗi split có `6 * 192 = 1152` dòng feature.
- [X] `failed_videos = 0`.
- [X] ARFF sinh được cho train/test của UCSD Ped2 và Avenue.
- [X] Header `features_train.csv`, `frames_manifest.csv`, `videos_manifest.csv` của UCSD và Avenue khớp nhau sau khi chuyển output vào `src/outputs`.

Chưa kiểm tra ở quy mô full:

- [ ] Đọc toàn bộ video/sequence trong split.
- [ ] So khớp frame manifest với toàn bộ frame thực tế.
- [ ] Kiểm tra NaN trên toàn bộ feature CSV lớn.
- [ ] Kiểm tra phân phối feature trên toàn bộ dataset.

## 9. Checklist thực hiện từ SPEC 1

- [X] Tạo config riêng cho `ucsd_ped2`.
- [X] Tạo config riêng cho `ucsd_ped1`.
- [X] Tạo config riêng cho `avenue`.
- [X] Tách file chạy riêng cho UCSD.
- [X] Tách file chạy riêng cho Avenue.
- [X] Viết dataset scanner cho frame sequence và video.
- [X] Viết frame reader cho UCSD.
- [X] Viết video reader cho Avenue.
- [X] Viết preprocess transform dùng chung.
- [X] Viết grid generator.
- [X] Viết cube iterator.
- [X] Viết feature extractor baseline bằng frame differencing.
- [X] Lưu manifest, grid và feature CSV.
- [X] Tạo script convert CSV sang ARFF cho WEKA.
- [X] Chạy smoke test trên 1 video/sequence mỗi dataset.
- [X] Chuyển dataset UCSD và Avenue vào `src/dataset`.
- [X] Chuyển output mặc định vào `src/outputs`.
- [X] Thêm `.gitignore` cho dataset/output/PDF/archive/cache.
- [X] Chạy full preprocess cho UCSD Ped2.
- [ ] Chạy full preprocess cho Avenue.
- [X] Ghi `preprocess_stats.json`.

## 10. Tiêu chí hoàn thành SPEC 1

- [ ] UCSD Ped2 có `features_train.csv` và `features_test.csv` full dataset.
- [ ] Avenue có `features_train.csv` và `features_test.csv` full dataset.
- [X] Mỗi feature row truy vết được về video/frame/cell/cube.
- [X] UCSD và Avenue xuất cùng một schema chung qua `src/kpdl_preprocess/schema.py`.
- [X] Có `grid.json` để dùng lại khi vẽ heatmap.
- [X] Có `preprocess_stats.json` cho mỗi dataset trong smoke test.
- [X] Có thể xuất ARFF để thử nghiệm WEKA.
- [X] Pipeline có thể chạy lại bằng config mà không cần sửa code.
- [X] Kết quả tiền xử lý mặc định nằm trong `src/outputs`.
- [X] Dataset và output không bị commit nhờ `.gitignore`.

## 11. Lệnh đã dùng để kiểm thử

```bash
python tool/preprocess_ucsd.py --ped ped2 --limit-videos 1 --limit-frames 10 --export-arff
```

```bash
python tool/preprocess_avenue.py --limit-videos 1 --limit-frames 10 --export-arff
```

```bash
python tool/preprocess_ucsd.py --ped ped1 --split train --limit-videos 1 --limit-frames 10
```

## 12. Lệnh đề xuất để hoàn tất full preprocess

```bash
python tool/preprocess_ucsd.py --ped ped2 --export-arff
```

```bash
python tool/preprocess_avenue.py --export-arff
```

## 13. Quản lý dữ liệu và Git

Đã thêm `.gitignore` để tránh commit các dữ liệu và artifact nặng:

- [X] `/New folder/`
- [X] `/dataset/`
- [X] `/src/dataset/`
- [X] `/outputs/`
- [X] `/src/outputs/`
- [X] `/*.pdf`
- [X] `__pycache__/`
- [X] `*.py[cod]`

Đã kiểm tra bằng `git check-ignore`:

- [X] `New folder`
- [X] `dataset`
- [X] `src/dataset`
- [X] `src/outputs`
- [X] các PDF paper ở project root.

## 14. Cập nhật 2026-05-26 - Avenue full preprocess chạy lâu

Spec gốc: `src/doc/spec_1.md`

- [X] Kiểm tra lại luồng `src/tool/preprocess_avenue.py`: entrypoint chỉ gọi pipeline dùng chung, nguyên nhân nằm ở đọc video/ghi feature và việc thiếu log tiến độ.
- [X] Probe toàn bộ CUHK Avenue: 16 video train, 21 video test, tổng `30652` frame; OpenCV đọc thô toàn bộ video kết thúc bình thường trong khoảng `9.37s`, không thấy file `.avi` bị đọc vô hạn.
- [X] Thêm `--progress-every` cho `src/tool/_common.py` và `src/kpdl_preprocess/cli.py` để in tiến độ theo video/frame khi chạy full preprocess.
- [X] Thêm guard trong `src/kpdl_preprocess/readers.py` dựa trên `CAP_PROP_FRAME_COUNT` cộng tolerance để tránh trường hợp `VideoCapture.read()` không tự kết thúc ở video lỗi.
- [X] Cập nhật `src/kpdl_preprocess/pipeline.py` để log start/progress/done/fail từng video và ghi `missing_frames` khi số frame đọc được thấp hơn metadata.
- [X] Verification: `python -m compileall src\kpdl_preprocess src\tool`
- [X] Verification: `python src\tool\preprocess_avenue.py --limit-videos 1 --limit-frames 10 --output-root src\outputs\preprocessed_fix_smoke --export-arff --progress-every 5`
- [ ] Chưa chạy full Avenue lại trong bước này vì full dataset sẽ tạo khoảng `5.85M` dòng feature trước khi export ARFF.
