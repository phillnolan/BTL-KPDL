# SPEC 2 - Kế hoạch triển khai phân cụm và khai phá luật trên WEKA

## 1. Mục tiêu

Tài liệu này mô tả kế hoạch dùng WEKA cho giai đoạn sau tiền xử lý của dự án phát hiện hành vi bất thường trên camera giám sát.

SPEC 1 đã tạo dữ liệu đặc trưng dạng bảng và xuất ARFF. SPEC 2 tập trung vào việc dùng các file ARFF đó để:

- kiểm tra nhanh chất lượng feature bằng giao diện WEKA;
- chạy phân cụm hành vi không gian-thời gian trên dữ liệu train normal;
- so sánh một số cấu hình phân cụm cơ bản;
- gán nhãn cụm cho train/test để phục vụ bước anomaly scoring sau này;
- rời rạc hóa feature và thử khai phá luật kết hợp bằng Apriori trong WEKA;
- ghi lại kết quả thực nghiệm sao cho có thể đối chiếu với pipeline Python của dự án.

WEKA trong SPEC 2 được dùng như công cụ thực nghiệm, phân tích và đối chiếu. Runtime chính của hệ thống vẫn nên được triển khai bằng Python ở các SPEC sau để dễ tự động hóa, tính điểm bất thường, vẽ heatmap và đánh giá ROC-AUC/EER.

## 2. Liên hệ với PRD và SPEC 1

Theo PRD, hai trụ cột nghiên cứu của hệ thống là:

- phân cụm hành vi-không gian-thời gian;
- khai phá luật kết hợp để giải thích ngữ cảnh bất thường.

SPEC 1 đã hoàn thành phần tạo feature đầu vào cho hai trụ cột này:

- đọc UCSD Ped1/Ped2 dạng frame `.tif`;
- đọc CUHK Avenue dạng video `.avi`;
- resize, grayscale, blur theo cấu hình;
- chia grid `12 x 16`;
- tạo cube độ dài `5`, stride `1`;
- trích xuất feature bằng frame differencing;
- xuất `features_train.csv`, `features_test.csv`;
- xuất ARFF cho WEKA.

SPEC 2 bắt đầu từ các file ARFF đã có, không xử lý ảnh/video thô trong WEKA.

## 3. Phạm vi

### 3.1. Nằm trong phạm vi

- Import ARFF vào WEKA Explorer.
- Kiểm tra schema, số dòng, kiểu thuộc tính và giá trị thiếu.
- Lọc bỏ các thuộc tính định danh không nên đưa vào mô hình.
- Chuẩn hóa feature numeric trước khi phân cụm.
- Chạy phân cụm bằng `SimpleKMeans` làm baseline chính.
- Thử `EM` để so sánh cụm mềm và số cụm tự ước lượng.
- Thử `Canopy` hoặc `FarthestFirst` nếu cần baseline nhanh trên dữ liệu lớn.
- Chạy per-cell clustering ở mức thử nghiệm cho một số cell đại diện.
- Xuất model, log kết quả, centroid, cluster size và cluster assignment.
- Dùng `Discretize` và `Apriori` trong WEKA để thử khai phá luật kết hợp.
- Ghi lại kết quả vào thư mục thí nghiệm và file processed sau khi triển khai.

### 3.2. Ngoài phạm vi

- Xử lý ảnh/video thô bằng WEKA.
- Vẽ heatmap bất thường.
- Tính anomaly score hoàn chỉnh.
- Tính ROC-AUC/EER hoàn chỉnh.
- Train model production chạy realtime.
- Tối ưu thuật toán phân cụm ngoài các baseline có sẵn trong WEKA.
- Thay thế pipeline Python của dự án.

## 4. Dữ liệu đầu vào

Các file ARFF đầu vào mặc định nằm tại:

