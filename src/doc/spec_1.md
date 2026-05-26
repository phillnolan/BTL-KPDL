# SPEC 1 - Kế hoạch tiền xử lý dữ liệu UCSD và CUHK Avenue

## 1. Mục tiêu

Tài liệu này mô tả kế hoạch tiền xử lý dữ liệu cho hai bộ dataset:

- UCSD Ped1/Ped2;
- CUHK Avenue.

Mục tiêu của giai đoạn này là biến dữ liệu video/frame thô thành tập dữ liệu đặc trưng có cấu trúc, sẵn sàng cho các bước phân cụm hành vi, token hóa và khai phá luật kết hợp trong pipeline phát hiện bất thường.

Kết quả đầu ra không phải là các file ảnh/video đã xử lý đơn lẻ, mà là:

- frame đã được chuẩn hóa để pipeline có thể đọc lại;
- metadata về video/frame/cell/cube;
- feature dạng bảng CSV/Parquet;
- mapping giữa feature và vị trí trên frame để vẽ heatmap sau này.

## 2. Nguyên tắc thiết kế

- Tiền xử lý video/frame bằng Python và OpenCV, không dùng WEKA cho bước xử lý ảnh thô.
- WEKA chỉ được dùng sau khi đã trích xuất feature thành bảng CSV/ARFF.
- Giữ nguyên cấu trúc train/test gốc của dataset.
- Không trộn frame train và test trong quá trình tính thống kê chuẩn hóa.
- Mỗi bản ghi feature phải truy vết được về `dataset`, `split`, `video_id`, `frame_id`, `cube_id` và `cell_id`.
- Ưu tiên pipeline chạy lặp lại được bằng config.
- Lưu các thông số tiền xử lý để bảo đảm train/test dùng cùng một cách xử lý.

## 3. Phạm vi

### 3.1. Nằm trong phạm vi

- Đọc frame `.tif` của UCSD Ped1/Ped2.
- Đọc video `.avi` của CUHK Avenue.
- Resize frame về kích thước cấu hình.
- Chuyển grayscale.
- Làm trơn nhẹ bằng Gaussian blur nếu cấu hình bật.
- Chuẩn hóa độ sáng nhẹ nếu cấu hình bật.
- Chia frame thành grid cố định.
- Tạo spatio-temporal cube.
- Trích xuất feature chuyển động và ngữ cảnh cơ bản.
- Lưu feature và metadata.
- Kiểm tra số lượng frame, cube, cell và feature.

### 3.2. Ngoài phạm vi

- Train model phân cụm.
- Tính anomaly score.
- Khai phá association rules.
- Vẽ heatmap kết quả bất thường.
- Đánh giá ROC-AUC/EER.
- Xử lý semantic object detection.

## 4. Cấu trúc dataset hiện có

### 4.1. UCSD

Thư mục gốc:

```text
dataset/UCSD_Anomaly_Dataset.v1p2/
  UCSDped1/
  UCSDped2/
```

Mỗi tập Ped1/Ped2 có cấu trúc chính:

```text
UCSDpedX/
  Train/
    Train001/
      001.tif
      002.tif
      ...
  Test/
    Test001/
      001.tif
      002.tif
      ...
    Test001_gt/
      frame001.bmp
      ...
```

Đặc điểm:

- dữ liệu đã tách thành chuỗi frame `.tif`;
- train mặc định là normal;
- test có thể có thư mục ground truth mask `_gt`;
- Ped2 nhỏ hơn, nên ưu tiên làm baseline đầu tiên.

### 4.2. CUHK Avenue

Thư mục gốc:

```text
dataset/CUHK-avenue/
  training_videos/
  testing_videos/
  training_vol/
  testing_vol/
```

Đặc điểm:

- video train/test ở dạng `.avi`;
- các file `.mat` trong `training_vol` và `testing_vol` có thể dùng đối chiếu hoặc nghiên cứu sau;
- nên đọc trực tiếp `.avi` bằng OpenCV cho pipeline MVP;
- train mặc định là normal.

## 5. Đầu ra chuẩn hóa

