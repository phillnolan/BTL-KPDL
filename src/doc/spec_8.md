# SPEC 8 - Metric-driven tuning for threshold, smoothing, and score weights

## 1. Muc tieu

SPEC 8 bo sung workflow tinh chinh tham so scoring dua tren metric dinh luong sau SPEC 6 va SPEC 7.

Muc tieu chinh:

- tune `model.threshold_percentile` cho cluster distance threshold;
- tune `scoring.top_k_cells` khi tong hop cell score thanh frame score;
- tune `scoring.smoothing_window` cho `smoothed_frame_score`;
- tune cac weight `cluster_weight`, `temporal_weight`, `rare_token_weight`, `rule_weight`;
- tune alert threshold de severity/alert phu hop hon voi metric;
- xuat leaderboard so sanh no-rules, with-rules va cac bien the tuned;
- xuat `best_config.yaml` hoac config patch de chay lai pipeline;
- giu token/rule la tin hieu phu co the giai thich, khong ep rule phai cai thien ROC-AUC neu metric khong ung ho.

SPEC 8 uu tien tinh lap lai va minh bach hon viec toi uu tuyet doi tren mot benchmark.

## 2. Lien he PRD va spec truoc

PRD yeu cau pipeline co frame-level ROC-AUC, PR-AUC, EER, false positive rate, recall va ablation giua score co rule/khong rule.

SPEC 6 da them evaluation UCSD va cho thay:

- no-rules `smoothed_frame_score` dat ROC-AUC `0.772427`, EER `0.297668`;
- with-rules `smoothed_frame_score` dat ROC-AUC `0.766468`, EER `0.300041`;
- with-rules chi cai thien raw `frame_score` rat nhe: ROC-AUC tang `+0.000652`;
- with-rules lam giam smoothed ROC-AUC `-0.005959`.

SPEC 7 da them optical flow direction feature va direction token, nhung moi smoke tren UCSD Ped2, chua danh gia/tune dinh luong.

SPEC 8 vi vay can:

- dung SPEC 6 lam baseline metric chinh;
- tune smoothing/weight truoc khi ket luan rule co ich ve metric;
- co the chay tren frame-diff config truoc, sau do mo rong sang optical-flow config neu thoi gian cho phep.

## 3. Pham vi

Trong pham vi:

- UCSD Ped2 la dataset uu tien;
- frame-level tuning dua tren `frame_scores.csv`, `cell_scores.csv` va ground truth UCSD;
- grid search nho, cau hinh bang YAML/list mac dinh trong code;
- leaderboard theo ROC-AUC, PR-AUC, EER, best F1 va threshold diagnostics;
- best config/patch de cap nhat cac tham so scoring;
- comparison giua current no-rules, current with-rules va tuned variants;
- ghi ro khi rule tang kha nang giai thich nhung khong tang metric.

Ngoai pham vi:

- Bayesian optimization hoac hyperparameter search lon;
- pixel-level localization metric;
- training full optical flow tren toan bo dataset neu qua cham;
- thay doi feature extraction lon;
- dashboard tuning UI;
- toi uu theo test set de bao cao nhu ket qua tong quat. Ket qua tuning tren UCSD Ped2 can duoc xem la experimental.

## 4. Input va output

Input chinh:

```text
src/configs/ucsd_ped2.yaml
src/outputs/results_spec6_no_rules/ucsd_ped2/cell_scores.csv
src/outputs/results_spec6_rules/ucsd_ped2/cell_scores.csv
src/outputs/results_spec6_no_rules/ucsd_ped2/frame_scores.csv
src/outputs/results_spec6_rules/ucsd_ped2/frame_scores.csv
src/outputs/evaluation/ucsd_ped2_spec6_compare/comparison.json
src/dataset/UCSD_Anomaly_Dataset.v1p2/UCSDped2/Test/*_gt
```

Output de xuat:

```text
src/outputs/tuning/ucsd_ped2/
  leaderboard.csv
  leaderboard.json
  best_config.yaml
  tuning_summary.md
  variants/
    <variant_name>/frame_scores.csv
    <variant_name>/alerts.json
    <variant_name>/metrics.json
```

Neu co chay threshold percentile sweep cham:

```text
src/outputs/models_spec8_threshold/<variant>/ucsd_ped2/
src/outputs/results_spec8_threshold/<variant>/ucsd_ped2/
src/outputs/evaluation/spec8_threshold/<variant>/
```

