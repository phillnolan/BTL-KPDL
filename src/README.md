# SPEC 1 preprocessing

This folder implements the `doc/spec_1.md` preprocessing stage for UCSD Ped1/Ped2
and CUHK Avenue.

## Install

```bash
python -m pip install -r src/requirements.txt
```

## Dataset location

The SPEC 1 datasets are stored under `src/dataset/`:

```text
src/dataset/
  UCSD_Anomaly_Dataset.v1p2/
  CUHK-avenue/
```

## Smoke test

```bash
python src/tool/preprocess_ucsd.py --ped ped2 --split train --limit-videos 1 --limit-frames 20 --output-root outputs/preprocessed_smoke --export-arff
```

```bash
python src/tool/preprocess_avenue.py --split train --limit-videos 1 --limit-frames 20 --output-root outputs/preprocessed_smoke --export-arff
```

## Full preprocess

```bash
python src/tool/preprocess_ucsd.py --ped ped2 --export-arff
python src/tool/preprocess_avenue.py --export-arff
```

`src/tool/preprocess_ucsd.py` handles UCSD Ped2 by default. Use `--ped ped1`
to process UCSD Ped1 with the same output schema.

Outputs follow the SPEC 1 layout:

```text
src/outputs/preprocessed/<dataset>/
  frames_manifest.csv
  videos_manifest.csv
  grid.json
  features_train.csv
  features_test.csv
  preprocess_stats.json

src/outputs/weka/
  <dataset>_features_train.arff
  <dataset>_features_test.arff
```

The baseline feature extractor uses frame differencing. Direction histogram columns
are present and set to zero in this SPEC 1 baseline, matching the note in the spec.

Both dataset-specific scripts call the same common schema. UCSD frame sequences and
CUHK Avenue videos are normalized into identical `frames_manifest.csv`,
`videos_manifest.csv`, `features_train.csv`, `features_test.csv`, `grid.json`, and
`preprocess_stats.json` layouts.
