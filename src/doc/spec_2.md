# SPEC 2 - Thực hành phân cụm và khai phá luật trên WEKA 3.8.7 với K=5

## 1. Mục tiêu

Tài liệu này mô tả chi tiết quy trình thực hành phân cụm và khai phá luật kết hợp bằng **WEKA 3.8.7** trên dữ liệu đặc trưng đã được sinh ở SPEC 1. SPEC 2 không xử lý ảnh hoặc video thô. Điểm bắt đầu của SPEC 2 là các file ARFF/CSV đã có trong `src/outputs`.

Trọng tâm của SPEC 2 là:

- mở và kiểm tra dữ liệu đặc trưng trong WEKA Explorer;
- chuẩn bị đúng bộ thuộc tính để phân cụm;
- chạy `SimpleKMeans` với **K=5** làm cấu hình thực hành chính;
- đọc centroid, kích thước cụm và phân bố train/test để hiểu các mẫu hành vi bình thường;
- tạo token `cluster=C0..C4` để phục vụ giải thích;
- rời rạc hóa đặc trưng liên tục;
- chạy `Apriori` để khai phá luật kết hợp trên dữ liệu normal;
- ghi lại báo cáo thực hành đủ chi tiết để chuyển kết quả sang pipeline Python ở SPEC sau.

Trong tài liệu này, **K=5 là cấu hình mặc định và bắt buộc**. Các giá trị K khác chỉ được nhắc như bối cảnh tham khảo từ lần thử trước, không phải yêu cầu thực hành chính của SPEC 2.

## 2. Liên hệ với PRD và các spec trước

Theo PRD, dự án có hai trụ cột nghiên cứu:

- phân cụm hành vi-không gian-thời gian để học mẫu bình thường theo vùng camera;
- khai phá luật kết hợp để giải thích quan hệ giữa vùng, chuyển động, mật độ, độ sáng và cụm hành vi.

SPEC 1 đã chuẩn bị dữ liệu đầu vào cho hai trụ cột này:

- đọc UCSD Ped1/Ped2 dạng chuỗi frame `.tif`;
- đọc CUHK Avenue dạng video `.avi`;
- resize, grayscale và blur theo cấu hình;
- chia frame thành grid `12 x 16`;
- tạo cube độ dài `5`, stride `1`;
- trích xuất feature bằng frame differencing;
- xuất `features_train.csv`, `features_test.csv`;
- xuất ARFF cho WEKA.

SPEC 2 dùng WEKA như môi trường thực hành, phân tích và đối chiếu. Runtime chính của hệ thống vẫn nên được tự động hóa bằng Python ở SPEC sau để train hàng loạt theo cell, tính anomaly score, xuất heatmap và đánh giá ROC-AUC/EER.

## 3. Nguyên tắc thực hành SPEC 2

### 3.1. Cố định phiên bản và cấu hình chính

Phiên bản công cụ:

```text
WEKA: 3.8.7
JVM heap khuyến nghị: 4g đến 8g cho UCSD Ped2, cao hơn nếu thử Avenue
Giao diện chính: WEKA Explorer
Tab dùng chính: Preprocess, Cluster, Associate
```

Cấu hình phân cụm chính:

```text
Algorithm: weka.clusterers.SimpleKMeans
numClusters: 5
seed: 10
maxIterations: 500
preserveInstancesOrder: True
distanceFunction: EuclideanDistance
feature scaling: Standardize trước khi train
```

Quy ước cụm:

```text
cluster_id = C0, C1, C2, C3, C4
```

Không được diễn giải `C0..C4` như nhãn ngữ nghĩa cố định trước khi đọc centroid. Ý nghĩa cụm phải được suy ra từ centroid, kích thước cụm và phân bố feature sau khi chuẩn hóa.

### 3.2. Ưu tiên dữ liệu

Thực hành theo thứ tự:

1. `ucsd_ped2_features_train.arff`: dữ liệu chính để train và phân tích.
2. `ucsd_ped2_features_test.arff`: dữ liệu để kiểm tra phân bố cụm trên test.
3. `ucsd_ped1_features_train.arff`: mở rộng nếu Ped2 ổn.
4. `avenue_features_train.arff`: chỉ thử sau cùng vì dữ liệu lớn.

SPEC 2 phải hoàn thành trên UCSD Ped2 trước khi mở rộng sang dataset khác.

### 3.3. Không đưa metadata vào KMeans baseline

Các cột như `dataset`, `split`, `video_id`, `cube_id`, `start_frame_id`, `end_frame_id`, `center_frame_id` dùng để truy vết, không dùng để phân cụm. Nếu đưa vào mô hình, KMeans có thể học định danh hoặc thứ tự thời gian thay vì hành vi.

Với baseline hành vi chính, chỉ dùng:

```text
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
brightness_mean
brightness_delta
```

Trong ARFF gốc, đây là các cột:

```text
11-14,23-24
```

## 4. Dữ liệu đầu vào

Các file ARFF mặc định:

```text
src/outputs/weka/
  ucsd_ped2_features_train.arff
  ucsd_ped2_features_test.arff
  ucsd_ped1_features_train.arff
  ucsd_ped1_features_test.arff
  avenue_features_train.arff
  avenue_features_test.arff
```

Các file CSV metadata tương ứng:

```text
src/outputs/preprocessed/{dataset}/
  features_train.csv
  features_test.csv
  frames_manifest.csv
  videos_manifest.csv
  grid.json
  preprocess_stats.json
```

Kích thước dữ liệu hiện tại:

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

Với Avenue, WEKA Explorer có thể chậm hoặc hết bộ nhớ. Không dùng Avenue làm bài thực hành đầu tiên.

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

Ghi chú:

- `cell_id` là nominal, cần giữ khi khai phá luật hoặc truy vết, nhưng không dùng trực tiếp trong KMeans behavior-only.
- `cell_row`, `cell_col` chỉ dùng ở thí nghiệm spatio-behavior để kiểm tra ảnh hưởng vị trí.
- `direction_hist_0..7` hiện chưa mang thông tin hướng đáng tin cậy với `motion_method = frame_diff`, nên loại khỏi baseline KMeans.
- `brightness_mean` có thang đo khác motion feature, vì vậy phải dùng `Standardize` trước KMeans.

## 6. Bộ dữ liệu thực hành trong WEKA

### 6.1. Baseline A - Global behavior KMeans K=5

Mục tiêu: kiểm tra các mẫu hành vi tổng quát dựa trên motion và brightness, không cho model biết vị trí.

Giữ:

```text
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
brightness_mean
brightness_delta
```

Trong ARFF gốc:

```text
Giữ: 11-14,23-24
Loại: 1-10,15-22
```

Đây là dataset chính của SPEC 2.

### 6.2. Baseline B - Global spatio-behavior KMeans K=5

Mục tiêu: kiểm tra nếu thêm vị trí cell thì cụm có bị chi phối bởi không gian hay không.

Giữ:

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

Trong ARFF gốc:

```text
Giữ: 9-14,23-24
Loại: 1-8,15-22
```

Baseline B chỉ dùng để phân tích. Nếu centroid chủ yếu tách theo `cell_row`, `cell_col`, không nên dùng nó làm baseline scoring chính.

### 6.3. Dataset C - Per-cell behavior KMeans K=5

Mục tiêu: bám sát PRD hơn vì mỗi cell/zone có normal pattern riêng.

Quy trình:

1. Lọc dữ liệu theo một `cell_id`.
2. Sau khi chỉ còn một cell, loại toàn bộ metadata.
3. Giữ 6 feature hành vi như Baseline A.
4. `Standardize`.
5. Chạy `SimpleKMeans` với `K=5`.

Cell khởi đầu đề xuất:

```text
04_08
06_08
08_05
09_06
```

Nếu muốn phân tích rộng hơn:

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

Không chạy thủ công đủ `192` cell bằng Explorer. Nếu cần chạy tất cả cell, chuyển sang WEKA CLI hoặc Python.

### 6.4. Dataset D - Association rules sau KMeans K=5

Mục tiêu: tạo dữ liệu nominal để chạy Apriori.

Giữ:

```text
cell_id
motion_magnitude_mean
motion_density
brightness_mean
brightness_delta
cluster_id
```

Trong đó `cluster_id` là cụm `C0..C4` từ KMeans K=5. Nếu chưa có `cluster_id`, vẫn có thể chạy luật trên feature rời rạc hóa, nhưng phần rule sẽ thiếu token cụm hành vi.

Loại:

```text
dataset
split
video_id
cube_id
start_frame_id
end_frame_id
center_frame_id
cell_row
cell_col
foreground_ratio nếu tạo quá nhiều luật nhiễu
motion_magnitude_std nếu khó diễn giải
direction_hist_0..7
```

## 7. Cấu trúc output thực hành

Kết quả thực hành nên lưu dưới thư mục output bị `.gitignore`:

```text
src/outputs/weka_experiments/spec_2_weka_3_8_7/
  spec_2_log.md
  prepared/
    ucsd_ped2_train_behavior_k5_standardized.arff
    ucsd_ped2_test_behavior_k5_standardized.arff
    ucsd_ped2_train_spatiobehavior_k5_standardized.arff
    ucsd_ped2_train_rules_k5_discretized.arff
  models/
    ucsd_ped2_global_behavior_simplekmeans_k5.model
    ucsd_ped2_global_spatiobehavior_simplekmeans_k5.model
  reports/
    ucsd_ped2_global_behavior_simplekmeans_k5_train.txt
    ucsd_ped2_global_behavior_simplekmeans_k5_test.txt
    ucsd_ped2_global_spatiobehavior_simplekmeans_k5_train.txt
    ucsd_ped2_rules_apriori_k5.txt
  assignments/
    ucsd_ped2_train_behavior_k5_clusters.csv
    ucsd_ped2_test_behavior_k5_clusters.csv
  rules/
    ucsd_ped2_rules_k5_selected.md
```

Quy ước đặt tên:

```text
{dataset}_{scope}_{feature_set}_{algorithm}_k5
```

Ví dụ:

```text
ucsd_ped2_global_behavior_simplekmeans_k5
ucsd_ped2_global_spatiobehavior_simplekmeans_k5
ucsd_ped2_cell_08_05_behavior_simplekmeans_k5
ucsd_ped2_rules_discretize5_apriori_k5_s001_c06
```

## 8. Chuẩn bị WEKA 3.8.7

### 8.1. Mở WEKA với heap đủ lớn

Trên Windows, có thể mở bằng shortcut WEKA nếu dataset nhỏ. Với UCSD Ped2 full, nên mở bằng JVM heap rõ ràng:

```powershell
java -Xmx8g -cp "C:\Program Files\Weka-3-8-7\weka.jar" weka.gui.GUIChooser
```

Nếu đường dẫn khác, thay lại vị trí `weka.jar`.

Kiểm tra phiên bản:

1. Mở `GUIChooser`.
2. Chọn menu `Help`.
3. Chọn `About`.
4. Ghi vào log: `WEKA 3.8.7`.

### 8.2. Tạo log trước khi thao tác

Tạo hoặc mở:

```text
src/outputs/weka_experiments/spec_2_weka_3_8_7/spec_2_log.md
```

Mỗi lần chạy cần ghi:

```text
experiment_id:
date:
weka_version:
input_file:
num_instances:
num_attributes_before_filter:
filter_steps:
algorithm:
parameters:
runtime:
output_files:
observations:
accepted_or_rejected:
reason:
```

