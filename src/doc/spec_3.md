# SPEC 3 - Pipeline Python phân cụm theo cell và anomaly scoring sau tiền xử lý

## 1. Mục tiêu

Tài liệu này mô tả bước triển khai tiếp theo sau khi giai đoạn tiền xử lý đã sinh feature CSV/ARFF. Mục tiêu của SPEC 3 là chuyển từ dữ liệu đặc trưng đã chuẩn hóa sang một pipeline Python có thể chạy lặp lại để:

- huấn luyện mô hình phân cụm hành vi bình thường theo từng cell;
- tính khoảng cách của mỗi feature row tới cụm bình thường gần nhất;
- chọn threshold theo phân phối train normal;
- sinh anomaly score ở mức cell/cube và frame;
- làm mượt score theo thời gian;
- xuất kết quả phục vụ bước heatmap, alert, token/rule và đánh giá sau này.

SPEC 3 ưu tiên UCSD Ped2 vì dữ liệu nhỏ hơn, đã có đầy đủ `features_train.csv`, `features_test.csv`, ARFF và `preprocess_stats.json`.

## 2. Liên hệ với PRD và các spec trước

Theo PRD, giai đoạn sau tiền xử lý cần học normal pattern riêng theo vùng camera, sau đó dùng độ lệch so với normal pattern để tính bất thường. SPEC 1 đã tạo feature đầu vào. SPEC 2 mô tả hướng dùng WEKA để thử nghiệm, phân tích và đối chiếu. SPEC 3 triển khai nhánh Python tự động hóa để có thể train, test, lưu model, tính score và chạy lại bằng config.

SPEC 3 không thay thế SPEC 2. Kết quả WEKA như `src/doc/Kmean.md` có thể dùng để chọn cấu hình khởi đầu, ví dụ `K=5` cho baseline behavior-only trên UCSD Ped2.

## 3. Trạng thái dữ liệu đầu vào hiện có

Feature đầu vào mặc định:

```text
src/outputs/preprocessed/
  ucsd_ped2/
    features_train.csv
    features_test.csv
    grid.json
    preprocess_stats.json
  ucsd_ped1/
    features_train.csv
    features_test.csv
    grid.json
    preprocess_stats.json
  avenue/
    features_train.csv
    features_test.csv
    grid.json
    preprocess_stats.json
```

Kích thước hiện tại theo `preprocess_stats.json`:

```text
UCSD Ped2 train:
  videos: 16
  frames: 2550
  cubes: 2486
  cells: 192
  feature rows: 477312

UCSD Ped2 test:
  videos: 12
  frames: 2010
  cubes: 1962
  cells: 192
  feature rows: 376704

UCSD Ped1 train:
  videos: 34
  frames: 6800
  cubes: 6664
  cells: 192
  feature rows: 1279488

UCSD Ped1 test:
  videos: 36
  frames: 7200
  cubes: 7056
  cells: 192
  feature rows: 1354752

Avenue train:
  videos: 16
  frames: 15328
  cubes: 15264
  cells: 192
  feature rows: 2930688

Avenue test:
  videos: 21
  frames: 15324
  cubes: 15240
  cells: 192
  feature rows: 2926080
```

Schema feature đang dùng:

```text
dataset
split
video_id
cube_id
start_frame_id
end_frame_id
center_frame_id
cell_id
cell_row
cell_col
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
direction_hist_0..7
brightness_mean
brightness_delta
```

Baseline đầu tiên chỉ dùng các feature hành vi sau:

```text
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
brightness_mean
brightness_delta
```

Không dùng `direction_hist_0..7` trong SPEC 3 baseline vì với `motion_method = frame_diff` các cột này hiện chưa mang thông tin hướng đáng tin cậy.

## 4. Phạm vi

### 4.1. Nằm trong phạm vi