```text
src/outputs/weka/
  ucsd_ped2_features_train.arff
  ucsd_ped2_features_test.arff
  ucsd_ped1_features_train.arff
  ucsd_ped1_features_test.arff
  avenue_features_train.arff
  avenue_features_test.arff
```

Thứ tự ưu tiên thực nghiệm:

1. `ucsd_ped2_features_train.arff`: nhỏ hơn Avenue, phù hợp để kiểm tra quy trình.
2. `ucsd_ped2_features_test.arff`: dùng để gán cụm và so sánh phân bố train/test.
3. `ucsd_ped1_features_train.arff`: mở rộng sau khi Ped2 ổn.
4. `avenue_features_train.arff`: dữ liệu lớn hơn, chỉ chạy sau khi quy trình và cấu hình đã rõ.

Kích thước dữ liệu hiện tại theo `preprocess_stats.json`:

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

Với Avenue, nên dùng sample hoặc chạy batch/CLI vì file ARFF có kích thước lớn.

## 5. Schema feature

ARFF từ SPEC 1 có các thuộc tính:

```text
1  dataset
2  split
3  video_id
4  cube_id
5  start_frame_id
6  end_frame_id
7  center_frame_id
8  cell_id
9  cell_row
10 cell_col
11 foreground_ratio
12 motion_magnitude_mean
13 motion_magnitude_std
14 motion_density
15 direction_hist_0
16 direction_hist_1
17 direction_hist_2
18 direction_hist_3
19 direction_hist_4
20 direction_hist_5
21 direction_hist_6
22 direction_hist_7
23 brightness_mean
24 brightness_delta
```

Ghi chú quan trọng:

- `dataset`, `split`, `video_id`, `cube_id` là định danh, không dùng để phân cụm.
- `start_frame_id`, `end_frame_id`, `center_frame_id` có thể tạo nhiễu hoặc làm cụm học theo thứ tự thời gian, không dùng trong baseline đầu tiên.
- `cell_id` là nominal, hữu ích để truy vết, nhưng không nên đưa trực tiếp vào KMeans baseline.
- `cell_row`, `cell_col` có thể dùng cho global spatio-temporal clustering, nhưng không dùng trong per-cell clustering.
- `direction_hist_0..7` hiện bằng `0.0` với `motion_method = frame_diff`, nên bỏ khỏi baseline đầu tiên.
- Các feature numeric chính hiện nên dùng là `foreground_ratio`, `motion_magnitude_mean`, `motion_magnitude_std`, `motion_density`, `brightness_mean`, `brightness_delta`.

## 6. Bộ thuộc tính đề xuất

### 6.1. Baseline A - Behavior-only global clustering

Mục tiêu: kiểm tra xem feature chuyển động và ánh sáng có tạo được cụm hành vi cơ bản hay không.

Giữ các thuộc tính:

```text
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
brightness_mean
brightness_delta
```

Trong ARFF gốc, giữ index:

```text
11-14,23-24
```

Loại bỏ:

```text
1-10,15-22
```

### 6.2. Baseline B - Spatio-behavior global clustering

Mục tiêu: cho phép cụm học thêm vị trí cell trong frame.

Giữ các thuộc tính:

```text
cell_row
cell_col
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
brightness_mean
brightness_delta
```

Trong ARFF gốc, giữ index:

```text
9-14,23-24
```

Baseline này có thể tạo cụm theo vùng không gian. Cần so sánh với Baseline A để tránh trường hợp model chỉ học vị trí mà không học hành vi.

### 6.3. Baseline C - Per-cell behavior clustering

Mục tiêu: bám sát PRD hơn, vì mỗi cell/zone có normal pattern riêng.

Với mỗi cell được chọn, lọc dữ liệu theo `cell_id`, sau đó giữ:

```text
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
brightness_mean
brightness_delta
```

Không giữ `cell_row`, `cell_col`, `cell_id` vì tất cả bản ghi đã thuộc cùng một cell.

