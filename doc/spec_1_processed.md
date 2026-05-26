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
- chạy smoke test trên UCSD Ped2 và CUHK Avenue.

Chưa chạy full preprocess toàn bộ UCSD Ped2 và toàn bộ Avenue trong bước này. Đã kiểm thử bằng giới hạn `1` video/sequence và `10-20` frame để xác nhận pipeline, schema và output.

## 2. Output đã có

Code chính:

- [x] `src/preprocess.py`
- [x] `src/csv_to_arff.py`
- [x] `src/tool/preprocess_ucsd.py`
- [x] `src/tool/preprocess_avenue.py`
- [x] `src/kpdl_preprocess/`
- [x] `src/configs/ucsd_ped2.yaml`
- [x] `src/configs/ucsd_ped1.yaml`
- [x] `src/configs/avenue.yaml`
- [x] `src/requirements.txt`
- [x] `src/README.md`

Output smoke test:

- [x] `src/outputs/preprocessed/ucsd_ped2/`
- [x] `src/outputs/preprocessed/avenue/`
- [x] `src/outputs/weka/ucsd_ped2_features_train.arff`
- [x] `src/outputs/weka/ucsd_ped2_features_test.arff`
- [x] `src/outputs/weka/avenue_features_train.arff`
- [x] `src/outputs/weka/avenue_features_test.arff`

## 3. Đánh dấu theo phạm vi SPEC 1

### 3.1. Nằm trong phạm vi

- [x] Đọc frame `.tif` của UCSD Ped1/Ped2.
- [x] Đọc video `.avi` của CUHK Avenue.
- [x] Resize frame về kích thước cấu hình.
- [x] Chuyển grayscale.
- [x] Làm trơn nhẹ bằng Gaussian blur nếu cấu hình bật.
- [x] Chuẩn hóa độ sáng nhẹ nếu cấu hình bật.
- [x] Chia frame thành grid cố định.
- [x] Tạo spatio-temporal cube.
- [x] Trích xuất feature chuyển động và ngữ cảnh cơ bản.
- [x] Lưu feature và metadata.
- [x] Kiểm tra số lượng frame, cube, cell và feature qua `preprocess_stats.json`.

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

- [x] `data.dataset = ucsd_ped2`
- [x] `data.root = src/dataset/UCSD_Anomaly_Dataset.v1p2/UCSDped2`
- [x] `video.input_type = frame_sequence`
- [x] `resize_width = 320`
- [x] `resize_height = 240`
- [x] `grayscale = true`
- [x] `blur.enabled = true`
- [x] `blur.kernel_size = 3`
- [x] `brightness_normalization.enabled = false`
- [x] `grid.rows = 12`
- [x] `grid.cols = 16`
- [x] `cube.length = 5`
- [x] `cube.stride = 1`
- [x] `motion_method = frame_diff`
- [x] `frame_diff_threshold = 15`
- [x] `direction_bins = 8`
- [x] `use_brightness = true`

File: `src/configs/ucsd_ped2.yaml`

### 4.2. CUHK Avenue baseline

- [x] `data.dataset = avenue`
- [x] `data.root = src/dataset/CUHK-avenue`
- [x] `video.input_type = video`
- [x] `resize_width = 320`
- [x] `resize_height = 240`
- [x] `grayscale = true`
- [x] `blur.enabled = true`
- [x] `blur.kernel_size = 3`
- [x] `brightness_normalization.enabled = false`
- [x] `grid.rows = 12`
- [x] `grid.cols = 16`
- [x] `cube.length = 5`
- [x] `cube.stride = 1`
- [x] `motion_method = frame_diff`
- [x] `frame_diff_threshold = 15`
- [x] `direction_bins = 8`
- [x] `use_brightness = true`

File: `src/configs/avenue.yaml`

## 5. Đánh dấu theo pipeline chung

### Bước 1 - Quét dataset

- [x] Tạo danh sách `dataset, split, video_id, source_path, input_type`.
- [x] UCSD: mỗi thư mục `TrainXXX` hoặc `TestXXX` là một sequence.
- [x] Avenue: mỗi file `.avi` là một video.
- [x] Bỏ qua thư mục ground truth `_gt` khi trích xuất feature.

