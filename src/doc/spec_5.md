# SPEC 5 - Tokenization, rare token score và association rules trong Python

## 1. Mục tiêu

SPEC 5 mô tả kế hoạch triển khai lớp token hóa và khai phá luật kết hợp trong Python sau khi SPEC 3 đã có anomaly score baseline và SPEC 4 đã có heatmap overlay.

Mục tiêu chính:

- biến feature liên tục và kết quả cụm `nearest_cluster` thành token dễ diễn giải;
- học phân phối token/itemset từ dữ liệu train normal;
- khai phá association rules từ train normal;
- tính `rare_token_score` và `rule_violation_score` cho từng cell/cube test;
- mở rộng công thức anomaly score theo PRD:

```text
score = 0.65 * cluster_distance_score
      + 0.20 * temporal_change_score
      + 0.10 * rare_token_score
      + 0.05 * rule_violation_score
```

SPEC 5 không thay thế cluster/distance baseline của SPEC 3. Token/rule chỉ là tín hiệu phụ để tăng khả năng giải thích và hỗ trợ phát hiện tổ hợp hành vi hiếm.

## 2. Liên hệ với PRD và các spec trước

Theo PRD, hệ thống có hai trụ cột:

- phân cụm hành vi-không gian-thời gian;
- khai phá luật kết hợp để giải thích quan hệ giữa vùng, chuyển động, mật độ, độ sáng và cụm hành vi.

SPEC 1 đã sinh feature CSV/ARFF. SPEC 2 mô tả thực hành WEKA với KMeans K=5 và Apriori. SPEC 3 đã triển khai Python per-cell KMeans K=5, sinh `cell_scores.csv`, `frame_scores.csv` và `alerts.json`. SPEC 4 đã hiển thị score bằng heatmap overlay.

SPEC 5 chuyển phần token/rule từ ý tưởng và thực hành thủ công sang pipeline Python chạy lại được bằng config.

Ghi chú trạng thái repo hiện tại:

- `src/doc/spec_5.md` chưa tồn tại trước tài liệu này.
- SPEC 2 processed hiện là tracker thực hành trống, chưa có output WEKA hoàn chỉnh.
- SPEC 5 vẫn có thể triển khai vì cluster assignment có thể lấy trực tiếp từ model Python của SPEC 3.

## 3. Trạng thái đầu vào hiện có

Dataset ưu tiên:

```text
ucsd_ped2
```

Artifact đầu vào chính:

```text
src/outputs/preprocessed/ucsd_ped2/
  features_train.csv
  features_test.csv
  grid.json
  preprocess_stats.json

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

Feature baseline đang dùng:

```text
foreground_ratio
motion_magnitude_mean
motion_magnitude_std
motion_density
brightness_mean
brightness_delta
```

Các cột `direction_hist_0..7` chưa dùng trong SPEC 5 MVP vì pipeline tiền xử lý hiện dùng `frame_diff`, direction histogram đang không mang thông tin hướng đáng tin cậy. Hướng chuyển động thật nên để SPEC sau cùng optical flow/Farneback.

## 4. Phạm vi

### 4.1. Nằm trong phạm vi

- Đọc feature train/test và model SPEC 3.
- Gán `cluster_id=C0..C4` cho train bằng model/scaler đã lưu.
- Dùng `nearest_cluster` từ scoring test hoặc tự gán khi cần.
- Fit bin/token thresholds từ train normal.
- Token hóa motion, density, brightness, brightness delta, cell và cluster.
- Tạo transaction cho từng feature row.
- Đếm support của item và itemset trong train normal.
- Sinh association rules giới hạn kích thước để chạy được trên UCSD Ped2.
- Tính rare-token score và rule-violation score cho test.
- Ghi output token/rule artifact.
- Mở rộng scoring để tạo `cell_scores.csv` có thêm token/rule columns khi `rules.enabled=true`.
- Mở rộng `alerts.json` reason bằng token/rule reason.
- Bảo toàn khả năng chạy SPEC 3 cũ khi rules disabled.

### 4.2. Ngoài phạm vi

- Không triển khai FP-Growth tối ưu cho dữ liệu rất lớn trong MVP đầu tiên.
- Không dùng WEKA làm runtime production.
- Không dùng direction token thật khi chưa có optical flow.
- Không đánh giá ROC-AUC/EER, phần đó để SPEC 6.
- Không làm dashboard.
- Không thay đổi heatmap rendering của SPEC 4, chỉ bảo đảm schema mới không làm hỏng visualization.

## 5. Nguyên tắc thiết kế

- Token/rule là tín hiệu phụ, không quyết định toàn bộ alert.
- Binning phải học từ train normal, sau đó áp dụng nguyên trạng cho test.
- Không tạo token quá mịn khiến luật bị vụn.
- Các rule phải có support/confidence/lift đủ rõ và có thể diễn giải.
- Nếu rule artifact thiếu hoặc disabled, pipeline scoring phải quay về công thức SPEC 3.
- Output phải truy vết được về `dataset`, `video_id`, `cube_id`, `center_frame_id`, `cell_id`.
- Giữ dependency nhẹ. MVP nên dùng Apriori giới hạn tự triển khai thay vì thêm dependency nặng nếu không cần.

## 6. Kiến trúc module đề xuất

Bổ sung các file:

```text
src/kpdl_anomaly/
  tokenization.py
  association.py
  rule_model.py
  rule_scoring.py