Trong WEKA Explorer, chỉ nên thử per-cell cho một số cell đại diện. Chạy đủ `192` cell bằng tay sẽ tốn thời gian và dễ sai. Nếu cần chạy toàn bộ cell, nên dùng WEKA CLI hoặc chuyển sang Python ở SPEC sau.

## 7. Quy trình thao tác trong WEKA Explorer

### Bước 1 - Mở dữ liệu

1. Mở `WEKA Explorer`.
2. Vào tab `Preprocess`.
3. Chọn `Open file`.
4. Mở `src/outputs/weka/ucsd_ped2_features_train.arff`.
5. Kiểm tra số instances, số attributes và kiểu dữ liệu.

Điều kiện chấp nhận:

- WEKA đọc được file không lỗi parse ARFF.
- Các feature numeric không bị nhận nhầm thành string.
- `cell_id` là nominal.
- Không có cột numeric bị missing hàng loạt.

### Bước 2 - Lọc thuộc tính

Với Baseline A, dùng filter:

```text
weka.filters.unsupervised.attribute.Remove
```

Cách cấu hình:

```text
attributeIndices: 11-14,23-24
invertSelection: True
```

Sau khi apply, chỉ còn 6 thuộc tính numeric.

Với Baseline B:

```text
attributeIndices: 9-14,23-24
invertSelection: True
```

Sau khi apply, chỉ còn 8 thuộc tính numeric.

### Bước 3 - Xử lý missing value

Nếu WEKA báo có missing value, dùng:

```text
weka.filters.unsupervised.attribute.ReplaceMissingValues
```

Điều kiện mong đợi: SPEC 1 không sinh missing value trong feature numeric. Bước này chủ yếu là guard.

### Bước 4 - Chuẩn hóa feature

Do `brightness_mean` có thang `[0, 255]` còn motion feature thường nhỏ hơn nhiều, cần chuẩn hóa trước KMeans.

Filter đề xuất:

```text
weka.filters.unsupervised.attribute.Standardize
```

Có thể dùng `Normalize`, nhưng `Standardize` phù hợp hơn cho KMeans khi các feature có đơn vị đo khác nhau.

### Bước 5 - Chạy SimpleKMeans

Vào tab `Cluster`, chọn:

```text
weka.clusterers.SimpleKMeans
```

Cấu hình baseline:

```text
numClusters: 5
seed: 10
maxIterations: 500
preserveInstancesOrder: True
```

Chạy các cấu hình K:

```text
K = 3
K = 5
K = 8
```

Lưu lại:

- cluster centroids;
- number of instances per cluster;
- within cluster sum of squared errors;
- thời gian chạy;
- nhận xét xem centroid có ý nghĩa hành vi hay không.

### Bước 6 - Gán cụm cho test set

Sau khi có cấu hình tốt trên train:

1. Lưu model clusterer.
2. Mở hoặc cung cấp `ucsd_ped2_features_test.arff`.
3. Áp dụng đúng chuỗi filter đã dùng cho train.
4. Gán cluster cho test set bằng model đã train.
5. Xuất cluster assignment để đối chiếu với metadata gốc.

Lưu ý: filter train và test phải giống nhau tuyệt đối. Nếu thao tác thủ công trong Explorer dễ lệch, cần ghi rõ cấu hình filter trong log.

### Bước 7 - Lưu kết quả

Kết quả thí nghiệm nên lưu ngoài repo hoặc dưới thư mục output bị `.gitignore`:

```text
src/outputs/weka_experiments/
  spec_2_log.md
  models/
    ucsd_ped2_behavior_kmeans_k3.model
    ucsd_ped2_behavior_kmeans_k5.model
    ucsd_ped2_behavior_kmeans_k8.model
  reports/
    ucsd_ped2_behavior_kmeans_k3.txt
    ucsd_ped2_behavior_kmeans_k5.txt
    ucsd_ped2_behavior_kmeans_k8.txt
  assignments/
    ucsd_ped2_train_behavior_k5_clusters.csv
    ucsd_ped2_test_behavior_k5_clusters.csv
```

