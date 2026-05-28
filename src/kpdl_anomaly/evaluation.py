from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve

from kpdl_preprocess.config import ConfigError, get_nested, resolve_path
from kpdl_preprocess.utils import ensure_dir, sorted_natural, stem_to_frame_id

from .config import AnomalyConfig
from .io import require_files, write_json


EVALUATION_SCHEMA_VERSION = "spec_6.evaluation.v1"
DEFAULT_SCORE_COLUMNS = ["frame_score", "smoothed_frame_score"]
GT_IMAGE_EXTENSIONS = {".bmp", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
LABEL_SOURCES = {"auto", "mask", "interval"}


@dataclass(frozen=True)
class FrameScoreRow:
    dataset: str
    split: str
    video_id: str
    frame_id: int
    severity: str
    top_cells: str
    scores: dict[str, float]


@dataclass(frozen=True)
class LabelResult:
    label: int | None
    source: str
    positive_pixels: int | None = None
    mask_path: str | None = None


@dataclass
class GroundTruthState:
    test_root: Path
    intervals_by_video: dict[str, list[tuple[int, int]]]
    mask_maps_by_video: dict[str, dict[int, Path]]
    warnings: list[str]
    mask_reads: int = 0


def evaluate_results(
    config: AnomalyConfig,
    result_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    score_columns: list[str] | None = None,
    label_source: str | None = None,
) -> dict[str, Any]:
    label_source = label_source or _configured_label_source(config)
    if label_source not in LABEL_SOURCES:
        raise ConfigError(f"label_source must be one of: {', '.join(sorted(LABEL_SOURCES))}")

    result_path = Path(result_dir or config.result_dir)
    output_path = ensure_dir(output_dir or _default_evaluation_output_dir(config))
    frame_scores_path = result_path / "frame_scores.csv"
    require_files([frame_scores_path])

    requested_score_columns = score_columns or _configured_score_columns(config)
    rows, read_warnings = _read_frame_scores(frame_scores_path, requested_score_columns)
    if not rows:
        raise ConfigError(f"No frame score rows found in {frame_scores_path}")

    active_score_columns = [column for column in requested_score_columns if column in rows[0].scores]
    if not active_score_columns:
        raise ConfigError("None of the requested score columns were found in frame_scores.csv")

    gt_state = _load_ground_truth_state(config)
    labeled_rows, label_summary = _label_rows(rows, gt_state, label_source, active_score_columns)
    valid_rows = [row for row in labeled_rows if row["label"] is not None]
    if not valid_rows:
        raise ConfigError("No scored frames could be matched to ground truth labels")

    labels = [int(row["label"]) for row in valid_rows]
    metrics_by_score = {
        column: _binary_metrics(
            labels,
            [float(row[column]) for row in valid_rows],
            medium_threshold=config.alert_threshold_medium,
            high_threshold=config.alert_threshold_high,
        )
        for column in active_score_columns
    }

    summary = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "dataset": config.dataset,
        "split": "test",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "result_dir": str(result_path),
        "frame_scores_path": str(frame_scores_path),
        "output_dir": str(output_path),
        "score_columns": active_score_columns,
        "ground_truth": {
            "label_source": label_source,
            "test_root": str(gt_state.test_root),
            "interval_videos": len(gt_state.intervals_by_video),
            "mask_videos_loaded": len(gt_state.mask_maps_by_video),
            "mask_reads": gt_state.mask_reads,
        },
        "frames": label_summary,
        "metrics": metrics_by_score,
        "warnings": read_warnings + gt_state.warnings + label_summary["warnings"],
    }

    _write_frame_labels(output_path / "frame_labels.csv", labeled_rows, active_score_columns)
    write_json(output_path / "metrics.json", summary)
    _write_metrics_summary(output_path / "metrics_summary.md", summary)
    return summary


def _default_evaluation_output_dir(config: AnomalyConfig) -> Path:
    root = get_nested(config.raw, "evaluation", "output_root", default="src/outputs/evaluation")
    return resolve_path(str(root), config.project_root) / config.dataset


