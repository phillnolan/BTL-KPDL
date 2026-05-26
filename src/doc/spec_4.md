# SPEC 4 - Heatmap overlay và kiểm tra định tính top anomaly frames

## 1. Mục tiêu

Tài liệu này mô tả bước triển khai tiếp theo sau SPEC 3. Mục tiêu của SPEC 4 là biến các score đã sinh bởi pipeline anomaly baseline thành artifact trực quan để kiểm tra định tính:

- dựng heatmap bất thường theo cell lên frame gốc hoặc frame đã resize;
- xuất ảnh top anomaly frames kèm overlay, top cells và reason;
- xuất video overlay cho từng test video hoặc một đoạn frame được chọn;
- tạo báo cáo định tính giúp xem nhanh cảnh báo đúng/sai trước khi làm ROC-AUC/EER ở SPEC sau;
- bảo đảm kết quả visualization truy vết được về `video_id`, `frame_id`, `cell_id`, `cell_score` và `alerts.json`.

SPEC 4 không thay đổi công thức anomaly score của SPEC 3. Đây là lớp hiển thị và phân tích định tính dựa trên các artifact hiện có.

## 2. Liên hệ với PRD và SPEC 3

Theo PRD, MVP cần có heatmap bất thường trên video, danh sách vùng bất thường và lý do cảnh báo dễ hiểu. SPEC 3 đã sinh:

```text
src/outputs/results/{dataset}/
  cell_scores.csv
  frame_scores.csv
  alerts.json
  scoring_stats.json
```

SPEC 4 dùng trực tiếp các output này cùng với:

```text
src/outputs/preprocessed/{dataset}/
  grid.json
  frames_manifest.csv
  videos_manifest.csv
```

và frame gốc trong dataset để tạo overlay. Với UCSD Ped2, frame được đọc lại từ chuỗi `.tif`; với Avenue, frame được đọc lại từ `.avi`.

SPEC 4 là bước chuẩn bị bắt buộc trước SPEC 6 evaluation định lượng, vì cần nhìn được các frame score cao nhất để biết score hiện tại đang bám vào chuyển động bất thường thật hay bị nhiễu bởi ánh sáng, bóng, vùng đứng yên hoặc threshold quá nhạy.

## 3. Trạng thái đầu vào hiện có

Dataset ưu tiên:

```text
ucsd_ped2
```

Artifact đã có sau SPEC 3:

```text
src/outputs/models/ucsd_ped2/
  model_manifest.json
  cell_models.joblib
  cell_scalers.joblib
  thresholds.json
  feature_stats.json

src/outputs/results/ucsd_ped2/
  cell_scores.csv
  frame_scores.csv
  alerts.json
  scoring_stats.json
```

Kích thước output UCSD Ped2 hiện tại:

```text
cell_scores.csv: 376704 dòng score
frame_scores.csv: 1962 frame
alerts.json: 16 alert segment
grid: 12 x 16 = 192 cell
resize: 320 x 240
```

Schema quan trọng:

```text
cell_scores.csv:
  dataset, split, video_id, cube_id, start_frame_id, end_frame_id,
  center_frame_id, cell_id, cell_row, cell_col, nearest_cluster,
  cluster_distance, cluster_threshold, cluster_distance_score,
  temporal_change_score, cell_score

frame_scores.csv:
  dataset, split, video_id, frame_id, frame_score,
  smoothed_frame_score, severity, top_cells

alerts.json:
  dataset, video_id, start_frame_id, end_frame_id,
  max_score, severity, top_cells, reasons
```

Grid mapping:

```text
grid.json:
  resized_width, resized_height, rows, cols, cells[]

cell:
  cell_id, row, col, x1, y1, x2, y2, width, height
```

## 4. Phạm vi

### 4.1. Nằm trong phạm vi

- Đọc `frame_scores.csv`, `cell_scores.csv`, `alerts.json` và `grid.json`.
- Chọn top anomaly frames theo `smoothed_frame_score` hoặc theo alert segment.
- Đọc lại frame test từ dataset bằng config hiện có.
- Tạo heatmap 2D từ `cell_score` theo từng `frame_id`.
- Resize hoặc map heatmap đúng kích thước frame hiển thị.
- Blend heatmap lên frame grayscale/RGB bằng OpenCV colormap.
- Vẽ viền cell top bất thường và nhãn ngắn nếu cần.
- Ghi ảnh overlay `.png` cho top frames.
- Ghi video overlay `.mp4` cho một video hoặc một đoạn alert.
- Tạo file index JSON/CSV mô tả các ảnh đã xuất.
- Tạo report Markdown định tính với top frame, score, top cells, reason và đường dẫn artifact.
- Thêm CLI `src/visualize.py`.
- Thêm package/module visualization trong `src/kpdl_anomaly/`.

