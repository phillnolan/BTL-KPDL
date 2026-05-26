# SPEC 2 Processed - Tracker thực hành WEKA 3.8.7 K=5

Original spec path: `src/doc/spec_2.md`

Date/time prepared: 2026-05-27 Asia/Bangkok

## 1. Mục đích file này

File này là bảng theo dõi thực hành cho `src/doc/spec_2.md`.

Các mục thực hành WEKA được cố ý để trống bằng checkbox `[ ]` và các trường chưa điền để người thực hành tự đánh dấu sau khi chạy trên WEKA 3.8.7. Không có mục thực hành nào bên dưới được đánh dấu hoàn thành sẵn.

## 2. Việc đã chuẩn bị bởi Codex

- [x] Đọc PRD trước khi cập nhật SPEC 2.
- [x] Đọc `repomix-output.xml` để nắm cấu trúc repo.
- [x] Đọc `src/doc/spec_2.md`.
- [x] Tạo tracker thực hành trống cho các phần chưa chạy của SPEC 2.

## 3. Trạng thái tổng quan SPEC 2

- [ ] Xác nhận WEKA version là `3.8.7`.
- [ ] Mở WEKA với heap đủ lớn.
- [ ] Tạo thư mục output thực hành `src/outputs/weka_experiments/spec_2_weka_3_8_7/`.
- [ ] Tạo hoặc mở `spec_2_log.md`.
- [ ] Hoàn thành Experiment 1 - Global behavior KMeans K=5.
- [ ] Hoàn thành Experiment 2 - Supplied test set cho global behavior K=5.
- [ ] Hoàn thành Experiment 3 - Global spatio-behavior KMeans K=5.
- [ ] Hoàn thành Experiment 4 - Selected per-cell KMeans K=5.
- [ ] Hoàn thành Experiment 5 - Apriori trên dữ liệu đã rời rạc hóa.
- [ ] Chọn 5 đến 10 luật dễ giải thích.
- [ ] Ghi nhận xét cấu hình nào nên chuyển sang Python ở SPEC 3/SPEC 5.

## 4. Output artifact cần tự đánh dấu

### 4.1. Thư mục

- [ ] `src/outputs/weka_experiments/spec_2_weka_3_8_7/`
- [ ] `src/outputs/weka_experiments/spec_2_weka_3_8_7/prepared/`
- [ ] `src/outputs/weka_experiments/spec_2_weka_3_8_7/models/`
- [ ] `src/outputs/weka_experiments/spec_2_weka_3_8_7/reports/`
- [ ] `src/outputs/weka_experiments/spec_2_weka_3_8_7/assignments/`
- [ ] `src/outputs/weka_experiments/spec_2_weka_3_8_7/rules/`

### 4.2. Prepared ARFF

- [ ] `prepared/ucsd_ped2_train_behavior_k5_standardized.arff`
- [ ] `prepared/ucsd_ped2_test_behavior_k5_standardized.arff`
- [ ] `prepared/ucsd_ped2_train_spatiobehavior_k5_standardized.arff`
- [ ] `prepared/ucsd_ped2_train_rules_k5_discretized.arff`

### 4.3. Models

- [ ] `models/ucsd_ped2_global_behavior_simplekmeans_k5.model`
- [ ] `models/ucsd_ped2_global_spatiobehavior_simplekmeans_k5.model`
- [ ] `models/ucsd_ped2_cell_04_08_behavior_simplekmeans_k5.model`
- [ ] `models/ucsd_ped2_cell_06_08_behavior_simplekmeans_k5.model`
- [ ] `models/ucsd_ped2_cell_08_05_behavior_simplekmeans_k5.model`
- [ ] `models/ucsd_ped2_cell_09_06_behavior_simplekmeans_k5.model`

### 4.4. Reports

- [ ] `reports/ucsd_ped2_global_behavior_simplekmeans_k5_train.txt`
- [ ] `reports/ucsd_ped2_global_behavior_simplekmeans_k5_test.txt`
- [ ] `reports/ucsd_ped2_global_spatiobehavior_simplekmeans_k5_train.txt`
- [ ] `reports/ucsd_ped2_cell_04_08_behavior_simplekmeans_k5.txt`
- [ ] `reports/ucsd_ped2_cell_06_08_behavior_simplekmeans_k5.txt`
- [ ] `reports/ucsd_ped2_cell_08_05_behavior_simplekmeans_k5.txt`
- [ ] `reports/ucsd_ped2_cell_09_06_behavior_simplekmeans_k5.txt`
- [ ] `reports/ucsd_ped2_rules_apriori_k5.txt`