Nếu export bằng Explorer không giữ được đầy đủ metadata, cần lưu thêm mapping từ file CSV gốc:

```text
src/outputs/preprocessed/ucsd_ped2/features_train.csv
src/outputs/preprocessed/ucsd_ped2/features_test.csv
```

Mapping tối thiểu cần giữ:

```text
dataset
split
video_id
cube_id
start_frame_id
end_frame_id
center_frame_id
cell_id
cluster_id
```

## 8. Quy trình per-cell clustering trong WEKA

### 8.1. Lý do cần per-cell

PRD ưu tiên học normal pattern riêng theo từng cell/zone. Một chuyển động có thể bình thường ở vùng này nhưng bất thường ở vùng khác. Vì vậy, per-cell clustering là hướng chính sau khi global baseline chạy ổn.

### 8.2. Chọn cell thử nghiệm

Không chạy ngay toàn bộ `192` cell trong Explorer. Chọn một nhóm nhỏ:

- cell có motion density trung bình cao;
- cell có motion density trung bình thấp;
- cell ở vùng biên;
- cell ở vùng giữa khung hình;
- cell nghi ngờ có nhiều chuyển động bất thường trong test.

Danh sách khởi đầu đề xuất:

```text
04_08
05_08
06_08
07_08
08_05
08_06
09_05
09_06
```

Danh sách này chỉ là điểm bắt đầu, cần điều chỉnh sau khi xem phân bố motion thực tế.

### 8.3. Lọc theo cell trong WEKA

Cách làm thủ công:

1. Mở `ucsd_ped2_features_train.arff`.
2. Dùng filter theo instance để giữ một giá trị `cell_id`.
3. Sau khi chỉ còn một cell, dùng `Remove` để giữ các thuộc tính behavior:

```text
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
brightness_mean
brightness_delta
```

4. Dùng `Standardize`.
5. Chạy `SimpleKMeans` với `K = 3`, `5`, `8`.

Nếu thao tác lọc instance trong Explorer quá chậm, cần tạo file ARFF per-cell bằng script ở SPEC sau, rồi dùng WEKA chỉ để chạy clusterer.

### 8.4. Kết quả cần ghi cho mỗi cell

```text
dataset
cell_id
num_train_instances
algorithm
K
cluster_sizes
centroids
within_cluster_sse
nhận xét ý nghĩa cụm
```

Ví dụ nhận xét mong muốn:

```text
cell=08_05, K=5:
  C0: gần như đứng yên, brightness trung bình
  C1: chuyển động nhẹ, density thấp
  C2: chuyển động mạnh, density cao
  C3: brightness thay đổi mạnh
  C4: cụm nhỏ, có thể là nhiễu hoặc hành vi hiếm
```

## 9. Khai phá luật kết hợp trong WEKA

### 9.1. Mục tiêu

Thử dùng WEKA để khai phá luật quan hệ giữa vùng, mức chuyển động, mật độ, độ sáng và cluster. Phần này hỗ trợ trụ cột thứ hai của PRD: association rule mining.

### 9.2. Chuẩn bị dữ liệu

Apriori trong WEKA cần dữ liệu rời rạc/nominal. Với feature numeric, cần dùng:

```text
weka.filters.unsupervised.attribute.Discretize
```

Nguồn dữ liệu đề xuất:

- `ucsd_ped2_features_train.arff`;
- bản đã gắn thêm `cluster_id` từ KMeans, nếu có.

Thuộc tính nên giữ:

```text
cell_id
foreground_ratio
motion_magnitude_mean
motion_density
brightness_mean
brightness_delta
cluster_id
```

Thuộc tính nên bỏ:

```text
dataset
split
video_id
cube_id
start_frame_id
end_frame_id
center_frame_id
direction_hist_0..7
```