### 4.2. Ngoài phạm vi

- Không tính lại model, threshold hoặc anomaly score.
- Không đánh giá ROC-AUC/EER.
- Không làm dashboard web.
- Không tạo annotation editor.
- Không huấn luyện optical flow hoặc direction feature thật.
- Không thay thế `alerts.json` của SPEC 3, trừ khi phát hiện lỗi schema rõ ràng.

## 5. Kiến trúc module đề xuất

Bổ sung các file:

```text
src/kpdl_anomaly/
  visualization.py
  frames.py
  qualitative.py

src/visualize.py
```

Vai trò:

```text
frames.py:
  đọc lại frame theo dataset/config/video_id/frame_id
  hỗ trợ frame_sequence và video
  tái dùng logic scan/read/preprocess từ kpdl_preprocess khi phù hợp

visualization.py:
  đọc score/grid
  tạo heatmap cell-level
  blend heatmap lên frame
  vẽ top cell boxes
  ghi PNG/MP4

qualitative.py:
  chọn top frames/top alert segments
  ghép reason từ alerts.json và top_cells từ frame_scores.csv
  tạo report Markdown/JSON

src/visualize.py:
  CLI entrypoint cho SPEC 4
```

Không nên đưa logic visualization vào `scoring.py`, vì SPEC 3 scoring cần giữ là pipeline số liệu thuần.

## 6. Cấu hình đề xuất

Bổ sung vào YAML dataset hiện có:

```yaml
visualization:
  output_root: "src/outputs/visualizations"
  colormap: "JET"
  alpha: 0.45
  heatmap_normalization: "per_frame"
  draw_grid: false
  draw_top_cells: true
  top_cells_per_frame: 5
  top_frames: 30
  min_score: 0.70
  frame_source: "preprocessed"
  image_format: "png"
  video_fps: 10
```

Ý nghĩa:

- `heatmap_normalization = per_frame`: chuẩn hóa heatmap theo max cell score của frame, dễ nhìn top vùng nóng.
- `heatmap_normalization = global`: dùng cùng scale toàn video, phù hợp so sánh giữa frame.
- `frame_source = preprocessed`: overlay lên frame đã resize/grayscale giống pipeline score.
- `frame_source = original`: overlay lên kích thước gốc, cần scale cell box từ resize về original.

MVP nên dùng `preprocessed` để đơn giản, đúng với `grid.json` và ít rủi ro lệch tọa độ.

## 7. Quy trình tạo heatmap cho một frame

### Bước 1 - Load grid

Đọc:

```text
src/outputs/preprocessed/{dataset}/grid.json
```

Tạo mapping:

```text
cell_id -> {x1, y1, x2, y2, row, col}
```

Kiểm tra:

- số cell trong `grid.json` khớp config `rows * cols` trừ `ignore_cells`;
- `resized_width` và `resized_height` khớp frame đọc lại;
- mọi `cell_id` trong `cell_scores.csv` tồn tại trong grid.

### Bước 2 - Load score theo frame

Đọc `cell_scores.csv`, nhóm theo:

```text
video_id, center_frame_id
```

Mỗi nhóm giữ:

```text
cell_id
cell_score
cluster_distance_score
temporal_change_score
cluster_distance
cluster_threshold
nearest_cluster
```

Để tránh load file lớn khi chỉ visualize vài frame, MVP có thể stream CSV và chỉ giữ những frame đã chọn từ `frame_scores.csv`/`alerts.json`.

### Bước 3 - Chọn frame cần visualize

Nguồn chọn:

```text
top smoothed_frame_score từ frame_scores.csv
top frame trong mỗi alert segment từ alerts.json
frame_id do người dùng chỉ định
range frame do người dùng chỉ định
```

Ưu tiên MVP:

1. `--top-frames 30`: chọn top 30 frame toàn test set.
2. `--video-id Test001 --start-frame 150 --end-frame 180`: xuất đoạn cụ thể.
3. `--alerts`: xuất peak frame của từng alert.

### Bước 4 - Tạo heatmap cell-level

Tạo mảng heatmap kích thước:

```text
resized_height x resized_width
```

Với mỗi cell:

```text
heatmap[y1:y2, x1:x2] = cell_score
```

