# SPEC 6 - Đánh giá định lượng ROC-AUC/EER với ground truth UCSD

## 1. Mục tiêu

SPEC 6 bổ sung lớp đánh giá định lượng cho pipeline anomaly sau SPEC 3, SPEC 4 và SPEC 5.

Mục tiêu chính:

- đọc `frame_scores.csv` từ kết quả test;
- map frame-level ground truth của UCSD Ped1/Ped2 bằng mask `_gt` hoặc file `UCSDped*.m`;
- tính ROC-AUC, PR-AUC, EER, best F1 cho `frame_score` và `smoothed_frame_score`;
- xuất `frame_labels.csv`, `metrics.json`, `metrics_summary.md`;
- so sánh baseline không dùng rule với kết quả có token/rule từ SPEC 5.

## 2. Liên hệ với PRD và các spec trước

PRD yêu cầu có metric định lượng như frame-level ROC-AUC, PR-AUC, EER, false positive rate và recall. SPEC 3 tạo score baseline, SPEC 4 giúp kiểm tra định tính, SPEC 5 thêm rare token/rule score. SPEC 6 là bước đo chính thức xem các score đó bám ground truth tốt đến đâu.

## 3. Phạm vi MVP

Trong phạm vi:

- UCSD Ped2 là dataset ưu tiên;
- hỗ trợ UCSD Ped1 nếu có score tương ứng;
- đánh giá ở frame level;
- dùng mask ground truth nếu có, fallback sang khoảng `gt_frame` trong file MATLAB;
- đánh giá `frame_score` và `smoothed_frame_score`;
- comparison giữa hai thư mục result, ví dụ `no_rules` và `with_rules`.

Ngoài phạm vi:

- pixel-level ROC;
- object-level localization metric;
- tối ưu threshold/model theo kết quả metric;
- dashboard.

## 4. Input và output

Input chính:

```text
src/outputs/results/{dataset}/frame_scores.csv
src/dataset/UCSD_Anomaly_Dataset.v1p2/UCSDped*/Test/*_gt
src/dataset/UCSD_Anomaly_Dataset.v1p2/UCSDped*/Test/UCSDped*.m
```

Output:

```text
src/outputs/evaluation/{dataset}/
  frame_labels.csv
  metrics.json
  metrics_summary.md

src/outputs/evaluation/{dataset}/comparison/
  comparison.json
  comparison_summary.md
```

## 5. CLI

Đánh giá một result dir:

```bash
python src/evaluate.py --config src/configs/ucsd_ped2.yaml --results src/outputs/results/ucsd_ped2
```

So sánh không rule và có rule:

```bash
python src/evaluate.py ^
  --config src/configs/ucsd_ped2.yaml ^
  --baseline-results src/outputs/results_spec6_no_rules/ucsd_ped2 ^
  --candidate-results src/outputs/results_spec6_rules/ucsd_ped2 ^
  --baseline-name no_rules ^
  --candidate-name with_rules ^
  --output-dir src/outputs/evaluation/ucsd_ped2/spec6_compare
```

## 6. Checklist triển khai

- [ ] Tạo module `src/kpdl_anomaly/evaluation.py`.
- [ ] Tạo CLI `src/evaluate.py`.
- [ ] Load ground truth UCSD từ mask `_gt`.
- [ ] Fallback sang `UCSDped*.m` khi thiếu mask.
- [ ] Align score với label theo `video_id` và `frame_id`.
- [ ] Tính ROC-AUC, PR-AUC, EER, best F1.
- [ ] Xuất `frame_labels.csv`, `metrics.json`, `metrics_summary.md`.
- [ ] Thêm comparison giữa hai result dir.
- [ ] Chạy baseline no-rules và candidate with-rules trên UCSD Ped2.
- [ ] Cập nhật `src/doc/spec_6_processed.md`.
- [ ] Refresh `repomix-output.xml` sau verification pass.

## 7. Tiêu chí hoàn thành

SPEC 6 hoàn thành khi:

- CLI evaluation chạy được trên UCSD Ped2;
- metric có đủ positive và negative frame;
- output ghi rõ số frame labeled/unlabeled;
- comparison no-rules vs with-rules có delta ROC-AUC/EER;
- processed file ghi rõ file thay đổi, lệnh verification và kết quả.
