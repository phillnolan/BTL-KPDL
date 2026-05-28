# SRC Runtime Root Processed

Original spec path: user request to run all commands from `src`.

Processed at: `2026-05-29T04:06:55+07:00`

## Checklist

- [Done] Read PRD before implementation.
- [Done] Read root `repomix-output.xml`.
- [Done] Inspected live CLI/config files that resolve dataset and output paths.
- [Done] Updated configs so relative paths are rooted at `src` instead of `Project`.
- [Done] Updated CLI defaults so `--project-root` resolves to the `src` directory.
- [Done] Updated preprocessing documentation for the new runtime-root convention.
- [Done] Run verification from inside `src`.
- [Done] Refresh root `repomix-output.xml`.

## Files changed

- `src/configs/avenue.yaml`
- `src/configs/ucsd_ped1.yaml`
- `src/configs/ucsd_ped2.yaml`
- `src/configs/ucsd_ped2_optical_flow.yaml`
- `src/requirements.txt`
- `src/kpdl_preprocess/cli.py`
- `src/kpdl_preprocess/config.py`
- `src/kpdl_preprocess/features.py`
- `src/kpdl_preprocess/readers.py`
- `src/kpdl_anomaly/config.py`
- `src/kpdl_anomaly/train.py`
- `src/kpdl_anomaly/test.py`
- `src/kpdl_anomaly/evaluate_cli.py`
- `src/kpdl_anomaly/evaluation.py`
- `src/kpdl_anomaly/visualization.py`
- `src/rules.py`
- `src/visualize.py`
- `src/explain.py`
- `src/tool/_common.py`
- `src/tool/preprocess_ucsd.py`
- `src/tool/preprocess_avenue.py`
- `src/doc/preprocessing_data.md`
- `src/doc/src_runtime_root_processed.md`

## Verification

- `python -m compileall kpdl_preprocess kpdl_anomaly preprocess.py train.py test.py rules.py visualize.py evaluate.py explain.py` passed from `src`.
- CLI help passed from `src` for `preprocess.py`, `train.py`, `test.py`, `rules.py`, `visualize.py`, `evaluate.py`, `explain.py`, `tool\preprocess_ucsd.py`, and `tool\preprocess_avenue.py`.
- `python preprocess.py --config configs\ucsd_ped2.yaml --limit-videos 1 --limit-frames 12 --progress-every 0` passed from `src` and wrote to `outputs\preprocessed\ucsd_ped2`.
- `python train.py --config configs\ucsd_ped2.yaml --model-root outputs\src_root_models_smoke --limit-rows 1000` passed from `src`.
- `python test.py --config configs\ucsd_ped2.yaml --model outputs\src_root_models_smoke\ucsd_ped2 --result-root outputs\src_root_results_smoke --limit-rows 1000 --no-rules` passed from `src`.
- `python evaluate.py --config configs\ucsd_ped2.yaml --results outputs\src_root_results_smoke\ucsd_ped2 --output-dir outputs\src_root_evaluation_smoke` passed from `src`.
- Removed accidental generated directory `src\src` from the previous bad path run.
- `git diff --check` passed with only LF-to-CRLF warnings.
- `C:\Users\Dell\AppData\Roaming\npm\repomix.cmd` passed and refreshed root `repomix-output.xml`.