Không chỉ chụp màn hình. Cần copy text output từ WEKA để kết quả có thể đọc lại.

## 9. Thực hành 1 - Mở và kiểm tra ARFF

### 9.1. Mở dữ liệu train

Trong WEKA Explorer:

1. Chọn `Explorer`.
2. Vào tab `Preprocess`.
3. Chọn `Open file`.
4. Mở:

```text
src/outputs/weka/ucsd_ped2_features_train.arff
```

Kiểm tra:

- số instances khoảng `477312`;
- số attributes là `24`;
- `cell_id` là nominal;
- các cột feature chính là numeric;
- không có missing value bất thường;
- relation name đọc được bình thường.

Ghi vào log:

```text
dataset = ucsd_ped2
split = train
instances = 477312
attributes = 24
```

### 9.2. Mở dữ liệu test

Lặp lại với:

```text
src/outputs/weka/ucsd_ped2_features_test.arff
```

Kiểm tra:

```text
instances = 376704
attributes = 24
```

Không apply filter lên test trước khi đã ghi rõ chuỗi filter dùng cho train.

## 10. Thực hành 2 - Tạo Baseline A behavior-only

### 10.1. Remove metadata và cột không dùng

Trong tab `Preprocess`, chọn filter:

```text
weka.filters.unsupervised.attribute.Remove
```

Cấu hình theo cách giữ cột:

```text
attributeIndices: 11-14,23-24
invertSelection: True
```

Sau khi nhấn `Apply`, dataset chỉ còn:

```text
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
brightness_mean
brightness_delta
```

Điều kiện chấp nhận:

```text
instances = 477312
attributes = 6
all attributes = numeric
```

### 10.2. Xử lý missing value nếu có

Nếu WEKA báo missing value, dùng:

```text
weka.filters.unsupervised.attribute.ReplaceMissingValues
```

Kỳ vọng của SPEC 1 là không có missing value trong feature numeric. Nếu có missing value, phải ghi rõ cột nào và số lượng bao nhiêu.

### 10.3. Chuẩn hóa feature

Chọn filter:

```text
weka.filters.unsupervised.attribute.Standardize
```

Nhấn `Apply`.

Lý do bắt buộc:

- `brightness_mean` có thang `[0, 255]`;
- motion feature thường nhỏ hơn nhiều;
- KMeans dùng khoảng cách Euclidean nên sẽ bị lệch nếu không chuẩn hóa.

Sau khi chuẩn hóa, lưu dataset:

```text
src/outputs/weka_experiments/spec_2_weka_3_8_7/prepared/
  ucsd_ped2_train_behavior_k5_standardized.arff
```

### 10.4. Lặp lại filter cho test

Mở `ucsd_ped2_features_test.arff` và áp dụng cùng chuỗi:

1. `Remove` giữ `11-14,23-24`.
2. `ReplaceMissingValues` nếu train đã dùng.
3. `Standardize`.

Lưu:

```text
src/outputs/weka_experiments/spec_2_weka_3_8_7/prepared/
  ucsd_ped2_test_behavior_k5_standardized.arff
```

Lưu ý quan trọng: với thực hành Explorer, `Standardize` trên test có thể fit lại thống kê của test. Điều này chấp nhận được cho bài phân tích thủ công, nhưng khi triển khai production phải dùng scaler học từ train. Vì vậy, kết quả WEKA chỉ là thực nghiệm đối chiếu, không phải pipeline cuối.

## 11. Thực hành 3 - Chạy SimpleKMeans K=5 cho Baseline A

### 11.1. Cấu hình clusterer

Vào tab `Cluster`, chọn:

```text
weka.clusterers.SimpleKMeans
```

Cấu hình:

```text
numClusters: 5
seed: 10
maxIterations: 500
preserveInstancesOrder: True
displayStdDevs: True nếu có
dontReplaceMissingValues: False
distanceFunction: weka.core.EuclideanDistance
```

Nếu WEKA 3.8.7 hiển thị `initializationMethod`, dùng:

```text
initializationMethod: k-means++
```

Nếu giữ mặc định, ghi rõ trong log.

### 11.2. Chọn test mode

Đối với lần train đầu tiên:

```text
Test mode: Use training set
```

Nhấn `Start`.

Sau khi chạy xong, copy toàn bộ output vào:

```text
src/outputs/weka_experiments/spec_2_weka_3_8_7/reports/
  ucsd_ped2_global_behavior_simplekmeans_k5_train.txt
```

Lưu model:

1. Nhấp phải vào result trong `Result list`.
2. Chọn `Save model`.
3. Lưu thành:

```text
src/outputs/weka_experiments/spec_2_weka_3_8_7/models/
  ucsd_ped2_global_behavior_simplekmeans_k5.model
```

### 11.3. Kết quả tham chiếu đã có

Kết quả KMeans K=5 behavior-only đã từng ghi trong `src/doc/Kmean.md`:

```text
Algorithm: SimpleKMeans
Dataset: UCSD Ped2 train
Feature set: 11-14,23-24
K: 5
Iterations: 37
Within cluster sum of squared errors: 6491.182908722241

Train cluster sizes:
  C0: 27842  ( 6%)
  C1: 182948 (38%)
  C2: 16491  ( 3%)
  C3: 116779 (24%)
  C4: 133252 (28%)

Supplied test set cluster sizes:
  C0: 29347  ( 8%)
  C1: 123477 (33%)
  C2: 26080  ( 7%)
  C3: 93161  (25%)
  C4: 104639 (28%)
```

Centroid chuẩn hóa tham chiếu:

```text
C0:
  foreground_ratio          1.6539
  motion_magnitude_mean     1.6991
  motion_magnitude_std      2.2719
  motion_density            1.5698
  brightness_mean           0.4286
  brightness_delta         -0.0129

C1:
  foreground_ratio         -0.2889
  motion_magnitude_mean    -0.3077
  motion_magnitude_std     -0.3149
  motion_density           -0.2838
  brightness_mean           1.1285
  brightness_delta          0.0194

C2:
  foreground_ratio          4.3947
  motion_magnitude_mean     4.2516
  motion_magnitude_std      3.6867
  motion_density            4.4482
  brightness_mean           0.1163
  brightness_delta         -0.1427

C3:
  foreground_ratio         -0.3128
  motion_magnitude_mean    -0.3537
  motion_magnitude_std     -0.3873
  motion_density           -0.3026
  brightness_mean          -1.1691
  brightness_delta          0.0039

C4:
  foreground_ratio         -0.2187
  motion_magnitude_mean    -0.1487
  motion_magnitude_std     -0.1592
  motion_density           -0.2237
  brightness_mean          -0.6288
  brightness_delta          0.0100
```

Diễn giải khởi đầu:

- `C2` là cụm nhỏ, motion rất cao, có thể đại diện cho chuyển động mạnh hoặc nhiễu hiếm.
- `C0` là cụm motion cao vừa, không hiếm bằng `C2`.
- `C1`, `C3`, `C4` chủ yếu là motion thấp nhưng khác nhau theo độ sáng.
- Vì dữ liệu train là normal, cụm nhỏ không tự động đồng nghĩa bất thường. Cụm nhỏ chỉ là ứng viên để kiểm tra kỹ hơn ở bước scoring.

### 11.4. Tiêu chí chấp nhận kết quả K=5

Kết quả K=5 được xem là dùng được nếu:

- WEKA chạy xong không lỗi bộ nhớ;
- không có một cụm duy nhất chiếm gần toàn bộ dữ liệu;
- centroid có thể diễn giải bằng motion và brightness;
- có ít nhất một cụm motion cao hoặc motion hiếm để phân tích;
- train/test có phân bố cụm không lệch quá bất thường;
- model được lưu lại;
- report được copy ra file text.

## 12. Thực hành 4 - Supplied test set cho KMeans K=5

### 12.1. Chạy test trong tab Cluster

Sau khi train model trên train:

1. Giữ cấu hình `SimpleKMeans K=5`.
2. Trong `Test mode`, chọn `Supplied test set`.
3. Chọn file đã chuẩn bị:

```text
ucsd_ped2_test_behavior_k5_standardized.arff
```

4. Nhấn `Start`.
5. Copy output vào:

```text
src/outputs/weka_experiments/spec_2_weka_3_8_7/reports/
  ucsd_ped2_global_behavior_simplekmeans_k5_test.txt
```

Ghi lại:

```text
cluster sizes on test
runtime
nhận xét train/test distribution shift
```

### 12.2. Gán cụm về metadata

Mục tiêu cuối là có mapping:

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

Trong Explorer, việc export cluster assignment từng dòng có thể bất tiện với dữ liệu lớn. Có ba lựa chọn:

1. Dùng `preserveInstancesOrder=True`, xuất prediction/assignment nếu môi trường WEKA đang dùng hỗ trợ.
2. Dùng WEKA CLI để xuất cluster assignment theo thứ tự instance.
3. Chuyển sang Python ở SPEC 3 để gán cụm hàng loạt bằng model tương đương.

Trong SPEC 2, mức tối thiểu bắt buộc là ghi được phân bố cụm train/test và lưu model/report. File assignment từng dòng là khuyến nghị, không phải điều kiện duy nhất để hoàn thành phần thực hành WEKA thủ công.

Nếu xuất được assignment, join theo thứ tự dòng với:

```text
src/outputs/preprocessed/ucsd_ped2/features_train.csv
src/outputs/preprocessed/ucsd_ped2/features_test.csv
```

Không được làm mất các cột truy vết `video_id`, `cube_id`, `center_frame_id`, `cell_id`.

## 13. Thực hành 5 - Baseline B spatio-behavior KMeans K=5

### 13.1. Tạo dataset

Mở lại ARFF train gốc:

```text
src/outputs/weka/ucsd_ped2_features_train.arff
```

Filter `Remove`:

```text
attributeIndices: 9-14,23-24
invertSelection: True
```

Sau đó dùng:

```text
Standardize
```

Lưu:

```text
prepared/ucsd_ped2_train_spatiobehavior_k5_standardized.arff
```

### 13.2. Chạy SimpleKMeans K=5

Cấu hình giống Baseline A:

```text
SimpleKMeans
numClusters: 5
seed: 10
maxIterations: 500
preserveInstancesOrder: True
```

Lưu:

```text
models/ucsd_ped2_global_spatiobehavior_simplekmeans_k5.model
reports/ucsd_ped2_global_spatiobehavior_simplekmeans_k5_train.txt
```

### 13.3. Kết quả tham chiếu đã có

Kết quả đã ghi trong `src/doc/Kmean.md`:

```text
Algorithm: SimpleKMeans
Dataset: UCSD Ped2 train
Feature set: 9-14,23-24
K: 5
Iterations: 19
Within cluster sum of squared errors: 39528.79068974148

Train cluster sizes:
  C0: 103507 (22%)
  C1: 104017 (22%)
  C2: 34287  ( 7%)
  C3: 120553 (25%)
  C4: 114948 (24%)

Supplied test set cluster sizes:
  C0: 71095 (19%)
  C1: 74284 (20%)
  C2: 44780 (12%)
  C3: 94962 (25%)
  C4: 91583 (24%)
```

Nhận xét cần kiểm tra:

- nếu centroid của `cell_row`, `cell_col` tách cụm rất mạnh, model đang học vị trí nhiều hơn hành vi;
- nếu cụm motion cao vẫn xuất hiện rõ, Baseline B có thể hữu ích cho phân tích không gian;
- Baseline B không thay thế per-cell clustering trong pipeline chính.

## 14. Thực hành 6 - Per-cell KMeans K=5

### 14.1. Lý do

PRD nhấn mạnh rằng hành vi bình thường phụ thuộc vị trí. Một cell ở vỉa hè và một cell ở lòng đường có thể có motion normal khác nhau. Vì vậy, per-cell KMeans là hướng phù hợp hơn cho anomaly scoring, dù WEKA Explorer chỉ nên dùng để thử trên một số cell đại diện.

### 14.2. Lọc một cell trong WEKA Explorer

Mở:

```text
src/outputs/weka/ucsd_ped2_features_train.arff
```

Trong tab `Preprocess`, dùng filter instance:

```text
weka.filters.unsupervised.instance.RemoveWithValues
```

Cấu hình:

```text
attributeIndex: 8
nominalIndices: giá trị tương ứng với cell cần giữ
invertSelection: True
```

Vì `nominalIndices` phụ thuộc thứ tự giá trị nominal trong ARFF, cần kiểm tra danh sách giá trị của `cell_id` trong giao diện WEKA trước khi apply.

Nếu thao tác này khó hoặc dễ nhầm, tạo ARFF per-cell từ CSV bằng script riêng ở SPEC sau. Với SPEC 2, chỉ cần làm thủ công cho vài cell đại diện.

### 14.3. Chuẩn bị feature sau khi lọc cell

Sau khi chỉ còn một cell, dùng `Remove` để giữ:

```text
11-14,23-24
```

Sau đó:

```text
ReplaceMissingValues nếu cần
Standardize
SimpleKMeans K=5
```

Lưu report theo mẫu:

```text
reports/ucsd_ped2_cell_08_05_behavior_simplekmeans_k5.txt
```

### 14.4. Kết quả cần ghi cho mỗi cell

```text
cell_id:
num_train_instances:
feature_set:
algorithm: SimpleKMeans
K: 5
seed:
iterations:
within_cluster_sse:
cluster_sizes:
centroid_summary:
interpretation:
usable_for_python_pipeline: yes/no
notes:
```

Ví dụ diễn giải mong muốn:

```text
cell=08_05, K=5:
  C0: motion gần 0, brightness thấp
  C1: motion thấp, brightness cao
  C2: motion trung bình, density tăng
  C3: motion rất cao, cụm nhỏ
  C4: brightness_delta thay đổi mạnh, có thể là nhiễu ánh sáng
```

Không cần các cụm của mọi cell có cùng ý nghĩa. `C2` ở cell này không nhất thiết tương đương `C2` ở cell khác.

## 15. Thực hành 7 - Tạo dữ liệu cho khai phá luật

### 15.1. Mục tiêu rule mining

Apriori trong WEKA dùng để tìm các quan hệ phổ biến trong train normal, ví dụ:

```text
cell_id=08_05 brightness=normal -> motion_density=low
cluster_id=C1 motion_density=low -> brightness=bright
cell_id=06_08 motion=slow -> cluster_id=C3
```

Các luật này không trực tiếp là nhãn bất thường. Chúng mô tả pattern normal. Khi test vi phạm một luật có support/confidence tốt, pipeline sau có thể dùng nó như tín hiệu giải thích phụ.

### 15.2. Tạo cluster_id K=5

Nếu đã có cluster assignment từ KMeans, thêm cột:

```text
cluster_id
```

Giá trị:

```text
C0
C1
C2
C3
C4
```

Nếu chưa có assignment từng dòng, vẫn chạy Apriori không có `cluster_id`, nhưng phải ghi rõ:

```text
cluster_id not available in this WEKA manual run
```

### 15.3. Chọn thuộc tính cho Apriori

Dataset rules tối thiểu:

```text
cell_id
motion_magnitude_mean
motion_density
brightness_mean
brightness_delta
cluster_id
```

Có thể thêm:

```text
foreground_ratio
motion_magnitude_std
```

nhưng chỉ thêm nếu số luật không quá vụn và vẫn diễn giải được.

Không đưa:

```text
video_id
cube_id
frame_id
start_frame_id
end_frame_id
center_frame_id
direction_hist_0..7
```

## 16. Thực hành 8 - Rời rạc hóa feature numeric

### 16.1. Vì sao cần rời rạc hóa

`Apriori` trong WEKA làm việc tốt với thuộc tính nominal. Các feature như `motion_density`, `motion_magnitude_mean`, `brightness_mean` là numeric nên cần rời rạc hóa thành các khoảng.

Mục tiêu token:

```text
motion_magnitude_mean = still | slow | medium | fast | very_fast
motion_density = low | medium | high
brightness_mean = dark | normal | bright
brightness_delta = stable | changing
cluster_id = C0 | C1 | C2 | C3 | C4
cell_id = 08_05 | ...
```

WEKA có thể đặt tên bin dạng khoảng số. Khi viết báo cáo, cần dịch các khoảng số đó thành mô tả dễ hiểu.

### 16.2. Cách làm đơn giản trong WEKA

Trong tab `Preprocess`, sau khi chỉ giữ thuộc tính rule:

```text
weka.filters.unsupervised.attribute.Discretize
```

Cấu hình khởi đầu:

```text
bins: 5
useEqualFrequency: True
```

Áp dụng cho các cột numeric:

```text
motion_magnitude_mean
motion_density
brightness_mean
brightness_delta
foreground_ratio nếu có giữ
motion_magnitude_std nếu có giữ
```

Nếu `cluster_id` đang là numeric, chuyển nó sang nominal hoặc tạo lại dưới dạng chuỗi `C0..C4`.

