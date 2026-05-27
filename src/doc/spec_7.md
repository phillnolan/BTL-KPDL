# SPEC 7 - Optical flow direction features and direction tokens

## 1. Muc tieu

SPEC 7 bo sung huong chuyen dong that cho pipeline feature/token sau SPEC 5.

Muc tieu chinh:

- ho tro `features.motion_method: "farneback"` ben canh baseline `frame_diff`;
- tinh optical-flow magnitude cho tung cube va tung cell;
- dien `direction_hist_0..7` bang histogram huong chuyen dong that thay vi toan 0;
- cho phep model KMeans dung direction histogram trong `scoring.feature_columns`;
- cho phep rule/token layer sinh `direction=...` khi `rules.include_direction_token=true`;
- chay smoke pipeline tren UCSD Ped2 de chung minh direction histogram va direction token da co tin hieu.

SPEC 7 khong thuc hien so sanh no-rules vs with-rules cua SPEC 6.

## 2. Lien he PRD va spec truoc

PRD yeu cau feature `direction_hist_8bins` va bat duoc hanh vi sai huong. SPEC 5 da co token/rule nhung chu dong tat direction token vi feature hien tai chi dung `frame_diff`, nen histogram huong chua dang tin cay.

SPEC 7 giai quyet nut that do bang Farneback optical flow:

- `motion_magnitude_mean/std` lay tu flow magnitude;
- `motion_density` va `foreground_ratio` lay tu pixel co flow magnitude vuot nguong;
- `direction_hist_0..7` la histogram huong co trong so theo flow magnitude;
- token direction lay bin lon nhat va gan nhan de doc.

## 3. Pham vi

Trong pham vi:

- module `kpdl_preprocess.features`;
- config rieng cho UCSD Ped2 optical flow;
- tokenization/rule scoring de su dung direction token;
- smoke verification gom preprocess, train, train rules va test scoring.

Ngoai pham vi:

- khong doi default `ucsd_ped2.yaml` dang dung `frame_diff`;
- khong danh gia ROC-AUC/EER;
- khong so sanh hai result directory;
- khong them optical flow nang cao ngoai Farneback.

## 4. Cau hinh de xuat

Config rieng:

```text
src/configs/ucsd_ped2_optical_flow.yaml
```

Phan feature:

```yaml
features:
  motion_method: "farneback"
  flow_magnitude_threshold: 0.2
  direction_bins: 8
```

Phan scoring them direction bins:

```yaml
scoring:
  feature_columns:
    - foreground_ratio
    - motion_magnitude_mean
    - motion_magnitude_std
    - motion_density
    - direction_hist_0
    - direction_hist_1
    - direction_hist_2
    - direction_hist_3
    - direction_hist_4
    - direction_hist_5
    - direction_hist_6
    - direction_hist_7
    - brightness_mean
    - brightness_delta
```

Phan rules bat direction token:

```yaml
rules:
  include_direction_token: true
```

## 5. Tieu chi chap nhan

- `frame_diff` cu van chay va van giu direction histogram bang 0.
- `farneback` sinh `direction_hist_*` co tong histogram hop le tren row co chuyen dong.
- Train KMeans doc duoc feature columns co direction bins.
- Rule artifact co token schema chua `direction`.
- `cell_scores.csv` khi scoring co rules chua token `direction=...`.
- Verification khong phu thuoc vao so sanh SPEC 6.

## 6. Lenh verification de xuat

```bash
python -m compileall src/kpdl_preprocess src/kpdl_anomaly src/preprocess.py src/train.py src/rules.py src/test.py
python src/preprocess.py --config src/configs/ucsd_ped2_optical_flow.yaml --limit-videos 1 --limit-frames 65 --progress-every 0
python src/train.py --config src/configs/ucsd_ped2_optical_flow.yaml
python src/rules.py --config src/configs/ucsd_ped2_optical_flow.yaml --model src/outputs/models_spec7_flow/ucsd_ped2
python src/test.py --config src/configs/ucsd_ped2_optical_flow.yaml --model src/outputs/models_spec7_flow/ucsd_ped2 --rules src/outputs/rules_spec7_flow/ucsd_ped2
```
