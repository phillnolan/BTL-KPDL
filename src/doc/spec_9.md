# SPEC 9 - Hồ sơ cụm, giải thích cảnh báo và casebook phục vụ báo cáo

## 1. Mục tiêu

SPEC 9 bổ sung lớp diễn giải sau khi pipeline đã có phân cụm theo cell, token/rule, optical-flow direction feature, score, alert và heatmap overlay.

Mục tiêu chính:

- tạo hồ sơ cụm hành vi bình thường cho từng cell từ model KMeans đã train;
- diễn giải cụm bằng các feature dễ hiểu như motion, density, brightness, direction và support trong train;
- nối lý do cảnh báo từ cluster distance, token hiếm, rule violation và heatmap top cells thành một bằng chứng thống nhất;
- tạo casebook Markdown/JSON phục vụ báo cáo, gồm alert, frame đại diện, overlay path, top cells, rule evidence và nhận xét placeholder;
- giữ trọng tâm vào khả năng giải thích và artifact báo cáo, không thêm workflow tuning/leaderboard/ablation mới.

SPEC 9 không thay đổi công thức anomaly score và không chọn cấu hình tốt nhất theo metric. Các metric từ SPEC 6 chỉ được dùng như ngữ cảnh phụ nếu cần nhắc trong báo cáo.

## 2. Liên hệ với PRD và các spec trước

Theo PRD, MVP cần có:

- phát hiện bất thường theo cell/frame;
- heatmap bất thường;
- lý do cảnh báo dễ hiểu bằng cluster distance, token hiếm và rule;
- artifact đủ tốt để phân tích định tính và viết báo cáo.

Trạng thái sau các spec trước:

- SPEC 3 đã có per-cell MiniBatchKMeans, distance threshold, `cell_scores.csv`, `frame_scores.csv`, `alerts.json`.
- SPEC 4 đã có heatmap overlay, ảnh top frames, alert peaks và qualitative report.
- SPEC 5 đã có tokenization, bounded Apriori, rare token score, rule violation score và reason text cơ bản.
- SPEC 6 đã có frame-level evaluation ROC-AUC/PR-AUC/EER.
- SPEC 7 đã thêm Farneback optical flow, direction histogram và direction token.
- SPEC 8 bị skip theo định hướng mới: không mở rộng thêm tuning/leaderboard nếu người dùng không yêu cầu rõ.

SPEC 9 vì vậy tập trung biến các artifact đã có thành bằng chứng diễn giải có cấu trúc, bám sát chủ đề phân cụm hành vi-không gian-thời gian và khai phá luật kết hợp.

## 3. Phạm vi

### 3.1. Nằm trong phạm vi

- Đọc model artifact của SPEC 3/SPEC 7.
- Tạo hồ sơ cụm theo từng `cell_id` và `cluster=Cx`.
- Inverse-transform centroid về thang feature gốc khi có scaler.
- Gán nhãn diễn giải cho cluster bằng token/bin hiện có.
- Tính support hoặc số mẫu train của mỗi cluster nếu artifact có đủ dữ liệu hoặc có thể suy ra an toàn.
- Đọc rule artifact của SPEC 5.
- Đọc `cell_scores.csv`, `frame_scores.csv`, `alerts.json` của kết quả scoring.
- Ghép reason cluster/token/rule thành explanation record thống nhất cho alert/frame.
- Tham chiếu overlay image/video đã sinh bởi SPEC 4 nếu có.
- Tạo `cluster_profiles.json`, `cluster_profiles.md`, `alert_casebook.json`, `alert_casebook.md`.
- Tạo CLI chạy lại được bằng config.
- Hoạt động được cả khi rules disabled hoặc visualization artifact chưa có, nhưng phải ghi warning rõ.

### 3.2. Ngoài phạm vi

- Không train lại model.
- Không thay đổi scoring weight, threshold, smoothing hoặc alert logic.
- Không sinh tuning leaderboard, best config hoặc ablation runner.
- Không thêm dashboard web.
- Không yêu cầu chạy full optical flow nếu chỉ cần casebook từ artifact sẵn có.
- Không tự động kết luận true/false positive nếu không có người xem hoặc ground truth được yêu cầu rõ.

## 4. Input và output

Input chính:

```text
src/configs/{dataset}.yaml
src/outputs/models/{dataset}/
  model_manifest.json
  cell_models.joblib
  cell_scalers.joblib
  thresholds.json
  feature_stats.json

src/outputs/rules/{dataset}/
  rule_manifest.json
  token_bins.json
  itemsets.json
  rules.json
  selected_rules.md

src/outputs/results/{dataset}/
  cell_scores.csv
  frame_scores.csv
  alerts.json

src/outputs/visualizations/{dataset}/
  visualization_index.json
  qualitative_report.md
  top_frames/*.png
  alerts/*.png
```

Với optical-flow smoke hoặc artifact SPEC 7, input có thể nằm ở root output riêng:

```text
src/outputs/models_spec7_flow/{dataset}/
src/outputs/rules_spec7_flow/{dataset}/
src/outputs/results_spec7_flow/{dataset}/
src/outputs/visualizations_spec7_flow/{dataset}/
```

Output đề xuất:

```text
src/outputs/analysis/{dataset}/
  cluster_profiles.json
  cluster_profiles.md
  rule_evidence_index.json
  alert_casebook.json
  alert_casebook.md
  analysis_manifest.json
```

## 5. Hồ sơ cụm hành vi

### 5.1. Mục tiêu

Mỗi cụm trong per-cell KMeans cần có mô tả đọc được:

```text
cell=08_05 cluster=C3:
  motion=slow
  density=low
  brightness=normal
  direction=left_to_right nếu có optical flow
  train_support=0.34
  distance_threshold_p99=...
```

Hồ sơ cụm không phải nhãn ngữ nghĩa cố định. `C3` ở cell này không nhất thiết giống `C3` ở cell khác. Mọi diễn giải phải luôn kèm `cell_id`.

### 5.2. Dữ liệu cần trích từ model

Từ `cell_models.joblib`:

- cluster centers;
- số cluster của cell;
- model status nếu có.

Từ `cell_scalers.joblib`:

- inverse-transform centroid về feature gốc.

Từ `thresholds.json`:

- train distance mean/std/p95/p99;
- threshold đang dùng;
- số mẫu train nếu đã lưu.

Từ `feature_stats.json` hoặc feature train nếu cần:

- phân phối feature toàn train;
- số mẫu theo cell/cluster nếu artifact hiện tại chưa lưu.

### 5.3. Diễn giải centroid

MVP dùng token/bin đã fit từ train normal:

```text
motion_magnitude_mean -> motion=still|slow|medium|fast|very_fast
motion_density -> density=low|medium|high
brightness_mean -> brightness=dark|normal|bright
brightness_delta -> brightness_delta=stable|changing
direction_hist_* -> direction=left|right|up|down|... nếu include_direction_token=true
```

Nếu không có `token_bins.json`, fallback dùng quantile/threshold trong `feature_stats.json`. Nếu vẫn không đủ dữ liệu, ghi:

```text
interpretation_status = "insufficient_token_bins"
```

### 5.4. Output `cluster_profiles.json`

Schema đề xuất:

```json
{
  "dataset": "ucsd_ped2",
  "generated_at": "2026-05-27T20:00:00+07:00",
  "model_dir": "src/outputs/models/ucsd_ped2",
  "feature_columns": ["foreground_ratio", "motion_magnitude_mean"],
  "cells": [
    {
      "cell_id": "08_05",
      "model_status": "trained",
      "threshold": 0.87,
      "clusters": [
        {
          "cluster_id": "C3",
          "centroid": {"motion_magnitude_mean": 0.42},
          "tokens": ["motion=slow", "density=low", "brightness=normal"],
          "support_count": 812,
          "support": 0.34,
          "summary": "normal low-density slow motion in cell 08_05"
        }
      ]
    }
  ],
  "warnings": []
}
```

`cluster_profiles.md` cần có bảng đọc nhanh:

```markdown
| Cell | Cluster | Support | Motion | Density | Brightness | Direction | Notes |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| 08_05 | C3 | 0.34 | slow | low | normal | left_to_right | common normal pattern |
```

## 6. Rule evidence index

### 6.1. Mục tiêu

Rule artifact hiện có chủ yếu phục vụ scoring. SPEC 9 cần thêm index để giải thích nhanh một alert:

- rule nào bị vi phạm;
- antecedent/consequent là gì;
- support/confidence/lift;
- rule liên quan tới cell, cluster, motion, direction hay brightness;
- câu diễn giải ngắn dùng được trong báo cáo.

### 6.2. Output `rule_evidence_index.json`

Schema đề xuất:

```json
[
  {
    "rule_id": "R0012",
    "antecedent": ["cell=08_05", "brightness=normal"],
    "consequent": ["motion=slow"],
    "support": 0.012,
    "confidence": 0.74,
    "lift": 1.18,
    "evidence_tags": ["cell", "motion", "brightness"],
    "plain_language": "In cell 08_05, normal-brightness training samples usually have slow motion."
  }
]
```

