# SPEC 10 - Hoan thien bao cao LaTeX tu pipeline, heatmap va casebook

## 1. Muc tieu

SPEC 10 chuyen cac artifact da co sau SPEC 9 thanh noi dung bao cao co the bien dich bang LaTeX. Trong giai doan nay, trong tam khong phai la tao them thuat toan moi, ma la dong goi pipeline da co thanh bang chung ro rang cho bao cao: so do xu ly, bang cau hinh, bang ket qua, hinh heatmap, ho so cum, rule evidence va casebook canh bao.

Muc tieu chinh:

- cap nhat cau truc bao cao LaTeX de phan anh dung pipeline hien tai tu tien xu ly den phan cum, token/rule, scoring, visualization va explanation;
- tao hoac cap nhat cac section LaTeX doc duoc bang tieng Viet, co hinh/bang minh hoa lay tu artifact thuc te;
- chon mot tap case tieu bieu tu `alert_casebook.json`/`alert_casebook.md` de dua vao phan ket qua dinh tinh;
- dua `cluster_profiles.md/json` va `rule_evidence_index.json` thanh bang/chung cu ngan gon trong bao cao;
- dam bao moi nhan dinh trong bao cao deu co nguon artifact ro, khong phong dai thanh ket luan benchmark neu artifact khong ung ho;
- bien dich duoc `latex/main.tex` thanh PDF ma khong loi tham chieu, loi hinh anh hoac bang tran trang nghiem trong.

SPEC 10 khong mo them tuning, leaderboard, ablation runner hay workflow chon cau hinh tot nhat. Metric neu duoc dua vao bao cao chi dong vai tro kiem tra va mo ta, khong phai trong tam cua spec.

## 2. Lien he voi PRD va cac spec truoc

Theo PRD, ket qua ban giao can co:

- source code pipeline;
- cau hinh dataset;
- ket qua score dang CSV/JSON;
- video/frame visualization;
- bao cao thuc nghiem;
- phan tich uu/nhuoc diem;
- thao luan ve cach tiep can Lu et al. nhu tai lieu tham khao tu duy.

Trang thai sau cac spec truoc:

- SPEC 3 da co train/test per-cell KMeans va score artifact.
- SPEC 4 da co heatmap, top frame image, alert peak image, overlay video va qualitative report.
- SPEC 5 da co tokenization, association rules va rule-based scoring/reason.
- SPEC 6 da co evaluation artifact, dung nhu sanity check khi can.
- SPEC 7 da co optical-flow direction feature va direction token.
- SPEC 8 da bi skip de tranh mo rong tuning/leaderboard.
- SPEC 9 da co cluster profiles, structured explanations va alert casebook.

SPEC 10 vi vay la buoc report-ready: dua pipeline va bang chung dinh tinh vao `latex/` de hoan thien tai lieu bao cao.

## 3. Pham vi

### 3.1. Nam trong pham vi

- Doc cac artifact mac dinh hoac duoc chi dinh:
  - config YAML;
  - model manifest;
  - result CSV/JSON;
  - visualization index;
  - cluster profile;
  - rule evidence index;
  - alert casebook;
  - evaluation summary neu co.
- Tao thu muc artifact on dinh cho bao cao, vi du `latex/generated/ucsd_ped2/`.
- Copy hoac tham chieu cac hinh anh heatmap/alert peak can dung trong bao cao vao duong dan on dinh, vi du `latex/figures/ucsd_ped2/`.
- Tao cac bang LaTeX tu JSON/Markdown artifact:
  - bang cau hinh dataset/pipeline;
  - bang feature/token/rule;
  - bang cluster profile rut gon;
  - bang casebook tieu bieu;
  - bang metric neu co.
- Cap nhat `latex/main.tex` de include cac section moi.
- Tao/cap nhat cac file trong `latex/sections/`:
  - co so ly thuyet va huong tiep can;
  - thiet ke pipeline;
  - trien khai;
  - thuc nghiem va artifact;
  - ket qua dinh tinh;
  - thao luan va ket luan.