Lưu:

```text
prepared/ucsd_ped2_train_rules_k5_discretized.arff
```

### 16.3. Cách diễn giải bin

Sau khi `Discretize`, WEKA có thể tạo khoảng như:

```text
motion_density='(-inf-0.002]'
motion_density='(0.002-0.015]'
motion_density='(0.015-inf)'
```

Trong báo cáo, diễn giải lại:

```text
motion_density bin thấp nhất  -> density=low
motion_density bin giữa       -> density=medium
motion_density bin cao nhất   -> density=high
motion_magnitude bin cao nhất -> motion=very_fast hoặc motion=high
```

Không cần sửa trực tiếp tên bin trong ARFF nếu chỉ làm thực hành WEKA, nhưng phần `selected.md` nên có bản diễn giải dễ đọc.

## 17. Thực hành 9 - Chạy Apriori trong WEKA 3.8.7

### 17.1. Mở tab Associate

Trong WEKA Explorer:

1. Vào tab `Associate`.
2. Chọn:

```text
weka.associations.Apriori
```

3. Dùng dataset đã rời rạc hóa:

```text
ucsd_ped2_train_rules_k5_discretized.arff
```

### 17.2. Cấu hình Apriori khởi đầu

Cấu hình:

```text
numRules: 50
metricType: Confidence
minMetric: 0.6
lowerBoundMinSupport: 0.01
upperBoundMinSupport: 1.0
delta: 0.05
```

Sau lần đầu, thử các ngưỡng:

```text
support = 0.005, 0.01, 0.02
confidence = 0.6, 0.7, 0.8
numRules = 50 hoặc 100
```

Mỗi tổ hợp phải ghi rõ trong log. Không chọn luật chỉ vì confidence cao nếu support quá thấp hoặc luật vô nghĩa.

### 17.3. Lưu kết quả

Copy output vào:

```text
reports/ucsd_ped2_rules_apriori_k5.txt
```

Chọn lại 5 đến 10 luật tốt nhất và viết vào:

```text
rules/ucsd_ped2_rules_k5_selected.md
```

Mỗi luật được chọn cần có:

```text
rule_id:
antecedent:
consequent:
support:
confidence:
lift nếu WEKA output có:
interpretation:
why_useful_for_anomaly_explanation:
warning:
```

### 17.4. Tiêu chí chọn luật tốt

Ưu tiên luật:

- có `cell_id` hoặc `cluster_id`;
- liên quan đến motion, density hoặc brightness;
- có support đủ lớn để không quá hiếm;
- có confidence đủ cao để diễn giải normal pattern;
- không chỉ lặp lại quan hệ hiển nhiên;
- có thể chuyển thành câu giải thích khi test bất thường.

Loại luật:

- chỉ nói về định danh hoặc thứ tự thời gian;
- confidence cao nhưng support cực thấp;
- luật do bin quá nhỏ tạo ra;
- luật không giúp giải thích hành vi;
- luật trùng lặp nhiều lần với nội dung gần giống nhau.

## 18. Ví dụ diễn giải rule

Ví dụ nếu WEKA sinh luật:

```text
cell_id=08_05 brightness_mean='normal' ==> motion_density='low'
```

Diễn giải:

```text
Trong cell 08_05, khi độ sáng ở mức bình thường, dữ liệu train normal thường có mật độ chuyển động thấp.
Nếu test xuất hiện cell=08_05, brightness=normal nhưng motion_density=high, đây là tổ hợp đáng chú ý.
```

Ví dụ nếu có `cluster_id`:

```text
cell_id=06_08 motion_magnitude_mean='slow' ==> cluster_id=C1
```

Diễn giải:

```text
Ở cell 06_08, chuyển động chậm thường rơi vào cụm C1.
Nếu mẫu mới có motion=slow nhưng rơi xa centroid C1 hoặc bị gán sang cụm motion cao, có thể dùng rule này để giải thích lệch mẫu.
```

Ví dụ luật cần loại:

```text
cluster_id=C1 ==> brightness_mean='bright'
```

Luật này chỉ hữu ích nếu `C1` đã được diễn giải rõ. Nếu không có `cell_id` hoặc motion token đi kèm, rule có thể quá chung và khó dùng cho cảnh báo.

## 19. CLI tham khảo để tái lập ngoài Explorer

WEKA Explorer là giao diện chính của SPEC 2. CLI dưới đây dùng để tái lập hoặc chạy batch khi GUI chậm. Kiểm tra lại path `weka.jar` trước khi chạy.

```powershell
$WEKA_JAR = "C:\Program Files\Weka-3-8-7\weka.jar"
```

Tạo Baseline A:

```powershell
java -Xmx8g -cp $WEKA_JAR weka.filters.unsupervised.attribute.Remove `
  -R 11-14,23-24 -V `
  -i src/outputs/weka/ucsd_ped2_features_train.arff `
  -o src/outputs/weka_experiments/spec_2_weka_3_8_7/prepared/ucsd_ped2_train_behavior_k5.arff
```

Standardize:

```powershell
java -Xmx8g -cp $WEKA_JAR weka.filters.unsupervised.attribute.Standardize `
  -i src/outputs/weka_experiments/spec_2_weka_3_8_7/prepared/ucsd_ped2_train_behavior_k5.arff `
  -o src/outputs/weka_experiments/spec_2_weka_3_8_7/prepared/ucsd_ped2_train_behavior_k5_standardized.arff
```

Train SimpleKMeans K=5:

```powershell
java -Xmx8g -cp $WEKA_JAR weka.clusterers.SimpleKMeans `
  -N 5 -S 10 -I 500 -P `
  -t src/outputs/weka_experiments/spec_2_weka_3_8_7/prepared/ucsd_ped2_train_behavior_k5_standardized.arff `
  > src/outputs/weka_experiments/spec_2_weka_3_8_7/reports/ucsd_ped2_global_behavior_simplekmeans_k5_train.txt
```