Nếu một cell thiếu score, đặt `0.0` và ghi warning nếu thiếu hàng loạt.

### Bước 5 - Normalize và colorize

MVP:

```text
normalized = clip(heatmap, 0, 1)
colored = cv2.applyColorMap((normalized * 255).astype(uint8), cv2.COLORMAP_JET)
overlay = cv2.addWeighted(frame_rgb, 1 - alpha, colored, alpha, 0)
```

Nếu `per_frame`, trước khi colorize:

```text
normalized = heatmap / max(heatmap)
```

với `max(heatmap) > 0`. Nếu max bằng 0, giữ heatmap zero.

### Bước 6 - Vẽ top cells

Vẽ viền cho các cell trong `top_cells`:

```text
cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness=1 hoặc 2)
```

Nhãn text nên ngắn để không che frame:

```text
08_10 0.91
```

Nếu nhiều cell gần nhau, MVP có thể chỉ vẽ viền và ghi top cell list vào report thay vì text trên ảnh.

## 8. Output mong muốn

Thư mục:

```text
src/outputs/visualizations/{dataset}/
  top_frames/
    Test001_000164_score_0.796.png
    Test002_000143_score_0.820.png
  alerts/
    Test001_000164_000178_peak.png
    Test001_000164_000178_overlay.mp4
  videos/
    Test001_overlay.mp4
  qualitative_report.md
  visualization_index.json
  visualization_stats.json
```

`visualization_index.json`:

```json
[
  {
    "dataset": "ucsd_ped2",
    "video_id": "Test001",
    "frame_id": 164,
    "frame_score": 0.79,
    "smoothed_frame_score": 0.79,
    "severity": "medium",
    "top_cells": ["08_10", "08_11", "09_11"],
    "image_path": "src/outputs/visualizations/ucsd_ped2/top_frames/Test001_000164_score_0.796.png",
    "alert_id": "Test001:164-178"
  }
]
```

`visualization_stats.json`:

```text
dataset
config_path
result_dir
grid_path
num_frames_selected
num_images_written
num_videos_written
missing_frames
missing_cell_score_frames
generated_at
```

`qualitative_report.md` cần có:

- bảng top frames theo score;
- bảng alert segments;
- ảnh preview cho peak frames nếu Markdown renderer hỗ trợ path tương đối;
- reason từ `alerts.json`;
- nhận xét thủ công placeholder để sinh viên điền sau khi xem ảnh.

## 9. CLI đề xuất

Xuất top frames:

```bash
python src/visualize.py --config src/configs/ucsd_ped2.yaml --top-frames 30
```

Xuất peak frame của alert segments:

```bash
python src/visualize.py --config src/configs/ucsd_ped2.yaml --alerts
```

Xuất đoạn frame cụ thể:

```bash
python src/visualize.py --config src/configs/ucsd_ped2.yaml --video-id Test001 --start-frame 150 --end-frame 180
```

Xuất video overlay cho một video:

```bash
python src/visualize.py --config src/configs/ucsd_ped2.yaml --video-id Test001 --write-video
```

Override output:

```bash
python src/visualize.py --config src/configs/ucsd_ped2.yaml --result-dir src/outputs/results/ucsd_ped2 --output-dir src/outputs/visualizations/ucsd_ped2_debug
```

Các tham số CLI cần có:

```text
--config
--project-root
--result-dir
--output-dir
--top-frames
--alerts
--video-id
--start-frame
--end-frame
--write-video
--alpha
--colormap
--min-score
--limit-frames
```

## 10. Đọc frame theo dataset

### 10.1. UCSD frame sequence

Với `input_type = frame_sequence`, có thể đọc lại frame từ:

```text
dataset/UCSD_Anomaly_Dataset.v1p2/UCSDped2/Test/Test001/001.tif
```

hoặc path đã lưu trong `frames_manifest.csv`.

Quy tắc:

- `video_id` khớp tên thư mục `Test001`;
- `frame_id` khớp tên file `.tif`;
- frame cần được preprocess lại cùng resize/grayscale/blur để khớp score;
- nếu overlay lên original frame, dùng raw frame trước resize và scale heatmap.

MVP nên tái dùng:

```text
kpdl_preprocess.datasets.scan_dataset
kpdl_preprocess.readers.iter_preprocessed_frames
```

để tránh lệch logic preprocess.

### 10.2. Avenue video

Với `input_type = video`, có thể đọc `.avi` bằng `cv2.VideoCapture` và seek tới frame cần xuất.