def _configured_score_columns(config: AnomalyConfig) -> list[str]:
    configured = get_nested(config.raw, "evaluation", "score_columns", default=None)
    if isinstance(configured, list) and all(isinstance(column, str) for column in configured):
        return configured
    return list(DEFAULT_SCORE_COLUMNS)


def _configured_label_source(config: AnomalyConfig) -> str:
    configured = str(get_nested(config.raw, "evaluation", "label_source", default="auto"))
    return configured if configured in LABEL_SOURCES else "auto"


def _read_frame_scores(
    path: Path,
    score_columns: list[str],
) -> tuple[list[FrameScoreRow], list[str]]:
    required = ["dataset", "split", "video_id", "frame_id"]
    warnings: list[str] = []
    rows: list[FrameScoreRow] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        missing_required = [column for column in required if column not in header]
        if missing_required:
            raise ConfigError(f"{path} is missing required column(s): {', '.join(missing_required)}")

        active_score_columns = [column for column in score_columns if column in header]
        missing_score_columns = [column for column in score_columns if column not in header]
        if missing_score_columns:
            warnings.append(f"Missing score column(s) skipped: {', '.join(missing_score_columns)}")

        for index, row in enumerate(reader, start=2):
            try:
                scores = {column: float(row[column]) for column in active_score_columns}
                frame_id = int(row["frame_id"])
            except (TypeError, ValueError) as exc:
                raise ConfigError(f"Invalid frame score row at {path}:{index}") from exc
            rows.append(
                FrameScoreRow(
                    dataset=str(row["dataset"]),
                    split=str(row["split"]),
                    video_id=str(row["video_id"]),
                    frame_id=frame_id,
                    severity=str(row.get("severity", "")),
                    top_cells=str(row.get("top_cells", "")),
                    scores=scores,
                )
            )
    return rows, warnings


def _load_ground_truth_state(config: AnomalyConfig) -> GroundTruthState:
    data = config.raw["data"]
    dataset_root = resolve_path(str(data["root"]), config.project_root)
    test_root = dataset_root / str(data["test_path"])
    if not test_root.exists():
        raise ConfigError(f"Test ground truth root does not exist: {test_root}")
    return GroundTruthState(
        test_root=test_root,
        intervals_by_video=_load_ucsd_intervals(test_root),
        mask_maps_by_video={},
        warnings=[],
    )


def _load_ucsd_intervals(test_root: Path) -> dict[str, list[tuple[int, int]]]:
    m_files = [
        path
        for path in sorted_natural(test_root.glob("*.m"))
        if path.is_file() and not path.name.startswith("._")
    ]
    if not m_files:
        return {}

    video_dirs = [
        path
        for path in sorted_natural(test_root.iterdir())
        if path.is_dir() and not path.name.lower().endswith("_gt")
    ]
    text = m_files[0].read_text(encoding="utf-8", errors="ignore")
    interval_exprs = re.findall(r"gt_frame\s*=\s*\[([^\]]*)\]", text)
    return {
        video_dir.name: _parse_matlab_intervals(expr)
        for video_dir, expr in zip(video_dirs, interval_exprs, strict=False)
    }


def _parse_matlab_intervals(expr: str) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    for part in expr.split(","):
        token = part.strip()
        if not token:
            continue
        if ":" in token:
            pieces = [piece.strip() for piece in token.split(":")]
            if len(pieces) != 2:
                continue
            start, end = int(pieces[0]), int(pieces[1])
        else:
            start = end = int(token)
        if start > end:
            start, end = end, start
        intervals.append((start, end))
    return intervals