Tất cả dataset sau tiền xử lý cần quy về cùng một schema logic.

### 5.1. FrameRecord

```text
FrameRecord {
  dataset,
  split,
  video_id,
  frame_id,
  timestamp,
  source_path,
  original_width,
  original_height,
  resized_width,
  resized_height,
  frame_gray
}
```

### 5.2. CellRecord

```text
CellRecord {
  cell_id,
  row,
  col,
  x1,
  y1,
  x2,
  y2,
  width,
  height
}
```

### 5.3. CubeRecord

```text
CubeRecord {
  dataset,
  split,
  video_id,
  cube_id,
  start_frame_id,
  end_frame_id,
  center_frame_id,
  cell_id
}
```

### 5.4. FeatureRecord

```text
FeatureRecord {
  dataset,
  split,
  video_id,
  cube_id,
  start_frame_id,
  end_frame_id,
  center_frame_id,
  cell_id,
  cell_row,
  cell_col,
  foreground_ratio,
  motion_magnitude_mean,
  motion_magnitude_std,
  motion_density,
  direction_hist_0,
  direction_hist_1,
  direction_hist_2,
  direction_hist_3,
  direction_hist_4,
  direction_hist_5,
  direction_hist_6,
  direction_hist_7,
  brightness_mean,
  brightness_delta
}
```

## 6. Cấu hình tiền xử lý đề xuất

### 6.1. UCSD Ped2 baseline

```yaml
data:
  dataset: "ucsd_ped2"
  root: "dataset/UCSD_Anomaly_Dataset.v1p2/UCSDped2"
  train_path: "Train"
  test_path: "Test"

video:
  input_type: "frame_sequence"
  resize_width: 320
  resize_height: 240
  grayscale: true
  blur:
    enabled: true
    kernel_size: 3
  brightness_normalization:
    enabled: false

grid:
  rows: 12
  cols: 16
  ignore_cells: []

cube:
  length: 5
  stride: 1

features:
  motion_method: "frame_diff"
  frame_diff_threshold: 15
  direction_bins: 8
  use_brightness: true
```

### 6.2. CUHK Avenue baseline

```yaml
data:
  dataset: "avenue"
  root: "dataset/CUHK-avenue"
  train_path: "training_videos"
  test_path: "testing_videos"

video:
  input_type: "video"
  resize_width: 320
  resize_height: 240
  grayscale: true
  blur:
    enabled: true
    kernel_size: 3
  brightness_normalization:
    enabled: false

grid:
  rows: 12
  cols: 16
  ignore_cells: []

cube:
  length: 5
  stride: 1

features:
  motion_method: "frame_diff"
  frame_diff_threshold: 15
  direction_bins: 8
  use_brightness: true
```

## 7. Pipeline tiền xử lý chung

### Bước 1 - Quét dataset

Với mỗi dataset, tạo danh sách video/sequence:

```text
dataset, split, video_id, source_path, input_type
```

Quy tắc:

- UCSD: mỗi thư mục `TrainXXX` hoặc `TestXXX` là một sequence.
- Avenue: mỗi file `.avi` là một video.
- Bỏ qua các thư mục ground truth `_gt` trong quá trình trích xuất feature đầu vào.

### Bước 2 - Đọc frame

UCSD:

- đọc ảnh `.tif` theo thứ tự tăng dần;
- `frame_id` lấy từ tên file;
- `timestamp` có thể gán theo thứ tự frame nếu không có FPS.

Avenue:

- đọc `.avi` bằng `cv2.VideoCapture`;
- `frame_id` là chỉ số frame bắt đầu từ 1;
- `timestamp = frame_id / fps` nếu đọc được FPS, ngược lại gán `null`.

### Bước 3 - Chuẩn hóa frame

Mỗi frame cần được xử lý theo thứ tự:

1. đọc frame RGB/BGR;
2. resize về kích thước cấu hình;
3. chuyển grayscale;
4. blur nhẹ nếu bật;
5. chuẩn hóa độ sáng nếu bật;
6. lưu thông tin kích thước gốc và kích thước resize.