src/rules.py
```

Vai trò:

```text
tokenization.py:
  fit ngưỡng rời rạc hóa từ train
  chuyển feature row + cluster_id thành token
  tạo transaction ổn định

association.py:
  đếm support itemset
  sinh association rules dạng bounded Apriori
  lọc rule theo support/confidence/lift

rule_model.py:
  train token/rule model từ features_train.csv và model SPEC 3
  lưu token bins, itemset support, rules, manifest

rule_scoring.py:
  load rule artifact
  tính rare_token_score
  tính rule_violation_score
  sinh reason text cho token/rule

src/rules.py:
  CLI entrypoint cho train token/rule artifact
```

Các file cần cập nhật:

```text
src/kpdl_anomaly/config.py
src/kpdl_anomaly/schema.py
src/kpdl_anomaly/scoring.py
src/kpdl_anomaly/alerts.py
src/kpdl_anomaly/test.py
src/configs/ucsd_ped2.yaml
src/configs/ucsd_ped1.yaml
src/configs/avenue.yaml
src/requirements.txt nếu cần
```

## 7. Cấu hình đề xuất

Bổ sung mục `rules` vào YAML dataset:

```yaml
rules:
  enabled: true
  output_root: "src/outputs/rules"
  model_dir: null
  algorithm: "bounded_apriori"
  min_support: 0.01
  min_confidence: 0.60
  min_lift: 1.05
  max_itemset_size: 3
  max_rules: 200
  include_cell_token: true
  include_cluster_token: true
  include_brightness_token: true
  include_direction_token: false
  rare_itemset_size: 3
  rare_support_floor: 0.001
  rare_score_cap: 1.0
```

Cập nhật `scoring` khi rules enabled:

```yaml
scoring:
  cluster_weight: 0.65
  temporal_weight: 0.20
  rare_token_weight: 0.10
  rule_weight: 0.05
```

Khi `rules.enabled=false` hoặc không có rule artifact, giữ công thức SPEC 3:

```yaml
scoring:
  cluster_weight: 0.80
  temporal_weight: 0.20
