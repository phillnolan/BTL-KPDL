# SPEC 5 Processed - Tokenization, rare token score and association rules

Original spec path: `src/doc/spec_5.md`

Date/time processed: 2026-05-27 11:28:44 +07:00

## Summary

Implemented SPEC 5 in the Python pipeline. The project now trains a token/rule artifact from SPEC 3 features and models, scores test rows with `rare_token_score` and `rule_violation_score`, appends token/rule columns only when rule scoring is active, and preserves the old SPEC 3 `cell_scores.csv` schema when rules are disabled.

Primary verified dataset: `ucsd_ped2`.

## Checklist

- [Done] Read PRD, root `repomix-output.xml`, and `src/doc/spec_5.md`.
- [Done] Add `rules` config to dataset YAML files.
- [Done] Update `AnomalyConfig` with rule settings and score weights.
- [Done] Add `src/kpdl_anomaly/tokenization.py`.
- [Done] Fit token bin thresholds from train normal rows.
- [Done] Tokenize feature rows into stable transactions.
- [Done] Assign `cluster=Cx` to train rows from SPEC 3 scaler/model artifacts.
- [Done] Add `src/kpdl_anomaly/association.py`.
- [Done] Count itemset support for bounded itemsets of size `1..3`.
- [Done] Generate bounded Apriori association rules by support/confidence/lift.
- [Done] Add `src/kpdl_anomaly/rule_model.py`.
- [Done] Write `rule_manifest.json`, `token_bins.json`, `itemsets.json`, `rules.json`, `token_stats.json`, and `selected_rules.md`.
- [Done] Add CLI `src/rules.py`.
- [Done] Add `src/kpdl_anomaly/rule_scoring.py`.
- [Done] Compute `rare_token_score`.
- [Done] Compute `rule_violation_score`.
- [Done] Extend `src/kpdl_anomaly/scoring.py` to use rules when active.
- [Done] Extend score CSV writer with token/rule columns when active.
- [Done] Extend alert reasons with token/rule reasons.
- [Done] Add `src/test.py` support for `--rules` and `--no-rules`.
- [Done] Smoke train token/rule artifact.
- [Done] Smoke scoring with token/rule artifact.
- [Done] Smoke fallback scoring with `--no-rules`.
- [Done] Full UCSD Ped2 token/rule training.
- [Done] Full UCSD Ped2 scoring with rules.
- [Done] Visualization smoke for SPEC 4 compatibility.
- [Done] Refresh `repomix-output.xml` after final checks.

## Files Changed

- `src/configs/ucsd_ped2.yaml`
- `src/configs/ucsd_ped1.yaml`
- `src/configs/avenue.yaml`
- `src/kpdl_anomaly/config.py`
- `src/kpdl_anomaly/schema.py`
- `src/kpdl_anomaly/tokenization.py`
- `src/kpdl_anomaly/association.py`
- `src/kpdl_anomaly/rule_model.py`
- `src/kpdl_anomaly/rule_scoring.py`
- `src/kpdl_anomaly/scoring.py`
- `src/kpdl_anomaly/alerts.py`
- `src/kpdl_anomaly/test.py`
- `src/rules.py`
- `src/doc/spec_5_processed.md`

## Verification Evidence

- [Done] `python -m compileall src\kpdl_anomaly src\rules.py src\test.py`
  - Result: compile completed successfully.
- [Done] `python src\rules.py --config src\configs\ucsd_ped2.yaml --model src\outputs\models\ucsd_ped2 --output-dir src\outputs\rules\ucsd_ped2_smoke --limit-rows 50000`
  - Result: `50000` transactions, `12877` itemsets, `200` rules.
- [Done] `python src\test.py --config src\configs\ucsd_ped2.yaml --model src\outputs\models\ucsd_ped2 --rules src\outputs\rules\ucsd_ped2_smoke --result-root src\outputs\results_smoke_rules --limit-rows 50000`
  - Result: `50000` rows scored, `261` frames, `1` alert, rules active.
- [Done] `python src\test.py --config src\configs\ucsd_ped2.yaml --model src\outputs\models\ucsd_ped2 --no-rules --result-root src\outputs\results_smoke_no_rules --limit-rows 50000`
  - Result: `50000` rows scored, SPEC 3 score columns only, first row score remains `0.39380409`.
- [Done] `python src\rules.py --config src\configs\ucsd_ped2.yaml --model src\outputs\models\ucsd_ped2`
  - Result: `477312` transactions, `13932` itemsets, `200` rules, no warnings.
- [Done] `python src\test.py --config src\configs\ucsd_ped2.yaml --model src\outputs\models\ucsd_ped2 --rules src\outputs\rules\ucsd_ped2`
  - Result: `376704` rows scored, `1962` frames, severity `none=844`, `medium=1118`, `high=0`, alerts `17`, rules active.
- [Done] Range check on full `cell_scores.csv`
  - Result: `376704` rows, `0` out-of-range values; `cell_score=[0.0897185, 0.9734689]`, `rare_token_score=[0.83176622, 1.0]`, `rule_violation_score=[0.0, 1.0]`.
- [Done] Alert reason check
  - Result: `alerts.json` includes token support reasons and rule violation reasons.
- [Done] Support/confidence sweep smoke
  - `min_support=0.005`, `min_confidence=0.60`, `limit_rows=50000`: `12877` itemsets, `200` rules.
  - `min_support=0.010`, `min_confidence=0.60`, `limit_rows=50000`: `12877` itemsets, `200` rules.
  - `min_support=0.020`, `min_confidence=0.70`, `limit_rows=50000`: `12877` itemsets, `200` rules.
- [Done] `python src\visualize.py --config src\configs\ucsd_ped2.yaml --top-frames 5 --output-dir src\outputs\visualizations\ucsd_ped2_spec5_top`
  - Result: 5 images written, 0 missing frames, 0 missing cell score frames.
- [Done] `python src\visualize.py --config src\configs\ucsd_ped2.yaml --alerts --limit-frames 5 --output-dir src\outputs\visualizations\ucsd_ped2_spec5_alerts`
  - Result: 5 images written, 0 missing frames, 0 missing cell score frames.
- [Done] Automated OpenCV visualization validation
  - Result: 10 images checked, 0 missing, 0 blank.
- [Done] `repomix.cmd`
  - Result: Repomix v1.14.0 packed 69 files successfully and wrote `repomix-output.xml`.

## Generated Artifacts

- `src/outputs/rules/ucsd_ped2/rule_manifest.json`
- `src/outputs/rules/ucsd_ped2/token_bins.json`
- `src/outputs/rules/ucsd_ped2/itemsets.json`
- `src/outputs/rules/ucsd_ped2/rules.json`
- `src/outputs/rules/ucsd_ped2/token_stats.json`
- `src/outputs/rules/ucsd_ped2/selected_rules.md`
- `src/outputs/results/ucsd_ped2/cell_scores.csv`
- `src/outputs/results/ucsd_ped2/frame_scores.csv`
- `src/outputs/results/ucsd_ped2/alerts.json`
- `src/outputs/results/ucsd_ped2/scoring_stats.json`

## Remaining Risks

- Full support/confidence sweep was not run for all three settings; the sweep evidence is smoke-sized at `50000` rows to keep runtime controlled.
- Direction tokens remain disabled because current preprocessing uses frame differencing, as requested by SPEC 5.
- Rare token score is intentionally a weak weighted signal, but many UCSD Ped2 test cell/cube combinations are rare under the chosen cell-specific itemsets; future metric work should tune support thresholds and weights.