Quy tắc:

- ưu tiên rule có motion/density/direction/cluster;
- không đưa rule chỉ mô tả vị trí thuần vào top evidence;
- giữ rule support thấp nhưng quan trọng nếu nó thật sự liên quan alert, nhưng phải gắn warning.

## 7. Alert explanation record

### 7.1. Mục tiêu

Mỗi alert/frame trong casebook cần có explanation record thống nhất, thay vì reason text rời rạc.

Schema đề xuất:

```json
{
  "dataset": "ucsd_ped2",
  "video_id": "Test001",
  "frame_id": 164,
  "alert_range": {"start_frame_id": 150, "end_frame_id": 180},
  "score": {
    "frame_score": 0.78,
    "smoothed_frame_score": 0.81,
    "severity": "medium"
  },
  "top_cells": [
    {
      "cell_id": "08_05",
      "cell_score": 0.91,
      "nearest_cluster": "C3",
      "cluster_profile": {
        "summary": "normal slow low-density motion",
        "tokens": ["motion=slow", "density=low"]
      },
      "observed_tokens": ["motion=very_fast", "density=high", "cluster=C3"],
      "cluster_distance": {
        "distance": 1.42,
        "threshold": 0.87,
        "above_threshold": true
      },
      "rare_itemset": {
        "items": ["cell=08_05", "motion=very_fast", "density=high"],
        "support": 0.002,
        "min_support": 0.01
      },
      "violated_rules": ["R0012"],
      "plain_language": [
        "Cell 08_05 is far from its nearest normal cluster C3.",
        "The observed very-fast high-density motion is rare in train normal data.",
        "Rule R0012 expected slow motion under this context."
      ]
    }
  ],
  "overlay": {
    "image_path": "src/outputs/visualizations/ucsd_ped2/alerts/Test001_000164_peak.png",
    "video_path": null
  },
  "manual_review": {
    "label": "TBD",
    "notes": "TBD"
  }
}
```

### 7.2. Reason ưu tiên

Khi có nhiều reason, sắp xếp:

1. cluster distance vượt threshold của chính cell;
2. observed token lệch với cluster profile;
3. rare itemset có support thấp;
4. rule violation có confidence/lift tốt;
5. temporal/smoothing evidence.

Không để rule violation đứng một mình nếu cluster distance thấp và score chính không đáng kể.

## 8. Casebook phục vụ báo cáo

### 8.1. Mục tiêu

`alert_casebook.md` là artifact để đưa vào báo cáo hoặc phụ lục. Nó không phải dashboard. Nó cần giúp người đọc thấy:

- frame/alert nào được chọn;
- vùng nào nóng trên heatmap;
- cụm bình thường gần nhất là gì;
- observed token bất thường ở đâu;
- rule nào hỗ trợ giải thích;
- người review có thể điền đúng/sai/không chắc.

### 8.2. Cách chọn case

MVP hỗ trợ:

```text
--top-alerts 10
--top-frames 20
--video-id Test001
--start-frame 150
--end-frame 180
```

Mặc định:

- chọn peak frame của mỗi alert segment;
- nếu không có alert, chọn top frames theo `smoothed_frame_score`;
- giới hạn mặc định 20 case để report gọn.

### 8.3. Markdown layout

Mẫu:

```markdown
# Alert Casebook - ucsd_ped2

## Summary

- Result dir: `...`
- Model dir: `...`
- Rule dir: `...`
- Cases: 16
- Warnings: 0

## Cases

### Case 001 - Test001 frame 164

| Field | Value |
| --- | --- |
| Score | 0.81 |
| Severity | medium |
| Top cells | 08_05, 08_06, 09_05 |
| Overlay | `top_frames/Test001_000164_score_0.810.png` |
| Manual label | TBD |

Cluster/rule evidence:

- cell=08_05 nearest cluster C3: normal slow low-density motion.
- observed tokens: motion=very_fast, density=high, direction=left_to_right.
- rare itemset support: 0.002 below min_support 0.010.
- violated R0012: expected motion=slow with confidence 0.74.
```

Nếu Markdown renderer hỗ trợ ảnh relative path, có thể thêm preview. Nếu không, vẫn ghi path rõ.

## 9. Kiến trúc module đề xuất

Thêm file:

```text
src/kpdl_anomaly/cluster_profiles.py
src/kpdl_anomaly/explanations.py
src/kpdl_anomaly/casebook.py
src/explain.py
```