### 9.3. Rời rạc hóa

Cấu hình ban đầu:

```text
Discretize:
  bins: 3 hoặc 5
  useEqualFrequency: True
```

Mục tiêu token:

```text
motion_density = low | medium | high
motion_magnitude_mean = still | slow | medium | fast | very_fast
brightness_mean = dark | normal | bright
brightness_delta = stable | changing
cluster_id = C0 | C1 | C2 | ...
cell_id = 08_05 | ...
```

WEKA có thể tạo tên bin dạng khoảng số. Khi đưa về báo cáo, cần diễn giải lại các khoảng này thành token dễ hiểu.

### 9.4. Chạy Apriori

Vào tab `Associate`, chọn:

```text
weka.associations.Apriori
```

Cấu hình khởi đầu:

```text
lowerBoundMinSupport: 0.01
minMetric: 0.6
metricType: Confidence
numRules: 50
```

Sau đó thử:

```text
support = 0.005, 0.01, 0.02
confidence = 0.6, 0.7, 0.8
```

Kết quả cần lọc lại thủ công:

- bỏ luật quá hiển nhiên hoặc chỉ phản ánh cấu trúc grid;
- ưu tiên luật có `cell_id`, `motion_density`, `motion_magnitude_mean`, `cluster_id`;
- ghi lại luật giúp giải thích hành vi normal;
- ghi lại luật có khả năng dùng để phát hiện vi phạm trong test.

### 9.5. Ví dụ luật mong muốn

```text
cell_id=08_05 brightness_mean=normal -> motion_density=low
cell_id=06_08 motion_magnitude_mean=slow -> cluster_id=C1
cluster_id=C3 motion_density=high -> brightness_delta=stable
```

Các luật này chưa trực tiếp là bất thường. Chúng mô tả pattern phổ biến trong train normal. Bước anomaly scoring sau này sẽ dùng:

- độ hiếm của token combination;
- cluster distance;
- mức vi phạm luật có confidence/lift cao.

## 10. Thí nghiệm bắt buộc

### 10.1. Experiment 1 - UCSD Ped2 global behavior KMeans

Input:

```text
src/outputs/weka/ucsd_ped2_features_train.arff
```

Feature:

```text
11-14,23-24
```

Algorithm:

```text
SimpleKMeans
K = 3, 5, 8
Standardize = yes
```

Kết quả cần có:

- report cho từng K;
- nhận xét cụm;
- chọn một K hợp lý để gán test.

### 10.2. Experiment 2 - UCSD Ped2 global spatio-behavior KMeans

Input:

```text
src/outputs/weka/ucsd_ped2_features_train.arff
```

Feature:

```text
9-14,23-24
```

Algorithm:

```text
SimpleKMeans
K = 3, 5, 8
Standardize = yes
```

Mục tiêu:

- so sánh với behavior-only;
- xem thêm `cell_row`, `cell_col` có làm cụm bị chi phối bởi vị trí hay không.

### 10.3. Experiment 3 - UCSD Ped2 selected per-cell KMeans

Input:

```text
src/outputs/weka/ucsd_ped2_features_train.arff
```

Cell:

```text
04_08
06_08
08_05
09_06
```

Feature:

```text
11-14,23-24
```

Algorithm:

```text
SimpleKMeans
K = 3, 5
Standardize = yes
```

Mục tiêu:

- kiểm tra feasibility của per-cell normal pattern;
- xác định có cần tạo script per-cell ARFF hay không.

### 10.4. Experiment 4 - UCSD Ped2 EM comparison

Input:

```text
src/outputs/weka/ucsd_ped2_features_train.arff
```

Feature:

```text
11-14,23-24
```

Algorithm:

```text
EM
Standardize = yes
```

Mục tiêu:

- so sánh cluster size và ý nghĩa centroid với KMeans;
- xem EM có tạo cụm quá nhỏ hoặc khó giải thích không.