- Đọc feature CSV từ `src/outputs/preprocessed/{dataset}`.
- Huấn luyện MiniBatchKMeans riêng cho từng `cell_id`.
- Chuẩn hóa feature bằng scaler riêng cho từng cell.
- Lưu model, scaler, centroid, threshold và metadata train.
- Tính cluster distance cho train/test.
- Chọn threshold theo percentile train của từng cell.
- Tính `cluster_distance_score` theo từng cell/cube.
- Tính `temporal_change_score` baseline theo lịch sử score cùng cell.
- Tổng hợp thành `cell_score` và `frame_score`.
- Làm mượt frame score bằng moving average hoặc EMA.
- Sinh `frame_scores.csv`, `cell_scores.csv` và `alerts.json`.
- Ghi log train/test đủ để tái hiện.

### 4.2. Ngoài phạm vi

- Heatmap overlay lên video.
- ROC-AUC/EER hoàn chỉnh theo ground truth mask.
- Tokenization và association rules production.
- Optical flow hoặc direction histogram thật.
- Dashboard hoặc realtime stream.
- Tối ưu model nâng cao như GMM, Isolation Forest, DBSCAN.

Các phần ngoài phạm vi nên đưa sang SPEC sau, sau khi SPEC 3 đã có score ổn định và có thể kiểm tra định tính.

## 5. Kiến trúc module đề xuất

Tạo package mới để tách rõ tiền xử lý và mô hình:

```text
src/kpdl_anomaly/
  __init__.py
  config.py
  io.py
  schema.py
  feature_selection.py
  modeling.py
  thresholds.py
  scoring.py
  smoothing.py
  alerts.py
  train.py
  test.py
```

Entrypoint đề xuất:

```text
src/train.py
src/test.py
```

Hoặc nếu muốn giữ style hiện tại của `src/tool/`, có thể thêm:

```text
src/tool/train_anomaly.py
src/tool/test_anomaly.py
```

Ưu tiên giữ CLI ngắn và tái dùng config:

```bash
python src/train.py --config src/configs/ucsd_ped2.yaml
python src/test.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2
```

## 6. Dependency cần bổ sung

SPEC 3 cần thêm thư viện machine learning nhẹ:

```text
scikit-learn>=1.3
joblib>=1.3
```

Nếu muốn đọc CSV lớn tiện hơn có thể thêm `pandas`, nhưng MVP nên cân nhắc đọc bằng `csv` chuẩn và gom theo cell bằng chunk/buffer để giảm dependency. Với UCSD Ped2, dùng `numpy` và `csv` là đủ.

## 7. Cấu hình đề xuất

Bổ sung các mục sau vào YAML dataset hiện có hoặc tạo file model riêng như `src/configs/ucsd_ped2_anomaly.yaml`:

```yaml
model:
  type: "minibatch_kmeans"
  clusters_per_cell: 5
  min_samples_per_cell: 50
  batch_size: 1024
  max_iter: 200
  random_state: 10
  threshold_percentile: 99.0

scoring:
  feature_columns:
    - foreground_ratio
    - motion_magnitude_mean
    - motion_magnitude_std
    - motion_density
    - brightness_mean
    - brightness_delta
  cluster_weight: 0.80
  temporal_weight: 0.20
  top_k_cells: 5
  smoothing_window: 5
  alert_threshold_medium: 0.70
  alert_threshold_high: 0.90
  min_consecutive_alerts: 3

output:
  model_root: "src/outputs/models"
  result_root: "src/outputs/results"
```

Trong MVP, công thức score dùng:

```text
score = 0.80 * cluster_distance_score
      + 0.20 * temporal_change_score
```

Khi token/rule đã sẵn sàng ở SPEC sau, có thể mở rộng:

```text
score = 0.65 * cluster_distance_score
      + 0.20 * temporal_change_score
      + 0.10 * rare_token_score
      + 0.05 * rule_violation_score
```

## 8. Quy trình train

### Bước 1 - Load config và input

Đọc:

```text
src/outputs/preprocessed/{dataset}/features_train.csv
src/outputs/preprocessed/{dataset}/grid.json
src/outputs/preprocessed/{dataset}/preprocess_stats.json
```

Kiểm tra:

- file tồn tại;
- schema feature có đủ cột bắt buộc;
- `split` trong train file là `train`;
- số dòng đọc được khớp với `preprocess_stats.json` hoặc ghi warning rõ.

### Bước 2 - Gom feature theo cell

Với mỗi dòng train:

1. lấy `cell_id`;
2. lấy feature columns đã cấu hình;
3. bỏ qua dòng có giá trị numeric không hợp lệ;
4. thêm vector vào buffer của cell.

MVP có thể load toàn bộ UCSD Ped2 train vào RAM. Với Avenue, cần hỗ trợ đọc streaming/chunk để không phụ thuộc vào RAM lớn.

### Bước 3 - Train scaler và KMeans theo cell

Với mỗi cell:

1. nếu số mẫu `< min_samples_per_cell`, tạo fallback model;
2. fit `StandardScaler` trên feature train của cell;
3. transform feature;
4. fit `MiniBatchKMeans`;
5. tính khoảng cách từng mẫu train tới centroid gần nhất;
6. lưu percentile distance làm threshold.

Fallback cho cell ít dữ liệu:

- dùng thống kê global train nếu có;
- hoặc đánh dấu `model_status = insufficient_samples`;
- score của cell đó dùng z-score đơn giản hoặc luôn thấp cho đến khi có đủ dữ liệu.

### Bước 4 - Lưu model artifact

Output đề xuất:

```text
src/outputs/models/{dataset}/
  config.yaml
  model_manifest.json
  cell_models.joblib
  cell_scalers.joblib
  thresholds.json
  feature_stats.json
```

`model_manifest.json` cần có:

```text
dataset
trained_at
schema_version
feature_columns
num_cells
num_models_trained
num_fallback_cells
clusters_per_cell
threshold_percentile
train_feature_path
grid_path
```

`thresholds.json` cần có:

```text
cell_id
distance_mean
distance_std
distance_p95
distance_p99
threshold
num_train_samples
```

## 9. Quy trình test/scoring

### Bước 1 - Load model và feature test

Đọc:

```text
src/outputs/models/{dataset}/
src/outputs/preprocessed/{dataset}/features_test.csv
```

Kiểm tra model manifest khớp:

- dataset;
- schema version;
- feature columns;
- grid rows/cols nếu có lưu trong manifest.

### Bước 2 - Tính cluster distance

Với mỗi feature row:

1. lấy model/scaler theo `cell_id`;
2. chuẩn hóa vector;
3. tìm centroid gần nhất;
4. tính distance;
5. chuẩn hóa distance thành `cluster_distance_score`.

Công thức MVP:

```text
cluster_distance_score = min(distance / threshold, 2.0) / 2.0
```

Nếu `threshold <= 0`, dùng fallback:

```text
cluster_distance_score = 0.0 nếu distance gần 0
cluster_distance_score = 1.0 nếu distance > 0
```

### Bước 3 - Tính temporal change

Theo từng `(video_id, cell_id)`, giữ score trước đó:

```text
temporal_change_score = abs(current_cluster_score - previous_cluster_score)
```

Chuẩn hóa về `[0, 1]` bằng clipping. Với dòng đầu tiên của mỗi video/cell, đặt `temporal_change_score = 0.0`.

### Bước 4 - Tính cell score

```text
cell_score = cluster_weight * cluster_distance_score
           + temporal_weight * temporal_change_score
```

Clip `cell_score` về `[0, 1]`.

### Bước 5 - Tổng hợp frame score

Nhóm theo:

```text
dataset, split, video_id, center_frame_id
```

Lấy `top_k_cells` cell score cao nhất:

```text
frame_score = mean(top_k cell_score)
```

Nếu số cell ít hơn `top_k_cells`, lấy mean các cell có sẵn.

### Bước 6 - Smoothing và alert

Làm mượt `frame_score` theo từng video:

```text
smoothed_frame_score = moving_average(frame_score, window=smoothing_window)
```

Sinh severity:

```text
if smoothed_frame_score >= alert_threshold_high for >= min_consecutive_alerts:
    severity = "high"
elif smoothed_frame_score >= alert_threshold_medium for >= min_consecutive_alerts:
    severity = "medium"
else:
    severity = "none"
```