## 5. Chien luoc tuning

### 5.1. Fast scoring sweep

Fast sweep khong train lai model. No doc `cell_scores.csv` da co cac thanh phan:

```text
cluster_distance_score
temporal_change_score
rare_token_score
rule_violation_score
```

Tu do tinh lai:

```text
cell_score =
    cluster_weight * cluster_distance_score
  + temporal_weight * temporal_change_score
  + rare_token_weight * rare_token_score
  + rule_weight * rule_violation_score
```

Sau do tong hop lai:

```text
frame_score = mean(top_k cell_score cao nhat theo frame)
smoothed_frame_score = moving_average(frame_score, smoothing_window)
```

Fast sweep cho phep thu nhieu bien the weight/top-k/smoothing nhanh ma khong can chay lai KMeans.

### 5.2. Threshold percentile sweep

`model.threshold_percentile` anh huong `cluster_distance_score`, nen can train/test lai artifact.

Percentile de xuat:

```text
95.0
97.0
99.0
99.5
```

Moi variant can:

1. train model voi percentile tuong ung;
2. score test no-rules va with-rules neu rule artifact phu hop;
3. evaluate ROC-AUC/PR-AUC/EER;
4. dua vao leaderboard rieng hoac chung.

Neu thoi gian han che, SPEC 8 co the implement fast sweep truoc va ghi threshold sweep la optional follow-up.

### 5.3. Alert threshold calibration

Alert threshold khong lam thay doi ROC-AUC, nhung anh huong severity, alert count, false positives va recall tai nguong van hanh.

Can lay threshold goi y tu metric:

```text
medium ~= youden_threshold hoac eer_threshold
high ~= percentile cao cua score tren negative frames, vi du 95-99th percentile
```

Acceptance khong yeu cau high alert phai xuat hien neu score distribution khong dat nguong phu hop, nhung phai co ly do ro trong summary.

## 6. Search grid de xuat

No-rules weight variants:

```text
cluster=0.90 temporal=0.10 rare=0.00 rule=0.00
cluster=0.80 temporal=0.20 rare=0.00 rule=0.00
cluster=0.70 temporal=0.30 rare=0.00 rule=0.00
```

With-rules weight variants:

```text
cluster=0.80 temporal=0.20 rare=0.00 rule=0.00
cluster=0.75 temporal=0.20 rare=0.05 rule=0.00
cluster=0.70 temporal=0.20 rare=0.08 rule=0.02
cluster=0.65 temporal=0.20 rare=0.10 rule=0.05
cluster=0.60 temporal=0.25 rare=0.10 rule=0.05
```

Aggregation/smoothing variants:

```text
top_k_cells: 1, 3, 5, 10
smoothing_window: 1, 3, 5, 7, 9
min_consecutive_alerts: 1, 3, 5
```

Default primary objective:

```text
maximize smoothed_frame_score ROC-AUC
tie-breaker 1: maximize PR-AUC
tie-breaker 2: minimize EER
tie-breaker 3: prefer simpler/no-rules config if metric difference < 0.001
```

## 7. CLI de xuat

Them CLI:

```bash
python src/tune.py --config src/configs/ucsd_ped2.yaml ^
  --baseline-results src/outputs/results_spec6_no_rules/ucsd_ped2 ^
  --candidate-results src/outputs/results_spec6_rules/ucsd_ped2 ^
  --output-dir src/outputs/tuning/ucsd_ped2
```

Option de xuat:

```text
--score-column smoothed_frame_score
--label-source auto
--max-variants 100
--include-rules
--no-threshold-sweep
--threshold-percentiles 95 97 99 99.5
```

Public summary nen in ngan gon:

```json
{
  "dataset": "ucsd_ped2",
  "variants": 120,
  "best_variant": "rules_cluster075_temporal020_rare005_rule000_top3_smooth3",
  "best_roc_auc": 0.78,
  "baseline_roc_auc": 0.772427,
  "output_dir": "src/outputs/tuning/ucsd_ped2"
}
```

## 8. Thay doi code du kien

File moi:

```text
src/kpdl_anomaly/tuning.py
src/tune.py
src/doc/spec_8_processed.md
```

File co the sua:

```text
src/kpdl_anomaly/config.py
src/kpdl_anomaly/evaluation.py
src/kpdl_anomaly/scoring.py
src/kpdl_anomaly/smoothing.py
src/kpdl_anomaly/schema.py
src/configs/ucsd_ped2.yaml
```