```

## 8. Token schema MVP

Mỗi feature row test/train sinh một transaction gồm các token:

```text
cell=08_05
cell_row=08
cell_col=05
motion=still|slow|medium|fast|very_fast
density=low|medium|high
brightness=dark|normal|bright
brightness_delta=stable|changing
cluster=C0|C1|C2|C3|C4
```

Token có thể thêm sau:

```text
foreground=low|medium|high
motion_std=low|medium|high
time_bucket=morning|day|evening|night
direction=...
```

Không đưa các token sau vào MVP:

```text
video_id
cube_id
start_frame_id
end_frame_id
center_frame_id
```

Lý do: các token định danh/thứ tự dễ tạo luật giả, không mô tả hành vi bình thường tổng quát.

## 9. Fit bin từ train normal

### 9.1. Motion magnitude

Dùng quantile train của `motion_magnitude_mean`:

```text
still      <= q20
slow       <= q40
medium     <= q60
fast       <= q80
very_fast  >  q80
```

Nếu phân phối quá nhiều zero, dùng fallback:

```text
still nếu motion_magnitude_mean <= epsilon
slow/medium/fast/very_fast theo quantile của phần > epsilon
```

### 9.2. Motion density

Dùng 3 bin:

```text
low     <= q33
medium  <= q66
high    >  q66
```

### 9.3. Brightness

Dùng 3 bin:

```text
dark    <= q33
normal  <= q66
bright  >  q66
```

### 9.4. Brightness delta

Dùng absolute value:

```text
stable    nếu abs(brightness_delta) <= q80_abs_delta
changing  nếu abs(brightness_delta) > q80_abs_delta
```

### 9.5. Scope của bin

MVP fit bin theo global train normal để token dễ ổn định và ít vụn. Sau đó có thể mở rộng:

- bin theo từng dataset;
- bin theo cell;
- bin theo zone semantic nếu có.

## 10. Train token/rule model

### Bước 1 - Load artifact

Đọc:

```text
features_train.csv
model_manifest.json
cell_models.joblib
cell_scalers.joblib
thresholds.json
```

Kiểm tra:

- dataset khớp config;
- feature columns khớp model;
- model KMeans có đủ cell;
- train feature có `split=train`.

### Bước 2 - Gán cluster cho train rows

Với mỗi train row:

1. lấy vector feature giống SPEC 3;
2. dùng scaler/model theo `cell_id`;
3. tìm centroid gần nhất;
4. tạo `cluster=Cx`.

Nếu cell fallback không có model:

```text
cluster=unknown
```

và không dùng row đó để sinh rule có cluster nếu số lượng fallback đáng kể.

### Bước 3 - Fit token bins

Fit bin thresholds từ train normal và lưu:

```text
token_bins.json
```

Payload:

```json
{
  "motion_magnitude_mean": {"q20": 0.0, "q40": 0.0, "q60": 0.0, "q80": 0.0},
  "motion_density": {"q33": 0.0, "q66": 0.0},
  "brightness_mean": {"q33": 0.0, "q66": 0.0},
  "brightness_delta_abs": {"q80": 0.0}
}
```

### Bước 4 - Tạo transactions

Mỗi transaction:

```json
{
  "dataset": "ucsd_ped2",
  "split": "train",
  "video_id": "Train001",
  "cube_id": "Train001_000001",
  "center_frame_id": 3,
  "cell_id": "08_05",
  "tokens": [
    "cell=08_05",
    "motion=slow",
    "density=low",
    "brightness=normal",
    "brightness_delta=stable",
    "cluster=C3"
  ]
}
```

MVP không nhất thiết phải lưu toàn bộ transaction JSONL nếu muốn tiết kiệm dung lượng, nhưng nên có tùy chọn `--write-transactions` để debug.

### Bước 5 - Count itemsets

Đếm support cho itemset kích thước `1..max_itemset_size`.

Mặc định:

```text
max_itemset_size = 3
min_support = 0.01
```

Với mỗi transaction có khoảng 6-8 token, số combination nhỏ và bounded Apriori có thể chạy được trên UCSD Ped2.

### Bước 6 - Sinh rules

Từ frequent itemsets kích thước >= 2:

```text
antecedent -> consequent
confidence = support(antecedent U consequent) / support(antecedent)
lift = confidence / support(consequent)
```

Lọc:

```text
support >= min_support
confidence >= min_confidence
lift >= min_lift
```

Ưu tiên rules có consequent thuộc:

```text
motion=...
density=...
cluster=...
brightness=...
```

Không chọn rule chỉ toàn vị trí:

```text
cell_row=08 -> cell_col=05
```

## 11. Output token/rule artifact

Thư mục:

```text
src/outputs/rules/{dataset}/
  rule_manifest.json
  token_bins.json
  itemsets.json
  rules.json
  selected_rules.md
  token_stats.json
  train_tokens_sample.jsonl
