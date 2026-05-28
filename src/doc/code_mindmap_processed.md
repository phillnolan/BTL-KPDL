# Code Mindmap Processed - Pipeline cleanup

Original spec path: `src/doc/code_mindmap.md`

Processed at: `2026-05-29T03:04:09+07:00`

## Checklist

- [Done] Read PRD before implementation.
- [Done] Read root `repomix-output.xml`.
- [Done] Read `src/doc/code_mindmap.md`.
- [Done] Removed LaTeX/report generator files from the runtime codebase.
- [Done] Removed ARFF/WEKA export files and CLI flags from preprocessing.
- [Done] Removed evaluation comparison mode while keeping single-result metrics.
- [Done] Removed historical WEKA/tuning/LaTeX-only spec files that no longer describe the active pipeline.
- [Done] Updated `src/doc/code_mindmap.md` to match the remaining pipeline.
- [Done] Run verification commands.
- [Done] Refresh root `repomix-output.xml`.

## Files changed

- `.gitignore`
- `src/configs/*.yaml`
- `src/kpdl_preprocess/cli.py`
- `src/kpdl_preprocess/pipeline.py`
- `src/tool/_common.py`
- `src/kpdl_anomaly/evaluate_cli.py`
- `src/kpdl_anomaly/evaluation.py`
- `src/doc/code_mindmap.md`
- Removed `latex/`
- Removed `src/csv_to_arff.py`, `src/kpdl_preprocess/arff.py`, `src/kpdl_preprocess/arff_cli.py`
- Removed `src/report.py`, `src/kpdl_anomaly/reporting.py`
- Removed obsolete docs: `src/doc/Kmean.md`, `src/doc/spec_2*.md`, `src/doc/spec_8*.md`, `src/doc/spec_10*.md`
- Removed duplicate packed snapshot `src/repomix-output.xml`

## Verification

- `python -m compileall src` passed.
- `python src\preprocess.py --help` passed and no longer shows `--export-arff`.
- `python src\evaluate.py --help` passed and no longer shows baseline/candidate comparison flags.
- `python src\preprocess.py --config src\configs\ucsd_ped2.yaml --output-root src\outputs\cleanup_smoke --limit-videos 1 --limit-frames 6 --progress-every 0` passed and wrote CSV/manifest artifacts.
- `python src\evaluate.py --config src\configs\ucsd_ped2.yaml --results src\outputs\results\ucsd_ped2 --output-dir src\outputs\evaluation\cleanup_smoke` passed for one result directory.
- `git diff --check` passed with only existing LF-to-CRLF warnings from Git on Windows.
- `repomix` PowerShell shim was blocked by execution policy, so `C:\Users\Dell\AppData\Roaming\npm\repomix.cmd` was used successfully.
- Root `repomix-output.xml` was refreshed; removed files no longer appear as `<file path=...>` entries.