### 4.5. Assignments và rules

- [ ] `assignments/ucsd_ped2_train_behavior_k5_clusters.csv`
- [ ] `assignments/ucsd_ped2_test_behavior_k5_clusters.csv`
- [ ] `rules/ucsd_ped2_rules_k5_selected.md`

## 5. Thực hành 1 - Mở và kiểm tra ARFF

### 5.1. Train ARFF

- [ ] Mở `src/outputs/weka/ucsd_ped2_features_train.arff`.
- [ ] Kiểm tra số instances.
- [ ] Kiểm tra số attributes.
- [ ] Kiểm tra `cell_id` là nominal.
- [ ] Kiểm tra các feature chính là numeric.
- [ ] Kiểm tra missing value bất thường.

Ghi nhận:

```text
WEKA version:
Input:
instances:
attributes:
cell_id type:
missing summary:
notes:
```

### 5.2. Test ARFF

- [ ] Mở `src/outputs/weka/ucsd_ped2_features_test.arff`.
- [ ] Kiểm tra số instances.
- [ ] Kiểm tra số attributes.
- [ ] Kiểm tra schema khớp train.

Ghi nhận:

```text
Input:
instances:
attributes:
schema matches train: yes/no
notes:
```

## 6. Thực hành 2 - Tạo Baseline A behavior-only

- [ ] Dùng `Remove` giữ `11-14,23-24` cho train.
- [ ] Dùng `Standardize` cho train.
- [ ] Lưu `ucsd_ped2_train_behavior_k5_standardized.arff`.
- [ ] Dùng cùng feature set cho test.
- [ ] Dùng `Standardize` cho test theo quy trình thực hành Explorer.
- [ ] Lưu `ucsd_ped2_test_behavior_k5_standardized.arff`.

Ghi nhận train:

```text
Remove attributeIndices:
invertSelection:
attributes after filter:
Standardize applied: yes/no
output file:
notes:
```

Ghi nhận test:

```text
Remove attributeIndices:
invertSelection:
attributes after filter:
Standardize applied: yes/no
output file:
notes:
```

## 7. Experiment 1 - Global behavior KMeans K=5

Status:

- [ ] Not started
- [ ] Done
- [ ] Skipped
- [ ] Blocked

Checklist:

- [ ] Chọn `weka.clusterers.SimpleKMeans`.
- [ ] Đặt `numClusters=5`.
- [ ] Đặt `seed=10`.
- [ ] Đặt `maxIterations=500`.
- [ ] Bật hoặc ghi nhận `preserveInstancesOrder=True`.
- [ ] Chạy `Use training set`.
- [ ] Lưu model.
- [ ] Lưu report train.
- [ ] Ghi centroid.
- [ ] Diễn giải 5 cụm.

Ghi nhận:

```text
experiment_id: ucsd_ped2_global_behavior_simplekmeans_k5
date:
WEKA version:
input file:
feature set:
filters:
algorithm:
K:
seed:
maxIterations:
preserveInstancesOrder:
runtime:
iterations:
within cluster SSE:
model file:
report file:
```

Cluster sizes:

```text
C0:
C1:
C2:
C3:
C4:
```

Centroid summary:

```text
C0:
C1:
C2:
C3:
C4:
```

Diễn giải:

```text
C0:
C1:
C2:
C3:
C4:
```

Nhận xét:

```text
cluster motion cao:
cluster motion thấp:
cluster brightness khác biệt:
cụm nhỏ cần chú ý:
accepted for next step: yes/no
reason:
```

## 8. Experiment 2 - Supplied test set cho global behavior K=5

Status:

- [ ] Not started
- [ ] Done
- [ ] Skipped
- [ ] Blocked

Checklist:

- [ ] Mở hoặc chọn test set đã chuẩn bị.
- [ ] Dùng supplied test set cho model K=5.
- [ ] Ghi phân bố cụm test.
- [ ] So sánh phân bố train/test.
- [ ] Lưu report test.
- [ ] Xuất assignment nếu môi trường WEKA hỗ trợ.
- [ ] Join assignment với metadata CSV nếu xuất được.

Ghi nhận:

```text
experiment_id: ucsd_ped2_global_behavior_simplekmeans_k5_test
date:
train model:
test input:
report file:
assignment file:
runtime:
```

Test cluster sizes:

```text
C0:
C1:
C2:
C3:
C4:
```

So sánh train/test:

```text
cluster tăng rõ trên test:
cluster giảm rõ trên test:
nhận xét distribution shift:
assignment exported: yes/no
notes:
```

## 9. Experiment 3 - Global spatio-behavior KMeans K=5

Status:

- [ ] Not started
- [ ] Done
- [ ] Skipped
- [ ] Blocked

Checklist:

- [ ] Tạo Baseline B bằng `Remove` giữ `9-14,23-24`.
- [ ] Dùng `Standardize`.
- [ ] Chạy `SimpleKMeans K=5`.
- [ ] Lưu model.
- [ ] Lưu report.
- [ ] Đọc centroid của `cell_row`, `cell_col`.
- [ ] So sánh với Baseline A.

Ghi nhận:

```text
experiment_id: ucsd_ped2_global_spatiobehavior_simplekmeans_k5
date:
input file:
feature set:
filters:
algorithm:
K:
seed:
maxIterations:
runtime:
iterations:
within cluster SSE:
model file:
report file:
```

Cluster sizes:

```text
C0:
C1:
C2:
C3:
C4:
```

Nhận xét:

```text
cell_row/cell_col có chi phối cụm không:
motion feature còn tạo cụm rõ không:
so sánh với Baseline A:
accepted for next step: yes/no
reason:
```

## 10. Experiment 4 - Selected per-cell KMeans K=5

Status:

- [ ] Not started
- [ ] Done
- [ ] Skipped
- [ ] Blocked

Checklist chung:

- [ ] Chạy cell `04_08`.
- [ ] Chạy cell `06_08`.
- [ ] Chạy cell `08_05`.
- [ ] Chạy cell `09_06`.
- [ ] Với mỗi cell, lọc đúng `cell_id`.
- [ ] Với mỗi cell, giữ feature `11-14,23-24`.
- [ ] Với mỗi cell, dùng `Standardize`.
- [ ] Với mỗi cell, chạy `SimpleKMeans K=5`.
- [ ] Với mỗi cell, lưu report.
- [ ] Ghi cell nào không phù hợp với K=5 nếu có.

### 10.1. Cell 04_08

- [ ] Done
- [ ] Skipped
- [ ] Blocked

```text
cell_id: 04_08
num_train_instances:
feature_set:
algorithm:
K:
seed:
iterations:
within_cluster_sse:
model file:
report file:
cluster_sizes:
centroid_summary:
interpretation:
usable_for_python_pipeline: yes/no
notes:
```

### 10.2. Cell 06_08

- [ ] Done
- [ ] Skipped
- [ ] Blocked

```text
cell_id: 06_08
num_train_instances:
feature_set:
algorithm:
K:
seed:
iterations:
within_cluster_sse:
model file:
report file:
cluster_sizes:
centroid_summary:
interpretation:
usable_for_python_pipeline: yes/no
notes:
```

### 10.3. Cell 08_05

- [ ] Done
- [ ] Skipped
- [ ] Blocked

```text
cell_id: 08_05
num_train_instances:
feature_set:
algorithm:
K:
seed:
iterations:
within_cluster_sse:
model file:
report file:
cluster_sizes:
centroid_summary:
interpretation:
usable_for_python_pipeline: yes/no
notes:
```

### 10.4. Cell 09_06

- [ ] Done
- [ ] Skipped
- [ ] Blocked

```text
cell_id: 09_06
num_train_instances:
feature_set:
algorithm:
K:
seed:
iterations:
within_cluster_sse:
model file:
report file:
cluster_sizes:
centroid_summary:
interpretation:
usable_for_python_pipeline: yes/no
notes:
```

## 11. Thực hành 7 - Tạo dữ liệu cho khai phá luật

Status:

- [ ] Not started
- [ ] Done
- [ ] Skipped
- [ ] Blocked

Checklist:

- [ ] Xác định có `cluster_id` từ KMeans K=5 hay chưa.
- [ ] Nếu có, thêm `cluster_id=C0..C4` vào dữ liệu rule.
- [ ] Nếu chưa có, ghi rõ Apriori chạy không có `cluster_id`.
- [ ] Giữ `cell_id`.
- [ ] Giữ `motion_magnitude_mean`.
- [ ] Giữ `motion_density`.
- [ ] Giữ `brightness_mean`.
- [ ] Giữ `brightness_delta`.
- [ ] Bỏ metadata không dùng cho luật.

Ghi nhận:

```text
input source:
cluster_id available: yes/no
attributes kept:
attributes removed:
output before discretize:
notes:
```