MVP cho Avenue chỉ cần hỗ trợ:

- xuất top frames bằng cách đọc tuần tự từng video;
- xuất video overlay tuần tự;
- không cần random seek tối ưu ngay.

## 11. Báo cáo định tính

SPEC 4 cần tạo report để sinh viên đánh giá thủ công. Mỗi record nên có:

```text
dataset
video_id
frame_id hoặc alert range
frame_score
smoothed_frame_score
severity
top_cells
reasons
image_path
manual_label placeholder: true_positive | false_positive | uncertain
notes placeholder
```

Mẫu Markdown:

```markdown
## Top Anomaly Frames

| Rank | Video | Frame | Score | Severity | Top cells | Image | Manual label | Notes |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| 1 | Test002 | 143 | 0.820 | medium | 09_10, 10_10 | top_frames/...png | TBD | TBD |
```

Phần report này không phải metric chính thức. Nó dùng để phát hiện các vấn đề như:

- score cao vì vùng nền nhiễu;
- heatmap nằm lệch vị trí chuyển động;
- top cell hợp lý nhưng threshold quá nhạy;
- alert kéo quá dài sau smoothing;
- frame score cao trong video nhưng không tương ứng bất thường rõ ràng.

## 12. Thí nghiệm bắt buộc

### Experiment 1 - UCSD Ped2 top 30 frames

Input:

```text
src/outputs/results/ucsd_ped2/frame_scores.csv
src/outputs/results/ucsd_ped2/cell_scores.csv
src/outputs/preprocessed/ucsd_ped2/grid.json
```

Output:

```text
src/outputs/visualizations/ucsd_ped2/top_frames/*.png
src/outputs/visualizations/ucsd_ped2/qualitative_report.md
```

Yêu cầu:

- xuất đủ 30 ảnh;
- ảnh không blank;
- heatmap đúng kích thước frame;
- top cells trong ảnh khớp `frame_scores.csv`.

### Experiment 2 - UCSD Ped2 alert peaks

Input:

```text
src/outputs/results/ucsd_ped2/alerts.json
```

Mỗi alert chọn frame có `smoothed_frame_score` cao nhất trong `[start_frame_id, end_frame_id]`.

Yêu cầu:

- xuất ít nhất 1 ảnh cho mỗi alert;
- report ghi reason từ alert;
- top cells và reason không bị mất dấu schema.

### Experiment 3 - UCSD Ped2 one overlay video

Chọn video có alert rõ, ví dụ `Test001` hoặc video có `max_score` cao nhất.

Output:

```text
src/outputs/visualizations/ucsd_ped2/videos/Test001_overlay.mp4
```

Yêu cầu:

- video mở được bằng OpenCV;
- số frame xuất khớp range đã chọn hoặc toàn video;
- overlay chạy đúng theo thời gian, không đứng một heatmap cố định.

### Experiment 4 - So sánh normalization

Chạy top frames với:

```text
heatmap_normalization = per_frame
heatmap_normalization = global
```

Ghi nhận:

- `per_frame` dễ thấy vùng nóng hơn;
- `global` tốt hơn khi so sánh độ mạnh giữa frame;
- chọn mặc định phù hợp cho report.

## 13. Kiểm tra chất lượng

Điều kiện chấp nhận:

- Không crash khi frame score có top cell không tìm thấy trong cell score, nhưng phải ghi warning.
- Không crash khi frame source thiếu frame, nhưng phải ghi `missing_frames`.
- Cell box không vượt biên frame.
- Heatmap có cùng width/height với frame overlay.
- Giá trị heatmap nằm trong `[0, 1]` trước khi colorize.
- File ảnh/video được ghi bằng path có dataset/video/frame rõ ràng.
- Report đủ thông tin để truy ngược về `frame_scores.csv`, `cell_scores.csv`, `alerts.json`.
- CLI chạy lại được chỉ bằng config và output của SPEC 3.

Kiểm tra tự động đề xuất:

```bash
python -m compileall src/kpdl_anomaly src/visualize.py
python src/visualize.py --config src/configs/ucsd_ped2.yaml --top-frames 5
python src/visualize.py --config src/configs/ucsd_ped2.yaml --alerts --limit-frames 5
```

Sau khi chạy, kiểm tra:

```text
num_images_written > 0
mọi image path trong visualization_index.json tồn tại
ảnh đọc lại bằng cv2.imread không None
ảnh có variance pixel > 0
visualization_stats.json không có missing frame nghiêm trọng
```

## 14. Checklist triển khai