Vai trò:

```text
cluster_profiles.py:
  load model/scaler/threshold artifact
  inverse-transform centroid
  label cluster bằng token bins
  write cluster_profiles.json/md

explanations.py:
  load rule evidence
  parse cell_scores/frame_scores/alerts
  build structured explanation records
  create plain-language reason strings

casebook.py:
  select cases
  attach visualization paths
  write alert_casebook.json/md
  write analysis_manifest.json

src/explain.py:
  CLI entrypoint cho SPEC 9
```

Tái sử dụng module hiện có:

- `kpdl_anomaly.config` để đọc config;
- `kpdl_anomaly.io` để read/write JSON/CSV nếu có helper sẵn;
- `kpdl_anomaly.tokenization` để gán token từ row/centroid;
- `kpdl_anomaly.rule_scoring` để đọc rule artifact và reason;
- `kpdl_anomaly.visualization` chỉ để đọc index/path, không render lại bắt buộc.

## 10. CLI đề xuất

Tạo hồ sơ cụm và casebook từ artifact mặc định:

```bash
python src/explain.py --config src/configs/ucsd_ped2.yaml ^
  --model src/outputs/models/ucsd_ped2 ^
  --rules src/outputs/rules/ucsd_ped2 ^
  --results src/outputs/results/ucsd_ped2 ^
  --visualizations src/outputs/visualizations/ucsd_ped2 ^
  --output-dir src/outputs/analysis/ucsd_ped2
```

Không có rules:

```bash
python src/explain.py --config src/configs/ucsd_ped2.yaml ^
  --model src/outputs/models/ucsd_ped2 ^
  --results src/outputs/results_spec6_no_rules/ucsd_ped2 ^
  --no-rules ^
  --output-dir src/outputs/analysis/ucsd_ped2_no_rules
```

Optical-flow artifact:

```bash
python src/explain.py --config src/configs/ucsd_ped2_optical_flow.yaml ^
  --model src/outputs/models_spec7_flow/ucsd_ped2 ^
  --rules src/outputs/rules_spec7_flow/ucsd_ped2 ^
  --results src/outputs/results_spec7_flow/ucsd_ped2 ^
  --output-dir src/outputs/analysis/ucsd_ped2_flow
```

Tùy chọn cần có:

```text
--config
--model
--rules
--results
--visualizations
--output-dir
--top-alerts
--top-frames
--video-id
--start-frame
--end-frame
--no-rules
--write-cluster-profiles-only
```

## 11. Tiêu chí chấp nhận

- `cluster_profiles.json` sinh được cho toàn bộ cell có model.
- `cluster_profiles.md` có bảng đọc được và không quá dài cho UCSD Ped2.
- Mỗi cluster profile có `cell_id`, `cluster_id`, centroid feature, token summary và threshold context.
- `rule_evidence_index.json` sinh được khi có rule artifact.
- `alert_casebook.json` có ít nhất một case nếu `alerts.json` hoặc `frame_scores.csv` có dữ liệu.
- `alert_casebook.md` có top cells, cluster profile summary, observed tokens, rare itemset/rule evidence nếu có.
- Chạy được với `--no-rules` và vẫn tạo cluster/cluster-distance explanation.
- Chạy được trên optical-flow artifact và giữ direction evidence khi token direction tồn tại.
- Không thêm code tuning, leaderboard, best-config selection hoặc ablation comparison.

## 12. Verification đề xuất

Compile:

```bash
python -m compileall src/kpdl_anomaly src/explain.py
```

Smoke UCSD Ped2 có rules:

```bash
python src/explain.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2 --rules src/outputs/rules/ucsd_ped2 --results src/outputs/results/ucsd_ped2 --visualizations src/outputs/visualizations/ucsd_ped2 --output-dir src/outputs/analysis/ucsd_ped2_smoke --top-alerts 5
```

Smoke no-rules:

```bash
python src/explain.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models/ucsd_ped2 --results src/outputs/results_spec6_no_rules/ucsd_ped2 --no-rules --output-dir src/outputs/analysis/ucsd_ped2_no_rules_smoke --top-frames 5
```

Smoke optical-flow nếu artifact SPEC 7 còn tồn tại:

```bash
python src/explain.py --config src/configs/ucsd_ped2_optical_flow.yaml --model src/outputs/models_spec7_flow/ucsd_ped2 --rules src/outputs/rules_spec7_flow/ucsd_ped2 --results src/outputs/results_spec7_flow/ucsd_ped2 --output-dir src/outputs/analysis/ucsd_ped2_flow_smoke --top-frames 5
```