## 10. Output kết quả

Output mặc định:

```text
src/outputs/results/{dataset}/
  cell_scores.csv
  frame_scores.csv
  alerts.json
  scoring_stats.json
```

`cell_scores.csv`:

```text
dataset
split
video_id
cube_id
start_frame_id
end_frame_id
center_frame_id
cell_id
cell_row
cell_col
nearest_cluster
cluster_distance
cluster_threshold
cluster_distance_score
temporal_change_score
cell_score
```

`frame_scores.csv`:

```text
dataset
split
video_id
frame_id
frame_score
smoothed_frame_score
severity
top_cells
```

`alerts.json`:

```json
[
  {
    "dataset": "ucsd_ped2",
    "video_id": "Test001",
    "start_frame_id": 61,
    "end_frame_id": 78,
    "max_score": 0.93,
    "severity": "high",
    "top_cells": ["08_05", "08_06", "09_05"],
    "reasons": [
      "cell=08_05 cluster distance is above its train p99 threshold",
      "frame score stayed high for 3 consecutive frames"
    ]
  }
]
```

## 11. Reason text MVP

SPEC 3 chưa làm token/rule đầy đủ, nhưng mỗi alert cần có reason tối thiểu:

- cell nào có score cao nhất;
- distance có vượt threshold train hay không;
- nearest cluster là cluster nào;
- score có kéo dài qua nhiều frame hay không.

Ví dụ:

```text
cell=08_05 has cluster_distance=1.42 above train threshold=0.87
nearest normal cluster is C3
smoothed frame score exceeded high threshold for 4 consecutive frames
```

## 12. CLI đề xuất

Train:

```bash
python src/train.py --config src/configs/ucsd_ped2.yaml
```

Train với override nhanh:

```bash
python src/train.py --config src/configs/ucsd_ped2.yaml --clusters-per-cell 5 --threshold-percentile 99
```

Test:

```bash
python src/test.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2
```

Debug với giới hạn dòng:

```bash
python src/test.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2 --limit-rows 50000
```

## 13. Thí nghiệm bắt buộc

### Experiment 1 - UCSD Ped2 per-cell KMeans K=5

Input:

```text
src/outputs/preprocessed/ucsd_ped2/features_train.csv
src/outputs/preprocessed/ucsd_ped2/features_test.csv
```

Config:

```text
clusters_per_cell = 5
threshold_percentile = 99
feature_columns = foreground_ratio, motion_magnitude_mean, motion_magnitude_std, motion_density, brightness_mean, brightness_delta
```

Kết quả cần có:

- model cho đủ 192 cell hoặc fallback rõ cho cell thiếu mẫu;
- `frame_scores.csv`;
- `alerts.json`;
- thống kê số frame vượt ngưỡng medium/high.

### Experiment 2 - So sánh threshold percentile

Chạy:

```text
threshold_percentile = 95, 97.5, 99
```

Ghi:

- số alert;
- số frame severity medium/high;
- phân phối score train/test;
- nhận xét threshold nào ít nhiễu hơn.

### Experiment 3 - So sánh K

Chạy:

```text
clusters_per_cell = 3, 5, 8
```

Ghi:

- train distance mean/std/p99;
- số cell có cụm quá nhỏ;
- thời gian train/test;
- nhận xét khả năng giải thích.

### Experiment 4 - Chạy Avenue hoặc UCSD Ped1 sau khi Ped2 ổn

Chỉ chạy sau khi UCSD Ped2 hoàn thành, vì dữ liệu lớn hơn. Cần log runtime và RAM nếu có thể.

## 14. Tiêu chí đánh giá

Một lần chạy SPEC 3 được xem là đạt khi:

- train hoàn tất trên UCSD Ped2 không lỗi;
- có model artifact đầy đủ trong `src/outputs/models/ucsd_ped2`;
- test hoàn tất trên UCSD Ped2 không lỗi;
- `cell_scores.csv` và `frame_scores.csv` truy vết được về `video_id`, `cube_id`, `frame_id`, `cell_id`;
- score nằm trong khoảng `[0, 1]` sau clipping;
- `alerts.json` có reason tối thiểu;
- cấu hình và model manifest đủ để chạy lại;
- runtime không phụ thuộc thao tác thủ công trong WEKA.

## 15. Rủi ro và giảm thiểu

### 15.1. Dữ liệu lớn gây tốn RAM

Rủi ro: Avenue có gần 3 triệu dòng mỗi split, load toàn bộ có thể tốn RAM.

Giảm thiểu:

- ưu tiên UCSD Ped2;
- đọc CSV theo chunk;
- train từng cell hoặc gom từng cell ra file tạm nếu cần;
- chỉ export score cần thiết, tránh giữ toàn bộ object lớn trong RAM.

### 15.2. Cell ít chuyển động tạo threshold quá nhỏ

Rủi ro: cell gần như đứng yên có train distance rất nhỏ, một nhiễu nhẹ cũng tạo score cao.

Giảm thiểu:

- dùng threshold floor;
- dùng `min_samples_per_cell`;
- thêm `motion_density` floor trước khi alert;
- yêu cầu smoothing và consecutive frames.

### 15.3. Feature frame_diff thiếu hướng chuyển động

Rủi ro: model chưa phát hiện tốt bất thường do sai hướng.

Giảm thiểu:

- ghi rõ SPEC 3 là baseline cluster/distance;
- không dùng direction hist zero trong model;
- tạo SPEC sau cho Farneback optical flow hoặc hướng chuyển động thật.

### 15.4. Không có ground truth trong scoring MVP

Rủi ro: chỉ nhìn score/alert chưa biết đúng sai định lượng.

Giảm thiểu:

- lưu output truy vết đầy đủ;
- chuẩn bị SPEC sau cho evaluation với mask UCSD;
- kiểm tra định tính bằng các frame top score trước.

## 16. Checklist triển khai

- [ ] Bổ sung dependency `scikit-learn` và `joblib`.
- [ ] Tạo package `src/kpdl_anomaly/`.
- [ ] Tạo loader đọc feature CSV và validate schema.
- [ ] Tạo feature selector bỏ metadata và direction histogram baseline.
- [ ] Tạo train per-cell scaler + MiniBatchKMeans.
- [ ] Tạo threshold percentile theo train distance.
- [ ] Lưu model artifact bằng joblib/JSON.
- [ ] Tạo test scorer đọc model và feature test.
- [ ] Xuất `cell_scores.csv`.
- [ ] Tổng hợp `frame_scores.csv` bằng top-k mean.
- [ ] Thêm smoothing theo video.
- [ ] Sinh `alerts.json` với reason tối thiểu.
- [ ] Thêm CLI `src/train.py`.
- [ ] Thêm CLI `src/test.py`.
- [ ] Chạy smoke test với `--limit-rows`.
- [ ] Chạy full UCSD Ped2 train/test.
- [ ] Ghi `src/doc/spec_3_processed.md`.

## 17. Tiêu chí hoàn thành SPEC 3

SPEC 3 hoàn thành khi:

- UCSD Ped2 train/test chạy được end-to-end bằng CLI Python;
- output model và result nằm đúng cấu trúc;
- có log hoặc processed file ghi rõ cấu hình K, threshold percentile, số cell train thành công, số fallback cell;
- có ít nhất một file `frame_scores.csv` và `alerts.json` dùng được cho bước visualization;
- có verification bằng smoke test và full Ped2;
- không cần mở WEKA để tính score.

## 18. Hướng sau SPEC 3

Sau SPEC 3, bước tiếp theo nên là:

- SPEC 4: heatmap overlay và kiểm tra định tính top anomaly frames;
- SPEC 5: tokenization, rare token score và association rules trong Python;
- SPEC 6: evaluation ROC-AUC/EER với ground truth UCSD;
- SPEC 7: optical flow hoặc direction feature thật để bắt bất thường sai hướng.