```

`rule_manifest.json`:

```text
schema_version
dataset
created_at
config_path
source_model_dir
train_feature_path
feature_columns
token_schema
num_transactions
num_itemsets
num_rules
min_support
min_confidence
min_lift
max_itemset_size
warnings
```

`itemsets.json`:

```json
[
  {
    "items": ["cell=08_05", "motion=slow", "density=low"],
    "count": 1234,
    "support": 0.0123
  }
]
```

`rules.json`:

```json
[
  {
    "rule_id": "R0001",
    "antecedent": ["cell=08_05", "brightness=normal"],
    "consequent": ["motion=slow"],
    "support": 0.0123,
    "confidence": 0.74,
    "lift": 1.18
  }
]
```

`selected_rules.md` chứa 20 rule tốt nhất kèm diễn giải để dùng trong báo cáo.

## 12. Tính rare token score

Với transaction test, chọn itemset quan trọng:

```text
{cell, motion, density}
{cell, motion, cluster}
{cell, density, cluster}
{cell, brightness, motion}
```

Tra support trong train:

```text
support = itemset_support.get(items, 0.0)
```

Công thức MVP:

```text
rare_token_score = 1.0 - min(support / min_support, 1.0)
```

Nếu itemset không đủ thông tin hoặc support không có:

```text
rare_token_score = 1.0
```

Nhưng để tránh false positive quá mạnh:

```text
rare_token_score = min(rare_token_score, rare_score_cap)
```

Khuyến nghị mặc định:

```text
rare_score_cap = 1.0
rare_token_weight = 0.10
```

Reason ví dụ:

```text
token combination {cell=08_05, motion=very_fast, density=high} has support=0.002 below min_support=0.010
```

## 13. Tính rule violation score

Với mỗi rule:

```text
antecedent -> consequent
```

Nếu tất cả token trong antecedent có trong transaction nhưng một hoặc nhiều token consequent không có, xem là rule bị vi phạm.

Điểm từng vi phạm:

```text
violation_strength = confidence * min(lift / 2.0, 1.0)
```

Điểm tổng:

```text
rule_violation_score = max(violation_strength của các rule bị vi phạm)
```

Hoặc lấy top-k mean nếu rule quá nhiễu:

```text
rule_violation_score = mean(top 3 violation_strength)
```

MVP dùng `max` để đơn giản và dễ giải thích.

Reason ví dụ:

```text
rule R0012 expected motion=slow for {cell=08_05, brightness=normal}, but transaction has motion=very_fast
```

## 14. Mở rộng scoring pipeline

Khi `rules.enabled=false`, `cell_scores.csv` giữ schema SPEC 3.

Khi `rules.enabled=true`, thêm cột:

```text
tokens
rare_token_score
rare_itemset
rare_itemset_support
rule_violation_score
violated_rules
token_rule_reasons
```

Schema mới đề xuất:

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
rare_token_score
rule_violation_score
cell_score
tokens
violated_rules
token_rule_reasons
```

`frame_scores.csv` có thể giữ nguyên:

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

`alerts.json` cần thêm reason từ token/rule nếu có:

```json
[
  "cell=08_05 has cluster_distance=1.42 above train threshold=0.87",
  "token combination {cell=08_05, motion=very_fast, density=high} has low support",
  "rule R0012 was violated: expected motion=slow"
]
```

## 15. CLI đề xuất

Train token/rule artifact:

```bash
python src/rules.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2
```

Smoke train:

```bash
python src/rules.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2 --limit-rows 50000
```

Score test với rule artifact:

```bash
python src/test.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2 --rules src/outputs/rules/ucsd_ped2
```

Score test fallback không rules:

```bash
python src/test.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2 --no-rules
```

Xuất visualization để kiểm tra tương thích:

```bash
python src/visualize.py --config src/configs/ucsd_ped2.yaml --top-frames 5
```