Nguyen tac:

- tai su dung `moving_average` trong `kpdl_anomaly.smoothing`;
- tai su dung metric logic cua `kpdl_anomaly.evaluation`;
- khong copy/paste cong thuc metric neu co the tach helper;
- giu output `frame_scores.csv` tuong thich SPEC 3/4/6;
- them cot/metadata moi o artifact tuning, khong lam hong pipeline cu.

## 9. Tieu chi chap nhan

- Tao duoc `src/tune.py` va module tuning co the chay tren UCSD Ped2 artifacts hien co.
- Leaderboard co it nhat cac cot:
  - `variant_name`;
  - `source_result`;
  - `cluster_weight`;
  - `temporal_weight`;
  - `rare_token_weight`;
  - `rule_weight`;
  - `top_k_cells`;
  - `smoothing_window`;
  - `roc_auc`;
  - `pr_auc`;
  - `eer`;
  - `best_f1`;
  - `recommended_medium_threshold`;
  - `recommended_high_threshold`.
- `best_config.yaml` chua day du cac tham so scoring duoc chon.
- `tuning_summary.md` neu ro baseline, best variant, delta metric va nhan xet ve rule.
- Neu best no-rules tot hon with-rules, summary phai noi ro rule nen giu cho explanation thay vi metric.
- Neu best with-rules tot hon, summary phai chi ra rule/rare weights nho va khong duoc de rule quyet dinh doc lap alert.
- Chay duoc evaluation cho best variant va xuat `metrics.json`.

## 10. Verification de xuat

```bash
python -m compileall src/kpdl_anomaly src/tune.py
python src/tune.py --config src/configs/ucsd_ped2.yaml --baseline-results src/outputs/results_spec6_no_rules/ucsd_ped2 --candidate-results src/outputs/results_spec6_rules/ucsd_ped2 --output-dir src/outputs/tuning/ucsd_ped2 --no-threshold-sweep
python src/evaluate.py --config src/configs/ucsd_ped2.yaml --results src/outputs/tuning/ucsd_ped2/variants/<best_variant> --output-dir src/outputs/tuning/ucsd_ped2/best_eval
```

Neu implement threshold sweep:

```bash
python src/train.py --config src/configs/ucsd_ped2.yaml --threshold-percentile 97 --model-root src/outputs/models_spec8_p97
python src/test.py --config src/configs/ucsd_ped2.yaml --model src/outputs/models_spec8_p97/ucsd_ped2 --result-root src/outputs/results_spec8_p97 --no-rules
python src/evaluate.py --config src/configs/ucsd_ped2.yaml --results src/outputs/results_spec8_p97/ucsd_ped2 --output-dir src/outputs/evaluation/spec8_p97
```

## 11. Rui ro va giam thieu

### 11.1. Overfit vao UCSD Ped2 test set

Rui ro: tuning tren test label lam metric dep nhung khong tong quat.

Giam thieu:

- goi ket qua la experimental tuning;
- uu tien grid nho, co ly giai;
- neu co the, tach mot phan train/validation hoac chay lai tren Ped1/Avenue sau.

### 11.2. Rule score lam giam AUC

Rui ro: rare/rule score them nhieu tin hieu khong trung voi ground truth frame-level.

Giam thieu:

- rule/rare weight nho;
- co variant rare-only, rule-off;
- tie-breaker uu tien simpler/no-rules neu delta rat nho;
- van giu rule reason trong alert khi can giai thich.

### 11.3. Smoothing che mat bat thuong ngan

Rui ro: window lon lam giam recall voi event ngan.

Giam thieu:

- sweep window `1, 3, 5, 7, 9`;
- so sanh raw va smoothed score;
- bao cao EER/best F1/threshold metrics.

### 11.4. High threshold qua cao

Rui ro: `alert_threshold_high=0.90` hien tai gan nhu khong tao high alert.

Giam thieu:

- de xuat high threshold theo score distribution;
- bao cao count severity/alert sau calibration;
- khong ep high alert neu metric/score distribution khong hop ly.

## 12. Ket qua ban giao

- Spec va processed log cho SPEC 8.
- Tuning CLI va module.
- Leaderboard va summary tuning UCSD Ped2.
- Best config/patch.
- Comparison metric truoc/sau tuning.
- Nhan xet ve vai tro rule trong metric va explanation.