Chạy Apriori trên dữ liệu đã rời rạc hóa:

```powershell
java -Xmx8g -cp $WEKA_JAR weka.associations.Apriori `
  -N 50 -T 0 -C 0.6 -M 0.01 `
  -t src/outputs/weka_experiments/spec_2_weka_3_8_7/prepared/ucsd_ped2_train_rules_k5_discretized.arff `
  > src/outputs/weka_experiments/spec_2_weka_3_8_7/reports/ucsd_ped2_rules_apriori_k5.txt
```

Nếu option CLI khác với GUI trong máy đang dùng, ưu tiên cấu hình hiển thị trong WEKA 3.8.7 và ghi lại option thực tế vào log.

## 20. Thí nghiệm bắt buộc của SPEC 2

### Experiment 1 - Global behavior KMeans K=5

Input:

```text
src/outputs/weka/ucsd_ped2_features_train.arff
```

Feature:

```text
11-14,23-24
```

Filter:

```text
Remove
Standardize
```

Algorithm:

```text
SimpleKMeans
K=5
seed=10
maxIterations=500
```

Kết quả cần có:

- report train;
- model `.model`;
- cluster sizes;
- centroid;
- diễn giải 5 cụm;
- nhận xét cụm motion cao/hiếm.

### Experiment 2 - Supplied test set cho global behavior K=5

Input:

```text
src/outputs/weka/ucsd_ped2_features_test.arff
```

Yêu cầu:

- áp dụng cùng feature set;
- chạy supplied test set;
- ghi phân bố cụm test;
- so sánh với train;
- nếu xuất được assignment thì join với metadata CSV.

### Experiment 3 - Global spatio-behavior KMeans K=5

Feature:

```text
9-14,23-24
```

Mục tiêu:

- kiểm tra ảnh hưởng của `cell_row`, `cell_col`;
- xác định model có bị tách theo vị trí quá mạnh không;
- so sánh với Baseline A.

### Experiment 4 - Selected per-cell KMeans K=5

Cell tối thiểu:

```text
04_08
06_08
08_05
09_06
```

Mục tiêu:

- xem mỗi cell có đủ mẫu để chia 5 cụm không;
- đọc centroid theo cell;
- xác định per-cell KMeans có phù hợp để chuyển sang Python không.

### Experiment 5 - Apriori trên dữ liệu đã rời rạc hóa

Input:

```text
ucsd_ped2 train normal
feature rời rạc hóa
cluster_id C0..C4 nếu đã có
```

Yêu cầu:

- chạy ít nhất một cấu hình Apriori;
- sinh tối thiểu 20 luật thô nếu dữ liệu cho phép;
- chọn 5 đến 10 luật dễ giải thích;
- ghi rõ support/confidence;
- nhận xét luật nào có thể dùng làm reason trong anomaly alert.

## 21. Mẫu log thực nghiệm

```markdown
## ucsd_ped2_global_behavior_simplekmeans_k5

- Date:
- WEKA version: 3.8.7
- Input: src/outputs/weka/ucsd_ped2_features_train.arff
- Instances: 477312
- Original attributes: 24
- Kept attributes: 11-14,23-24
- Filters:
  - Remove(attributeIndices=11-14,23-24, invertSelection=True)
  - Standardize
- Algorithm: SimpleKMeans
- Parameters:
  - numClusters=5
  - seed=10
  - maxIterations=500
  - preserveInstancesOrder=True
- Runtime:
- Within cluster SSE:
- Cluster sizes:
  - C0:
  - C1:
  - C2:
  - C3:
  - C4:
- Centroid interpretation:
  - C0:
  - C1:
  - C2:
  - C3:
  - C4:
- Accepted for next step: yes/no
- Reason:
- Output files:
```

Mẫu log luật:

```markdown
## ucsd_ped2_rules_discretize5_apriori_k5_s001_c06

- Date:
- WEKA version: 3.8.7
- Input:
- Attributes:
- Discretize:
  - bins=5
  - useEqualFrequency=True
- Apriori:
  - lowerBoundMinSupport=0.01
  - minMetric=0.6
  - metricType=Confidence
  - numRules=50
- Raw rules count:
- Selected rules:
  1. rule:
     support:
     confidence:
     interpretation:
     use for anomaly explanation:
- Rejected rule patterns:
- Notes:
```

## 22. Tiêu chí đánh giá kết quả

### 22.1. KMeans K=5 đạt yêu cầu khi

- train UCSD Ped2 chạy xong trên WEKA 3.8.7;
- K được đặt đúng bằng `5`;
- có 5 centroid được ghi lại;
- cluster size không sụp vào một cụm duy nhất;
- centroid có thể diễn giải bằng motion/brightness;
- phân bố test không quá lệch so với train mà không có giải thích;
- model và report được lưu;
- log có đủ filter, feature, seed, runtime và nhận xét.

### 22.2. Per-cell KMeans đạt yêu cầu khi

- chạy được tối thiểu 4 cell đại diện;
- mỗi cell có report K=5 riêng;
- có nhận xét cụm nào là motion thấp, motion cao, brightness khác biệt hoặc nhiễu;
- ghi rõ cell nào không phù hợp với K=5 nếu cụm quá nhỏ hoặc centroid khó diễn giải.

### 22.3. Apriori đạt yêu cầu khi

- dữ liệu đầu vào là nominal hoặc đã discretize;
- có ít nhất một lần chạy Apriori thành công;
- chọn được 5 đến 10 luật có thể diễn giải;
- luật được ghi với support/confidence;
- có nhận xét luật dùng được như reason hay chỉ dùng tham khảo;
- không xem luật là quyết định bất thường độc lập.

## 23. Rủi ro và giảm thiểu

### 23.1. WEKA thiếu bộ nhớ

Rủi ro: ARFF lớn làm Explorer chậm hoặc crash.

Giảm thiểu:

- chạy UCSD Ped2 trước;
- mở WEKA bằng `-Xmx8g`;
- không mở Avenue full ngay;
- tạo sample ARFF nếu cần;
- dùng CLI hoặc Python khi chạy batch.

### 23.2. Standardize trên train/test trong Explorer không dùng chung thống kê

Rủi ro: thao tác thủ công có thể chuẩn hóa test bằng thống kê test.

Giảm thiểu:

- ghi rõ đây là thực nghiệm WEKA;
- dùng kết quả để phân tích, không dùng làm production;
- ở SPEC 3, dùng scaler fit trên train rồi transform test bằng Python.

### 23.3. K=5 không phù hợp với mọi cell

Rủi ro: cell ít chuyển động hoặc rất yên tĩnh có thể không chia được 5 cụm có ý nghĩa.

Giảm thiểu:

- vẫn thực hành K=5 để thống nhất bài làm;
- ghi cell nào có cụm quá nhỏ;
- ở pipeline sau, thêm `min_samples_per_cell`, threshold floor hoặc fallback.

### 23.4. Cụm nhỏ không đồng nghĩa bất thường

Rủi ro: train normal vẫn có cụm motion cao hoặc hiếm, nhưng đó có thể là normal pattern ít gặp.

Giảm thiểu:

- không gán nhãn bất thường chỉ dựa vào cluster size;
- dùng distance tới centroid và percentile threshold ở SPEC sau;
- kết hợp smoothing, rare token và rule violation.

### 23.5. Apriori sinh luật quá vụn

Rủi ro: nhiều `cell_id` và nhiều bin làm support thấp.

Giảm thiểu:

- bắt đầu với `minSupport=0.01`;
- giảm số thuộc tính nếu luật quá nhiều;
- dùng 3 hoặc 5 bin, không rời rạc quá mịn;
- chọn luật có ý nghĩa giải thích, không chọn máy móc theo confidence.

### 23.6. Luật chỉ phản ánh độ sáng hoặc vị trí

Rủi ro: rule mining có thể sinh luật đúng nhưng không hữu ích cho anomaly.

Giảm thiểu:

- ưu tiên luật có motion/density/cluster;
- loại luật chỉ mô tả brightness nếu không liên quan hành vi;
- ghi rõ luật dùng để giải thích phụ, không thay score chính.

## 24. Checklist thực hành

- [ ] Xác nhận WEKA version là `3.8.7`.
- [ ] Mở WEKA với heap đủ lớn.
- [ ] Mở `ucsd_ped2_features_train.arff`.
- [ ] Kiểm tra số instances và attributes.
- [ ] Tạo Baseline A bằng `Remove` giữ `11-14,23-24`.
- [ ] Dùng `Standardize` cho Baseline A.
- [ ] Lưu `ucsd_ped2_train_behavior_k5_standardized.arff`.
- [ ] Chạy `SimpleKMeans K=5` trên Baseline A.
- [ ] Lưu model K=5.
- [ ] Lưu report train K=5.
- [ ] Diễn giải 5 centroid.
- [ ] Mở `ucsd_ped2_features_test.arff`.
- [ ] Áp dụng cùng feature set cho test.
- [ ] Chạy supplied test set và ghi phân bố cụm.
- [ ] Tạo Baseline B giữ `9-14,23-24`.
- [ ] Chạy `SimpleKMeans K=5` cho Baseline B.
- [ ] So sánh Baseline A và Baseline B.
- [ ] Chạy per-cell KMeans K=5 cho ít nhất 4 cell.
- [ ] Tạo dataset rule có `cell_id`, motion/density/brightness và `cluster_id` nếu có.
- [ ] Rời rạc hóa bằng `Discretize`.
- [ ] Chạy Apriori.
- [ ] Chọn 5 đến 10 luật dễ giải thích.
- [ ] Ghi toàn bộ kết quả vào `spec_2_log.md`.
- [ ] Cập nhật `src/doc/spec_2_processed.md`.

## 25. Tiêu chí hoàn thành SPEC 2

SPEC 2 được xem là hoàn thành khi:

- có bản thực hành WEKA 3.8.7 rõ ràng cho UCSD Ped2;
- phân cụm chính dùng `SimpleKMeans` với `K=5`;
- có report centroid và cluster size của global behavior K=5;
- có phân bố cụm trên supplied test set;
- có ít nhất một phân tích spatio-behavior K=5;
- có ít nhất bốn thử nghiệm per-cell K=5 hoặc ghi rõ lý do không thể thao tác trong WEKA;
- có ít nhất một lần chạy Apriori trên dữ liệu đã rời rạc hóa;
- có 5 đến 10 luật được chọn và diễn giải;
- có log thực nghiệm đủ để tái hiện;
- có nhận xét cấu hình nào nên chuyển sang Python ở SPEC 3 và SPEC 5.

## 26. Hướng chuyển sang các spec sau

Sau SPEC 2:

- SPEC 3 dùng Python để train per-cell MiniBatchKMeans với `clusters_per_cell=5`;
- SPEC 3 tính distance tới centroid gần nhất và threshold theo percentile train;
- SPEC 5 tạo token `cluster=C0..C4`, rời rạc hóa feature và tính rare token/rule violation score;
- SPEC 4 và SPEC 6 dùng score để vẽ heatmap và đánh giá định lượng;
- WEKA tiếp tục đóng vai trò công cụ phân tích, không phải runtime production.