- Neu them script tu dong, tao CLI chay lai duoc de tao snippet LaTeX va manifest.
- Ghi warning ro khi artifact thieu thay vi chen noi dung gia.
- Bien dich PDF va kiem tra output render duoc.

### 3.2. Ngoai pham vi

- Khong train lai model neu khong can cho artifact bao cao.
- Khong thay doi cong thuc anomaly score.
- Khong thay doi threshold, smoothing hoac alert logic.
- Khong tao metric-driven comparison moi.
- Khong tu dong viet ket luan "tot hon" neu chi co smoke artifact.
- Khong them dashboard web.
- Khong dua raw JSON dai vao bao cao chinh; chi dung phu luc hoac bang tom tat.

## 4. Input va output

Input chinh:

```text
latex/main.tex
latex/sections/project_overview.tex

src/configs/ucsd_ped2.yaml

src/outputs/results/ucsd_ped2/
  frame_scores.csv
  cell_scores.csv
  alerts.json
  scoring_stats.json

src/outputs/visualizations/ucsd_ped2/
  visualization_index.json
  visualization_stats.json
  qualitative_report.md
  top_frames/*.png
  alerts/*.png
  videos/*.mp4

src/outputs/analysis/ucsd_ped2/
  cluster_profiles.json
  cluster_profiles.md
  rule_evidence_index.json
  alert_casebook.json
  alert_casebook.md
  analysis_manifest.json

src/outputs/evaluation/<dataset>/
  metrics.json
  metrics_summary.md
```

Neu artifact production chua co, co the dung smoke artifact da co, nhung bao cao phai ghi ro do la smoke/minh hoa:

```text
src/outputs/analysis/ucsd_ped2_smoke/
src/outputs/analysis/ucsd_ped2_flow_smoke/
```

Output de xuat:

```text
latex/generated/ucsd_ped2/
  report_artifacts_manifest.json
  pipeline_summary.tex
  config_table.tex
  metrics_table.tex
  cluster_profile_table.tex
  rule_evidence_table.tex
  casebook_cases.tex

latex/figures/ucsd_ped2/
  case_001_heatmap.png
  case_002_heatmap.png
  pipeline_overview.pdf hoac pipeline_overview.png

latex/sections/
  background.tex
  system_design.tex
  implementation.tex
  experiments.tex
  results_discussion.tex
  conclusion.tex

latex/main.pdf
```

Neu chon khong them generator script, van phai tao cac section LaTeX thu cong va ghi nguon artifact da dung trong processed file. Neu them generator script, output them:

```text
src/kpdl_anomaly/reporting.py
src/report.py
```

## 5. Nguyen tac noi dung bao cao

### 5.1. Bam artifact, khong doan

Moi cau ve ket qua thuc nghiem can dua tren artifact co san:

- score/frame/cell lay tu `frame_scores.csv` va `cell_scores.csv`;
- alert segment lay tu `alerts.json`;
- hinh minh hoa lay tu `visualization_index.json` hoac file anh ton tai;
- cluster profile lay tu `cluster_profiles.json`;
- rule evidence lay tu `rule_evidence_index.json`;
- metric lay tu `metrics.json` neu co.

Neu artifact thieu, ghi "chua co artifact" hoac "khong danh gia trong pham vi nay", khong viet thay bang ket luan tuong doi.

### 5.2. Phan biet ket qua dinh tinh va dinh luong

Bao cao can tach ro:

- ket qua dinh tinh: heatmap, casebook, reason text, rule evidence;
- ket qua dinh luong: ROC-AUC, PR-AUC, EER, FPS neu co;
- nhan xet nghien cuu: uu/nhuoc diem cua pipeline.

Token/rule trong du an chu yeu tang kha nang giai thich. Khong nen viet rang rule chac chan cai thien metric neu khong co bang chung da chay.

