# SPEC 9 Processed

Original spec: `src/doc/spec_9.md`

Processed at: `2026-05-27T19:43:18+07:00`

## Progress Checklist

- Done: Read PRD, `repomix-output.xml`, and `src/doc/spec_9.md`.
- Done: Added `src/kpdl_anomaly/cluster_profiles.py`.
- Done: Load model/scaler/threshold artifacts.
- Done: Inverse-transform KMeans centroids to original feature scale.
- Done: Assign centroid token summaries when compatible `token_bins.json` is available.
- Done: Load cluster support from threshold `cluster_sizes` when available.
- Done: Write `cluster_profiles.json`.
- Done: Write compact `cluster_profiles.md`.
- Done: Added `src/kpdl_anomaly/explanations.py`.
- Done: Load rule artifacts and create `rule_evidence_index.json`.
- Done: Load `cell_scores.csv`, `frame_scores.csv`, and `alerts.json`.
- Done: Join cluster profile evidence with top cell scores.
- Done: Join rare itemset and violated-rule evidence when rule columns exist.
- Done: Create plain-language reason strings.
- Done: Added `src/kpdl_anomaly/casebook.py`.
- Done: Select cases from alert peaks or top-frame fallback.
- Done: Attach overlay paths from `visualization_index.json`, with alert-range fallback.
- Done: Write `alert_casebook.json`.
- Done: Write `alert_casebook.md`.
- Done: Write `analysis_manifest.json`.
- Done: Added CLI `src/explain.py`.
- Done: Compile verification passed.
- Done: Smoke UCSD Ped2 with rules passed.
- Done: Smoke no-rules fallback passed.
- Done: Smoke optical-flow artifact passed; direction evidence is preserved.
- Done: JSON validation passed for all smoke outputs.
- Done: Refreshed root `repomix-output.xml` with `repomix.cmd`.

## Files Changed

- `src/kpdl_anomaly/cluster_profiles.py`
- `src/kpdl_anomaly/explanations.py`
- `src/kpdl_anomaly/casebook.py`
- `src/explain.py`
- `src/doc/spec_9_processed.md`

## Verification Evidence

- `python -m compileall src\kpdl_anomaly src\explain.py` passed.
- `python src\explain.py --config src\configs\ucsd_ped2.yaml --model src\outputs\models\ucsd_ped2 --rules src\outputs\rules\ucsd_ped2 --results src\outputs\results\ucsd_ped2 --visualizations src\outputs\visualizations\ucsd_ped2 --output-dir src\outputs\analysis\ucsd_ped2_smoke --top-alerts 5` passed with 5 cases and 0 warnings.
- `python src\explain.py --config src\configs\ucsd_ped2.yaml --model src\outputs\models\ucsd_ped2 --results src\outputs\results_spec6_no_rules\ucsd_ped2 --no-rules --output-dir src\outputs\analysis\ucsd_ped2_no_rules_smoke --top-frames 5` passed with 5 cases and expected no-rules warnings.
- `python src\explain.py --config src\configs\ucsd_ped2_optical_flow.yaml --model src\outputs\models_spec7_flow\ucsd_ped2 --rules src\outputs\rules_spec7_flow\ucsd_ped2 --results src\outputs\results_spec7_flow\ucsd_ped2 --output-dir src\outputs\analysis\ucsd_ped2_flow_smoke --top-frames 5` passed with 5 cases and expected missing-visualization warnings.
- JSON validation passed for `cluster_profiles.json` and `alert_casebook.json` in all smoke outputs, including support/score bounds and flow `direction=` evidence.
- `repomix.cmd` completed successfully and refreshed root `repomix-output.xml`.

## Remaining Risks

- Some smoke output directories are debug artifacts under `src/outputs/analysis/*_smoke`.
- Optical-flow visualization artifacts are not present, so the flow smoke records warnings for missing overlay images.