Module: `src/kpdl_preprocess/datasets.py`

### Bước 2 - Đọc frame

UCSD:

- [x] Đọc ảnh `.tif` theo thứ tự tăng dần.
- [x] `frame_id` lấy từ tên file.
- [x] `timestamp` gán theo thứ tự frame khi không có FPS.

Avenue:

- [x] Đọc `.avi` bằng `cv2.VideoCapture`.
- [x] `frame_id` bắt đầu từ 1.
- [x] `timestamp = frame_id / fps` nếu đọc được FPS, ngược lại để trống.

Module: `src/kpdl_preprocess/readers.py`

### Bước 3 - Chuẩn hóa frame

- [x] Đọc frame RGB/BGR hoặc grayscale.
- [x] Resize theo config.
- [x] Chuyển grayscale.
- [x] Blur nhẹ nếu bật.
- [x] Chuẩn hóa độ sáng nếu bật.
- [x] Lưu kích thước gốc và kích thước resize trong manifest.

Module: `src/kpdl_preprocess/readers.py`

### Bước 4 - Tạo grid

- [x] Grid mặc định `rows = 12`, `cols = 16`.
- [x] Với `320x240`, tạo `192` cell.
- [x] Lưu `cell_id` dạng `row_col`, ví dụ `08_05`.
- [x] Xuất `grid.json`.

Module: `src/kpdl_preprocess/grid.py`

### Bước 5 - Tạo cube

- [x] Cube sliding window với `length = 5`, `stride = 1`.
- [x] Công thức số cube đúng: `floor((N - length) / stride) + 1`.
- [x] Không lưu ảnh cube ra đĩa.
- [x] Lưu metadata cube trong từng dòng feature.

Module: `src/kpdl_preprocess/pipeline.py`

### Bước 6 - Trích xuất feature

- [x] Tính chênh lệch tuyệt đối giữa các frame liên tiếp trong cube.
- [x] Threshold để tạo motion mask.
- [x] Tính feature theo từng cell.
- [x] `foreground_ratio`
- [x] `motion_magnitude_mean`
- [x] `motion_magnitude_std`
- [x] `motion_density`
- [x] `direction_hist_0..7`
- [x] `brightness_mean`
- [x] `brightness_delta`

Ghi chú: với `motion_method = frame_diff`, các cột `direction_hist_0..7` hiện được tạo và gán `0.0`, đúng với ghi chú trong SPEC 1 rằng direction histogram chưa đáng tin cậy nếu chưa dùng optical flow.

Module: `src/kpdl_preprocess/features.py`

### Bước 7 - Lưu feature

- [x] `frames_manifest.csv`
- [x] `videos_manifest.csv`
- [x] `grid.json`
- [x] `features_train.csv`
- [x] `features_test.csv`
- [x] `preprocess_stats.json`

Đã xác nhận bằng smoke test tại:

- `src/outputs/preprocessed/ucsd_ped2/`
- `src/outputs/preprocessed/avenue/`

### Bước 8 - Xuất ARFF cho WEKA

- [x] Convert feature CSV sang ARFF.
- [x] Giữ `cell_id` dạng nominal.
- [x] Cột numeric giữ dạng numeric.
- [x] Cột text dài như `dataset`, `split`, `video_id`, `cube_id` để dạng string.

Module:

- `src/kpdl_preprocess/arff.py`
- `src/csv_to_arff.py`

## 6. Đánh dấu theo kế hoạch riêng cho UCSD

- [x] Ưu tiên UCSD Ped2 trước.
- [x] Đọc các file `.tif` theo thứ tự tên file.
- [x] Tên sequence là tên thư mục, ví dụ `Train001`, `Test001`.
- [x] Không đọc thư mục `*_gt` trong tiền xử lý feature.
- [x] Ground truth mask chưa dùng, đúng phạm vi SPEC 1.
- [x] Lưu `videos_manifest.csv`.
- [x] Lưu `frames_manifest.csv`.
- [x] Không hard-code kích thước frame gốc.
- [ ] Chạy full preprocess toàn bộ UCSD Ped2.
- [ ] Mở rộng/chạy full UCSD Ped1.

## 7. Đánh dấu theo kế hoạch riêng cho CUHK Avenue