## 12. Thực hành 8 - Rời rạc hóa feature numeric

Status:

- [ ] Not started
- [ ] Done
- [ ] Skipped
- [ ] Blocked

Checklist:

- [ ] Dùng `weka.filters.unsupervised.attribute.Discretize`.
- [ ] Đặt `bins=5`.
- [ ] Đặt `useEqualFrequency=True`.
- [ ] Kiểm tra các cột numeric đã thành nominal.
- [ ] Lưu `prepared/ucsd_ped2_train_rules_k5_discretized.arff`.
- [ ] Ghi cách diễn giải bin thành token dễ hiểu.

Ghi nhận:

```text
input:
Discretize bins:
useEqualFrequency:
numeric attributes discretized:
output file:
bin interpretation:
notes:
```

## 13. Experiment 5 - Apriori trên dữ liệu đã rời rạc hóa

Status:

- [ ] Not started
- [ ] Done
- [ ] Skipped
- [ ] Blocked

Checklist:

- [ ] Mở tab `Associate`.
- [ ] Chọn `weka.associations.Apriori`.
- [ ] Dùng dữ liệu đã discretize.
- [ ] Chạy cấu hình support/confidence đầu tiên.
- [ ] Lưu output thô.
- [ ] Thử ngưỡng khác nếu luật quá ít hoặc quá nhiều.
- [ ] Chọn 5 đến 10 luật tốt nhất.
- [ ] Ghi support/confidence/lift nếu có.
- [ ] Diễn giải luật bằng câu dễ hiểu.
- [ ] Ghi luật nào dùng được cho anomaly reason.

Ghi nhận cấu hình chính:

```text
experiment_id: ucsd_ped2_rules_discretize5_apriori_k5_s001_c06
date:
input file:
attributes:
numRules:
metricType:
minMetric:
lowerBoundMinSupport:
upperBoundMinSupport:
delta:
runtime:
raw rules count:
report file:
selected rules file:
```

Selected rules:

```text
Rule 1:
  antecedent:
  consequent:
  support:
  confidence:
  lift:
  interpretation:
  use_for_anomaly_reason:

Rule 2:
  antecedent:
  consequent:
  support:
  confidence:
  lift:
  interpretation:
  use_for_anomaly_reason:

Rule 3:
  antecedent:
  consequent:
  support:
  confidence:
  lift:
  interpretation:
  use_for_anomaly_reason:

Rule 4:
  antecedent:
  consequent:
  support:
  confidence:
  lift:
  interpretation:
  use_for_anomaly_reason:

Rule 5:
  antecedent:
  consequent:
  support:
  confidence:
  lift:
  interpretation:
  use_for_anomaly_reason:
```

Nếu chọn thêm luật:

```text
Rule 6:
Rule 7:
Rule 8:
Rule 9:
Rule 10:
```

Rejected rule patterns:

```text

```

Notes:

```text

```

## 14. Tiêu chí hoàn thành để tự tick

- [ ] Có bản thực hành WEKA 3.8.7 rõ ràng cho UCSD Ped2.
- [ ] Phân cụm chính dùng `SimpleKMeans` với `K=5`.
- [ ] Có report centroid và cluster size của global behavior K=5.
- [ ] Có phân bố cụm trên supplied test set.
- [ ] Có ít nhất một phân tích spatio-behavior K=5.
- [ ] Có ít nhất bốn thử nghiệm per-cell K=5 hoặc ghi rõ lý do không thể thao tác.
- [ ] Có ít nhất một lần chạy Apriori trên dữ liệu đã rời rạc hóa.
- [ ] Có 5 đến 10 luật được chọn và diễn giải.
- [ ] Có log thực nghiệm đủ để tái hiện.
- [ ] Có nhận xét cấu hình nào nên chuyển sang Python ở SPEC 3 và SPEC 5.

## 15. Verification do người thực hành điền

```text
WEKA version verified:
Date completed:
Commands or GUI actions verified:
Files manually checked:
Known issues:
Final notes:
```

## 16. Lượt cập nhật tracker

- [x] 2026-05-27: Codex tạo tracker trống cho các phần thực hành chưa hoàn thành của SPEC 2.
- [x] 2026-05-27: Codex kiểm tra `git diff --check -- src/doc/spec_2_processed.md`.
- [x] 2026-05-27: Codex chạy `repomix.cmd` từ repo root để refresh `repomix-output.xml`.
- [ ] Người thực hành cập nhật các checkbox và trường ghi nhận sau khi chạy WEKA.