### 10.5. Experiment 5 - Apriori trên feature đã rời rạc hóa

Input:

```text
ucsd_ped2 train, ưu tiên bản sample nếu WEKA chạy chậm
```

Feature:

```text
cell_id
motion_magnitude_mean
motion_density
brightness_mean
brightness_delta
cluster_id nếu có
```

Algorithm:

```text
Discretize + Apriori
```

Mục tiêu:

- sinh tối thiểu 20 luật có thể diễn giải;
- chọn 5-10 luật tốt nhất để đưa vào báo cáo phân tích.

## 11. Đầu ra mong muốn

Sau khi triển khai SPEC 2, cần có:

```text
src/outputs/weka_experiments/
  spec_2_log.md
  models/
  reports/
  assignments/
  rules/
```

File log cần ghi:

```text
experiment_id
dataset
input_file
filter_steps
algorithm
parameters
runtime
num_instances
num_attributes
cluster_sizes
main_centroids
observations
accepted_or_rejected
reason
```

Cluster assignment cần có tối thiểu:

```text
dataset
split
video_id
cube_id
start_frame_id
end_frame_id
center_frame_id
cell_id
cluster_id
```

Rule output cần có:

```text
rule_id
antecedent
consequent
support
confidence
lift nếu có
interpretation
use_for_anomaly_reason
```

## 12. Quy ước đặt tên thí nghiệm

Định dạng:

```text
{dataset}_{scope}_{feature_set}_{algorithm}_{params}
```

Ví dụ:

```text
ucsd_ped2_global_behavior_kmeans_k5
ucsd_ped2_global_spatiobehavior_kmeans_k5
ucsd_ped2_cell_08_05_behavior_kmeans_k3
ucsd_ped2_global_behavior_em_auto
ucsd_ped2_rules_discretize5_apriori_s001_c06
```

## 13. Tiêu chí đánh giá kết quả WEKA

Một kết quả phân cụm được xem là dùng được cho bước sau nếu:

- WEKA train xong không lỗi bộ nhớ;
- cluster không bị lệch hoàn toàn vào một cụm duy nhất;
- centroid có thể diễn giải bằng motion/brightness;
- cụm nhỏ có ý nghĩa như hành vi hiếm hoặc nhiễu, không chỉ là lỗi scale;
- train/test có thể dùng cùng schema và cùng filter;
- cluster assignment truy vết được về `video_id`, `frame_id`, `cube_id`, `cell_id`;
- kết quả có thể chuyển thành token `cluster=Cx`.

Một tập luật được xem là dùng được nếu:

- luật không chỉ lặp lại quan hệ định danh vô nghĩa;
- support không quá thấp;
- confidence đủ cao để diễn giải normal pattern;
- có thể chuyển thành câu giải thích dễ hiểu;
- có thể dùng như tín hiệu phụ, không quyết định alert một mình.

## 14. Rủi ro và giảm thiểu

### 14.1. WEKA thiếu bộ nhớ khi mở ARFF lớn

Rủi ro: Avenue ARFF hơn 500 MB mỗi split, WEKA Explorer có thể chậm hoặc crash.

Giảm thiểu:

- chạy UCSD Ped2 trước;
- tăng JVM heap khi mở WEKA, ví dụ `-Xmx8g` hoặc cao hơn nếu máy đủ RAM;
- tạo sample ARFF cho Avenue;
- dùng WEKA CLI thay vì Explorer khi dữ liệu lớn.

### 14.2. KMeans bị chi phối bởi thang đo brightness

Rủi ro: `brightness_mean` có giá trị lớn hơn motion feature, làm cụm chủ yếu theo độ sáng.

Giảm thiểu:

- luôn dùng `Standardize` trước KMeans;
- so sánh kết quả có và không có brightness;
- ghi rõ filter trong log.

### 14.3. Cụm global không phản ánh normal pattern theo vùng