- [x] Đọc `training_videos/*.avi`.
- [x] Đọc `testing_videos/*.avi`.
- [x] Bỏ qua `training_vol` và `testing_vol` trong MVP.
- [x] Dùng OpenCV đọc từng frame.
- [x] Lấy FPS, width, height từ `VideoCapture`.
- [x] `video_id` lấy từ tên file không có đuôi, ví dụ `01`.
- [x] Lưu `videos_manifest.csv`.
- [x] Lưu `frames_manifest.csv`.
- [ ] Chạy full preprocess toàn bộ Avenue.
- [ ] Nghiên cứu file `.mat` để lấy annotation sau.

## 8. Kiểm tra chất lượng đầu ra

Đã có các trường thống kê trong `preprocess_stats.json`:

- [x] `dataset`
- [x] `split`
- [x] `num_videos`
- [x] `num_frames`
- [x] `num_cubes`
- [x] `num_cells`
- [x] `num_feature_rows`
- [x] `missing_frames`
- [x] `failed_videos`
- [x] `avg_motion_density`
- [x] `avg_brightness`

Kết quả smoke test:

- [x] UCSD Ped2 train/test đọc được `1` sequence mỗi split.
- [x] Avenue train/test đọc được `1` video mỗi split.
- [x] Với `10` frame, `cube.length = 5`, `stride = 1`: mỗi split có `6` cube.
- [x] Với `12 x 16 = 192` cell: mỗi split có `6 * 192 = 1152` dòng feature.
- [x] `failed_videos = 0`.
- [x] ARFF sinh được cho train/test của UCSD Ped2 và Avenue.

Chưa kiểm tra ở quy mô full:

- [ ] Đọc toàn bộ video/sequence trong split.
- [ ] So khớp frame manifest với toàn bộ frame thực tế.
- [ ] Kiểm tra NaN trên toàn bộ feature CSV lớn.
- [ ] Kiểm tra phân phối feature trên toàn bộ dataset.

## 9. Checklist thực hiện từ SPEC 1

- [x] Tạo config riêng cho `ucsd_ped2`.
- [x] Tạo config riêng cho `avenue`.
- [x] Viết dataset scanner cho frame sequence và video.
- [x] Viết frame reader cho UCSD.
- [x] Viết video reader cho Avenue.
- [x] Viết preprocess transform dùng chung.
- [x] Viết grid generator.
- [x] Viết cube iterator.
- [x] Viết feature extractor baseline bằng frame differencing.
- [x] Lưu manifest, grid và feature CSV.
- [x] Tạo script convert CSV sang ARFF cho WEKA.
- [x] Chạy smoke test trên 1 video/sequence mỗi dataset.
- [ ] Chạy full preprocess cho UCSD Ped2.
- [ ] Chạy full preprocess cho Avenue.
- [x] Ghi `preprocess_stats.json`.

## 10. Tiêu chí hoàn thành SPEC 1

- [ ] UCSD Ped2 có `features_train.csv` và `features_test.csv` full dataset.
- [ ] Avenue có `features_train.csv` và `features_test.csv` full dataset.
- [x] Mỗi feature row truy vết được về video/frame/cell/cube.
- [x] UCSD và Avenue xuất cùng một schema chung qua `src/kpdl_preprocess/schema.py`.
- [x] Có `grid.json` để dùng lại khi vẽ heatmap.
- [x] Có `preprocess_stats.json` cho mỗi dataset trong smoke test.
- [x] Có thể xuất ARFF để thử nghiệm WEKA.
- [x] Pipeline có thể chạy lại bằng config mà không cần sửa code.

## 11. Lệnh đã dùng để kiểm thử

```bash
python src/tool/preprocess_ucsd.py --ped ped2 --limit-videos 1 --limit-frames 10 --output-root outputs/preprocessed_smoke_both --export-arff
```

```bash
python src/tool/preprocess_avenue.py --limit-videos 1 --limit-frames 10 --output-root outputs/preprocessed_smoke_both --export-arff
```

## 12. Lệnh đề xuất để hoàn tất full preprocess

```bash
python src/tool/preprocess_ucsd.py --ped ped2 --export-arff
```

```bash
python src/tool/preprocess_avenue.py --export-arff
```