Khuyến nghị MVP:

- bật resize và grayscale;
- bật blur kernel `3x3`;
- tắt brightness normalization trong lần đầu để pipeline đơn giản và dễ giải thích.

### Bước 4 - Tạo grid

Grid mặc định:

```text
rows = 12
cols = 16
```

Với frame `320x240`, mỗi cell có kích thước xấp xỉ:

```text
cell_width = 20
cell_height = 20
```

Cần lưu `cell_id` theo dạng:

```text
row_col
```

Ví dụ:

```text
08_05
```

### Bước 5 - Tạo cube

Cube là cửa sổ trượt theo thời gian:

```text
length = 5
stride = 1
```

Với mỗi video/sequence có `N` frame, số cube:

```text
num_cubes = floor((N - length) / stride) + 1
```

Mỗi cube được cắt theo từng cell, nhưng không cần lưu ảnh cube ra đĩa nếu không cần debug. Chỉ cần trích xuất feature và lưu metadata.

### Bước 6 - Trích xuất feature

Baseline dùng frame differencing:

1. tính chênh lệch tuyệt đối giữa các frame liên tiếp trong cube;
2. threshold để tạo motion mask;
3. tính feature theo từng cell.

Feature bắt buộc:

- `foreground_ratio`: tỷ lệ pixel có chuyển động trong cell;
- `motion_magnitude_mean`: trung bình độ lớn chuyển động;
- `motion_magnitude_std`: độ lệch chuẩn độ lớn chuyển động;
- `motion_density`: tỷ lệ pixel vượt ngưỡng chuyển động;
- `direction_hist_8bins`: histogram hướng chuyển động, nếu chưa dùng optical flow thì có thể gán zero hoặc ước lượng sau;
- `brightness_mean`: độ sáng trung bình trong cell;
- `brightness_delta`: chênh lệch độ sáng giữa frame đầu và frame cuối cube.

Ghi chú:

- Nếu `motion_method = frame_diff`, direction histogram có thể chưa đáng tin cậy.
- Khi cần hướng chuyển động tốt hơn, thêm biến thể `motion_method = farneback`.

### Bước 7 - Lưu feature

Đầu ra đề xuất:

```text
outputs/preprocessed/
  ucsd_ped2/
    frames_manifest.csv
    videos_manifest.csv
    grid.json
    features_train.csv
    features_test.csv
    preprocess_stats.json
  avenue/
    frames_manifest.csv
    videos_manifest.csv
    grid.json
    features_train.csv
    features_test.csv
    preprocess_stats.json
```

Nếu dữ liệu lớn, có thể dùng Parquet:

```text
features_train.parquet
features_test.parquet
```

CSV vẫn nên được hỗ trợ để có thể import vào WEKA.

### Bước 8 - Xuất ARFF cho WEKA

Sau khi có CSV feature, tạo thêm file ARFF nếu cần chạy WEKA:

```text
outputs/weka/
  ucsd_ped2_features_train.arff
  ucsd_ped2_features_test.arff
  avenue_features_train.arff
  avenue_features_test.arff
```

Quy tắc:

- bỏ các cột text dài nếu WEKA xử lý chậm;
- giữ `cell_id` dạng nominal nếu cần phân tích theo cell;
- các cột numeric giữ nguyên;
- chưa gán label anomaly trong file train.

## 8. Kế hoạch riêng cho UCSD

### 8.1. Thứ tự ưu tiên

1. Làm UCSD Ped2 trước.
2. Kiểm tra pipeline với 1 sequence train và 1 sequence test.
3. Chạy toàn bộ Ped2.
4. Sau khi ổn định, mở rộng sang Ped1.

### 8.2. Xử lý frame

- Đọc các file `.tif` theo thứ tự tên file.
- Tên sequence là tên thư mục, ví dụ `Train001`, `Test001`.
- Không đọc thư mục `*_gt` trong tiền xử lý feature.
- Ground truth mask chỉ dùng trong giai đoạn đánh giá sau.

### 8.3. Lưu metadata UCSD

