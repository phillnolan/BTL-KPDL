# SPEC 4 Processed - Heatmap overlay and qualitative anomaly review

Original spec path: `src/doc/spec_4.md`

Date/time processed: 2026-05-26 23:58:44 +07:00

## Summary

Implementation is complete for SPEC 4. The scope is a visualization layer over existing SPEC 3 outputs: heatmap PNGs, alert peak images, overlay videos, JSON index/stats, and a qualitative Markdown report. The scoring formula is unchanged.

2026-05-27 re-check: SPEC 4 is complete in the live repository. No source changes were required during this check; only verification artifacts were regenerated under separate `src/outputs/visualizations/ucsd_ped2_codex_*` folders and `repomix-output.xml` was refreshed.

## Checklist

- [Done] Read PRD, `repomix-output.xml`, and `src/doc/spec_4.md`.
- [Done] Inspect current SPEC 3 result schemas and preprocessing frame readers.
- [Done] Add `visualization` config defaults to dataset YAML files.
- [Done] Add `src/kpdl_anomaly/frames.py` for preprocessed test frame lookup.
- [Done] Add `src/kpdl_anomaly/visualization.py` for score loading, heatmap rendering, PNG/MP4 export, index, and stats.
- [Done] Add `src/kpdl_anomaly/qualitative.py` for Markdown report generation.
- [Done] Add CLI entrypoint `src/visualize.py`.
- [Done] Run compile and smoke visualization commands.
- [Done] Validate generated images/videos are readable and nonblank.
- [Done] Refresh `repomix-output.xml` after verification passes.

## Files Changed

- `src/configs/ucsd_ped2.yaml`
- `src/configs/ucsd_ped1.yaml`
- `src/configs/avenue.yaml`
- `src/kpdl_anomaly/frames.py`
- `src/kpdl_anomaly/visualization.py`
- `src/kpdl_anomaly/qualitative.py`
- `src/visualize.py`
- `src/doc/spec_4_processed.md`

## Verification Evidence

- [Done] `python -m compileall src\kpdl_anomaly src\visualize.py`
- [Done] `python src\visualize.py --config src\configs\ucsd_ped2.yaml --top-frames 5`
  - Result: 5 frames selected, 5 images written, 0 missing frames, 0 missing cell score frames.
- [Done] `python src\visualize.py --config src\configs\ucsd_ped2.yaml --alerts --limit-frames 5`
  - Result: 5 alert peak frames selected, 5 images written, 0 missing frames, 0 missing cell score frames.
- [Done] `python src\visualize.py --config src\configs\ucsd_ped2.yaml --video-id Test001 --start-frame 150 --end-frame 180 --write-video --limit-frames 10`
  - Result: 1 overlay video written, 0 missing frames, 0 missing cell score frames.
- [Done] `python src\visualize.py --config src\configs\ucsd_ped2.yaml --top-frames 5 --alerts --video-id Test001 --start-frame 150 --end-frame 180 --write-video --limit-frames 10`
  - Final artifact set: 15 images and 1 video in `src/outputs/visualizations/ucsd_ped2`.
- [Done] Automated artifact validation with OpenCV.
  - Result: 15 index image paths exist, no blank images, 1 video opens, 0 missing frames, 0 missing cell score frames.
- [Done] Scoped whitespace check: `git diff --check -- src\configs\ucsd_ped2.yaml src\configs\ucsd_ped1.yaml src\configs\avenue.yaml src\kpdl_anomaly\frames.py src\kpdl_anomaly\visualization.py src\kpdl_anomaly\qualitative.py src\visualize.py src\doc\spec_4_processed.md`
  - Result: no whitespace errors in files changed for SPEC 4; Git reported only LF-to-CRLF warnings for YAML files.
- [Blocked] Full `git diff --check`
  - Reason: generated `repomix-output.xml` has trailing whitespace from packed LaTeX/KMeans text sections after the final SPEC 4 repomix refresh; scoped SPEC 4 source files are clean.
- [Done] `repomix.cmd`
  - Result: Repomix v1.14.0 packed 62 files successfully and wrote `repomix-output.xml`.

## 2026-05-27 Re-check Evidence

- [Done] `python -m compileall src\kpdl_anomaly src\visualize.py`
  - Result: compile completed successfully.
- [Done] `python src\visualize.py --config src\configs\ucsd_ped2.yaml --top-frames 5 --output-dir src\outputs\visualizations\ucsd_ped2_codex_verify_top`
  - Result: 5 frames selected, 5 images written, 0 missing frames, 0 missing cell score frames.
- [Done] `python src\visualize.py --config src\configs\ucsd_ped2.yaml --alerts --limit-frames 5 --output-dir src\outputs\visualizations\ucsd_ped2_codex_verify_alerts`
  - Result: 5 alert peak frames selected, 5 images written, 0 missing frames, 0 missing cell score frames.
- [Done] `python src\visualize.py --config src\configs\ucsd_ped2.yaml --video-id Test001 --start-frame 150 --end-frame 180 --write-video --limit-frames 10 --output-dir src\outputs\visualizations\ucsd_ped2_codex_verify_video`
  - Result: 1 overlay video written, 0 missing frames, 0 missing cell score frames.
- [Done] Acceptance run: top 30 frames, all 16 alert peaks, and one `Test001` overlay video were exported to `src/outputs/visualizations/ucsd_ped2_codex_accept_*`.
- [Done] Automated OpenCV validation.
  - Result: 46 acceptance images exist and are nonblank; `Test001_overlay.mp4` opens and contains 29 frames, matching `visualization_stats.json`.
- [Done] `git diff --check -- src\configs\ucsd_ped2.yaml src\configs\ucsd_ped1.yaml src\configs\avenue.yaml src\kpdl_anomaly\frames.py src\kpdl_anomaly\visualization.py src\kpdl_anomaly\qualitative.py src\visualize.py src\doc\spec_4_processed.md`
  - Result: no whitespace errors.
- [Done] `repomix.cmd`
  - Result: Repomix v1.14.0 packed 62 files successfully and wrote `repomix-output.xml`.

## Remaining Risks

- Full Avenue visualization is not verified yet; SPEC 4 smoke verification focuses on UCSD Ped2 artifacts from SPEC 3.
- MVP supports `visualization.frame_source: preprocessed`; original-frame coordinate scaling is intentionally left for a later extension.