## 16. Thí nghiệm bắt buộc

### Experiment 1 - Train token/rule UCSD Ped2

Input:

```text
features_train.csv
SPEC 3 model artifact
```

Yêu cầu:

- sinh `rule_manifest.json`;
- sinh `token_bins.json`;
- sinh `itemsets.json`;
- sinh `rules.json`;
- chọn được ít nhất 20 rule thô hoặc ghi rõ nếu rule quá ít;
- `selected_rules.md` có diễn giải rule dễ đọc.

### Experiment 2 - Score test có token/rule

Input:

```text
features_test.csv
SPEC 3 model artifact
SPEC 5 rule artifact
```

Yêu cầu:

- `cell_scores.csv` có `rare_token_score` và `rule_violation_score`;
- score nằm trong `[0, 1]`;
- `alerts.json` có reason token/rule khi có vi phạm;
- không làm hỏng `frame_scores.csv`.

### Experiment 3 - So sánh baseline không rule và có rule

Chạy:

```text
SPEC 3 score: cluster + temporal
SPEC 5 score: cluster + temporal + rare + rule
```

Ghi:

- số frame medium/high;
- số alert;
- top 20 frame thay đổi nhiều nhất;
- số alert có thêm reason token/rule;
- nhận xét rule có làm score nhiễu hơn không.

### Experiment 4 - Support/confidence sweep

Chạy ít nhất 3 cấu hình:

```text
min_support=0.005, min_confidence=0.60
min_support=0.010, min_confidence=0.60
min_support=0.020, min_confidence=0.70
```

Ghi:

- số itemsets;
- số rules;
- số violated rules trên test;
- số alert có reason rule;
- cấu hình nên dùng mặc định.

### Experiment 5 - Visualization compatibility

Sau khi scoring có schema mới:

```bash
python src/visualize.py --config src/configs/ucsd_ped2.yaml --top-frames 5
python src/visualize.py --config src/configs/ucsd_ped2.yaml --alerts --limit-frames 5
```

Yêu cầu:

- ảnh không blank;
- top cells vẫn đọc đúng;
- report hiển thị reason mới nếu có.

## 17. Kiểm tra chất lượng

Điều kiện chấp nhận:

- Rule artifact load lại được bằng JSON.
- Token bins chỉ fit từ train, không fit từ test.
- Không có token rỗng hoặc token chứa dấu phân tách khó parse.
- Itemset support nằm trong `[0, 1]`.
- Confidence và lift tính đúng từ support.
- `rare_token_score`, `rule_violation_score`, `cell_score` nằm trong `[0, 1]`.
- Scoring vẫn chạy khi không có rules.
- Visualization SPEC 4 vẫn chạy với `cell_scores.csv` mới.
- Output có manifest ghi rõ config và số transaction/rule.

Kiểm tra tự động đề xuất:

```bash
python -m compileall src/kpdl_anomaly src/rules.py src/test.py
python src/rules.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2 --limit-rows 50000
python src/test.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2 --rules src/outputs/rules/ucsd_ped2 --limit-rows 50000
python src/visualize.py --config src/configs/ucsd_ped2.yaml --top-frames 5
```

Full verification sau smoke:

```bash
python src/rules.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2
python src/test.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2 --rules src/outputs/rules/ucsd_ped2
```

## 18. Checklist triển khai

