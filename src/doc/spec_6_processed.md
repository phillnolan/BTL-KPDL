# SPEC 6 Processed - Quantitative UCSD evaluation

Original spec path: `src/doc/spec_6.md`

Date/time processed: 2026-05-27 15:58:32 +07:00

## Summary

Implemented SPEC 6 as a frame-level quantitative evaluation workflow for UCSD ground truth. The project now evaluates `frame_scores.csv` against UCSD mask/interval labels, writes metrics artifacts, and compares no-rules vs with-rules result directories.

## Checklist

- [Done] Read PRD, root `repomix-output.xml`, and prior SPEC 3/4/5 references to derive SPEC 6 because `src/doc/spec_6.md` was absent.
- [Done] Create `src/doc/spec_6.md`.
- [Done] Add evaluation module and CLI.
- [Done] Load UCSD frame labels from `_gt` masks with `UCSDped*.m` interval fallback.
- [Done] Align scores and labels by `video_id` and `frame_id`.
- [Done] Compute ROC-AUC, PR-AUC, EER, best F1, and threshold diagnostics.
- [Done] Write `frame_labels.csv`, `metrics.json`, and `metrics_summary.md`.
- [Done] Add no-rules vs with-rules comparison output.
- [Done] Verify single-result evaluation.
- [Done] Verify no-rules vs with-rules comparison.
- [Done] Refresh `repomix-output.xml`.

## Files Changed

- `src/kpdl_anomaly/evaluation.py`
- `src/kpdl_anomaly/evaluate_cli.py`
- `src/evaluate.py`
- `src/configs/ucsd_ped2.yaml`
- `src/doc/spec_6.md`
- `src/doc/spec_6_processed.md`

## Verification Evidence

- [Done] `python -m compileall src\kpdl_anomaly src\evaluate.py`
  - Result: compile completed successfully.
- [Done] `python src\evaluate.py --config src\configs\ucsd_ped2.yaml --results src\outputs\results\ucsd_ped2 --output-dir src\outputs\evaluation\ucsd_ped2_smoke --score-columns frame_score --label-source auto`
  - Result: `1962` scored frames, `1962` labeled frames, `1616` positive, `346` negative, labels from masks, `frame_score ROC-AUC=0.766247`, `EER=0.294676`.
- [Done] `python src\evaluate.py --config src\configs\ucsd_ped2.yaml --results src\outputs\results\ucsd_ped2 --output-dir src\outputs\evaluation\ucsd_ped2_smoke_config_label --score-columns smoothed_frame_score`
  - Result: config `evaluation.label_source=auto` was used; `smoothed_frame_score ROC-AUC=0.766468`, `EER=0.300041`.
- [Done] `python src\test.py --config src\configs\ucsd_ped2.yaml --model src\outputs\models\ucsd_ped2 --no-rules --result-root src\outputs\results_spec6_no_rules`
  - Result: `376704` rows scored, `1962` frames, severity `none=795`, `medium=1167`, `high=0`, alerts `16`, rules inactive.
- [Done] `python src\test.py --config src\configs\ucsd_ped2.yaml --model src\outputs\models\ucsd_ped2 --rules src\outputs\rules\ucsd_ped2 --result-root src\outputs\results_spec6_rules`
  - Result: `376704` rows scored, `1962` frames, severity `none=844`, `medium=1118`, `high=0`, alerts `17`, rules active.
- [Done] `python src\evaluate.py --config src\configs\ucsd_ped2.yaml --baseline-results src\outputs\results_spec6_no_rules\ucsd_ped2 --candidate-results src\outputs\results_spec6_rules\ucsd_ped2 --baseline-name no_rules --candidate-name with_rules --output-dir src\outputs\evaluation\ucsd_ped2_spec6_compare`
  - Result: comparison artifacts written.
  - `frame_score`: ROC-AUC `0.765595 -> 0.766247`, delta `+0.000652`; EER `0.295812 -> 0.294676`, improvement `+0.001136`.
  - `smoothed_frame_score`: ROC-AUC `0.772427 -> 0.766468`, delta `-0.005959`; EER `0.297668 -> 0.300041`, improvement `-0.002373`.
- [Done] `repomix.cmd`
  - Result: Repomix v1.14.0 packed `74` files successfully and wrote `repomix-output.xml`.

## Generated Artifacts

- `src/outputs/evaluation/ucsd_ped2_smoke/`
- `src/outputs/evaluation/ucsd_ped2_smoke_config_label/`
- `src/outputs/results_spec6_no_rules/ucsd_ped2/`
- `src/outputs/results_spec6_rules/ucsd_ped2/`
- `src/outputs/evaluation/ucsd_ped2_spec6_compare/`

## Remaining Risks

- SPEC 6 is frame-level only; pixel-level localization metrics remain out of scope.
- With-rules improves raw `frame_score` only slightly and reduces smoothed ROC-AUC on this Ped2 run, so SPEC 8 should tune weights/smoothing before treating rule score as a metric win.
