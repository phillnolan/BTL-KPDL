# SPEC 7 Processed - Optical flow direction features and direction tokens

Original spec path: `src/doc/spec_7.md`

Date/time processed: 2026-05-27 16:13:18 +07:00

## Summary

Implemented SPEC 7 as a Farneback optical-flow feature path with real `direction_hist_*` values and direction-aware token/rule scoring. A separate UCSD Ped2 optical-flow config proves the path without replacing the existing `frame_diff` config. SPEC 6 comparison work was intentionally skipped.

2026-05-27 16:22:08 +07:00 re-check: SPEC 7 remains complete in the live repository. No source edits were required during this pass; verification artifacts were regenerated under the existing SPEC 7 output folders and `repomix-output.xml` was refreshed after verification.

## Checklist

- [Done] Read PRD and root `repomix-output.xml`.
- [Done] Read SPEC 5 context that left direction tokens for SPEC 7.
- [Done] Create `src/doc/spec_7.md`.
- [Done] Add Farneback optical-flow feature extraction while preserving `frame_diff`.
- [Done] Add direction token labels and direction-aware rare itemsets.
- [Done] Add `src/configs/ucsd_ped2_optical_flow.yaml`.
- [Done] Compile Python modules.
- [Done] Run UCSD Ped2 optical-flow smoke preprocessing.
- [Done] Verify `direction_hist_*` has nonzero signal.
- [Done] Train KMeans with direction feature columns.
- [Done] Train token/rule artifact with direction tokens.
- [Done] Score test rows with direction-aware rules.
- [Done] Verify `frame_diff` compatibility with zero direction histogram.
- [Done] Refresh `repomix-output.xml`.

## Files Changed

- `src/kpdl_preprocess/features.py`
- `src/kpdl_preprocess/config.py`
- `src/kpdl_preprocess/schema.py`
- `src/kpdl_anomaly/tokenization.py`
- `src/kpdl_anomaly/rule_model.py`
- `src/kpdl_anomaly/rule_scoring.py`
- `src/configs/ucsd_ped2_optical_flow.yaml`
- `src/doc/spec_7.md`
- `src/doc/spec_7_processed.md`

## Verification Evidence

- [Done] `python -m compileall src\kpdl_preprocess src\kpdl_anomaly src\preprocess.py src\train.py src\rules.py src\test.py`
  - Result: compile completed successfully.
- [Done] `python src\preprocess.py --config src\configs\ucsd_ped2_optical_flow.yaml --limit-videos 1 --limit-frames 65 --progress-every 0`
  - Result: train/test each processed `1` video, `65` frames, `61` cubes, `11712` feature rows.
- [Done] Direction histogram validation on `src/outputs/preprocessed_spec7_flow/ucsd_ped2/features_train.csv`
  - Result: `11712` rows checked, `6602` rows had nonzero direction histograms, `0` bad histogram sums, first nonzero row was `cell_id=00_00`, `cube_id=Train001_000001_000005`.
- [Done] `python src\train.py --config src\configs\ucsd_ped2_optical_flow.yaml`
  - Result: `192` cell models trained, `0` fallback cells, `11712` train rows loaded.
- [Done] `python src\rules.py --config src\configs\ucsd_ped2_optical_flow.yaml --model src\outputs\models_spec7_flow\ucsd_ped2`
  - Result: `11712` transactions, `17840` itemsets, `200` rules, no warnings.
- [Done] Direction token schema check
  - Result: rule manifest has `include_direction_token=true`, token schema includes `direction`, and sample tokens include `direction=up` and `direction=down`.
- [Done] `python src\test.py --config src\configs\ucsd_ped2_optical_flow.yaml --model src\outputs\models_spec7_flow\ucsd_ped2 --rules src\outputs\rules_spec7_flow\ucsd_ped2`
  - Result: `11712` rows scored, `61` frames, rules active, `1` alert.
- [Done] Direction token scoring check
  - Result: `6940` of `11712` scored rows include a `direction=...` token.
- [Done] `python src\preprocess.py --config src\configs\ucsd_ped2.yaml --split train --limit-videos 1 --limit-frames 8 --output-root src\outputs\preprocessed_spec7_frame_diff_smoke --progress-every 0`
  - Result: baseline `frame_diff` still processed `768` rows.
- [Done] Frame-diff compatibility check
  - Result: `0` of `768` baseline `frame_diff` rows had nonzero direction histogram values.