Validation tự động:

```text
cluster_profiles.json load được bằng JSON.
alert_casebook.json load được bằng JSON.
Số case > 0 khi input có alert/frame score.
Các path overlay tồn tại hoặc được ghi vào warning nếu thiếu.
Không có score hoặc support ngoài khoảng [0, 1].
```

Sau khi verification pass:

```bash
repomix.cmd
```

## 13. Checklist triển khai

- [ ] Đọc PRD, `repomix-output.xml` và `src/doc/spec_9.md`.
- [ ] Tạo `src/kpdl_anomaly/cluster_profiles.py`.
- [ ] Load model/scaler/threshold artifact.
- [ ] Inverse-transform centroid về feature gốc.
- [ ] Gán token summary cho centroid.
- [ ] Tính hoặc nạp cluster support theo train nếu có thể.
- [ ] Ghi `cluster_profiles.json`.
- [ ] Ghi `cluster_profiles.md`.
- [ ] Tạo `src/kpdl_anomaly/explanations.py`.
- [ ] Load rule artifact và tạo `rule_evidence_index.json`.
- [ ] Load `cell_scores.csv`, `frame_scores.csv`, `alerts.json`.
- [ ] Ghép cluster profile với top cell score.
- [ ] Ghép rare itemset và violated rule evidence.
- [ ] Tạo plain-language reason strings.
- [ ] Tạo `src/kpdl_anomaly/casebook.py`.
- [ ] Chọn case từ alert peaks hoặc top frames.
- [ ] Gắn overlay path từ visualization index nếu có.
- [ ] Ghi `alert_casebook.json`.
- [ ] Ghi `alert_casebook.md`.
- [ ] Ghi `analysis_manifest.json`.
- [ ] Thêm CLI `src/explain.py`.
- [ ] Chạy compile verification.
- [ ] Chạy smoke UCSD Ped2 có rules.
- [ ] Chạy smoke no-rules fallback.
- [ ] Chạy smoke optical-flow nếu artifact còn sẵn.
- [ ] Cập nhật `src/doc/spec_9_processed.md` sau khi triển khai.
- [ ] Refresh `repomix-output.xml` sau verification pass.

## 14. Rủi ro và giảm thiểu

### 14.1. Centroid khó diễn giải

Rủi ro: centroid chuẩn hóa hoặc feature direction histogram khó chuyển thành câu đơn giản.

Giảm thiểu:

- inverse-transform bằng scaler;
- chỉ gán nhãn coarse token;
- nếu direction không rõ, ghi `direction=mixed` hoặc `direction=unknown`.

### 14.2. Cluster support chưa có sẵn

Rủi ro: model artifact hiện tại có centroid nhưng chưa lưu số mẫu theo cluster.

Giảm thiểu:

- tính lại cluster assignment từ `features_train.csv` nếu cần;
- cho phép `--cluster-profiles-fast` chỉ ghi centroid/threshold và để support là `null`;
- ghi warning trong manifest.

### 14.3. Reason quá dài

Rủi ro: mỗi alert có nhiều cell, token và rule, làm report khó đọc.

Giảm thiểu:

- mặc định chỉ lấy top 3 cell;
- mỗi cell chỉ lấy top 2 rule evidence;
- Markdown có summary ngắn và JSON giữ chi tiết đầy đủ.

### 14.4. Visualization artifact thiếu

Rủi ro: người dùng chưa chạy SPEC 4 hoặc output nằm ở thư mục khác.

Giảm thiểu:

- casebook vẫn tạo được bằng score/reason;
- overlay path là optional;
- warning hướng dẫn chạy `src/visualize.py` nếu cần ảnh.

### 14.5. Rule evidence gây hiểu nhầm

Rủi ro: rule violation bị đọc như nguyên nhân duy nhất của bất thường.

Giảm thiểu:

- luôn ghi rule là tín hiệu giải thích phụ;
- ưu tiên cluster distance và observed token;
- hiển thị support/confidence/lift cùng rule.

## 15. Hướng sau SPEC 9

Sau SPEC 9, dự án có thể chuyển sang:

- dùng casebook để viết phần kết quả định tính trong báo cáo;
- chọn một số case minh họa đúng/sai và phân tích nguyên nhân;
- cập nhật LaTeX report với pipeline, hình heatmap và bảng rule evidence;
- chỉ mở thêm tuning hoặc comparison nếu người dùng yêu cầu rõ.
