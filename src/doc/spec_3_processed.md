# SPEC 3 Processed - Triển khai Python anomaly baseline

Spec gốc: `src/doc/spec_3.md`

Ngày xử lý: 2026-05-26 23:38:23 +07:00

## 1. Tóm tắt

Đã triển khai pipeline Python cho SPEC 3: train per-cell `StandardScaler` + `MiniBatchKMeans`, lưu model artifact, score test features, tổng hợp frame score, smoothing theo video và sinh alert JSON có reason tối thiểu.

Dataset xác minh chính: `ucsd_ped2`.

## 2. Checklist triển khai

- [Done] Bổ sung dependency `scikit-learn` và `joblib`.
- [Done] Tạo package `src/kpdl_anomaly/`.
- [Done] Tạo loader đọc feature CSV và validate schema.
- [Done] Tạo feature selector dùng baseline feature, bỏ `direction_hist_0..7`.
- [Done] Tạo train per-cell scaler + `MiniBatchKMeans`.
- [Done] Tạo threshold percentile theo train distance.
- [Done] Lưu model artifact bằng joblib/JSON.
- [Done] Tạo test scorer đọc model và feature test.
- [Done] Xuất `cell_scores.csv`.
- [Done] Tổng hợp `frame_scores.csv` bằng top-k mean.
- [Done] Thêm smoothing theo video.
- [Done] Sinh `alerts.json` với reason tối thiểu.
- [Done] Thêm CLI `src/train.py`.
- [Done] Thêm CLI `src/test.py`.
- [Done] Chạy smoke test với `--limit-rows`.
- [Done] Chạy full UCSD Ped2 train/test.
- [Done] Ghi `src/doc/spec_3_processed.md`.

## 3. File thay đổi

- `src/requirements.txt`
- `src/configs/ucsd_ped2.yaml`
- `src/train.py`
- `src/test.py`
- `src/kpdl_anomaly/__init__.py`
- `src/kpdl_anomaly/config.py`
- `src/kpdl_anomaly/io.py`
- `src/kpdl_anomaly/schema.py`
- `src/kpdl_anomaly/feature_selection.py`
- `src/kpdl_anomaly/modeling.py`
- `src/kpdl_anomaly/thresholds.py`
- `src/kpdl_anomaly/scoring.py`
- `src/kpdl_anomaly/smoothing.py`
- `src/kpdl_anomaly/alerts.py`
- `src/kpdl_anomaly/train.py`
- `src/kpdl_anomaly/test.py`
- `src/doc/spec_3_processed.md`

## 4. Artifact sinh ra

Model:

- `src/outputs/models/ucsd_ped2/config.yaml`
- `src/outputs/models/ucsd_ped2/model_manifest.json`
- `src/outputs/models/ucsd_ped2/cell_models.joblib`
- `src/outputs/models/ucsd_ped2/cell_scalers.joblib`
- `src/outputs/models/ucsd_ped2/thresholds.json`
- `src/outputs/models/ucsd_ped2/feature_stats.json`

Result:

- `src/outputs/results/ucsd_ped2/cell_scores.csv`
- `src/outputs/results/ucsd_ped2/frame_scores.csv`
- `src/outputs/results/ucsd_ped2/alerts.json`
- `src/outputs/results/ucsd_ped2/scoring_stats.json`

## 5. Kết quả full UCSD Ped2

- Train rows read/loaded: `477312` / `477312`.
- Cell models trained: `192`.
- Fallback cells: `0`.
- K: `5`.
- Threshold percentile: `99.0`.
- Test rows scored: `376704`.
- Frame scores: `1962`.
- Severity counts: `none=795`, `medium=1167`, `high=0`.
- Alerts: `16`.
- Cell score range: `0.00099569` to `0.99361403`.
- Smoothed frame score range: `0.35047918` to `0.85956522`.

## 6. Verification

- [Done] `python -m compileall kpdl_anomaly train.py test.py`
- [Done] `python train.py --config configs\ucsd_ped2.yaml --model-root outputs\models_smoke --limit-rows 50000`
- [Done] `python test.py --config configs\ucsd_ped2.yaml --model outputs\models_smoke\ucsd_ped2 --result-root outputs\results_smoke --limit-rows 50000`
- [Done] `python train.py --config configs\ucsd_ped2.yaml`
- [Done] `python test.py --config configs\ucsd_ped2.yaml --model outputs\models\ucsd_ped2`
- [Done] Kiểm tra `cell_scores.csv` có `376704` dòng score.
- [Done] Kiểm tra `frame_scores.csv` có `1962` frame và score nằm trong `[0, 1]`.
- [Done] Kiểm tra `alerts.json` có reason tối thiểu gồm cell, threshold, nearest cluster và consecutive frames.
- [Done] `git diff --check` không báo lỗi whitespace; chỉ có cảnh báo line-ending LF/CRLF từ Git trên Windows.
- [Done] `repomix.cmd` chạy thành công từ repo root và refresh `repomix-output.xml`.

## 7. Rủi ro và follow-up

- SPEC 3 vẫn là baseline cluster/distance, chưa dùng `direction_hist_0..7`, token/rule, heatmap hoặc ground truth evaluation.
- Một số frame có severity medium khá nhiều; cần SPEC sau hoặc bước phân tích định tính để chọn threshold/smoothing phù hợp hơn.
- Smoke artifact/result được ghi vào `src/outputs/models_smoke` và `src/outputs/results_smoke`; các thư mục output đang nằm trong `.gitignore`.