### 5.3. Giu van phong bao cao

- Viet tieng Viet ro rang, tranh liet ke log ky thuat qua dai.
- Moi hinh co caption va duong dan nguon artifact.
- Moi bang co caption, cot gon va khong tran trang.
- Neu can trich command, dua vao phu luc hoac doan ngan.
- Khong dua noise tu smoke/debug folder vao bao cao chinh neu co artifact production tot hon.

## 6. Cau truc bao cao de xuat

`latex/main.tex` nen include cac section theo thu tu:

```tex
\input{sections/project_overview.tex}
\input{sections/background.tex}
\input{sections/system_design.tex}
\input{sections/implementation.tex}
\input{sections/experiments.tex}
\input{sections/results_discussion.tex}
\input{sections/conclusion.tex}
```

### 6.1. `background.tex`

Noi dung:

- bai toan phat hien bat thuong trong video camera co dinh;
- ly do dung grid/cell va spatio-temporal cube;
- vai tro cua phan cum hanh vi binh thuong;
- vai tro cua token va association rule mining;
- Lu et al. chi la tai lieu tham khao ve tu duy xu ly nhanh va cau truc khong gian-thoi gian, khong phai muc tieu tai hien.

### 6.2. `system_design.tex`

Noi dung:

- so do pipeline tu video den alert/casebook;
- cac module:
  - input/preprocess;
  - grid/cube;
  - feature extraction;
  - per-cell clustering;
  - tokenization/rule mining;
  - scoring/smoothing;
  - visualization/explanation;
- cau hinh chinh tu YAML.

Nen co mot hinh pipeline, co the dung TikZ/LaTeX native de tranh phu thuoc anh ngoai.

### 6.3. `implementation.tex`

Noi dung:

- cau truc code trong `src/kpdl_preprocess` va `src/kpdl_anomaly`;
- data schema chinh;
- train/test/rules/visualize/explain CLI;
- artifact dau ra va cach tai lap.

Khong can paste code dai. Chi dua command mau ngan va bang module.

### 6.4. `experiments.tex`

Noi dung:

- dataset da dung, uu tien UCSD Ped2 neu artifact da co;
- cau hinh resize/grid/cube/feature/model/rule;
- cach train/test va sinh artifact;
- metric neu co ground truth;
- gioi han cua smoke run neu chi dung artifact smoke.

### 6.5. `results_discussion.tex`

Noi dung:

- bang metric tom tat neu co;
- mot so hinh heatmap/case tieu bieu;
- bang cluster profile rut gon;
- bang rule evidence rut gon;
- nhan xet ve case dung/sai/khong chac neu co manual review;
- thao luan loi ich va gioi han cua cluster/token/rule explanation.

### 6.6. `conclusion.tex`

Noi dung:

- tom tat pipeline da xay dung;
- muc da dat so voi PRD/MVP;
- han che:
  - nhay voi noise/anh sang;
  - grid chua co ngu nghia;
  - rule support co the thap;
  - chua co manual review day du;
- huong phat trien:
  - zone ngu nghia;
  - object detector nhe;
  - online adaptation;
  - report them case da review thu cong.

## 7. Generator report neu can

Neu them script, de xuat CLI:

```bash
python src/report.py --config src/configs/ucsd_ped2.yaml ^
  --analysis src/outputs/analysis/ucsd_ped2 ^
  --results src/outputs/results/ucsd_ped2 ^
  --visualizations src/outputs/visualizations/ucsd_ped2 ^
  --evaluation src/outputs/evaluation/ucsd_ped2_smoke ^
  --latex-dir latex ^
  --dataset ucsd_ped2 ^
  --case-limit 6
```

Neu chay tren smoke:

```bash
python src/report.py --config src/configs/ucsd_ped2.yaml ^
  --analysis src/outputs/analysis/ucsd_ped2_smoke ^
  --results src/outputs/results/ucsd_ped2 ^
  --visualizations src/outputs/visualizations/ucsd_ped2 ^
  --latex-dir latex ^
  --dataset ucsd_ped2 ^
  --case-limit 5 ^
  --artifact-label smoke
```

Tuy chon can co:

```text
--config
--analysis
--results
--visualizations
--evaluation
--latex-dir
--dataset
--case-limit
--artifact-label
--no-copy-figures
--sections-only
```

`report_artifacts_manifest.json` can ghi:

```json
{
  "dataset": "ucsd_ped2",
  "artifact_label": "smoke",
  "generated_at": "2026-05-27T20:00:00+07:00",
  "sources": {
    "config": "src/configs/ucsd_ped2.yaml",
    "analysis": "src/outputs/analysis/ucsd_ped2_smoke",
    "visualizations": "src/outputs/visualizations/ucsd_ped2"
  },
  "figures": [
    {
      "case_id": "case_001",
      "source": "src/outputs/visualizations/ucsd_ped2/alerts/...",
      "latex_path": "latex/figures/ucsd_ped2/case_001_heatmap.png"
    }
  ],
  "tables": [
    "latex/generated/ucsd_ped2/cluster_profile_table.tex"
  ],
  "warnings": []
}
```

## 8. Yeu cau LaTeX va render

- Giu `\usepackage[utf8]{inputenc}` va `\usepackage[T5]{fontenc}` vi bao cao dung tieng Viet.
- Neu dung hinh PNG, `\includegraphics` can duong dan tu thu muc `latex/`.
- Bang dai dung `longtable` hoac cat gon top-N.
- Anh heatmap nen co width khoang `0.75\textwidth` den `0.95\textwidth`.
- Caption can noi ro dataset/video/frame.
- Khong de duong dan Windows backslash trong LaTeX; dung slash `/`.
- File section phai compile doc lap voi `main.tex`, khong khai bao documentclass rieng.

## 9. Tieu chi chap nhan

- `src/doc/spec_10.md` mo ta ro cach dua artifact SPEC 3-9 vao bao cao LaTeX.
- Neu implement SPEC 10:
  - `latex/main.tex` include cac section moi hoac section hien co duoc mo rong co cau truc;
  - bao cao co mo ta pipeline, cau hinh, feature, model, token/rule, scoring va explanation;
  - co it nhat 3 hinh heatmap/case tieu bieu neu artifact hinh ton tai;
  - co bang cluster profile rut gon;
  - co bang rule evidence rut gon khi co rule artifact;
  - co phan thao luan gioi han va huong phat trien;
  - `latex/main.pdf` bien dich thanh cong;
  - khong co missing figure/reference nghiem trong;
  - moi artifact da chen vao bao cao duoc ghi trong manifest hoac processed file.
- Khong them workflow tuning, leaderboard, best-config selection hoac ablation comparison.

## 10. Verification de xuat

Neu chi tao/cap nhat tai lieu:

```bash
git diff --check -- src/doc/spec_10.md src/doc/spec_10_processed.md
```

Neu co them generator Python:

```bash
python -m compileall src/kpdl_anomaly src/report.py
python src/report.py --config src/configs/ucsd_ped2.yaml --analysis src/outputs/analysis/ucsd_ped2_smoke --results src/outputs/results/ucsd_ped2 --visualizations src/outputs/visualizations/ucsd_ped2 --latex-dir latex --dataset ucsd_ped2 --case-limit 5 --artifact-label smoke
```

Kiem tra generated artifact:

```text
report_artifacts_manifest.json load duoc bang JSON.
Moi figure trong manifest ton tai.
Moi generated .tex khong rong.
Khong co duong dan hinh dung backslash.
```

Bien dich LaTeX:

```bash
cd latex
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Neu `latexmk` khong co:

```bash
cd latex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Sau khi verification pass:

```bash
repomix.cmd
```

## 11. Checklist trien khai