- [ ] Bổ sung config `visualization` vào YAML dataset.
- [ ] Tạo `src/kpdl_anomaly/frames.py`.
- [ ] Tạo hàm đọc frame test theo `video_id` và `frame_id`.
- [ ] Tạo `src/kpdl_anomaly/visualization.py`.
- [ ] Load `grid.json` và validate cell bounds.
- [ ] Load `frame_scores.csv` và chọn top frames.
- [ ] Stream `cell_scores.csv` để lấy score cho frame được chọn.
- [ ] Tạo heatmap cell-level.
- [ ] Blend heatmap lên frame bằng OpenCV colormap.
- [ ] Vẽ top cell boxes.
- [ ] Xuất ảnh `.png` top frames.
- [ ] Xuất peak frame cho từng alert segment.
- [ ] Tạo `visualization_index.json`.
- [ ] Tạo `visualization_stats.json`.
- [ ] Tạo `qualitative_report.md`.
- [ ] Thêm CLI `src/visualize.py`.
- [ ] Thêm tùy chọn xuất video overlay.
- [ ] Chạy smoke visualization trên UCSD Ped2 top 5 frames.
- [ ] Chạy alert peak export trên UCSD Ped2.
- [ ] Kiểm tra ảnh/video không blank.
- [ ] Cập nhật `src/doc/spec_4_processed.md` sau khi triển khai.

## 15. Tiêu chí hoàn thành SPEC 4

SPEC 4 được xem là hoàn thành khi:

- có thể chạy CLI visualization từ config UCSD Ped2;
- xuất được ảnh heatmap overlay cho top anomaly frames;
- xuất được ảnh peak frame cho từng alert segment;
- xuất được ít nhất một video overlay cho một test video hoặc alert range;
- `visualization_index.json` và `visualization_stats.json` được ghi đầy đủ;
- `qualitative_report.md` có bảng top frames và alert segments;
- output có thể truy vết về score/reason của SPEC 3;
- có smoke test hoặc validation tự động chứng minh ảnh không blank và path tồn tại;
- `src/doc/spec_4_processed.md` ghi rõ file thay đổi, lệnh verification và kết quả.

## 16. Rủi ro và giảm thiểu

### 16.1. Heatmap lệch frame

Rủi ro: overlay dùng frame original nhưng grid là resize `320 x 240`, làm cell box lệch.

Giảm thiểu:

- MVP overlay lên preprocessed frame đã resize;
- nếu dùng original frame, scale `x1/y1/x2/y2` theo tỷ lệ original/resized;
- ghi rõ `frame_source` trong stats.

### 16.2. Load `cell_scores.csv` lớn

Rủi ro: Avenue có score lớn, load toàn bộ vào RAM không cần thiết.

Giảm thiểu:

- chọn frame trước từ `frame_scores.csv`;
- stream `cell_scores.csv` và chỉ giữ frame cần visualize;
- hỗ trợ `--video-id` và `--limit-frames`.

### 16.3. Overlay khó đọc

Rủi ro: colormap/alpha quá mạnh che mất nội dung frame.

Giảm thiểu:

- mặc định `alpha=0.45`;
- cho phép override `--alpha`;
- chỉ vẽ text cho số top cell nhỏ;
- report chứa top cell list thay vì nhồi nhiều chữ vào ảnh.

### 16.4. Alert kéo dài quá mức

Rủi ro: smoothing làm một alert segment dài, xuất video/ảnh quá nhiều.

Giảm thiểu:

- với `--alerts`, mặc định chỉ xuất peak frame;
- thêm `--write-video` khi cần video segment;
- giới hạn `--max-alerts` nếu cần debug nhanh.

### 16.5. Nhận xét định tính không đồng nhất

Rủi ro: manual label/notes tùy người xem, khó so sánh.

Giảm thiểu:

- report có cột label cố định: `true_positive`, `false_positive`, `uncertain`;
- thêm tiêu chí ngắn trong báo cáo dự án;
- SPEC 6 sẽ dùng ground truth để đánh giá định lượng.

## 17. Hướng sau SPEC 4

Sau SPEC 4, các bước tiếp theo nên là:

- SPEC 5: tokenization, rare token score và association rules trong Python;
- SPEC 6: evaluation ROC-AUC/EER với ground truth UCSD;
- SPEC 7: optical flow hoặc direction feature thật để bắt bất thường sai hướng;
- tinh chỉnh threshold/smoothing dựa trên report định tính từ SPEC 4 và metric từ SPEC 6.