Rủi ro: global clustering trộn nhiều cell, làm mất ngữ cảnh không gian.

Giảm thiểu:

- chỉ dùng global clustering như baseline kiểm tra nhanh;
- triển khai per-cell clustering cho cell đại diện;
- sau SPEC 2, ưu tiên script Python hoặc WEKA CLI để chạy đủ `192` cell.

### 14.4. Direction histogram hiện chưa có ý nghĩa

Rủi ro: `direction_hist_0..7` đang bằng `0.0` với frame differencing, đưa vào model sẽ thêm cột vô ích.

Giảm thiểu:

- bỏ direction histogram khỏi baseline WEKA;
- chỉ đưa lại khi pipeline feature có optical flow hoặc hướng chuyển động đáng tin cậy.

### 14.5. Apriori sinh quá nhiều luật vụn

Rủi ro: quá nhiều token theo cell làm support thấp và luật khó tổng quát.

Giảm thiểu:

- tăng `min_support`;
- giảm số bin rời rạc hóa;
- chạy luật trên nhóm cell hoặc global trước;
- chỉ dùng luật làm tín hiệu giải thích phụ.

## 15. Checklist triển khai

- [ ] Mở được `ucsd_ped2_features_train.arff` trong WEKA.
- [ ] Kiểm tra schema và kiểu thuộc tính.
- [ ] Tạo filter Baseline A giữ `11-14,23-24`.
- [ ] Standardize feature cho Baseline A.
- [ ] Chạy `SimpleKMeans` với `K=3`.
- [ ] Chạy `SimpleKMeans` với `K=5`.
- [ ] Chạy `SimpleKMeans` với `K=8`.
- [ ] Ghi report và nhận xét centroid cho từng K.
- [ ] Chọn một cấu hình KMeans để gán test set.
- [ ] Xuất cluster assignment cho train/test.
- [ ] Chạy Baseline B giữ `9-14,23-24`.
- [ ] So sánh Baseline A và B.
- [ ] Chạy per-cell KMeans cho ít nhất 4 cell đại diện.
- [ ] Chạy EM để so sánh với KMeans.
- [ ] Rời rạc hóa feature bằng `Discretize`.
- [ ] Chạy Apriori trên train normal.
- [ ] Chọn 5-10 luật dễ giải thích.
- [ ] Ghi toàn bộ kết quả vào `src/outputs/weka_experiments/spec_2_log.md`.
- [ ] Cập nhật `src/doc/spec_2_processed.md` sau khi thực nghiệm.

## 16. Tiêu chí hoàn thành SPEC 2

SPEC 2 được xem là hoàn thành khi:

- có tối thiểu một mô hình KMeans chạy thành công trên UCSD Ped2 train;
- có so sánh `K=3`, `K=5`, `K=8`;
- có report centroid và cluster size;
- có cluster assignment cho UCSD Ped2 train/test;
- có ít nhất một thử nghiệm per-cell;
- có ít nhất một thử nghiệm Apriori trên dữ liệu đã rời rạc hóa;
- có log thực nghiệm đủ để tái hiện thao tác;
- có nhận xét cấu hình nào nên chuyển sang Python trong SPEC tiếp theo.

## 17. Hướng mở rộng sau SPEC 2

Sau khi hoàn thành SPEC 2, các bước tiếp theo nên là:

- viết script Python train per-cell MiniBatchKMeans dựa trên kết quả WEKA;
- tính distance tới centroid gần nhất;
- chọn threshold theo percentile train;
- sinh `cluster=Cx` token cho mỗi feature row;
- kết hợp cluster distance, temporal change, rare token và rule violation thành anomaly score;
- tạo `frame_scores.csv`, `cell_scores`, `alerts.json`;
- vẽ heatmap overlay để kiểm tra định tính;
- đánh giá frame-level ROC-AUC/EER nếu có ground truth.