- [ ] Doc PRD, `repomix-output.xml`, `planning_direction.md` va SPEC 9.
- [ ] Kiem tra cau truc hien co cua `latex/main.tex`.
- [ ] Xac dinh artifact analysis/visualization/evaluation se dung cho bao cao.
- [ ] Tao/cap nhat section `background.tex`.
- [ ] Tao/cap nhat section `system_design.tex`.
- [ ] Tao/cap nhat section `implementation.tex`.
- [ ] Tao/cap nhat section `experiments.tex`.
- [ ] Tao/cap nhat section `results_discussion.tex`.
- [ ] Tao/cap nhat section `conclusion.tex`.
- [ ] Cap nhat `latex/main.tex` de include cac section can thiet.
- [ ] Neu can tu dong hoa, tao `src/kpdl_anomaly/reporting.py`.
- [ ] Neu can tu dong hoa, tao CLI `src/report.py`.
- [ ] Tao/cap nhat `latex/generated/<dataset>/report_artifacts_manifest.json`.
- [ ] Copy hoac tham chieu hinh heatmap/case vao duong dan LaTeX on dinh.
- [ ] Tao bang cau hinh pipeline.
- [ ] Tao bang cluster profile rut gon.
- [ ] Tao bang rule evidence rut gon.
- [ ] Tao block casebook tieu bieu.
- [ ] Chay compile Python neu co code moi.
- [ ] Chay generator report neu co.
- [ ] Bien dich `latex/main.tex` thanh PDF.
- [ ] Kiem tra PDF co hinh/bang dung va khong loi layout nghiem trong.
- [ ] Cap nhat `src/doc/spec_10_processed.md`.
- [ ] Refresh `repomix-output.xml` sau khi verification pass.

## 12. Rui ro va giam thieu

### 12.1. Artifact production chua day du

Rui ro: chi co smoke artifact hoac output nam o thu muc debug.

Giam thieu:

- cho phep `--artifact-label smoke`;
- ghi ro trong bao cao la minh hoa/smoke;
- de duong dan artifact production thanh tuy chon khi co du lieu day du.

### 12.2. Bao cao qua dai

Rui ro: cluster profile va casebook co nhieu dong, lam bao cao chinh kho doc.

Giam thieu:

- chi dua top-N cell/rule/case vao bao cao chinh;
- dua JSON/Markdown day du vao phu luc hoac dan duong dan artifact;
- bang dai dung `longtable` hoac cat gon theo support/score.

### 12.3. Figure path loi khi bien dich

Rui ro: LaTeX khong tim thay anh do duong dan Windows hoac file nam ngoai `latex/`.

Giam thieu:

- copy hinh can dung vao `latex/figures/<dataset>/`;
- dung slash `/`;
- manifest validate moi path truoc khi compile.

### 12.4. Noi dung metric bi hieu nhu leaderboard

Rui ro: dua metric vao bao cao lam trong tam lech sang so sanh bien the.

Giam thieu:

- metric chi de mo ta kha nang chay va sanity check;
- khong tao bang xep hang cau hinh;
- khong ket luan rule/token tot hon neu khong co thiet ke danh gia ro.

### 12.5. Bao cao thieu manual review

Rui ro: casebook co heatmap va reason nhung chua co nhan xet dung/sai tu nguoi xem.

Giam thieu:

- de cot `Manual review` la `TBD` neu chua review;
- chi viet nhan xet dinh tinh ve tin hieu ma pipeline dua ra;
- khong gan nhan true positive/false positive neu chua co can cu.

## 13. Huong sau SPEC 10

Sau SPEC 10, co the:

- chon 5-10 case de review thu cong va dien nhan xet vao casebook;
- bo sung phu luc lenh tai lap pipeline;
- them so sanh voi ground truth neu nguoi dung yeu cau ro;
- dong goi bao cao cuoi ky voi PDF, hinh minh hoa va artifact manifest.