def _label_rows(
    rows: list[FrameScoreRow],
    gt_state: GroundTruthState,
    label_source: str,
    score_columns: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    labeled_rows: list[dict[str, Any]] = []
    source_counts = {"mask": 0, "interval": 0, "missing": 0}
    warnings: list[str] = []
    missing_examples: list[str] = []

    for row in rows:
        label = _label_for_frame(gt_state, row.video_id, row.frame_id, label_source)
        source_counts[label.source] = source_counts.get(label.source, 0) + 1
        if label.label is None and len(missing_examples) < 10:
            missing_examples.append(f"{row.video_id}:{row.frame_id}")
        output_row: dict[str, Any] = {
            "dataset": row.dataset,
            "split": row.split,
            "video_id": row.video_id,
            "frame_id": row.frame_id,
            "label": label.label,
            "label_source": label.source,
            "positive_pixels": label.positive_pixels,
            "mask_path": label.mask_path,
            "severity": row.severity,
            "top_cells": row.top_cells,
        }
        for column in score_columns:
            output_row[column] = row.scores[column]
        labeled_rows.append(output_row)

    valid_labels = [int(row["label"]) for row in labeled_rows if row["label"] is not None]
    if missing_examples:
        warnings.append("Unlabeled scored frame examples: " + ", ".join(missing_examples))

    return labeled_rows, {
        "scored_frames": len(rows),
        "labeled_frames": len(valid_labels),
        "unlabeled_frames": len(rows) - len(valid_labels),
        "positive_frames": int(sum(valid_labels)),
        "negative_frames": int(len(valid_labels) - sum(valid_labels)),
        "label_source_counts": source_counts,
        "warnings": warnings,
    }


def _label_for_frame(
    gt_state: GroundTruthState,
    video_id: str,
    frame_id: int,
    label_source: str,
) -> LabelResult:
    if label_source in {"auto", "mask"}:
        mask_label = _label_from_mask(gt_state, video_id, frame_id)
        if mask_label is not None:
            return mask_label
        if label_source == "mask":
            return LabelResult(label=None, source="missing")

    if label_source in {"auto", "interval"}:
        intervals = gt_state.intervals_by_video.get(video_id)
        if intervals is not None:
            is_positive = any(start <= frame_id <= end for start, end in intervals)
            return LabelResult(label=1 if is_positive else 0, source="interval")
    return LabelResult(label=None, source="missing")


def _label_from_mask(
    gt_state: GroundTruthState,
    video_id: str,
    frame_id: int,
) -> LabelResult | None:
    mask_map = _mask_map_for_video(gt_state, video_id)
    mask_path = mask_map.get(frame_id)
    if mask_path is None:
        return None

    try:
        import cv2
    except ImportError as exc:
        raise ConfigError("OpenCV is required to read ground-truth mask images") from exc

    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        gt_state.warnings.append(f"Could not read ground-truth mask: {mask_path}")
        return None
    gt_state.mask_reads += 1
    positive_pixels = int(np.count_nonzero(mask))
    return LabelResult(
        label=1 if positive_pixels > 0 else 0,
        source="mask",
        positive_pixels=positive_pixels,
        mask_path=str(mask_path),
    )


def _mask_map_for_video(gt_state: GroundTruthState, video_id: str) -> dict[int, Path]:
    if video_id in gt_state.mask_maps_by_video:
        return gt_state.mask_maps_by_video[video_id]

    gt_dir = gt_state.test_root / f"{video_id}_gt"
    if not gt_dir.exists():
        gt_state.mask_maps_by_video[video_id] = {}
        return {}

    mask_map: dict[int, Path] = {}
    files = [
        path
        for path in sorted_natural(gt_dir.iterdir())
        if path.is_file() and path.suffix.lower() in GT_IMAGE_EXTENSIONS
    ]
    for index, path in enumerate(files, start=1):
        mask_map[stem_to_frame_id(path, index)] = path
    gt_state.mask_maps_by_video[video_id] = mask_map
    return mask_map


def _binary_metrics(
    labels: list[int],
    scores: list[float],
    medium_threshold: float,
    high_threshold: float,
) -> dict[str, Any]:
    y_true = np.asarray(labels, dtype=np.int32)
    y_score = np.asarray(scores, dtype=np.float64)
    positives = int(np.sum(y_true == 1))
    negatives = int(np.sum(y_true == 0))
    payload: dict[str, Any] = {
        "num_frames": int(len(y_true)),
        "positive_frames": positives,
        "negative_frames": negatives,
        "score_min": float(np.min(y_score)),
        "score_mean": float(np.mean(y_score)),
        "score_max": float(np.max(y_score)),
        "roc_auc": None,
        "pr_auc": None,
        "eer": None,
        "eer_threshold": None,
        "best_f1": None,
        "best_f1_threshold": None,
        "youden_j": None,
        "youden_threshold": None,
        "thresholds": {
            "medium": _threshold_metrics(y_true, y_score, medium_threshold),
            "high": _threshold_metrics(y_true, y_score, high_threshold),
        },
        "warnings": [],
    }
    if positives == 0 or negatives == 0:
        payload["warnings"].append("ROC-AUC/EER require both positive and negative frames")
        return payload

    payload["roc_auc"] = float(roc_auc_score(y_true, y_score))
    payload["pr_auc"] = float(average_precision_score(y_true, y_score))

    fpr, tpr, roc_thresholds = roc_curve(y_true, y_score)
    fnr = 1.0 - tpr
    eer_index = int(np.argmin(np.abs(fpr - fnr)))
    payload["eer"] = float((fpr[eer_index] + fnr[eer_index]) / 2.0)
    payload["eer_threshold"] = _finite_threshold(float(roc_thresholds[eer_index]), y_score)

    youden_values = tpr - fpr
    youden_index = int(np.argmax(youden_values))
    payload["youden_j"] = float(youden_values[youden_index])
    payload["youden_threshold"] = _finite_threshold(float(roc_thresholds[youden_index]), y_score)

    precision, recall, pr_thresholds = precision_recall_curve(y_true, y_score)
    f1 = np.divide(
        2.0 * precision * recall,
        precision + recall,
        out=np.zeros_like(precision, dtype=np.float64),
        where=(precision + recall) > 0.0,
    )
    f1_index = int(np.argmax(f1))
    payload["best_f1"] = float(f1[f1_index])
    if f1_index < len(pr_thresholds):
        payload["best_f1_threshold"] = float(pr_thresholds[f1_index])
    else:
        payload["best_f1_threshold"] = float(np.min(y_score) - 1.0e-12)
    return payload


def _threshold_metrics(y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> dict[str, Any]:
    y_pred = y_score >= threshold
    positives = y_true == 1
    negatives = y_true == 0
    tp = int(np.sum(y_pred & positives))
    fp = int(np.sum(y_pred & negatives))
    tn = int(np.sum(~y_pred & negatives))
    fn = int(np.sum(~y_pred & positives))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    fnr = fn / (fn + tp) if fn + tp else 0.0
    return {
        "threshold": float(threshold),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": float(precision),
        "recall": float(recall),
        "fpr": float(fpr),
        "fnr": float(fnr),
    }


def _finite_threshold(threshold: float, scores: np.ndarray) -> float:
    if np.isfinite(threshold):
        return float(threshold)
    return float(np.max(scores) + 1.0e-12)


def _write_frame_labels(path: Path, rows: list[dict[str, Any]], score_columns: list[str]) -> None:
    columns = [
        "dataset",
        "split",
        "video_id",
        "frame_id",
        "label",
        "label_source",
        "positive_pixels",
        "mask_path",
        "severity",
        "top_cells",
    ] + score_columns
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_metrics_summary(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# SPEC 6 Evaluation - {summary['dataset']}",
        "",
        f"- Result dir: `{summary['result_dir']}`",
        f"- Ground truth: `{summary['ground_truth']['label_source']}` from `{summary['ground_truth']['test_root']}`",
        f"- Labeled frames: {summary['frames']['labeled_frames']} / {summary['frames']['scored_frames']}",
        f"- Positive frames: {summary['frames']['positive_frames']}",
        f"- Negative frames: {summary['frames']['negative_frames']}",
        "",
        "| score | ROC-AUC | PR-AUC | EER | Best F1 | EER threshold |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for column, metrics in summary["metrics"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    column,
                    _md_float(metrics["roc_auc"]),
                    _md_float(metrics["pr_auc"]),
                    _md_float(metrics["eer"]),
                    _md_float(metrics["best_f1"]),
                    _md_float(metrics["eer_threshold"]),
                ]
            )
            + " |"
        )
    if summary["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in summary["warnings"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _md_float(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6f}"