- [Done] `git diff --check -- src\kpdl_preprocess\features.py src\kpdl_preprocess\config.py src\kpdl_preprocess\schema.py src\kpdl_anomaly\tokenization.py src\kpdl_anomaly\rule_model.py src\kpdl_anomaly\rule_scoring.py src\configs\ucsd_ped2_optical_flow.yaml src\doc\spec_7.md src\doc\spec_7_processed.md`
  - Result: no whitespace errors; Git reported only LF-to-CRLF warnings.
- [Done] `repomix.cmd`
  - Result: Repomix v1.14.0 packed `77` files successfully and wrote `repomix-output.xml`.

## Re-Verification Evidence - 2026-05-27 16:22:08 +07:00

- [Done] `python -m compileall src\kpdl_preprocess src\kpdl_anomaly src\preprocess.py src\train.py src\rules.py src\test.py`
  - Result: compile completed successfully.
- [Done] `python src\preprocess.py --config src\configs\ucsd_ped2_optical_flow.yaml --limit-videos 1 --limit-frames 65 --progress-every 0`
  - Result: train/test each processed `1` video, `65` frames, `61` cubes, `11712` feature rows.
- [Done] Direction histogram validation on `src\outputs\preprocessed_spec7_flow\ucsd_ped2\features_train.csv`
  - Result: `11712` rows checked, `6602` rows had nonzero direction histograms, `0` bad histogram sums, first nonzero row was `cell_id=00_00`, `cube_id=Train001_000001_000005`.
- [Done] `python src\train.py --config src\configs\ucsd_ped2_optical_flow.yaml`
  - Result: `192` cell models trained, `0` fallback cells, `11712` train rows loaded.
- [Done] `python src\rules.py --config src\configs\ucsd_ped2_optical_flow.yaml --model src\outputs\models_spec7_flow\ucsd_ped2`
  - Result: `11712` transactions, `17840` itemsets, `200` rules, no warnings.
- [Done] Direction token schema check
  - Result: rule manifest has `include_direction_token=true`, token schema includes `direction`, and generated artifacts include `direction=...` tokens.
- [Done] `python src\test.py --config src\configs\ucsd_ped2_optical_flow.yaml --model src\outputs\models_spec7_flow\ucsd_ped2 --rules src\outputs\rules_spec7_flow\ucsd_ped2`
  - Result: `11712` rows scored, `61` frames, rules active, `1` alert.
- [Done] Direction token scoring check
  - Result: `6940` of `11712` scored rows include a `direction=...` token.
- [Done] `python src\preprocess.py --config src\configs\ucsd_ped2.yaml --split train --limit-videos 1 --limit-frames 8 --output-root src\outputs\preprocessed_spec7_frame_diff_smoke --progress-every 0`
  - Result: baseline `frame_diff` still processed `768` rows.
- [Done] Frame-diff compatibility check
  - Result: `0` of `768` baseline `frame_diff` rows had nonzero direction histogram values.
- [Done] `git diff --check -- src\kpdl_preprocess\features.py src\kpdl_preprocess\config.py src\kpdl_preprocess\schema.py src\kpdl_anomaly\tokenization.py src\kpdl_anomaly\rule_model.py src\kpdl_anomaly\rule_scoring.py src\configs\ucsd_ped2_optical_flow.yaml src\doc\spec_7.md src\doc\spec_7_processed.md`
  - Result: no whitespace errors; Git reported only LF-to-CRLF warnings.
- [Done] `repomix.cmd`
  - Result: Repomix v1.14.0 packed `77` files successfully and wrote `repomix-output.xml`.

## Generated Artifacts

- `src/outputs/preprocessed_spec7_flow/ucsd_ped2/`
- `src/outputs/models_spec7_flow/ucsd_ped2/`
- `src/outputs/rules_spec7_flow/ucsd_ped2/`
- `src/outputs/results_spec7_flow/ucsd_ped2/`
- `src/outputs/preprocessed_spec7_frame_diff_smoke/ucsd_ped2/`

## Remaining Risks

- Smoke verification uses one UCSD Ped2 train video and one test video. Full-dataset optical-flow preprocessing is intentionally left for a longer run because Farneback is slower than `frame_diff`.
- The direction labels follow image coordinates: `right`, `down_right`, `down`, `down_left`, `left`, `up_left`, `up`, `up_right`.