- [ ] Bổ sung config `rules` vào YAML dataset.
- [ ] Cập nhật `AnomalyConfig` để đọc rules config và score weights mới.
- [ ] Tạo `src/kpdl_anomaly/tokenization.py`.
- [ ] Fit bin thresholds từ train normal.
- [ ] Token hóa row thành transaction.
- [ ] Gán `cluster=Cx` cho train bằng model SPEC 3.
- [ ] Tạo `src/kpdl_anomaly/association.py`.
- [ ] Đếm itemset support kích thước `1..3`.
- [ ] Sinh association rules theo support/confidence/lift.
- [ ] Tạo `src/kpdl_anomaly/rule_model.py`.
- [ ] Lưu `rule_manifest.json`, `token_bins.json`, `itemsets.json`, `rules.json`.
- [ ] Tạo `selected_rules.md`.
- [ ] Tạo CLI `src/rules.py`.
- [ ] Tạo `src/kpdl_anomaly/rule_scoring.py`.
- [ ] Tính `rare_token_score`.
- [ ] Tính `rule_violation_score`.
- [ ] Mở rộng `src/kpdl_anomaly/scoring.py` để dùng rules khi enabled.
- [ ] Mở rộng `CELL_SCORE_COLUMNS` hoặc writer để ghi token/rule columns.
- [ ] Mở rộng reason trong `alerts.json`.
- [ ] Thêm CLI `src/test.py --rules` và `--no-rules`.
- [ ] Chạy smoke train token/rule.
- [ ] Chạy smoke scoring có rules.
- [ ] Chạy full UCSD Ped2 token/rule.
- [ ] Chạy full UCSD Ped2 scoring có rules.
- [ ] Chạy visualization smoke để kiểm tra tương thích.
- [ ] Cập nhật `src/doc/spec_5_processed.md` sau khi triển khai.

## 19. Tiêu chí hoàn thành SPEC 5

SPEC 5 được xem là hoàn thành khi:

- train được token/rule artifact từ UCSD Ped2 train normal;
- sinh được bin thresholds, itemsets, rules và selected rule report;
- test scoring chạy được với công thức đầy đủ `cluster + temporal + rare + rule`;
- output cell score có rare/rule score và reason;
- alert JSON có ít nhất một reason token/rule khi dữ liệu kích hoạt;
- scoring cũ không rules vẫn chạy được;
- visualization SPEC 4 không bị hỏng bởi schema mới;
- có processed file ghi rõ file thay đổi, lệnh verification và kết quả;
- `repomix-output.xml` được refresh sau khi verification pass.

## 20. Rủi ro và giảm thiểu

### 20.1. Token quá vụn

Rủi ro: thêm `cell_id`, `cluster`, nhiều bin làm support thấp.

Giảm thiểu:

- giới hạn bin thô;
- mặc định itemset size tối đa 3;
- thử support sweep;
- không dùng direction token khi chưa có hướng thật.

### 20.2. Rare token không đồng nghĩa bất thường

Rủi ro: tổ hợp hợp lệ nhưng ít gặp bị cộng điểm.

Giảm thiểu:

- `rare_token_weight` chỉ 0.10;
- giữ cluster distance và temporal score làm thành phần chính;
- yêu cầu smoothing/consecutive frame như SPEC 3.

### 20.3. Rule gây hiểu sai

Rủi ro: rule có confidence cao nhưng support thấp hoặc chỉ mô tả độ sáng.

Giảm thiểu:

- lọc theo support/confidence/lift;
- chọn rule có motion/density/cluster;
- ghi warning trong selected rules;
- không dùng rule làm quyết định độc lập.

### 20.4. Bộ đếm itemset tốn RAM

Rủi ro: dữ liệu Avenue lớn hơn UCSD Ped2.

Giảm thiểu:

- ưu tiên UCSD Ped2;
- stream CSV;
- giới hạn max itemset size;
- chỉ lưu itemset đạt support ngưỡng;
- mở rộng FP-Growth sau nếu cần.

### 20.5. Schema mới làm hỏng visualization

Rủi ro: `cell_scores.csv` thêm cột làm code cũ parse sai.

Giảm thiểu:

- giữ nguyên các cột SPEC 3 bắt buộc;
- chỉ thêm cột phía sau;
- chạy smoke SPEC 4 sau scoring.

## 21. Hướng sau SPEC 5

Sau SPEC 5:

- SPEC 6: đánh giá ROC-AUC/EER với ground truth UCSD và so sánh có/không có rule.
- SPEC 7: thêm optical flow hoặc direction feature thật để token hướng chuyển động có ý nghĩa.
- SPEC 8: skipped theo cập nhật ngày 2026-05-27; không mở thêm tuning/leaderboard/comparison code nếu người dùng không yêu cầu rõ.