`videos_manifest.csv`:

```text
dataset,split,video_id,source_path,input_type,num_frames
```

`frames_manifest.csv`:

```text
dataset,split,video_id,frame_id,source_path,original_width,original_height,resized_width,resized_height
```

### 8.4. Rủi ro UCSD

- Frame `.tif` có thể đọc thành grayscale sẵn, cần xử lý thống nhất.
- Ped1 và Ped2 có kích thước frame khác nhau, không hard-code theo một bộ.
- Ground truth mask có tên file khác frame source, cần tách riêng cho giai đoạn evaluation.

## 9. Kế hoạch riêng cho CUHK Avenue

### 9.1. Thứ tự ưu tiên

1. Đọc `training_videos/*.avi`.
2. Đọc `testing_videos/*.avi`.
3. Bỏ qua `training_vol` và `testing_vol` trong MVP tiền xử lý.
4. Sau khi pipeline feature ổn định, nghiên cứu file `.mat` để lấy thêm annotation nếu cần.

### 9.2. Xử lý video

- Dùng OpenCV đọc từng frame.
- Lấy FPS, width, height từ `VideoCapture`.
- Nếu video lỗi frame, log cảnh báo và tiếp tục nếu có thể.
- `video_id` lấy từ tên file không có đuôi, ví dụ `01`, `02`, `21`.

### 9.3. Lưu metadata Avenue

`videos_manifest.csv`:

```text
dataset,split,video_id,source_path,input_type,fps,num_frames,original_width,original_height
```

`frames_manifest.csv`:

```text
dataset,split,video_id,frame_id,timestamp,original_width,original_height,resized_width,resized_height
```

### 9.4. Rủi ro Avenue

- `.avi` có thể có FPS/metadata không ổn định, cần fallback theo frame index.
- Video dài hơn UCSD, feature CSV có thể lớn.
- File `.mat` không cần dùng trong MVP đọc video, tránh làm chậm tiến độ.

## 10. Kiểm tra chất lượng đầu ra

Sau mỗi lần chạy tiền xử lý, cần có báo cáo:

```text
dataset
split
num_videos
num_frames
num_cubes
num_cells
num_feature_rows
missing_frames
failed_videos
avg_motion_density
avg_brightness
```

Điều kiện chấp nhận:

- đọc được tất cả video/sequence trong split;
- số frame trong manifest khớp với số frame thực tế đọc được;
- số dòng feature xấp xỉ `num_cubes * rows * cols`;
- không có cột feature numeric bị `NaN` hàng loạt;
- `foreground_ratio` và `motion_density` nằm trong khoảng `[0, 1]`;
- `brightness_mean` nằm trong khoảng `[0, 255]`;
- grid mapping đúng kích thước frame resize.

## 11. Checklist thực hiện

- Tạo config riêng cho `ucsd_ped2`.
- Tạo config riêng cho `avenue`.
- Viết dataset scanner cho frame sequence và video.
- Viết frame reader cho UCSD.
- Viết video reader cho Avenue.
- Viết preprocess transform dùng chung.
- Viết grid generator.
- Viết cube iterator.
- Viết feature extractor baseline bằng frame differencing.
- Lưu manifest, grid và feature CSV.
- Tạo script convert CSV sang ARFF cho WEKA.
- Chạy smoke test trên 1 video/sequence mỗi dataset.
- Chạy full preprocess cho UCSD Ped2.
- Chạy full preprocess cho Avenue.
- Ghi `preprocess_stats.json`.

## 12. Tiêu chí hoàn thành

Giai đoạn tiền xử lý được xem là hoàn thành khi:

- UCSD Ped2 có `features_train.csv` và `features_test.csv`;
- Avenue có `features_train.csv` và `features_test.csv`;
- mỗi feature row truy vết được về video/frame/cell/cube;
- có `grid.json` để dùng lại khi vẽ heatmap;
- có `preprocess_stats.json` cho mỗi dataset;
- có thể xuất ARFF để thử nghiệm WEKA;
- pipeline có thể chạy lại bằng config mà không cần sửa code.
