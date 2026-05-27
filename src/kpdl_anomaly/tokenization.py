from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from kpdl_preprocess.config import ConfigError

from .io import validate_feature_header
from .schema import METADATA_COLUMNS, RULE_SCHEMA_VERSION

MOTION_COLUMN = "motion_magnitude_mean"
DENSITY_COLUMN = "motion_density"
BRIGHTNESS_COLUMN = "brightness_mean"
BRIGHTNESS_DELTA_COLUMN = "brightness_delta"
TOKEN_NUMERIC_COLUMNS = [
    MOTION_COLUMN,
    DENSITY_COLUMN,
    BRIGHTNESS_COLUMN,
    BRIGHTNESS_DELTA_COLUMN,
]
DIRECTION_LABELS = (
    "right",
    "down_right",
    "down",
    "down_left",
    "left",
    "up_left",
    "up",
    "up_right",
)


def fit_token_bins(
    feature_path: str | Path,
    expected_split: str = "train",
    limit_rows: int | None = None,
) -> dict[str, Any]:
    required_columns = METADATA_COLUMNS + TOKEN_NUMERIC_COLUMNS
    validate_feature_header(feature_path, required_columns)

    values: dict[str, list[float]] = {column: [] for column in TOKEN_NUMERIC_COLUMNS}
    rows_read = 0
    rows_used = 0
    invalid_rows = 0
    split_mismatches = 0

    with Path(feature_path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if limit_rows is not None and rows_read >= limit_rows:
                break
            rows_read += 1
            if row.get("split") != expected_split:
                split_mismatches += 1
                continue

            parsed: dict[str, float] = {}
            try:
                for column in TOKEN_NUMERIC_COLUMNS:
                    value = float(row[column])
                    if not np.isfinite(value):
                        raise ValueError(column)
                    parsed[column] = value
            except (KeyError, TypeError, ValueError):
                invalid_rows += 1
                continue

            for column, value in parsed.items():
                values[column].append(value)
            rows_used += 1

    if split_mismatches:
        raise ConfigError(f"{feature_path} contains {split_mismatches} row(s) outside split={expected_split!r}")
    if rows_used == 0:
        raise ConfigError(f"No valid {expected_split!r} rows found for token bin fitting")

    motion_values = _array(values[MOTION_COLUMN])
    motion_positive = motion_values[motion_values > 1.0e-12]
    motion_quantiles = _quantiles(motion_values, [0.20, 0.40, 0.60, 0.80])
    positive_quantiles = _quantiles(motion_positive, [0.25, 0.50, 0.75]) if motion_positive.size else [0.0, 0.0, 0.0]

    return {
        "schema_version": RULE_SCHEMA_VERSION,
        "fit_split": expected_split,
        "rows_read": rows_read,
        "rows_used": rows_used,
        "invalid_rows": invalid_rows,
        "limit_rows": limit_rows,
        "features": {
            MOTION_COLUMN: {
                "q20": motion_quantiles[0],
                "q40": motion_quantiles[1],
                "q60": motion_quantiles[2],
                "q80": motion_quantiles[3],
                "epsilon": 1.0e-12,
                "zero_heavy": bool(motion_quantiles[1] <= 1.0e-12 and motion_positive.size > 0),
                "positive_q25": positive_quantiles[0],
                "positive_q50": positive_quantiles[1],
                "positive_q75": positive_quantiles[2],
            },
            DENSITY_COLUMN: _named_quantiles(values[DENSITY_COLUMN], {"q33": 0.33, "q66": 0.66}),
            BRIGHTNESS_COLUMN: _named_quantiles(values[BRIGHTNESS_COLUMN], {"q33": 0.33, "q66": 0.66}),
            "brightness_delta_abs": _named_quantiles(
                [abs(value) for value in values[BRIGHTNESS_DELTA_COLUMN]],
                {"q80": 0.80},
            ),
        },
    }


def row_to_tokens(
    row: Mapping[str, Any],
    bins: Mapping[str, Any],
    cluster_id: int | str | None,
    include_cell_token: bool = True,
    include_cluster_token: bool = True,
    include_brightness_token: bool = True,
    include_direction_token: bool = False,
) -> list[str]:
    tokens: list[str] = []
    if include_cell_token:
        cell_id = str(row.get("cell_id", "")).strip()
        if cell_id:
            tokens.append(f"cell={cell_id}")
        cell_row = _format_index(row.get("cell_row"))
        if cell_row is not None:
            tokens.append(f"cell_row={cell_row}")
        cell_col = _format_index(row.get("cell_col"))
        if cell_col is not None:
            tokens.append(f"cell_col={cell_col}")

    motion = _motion_bucket(_float_or_none(row.get(MOTION_COLUMN)), bins)
    if motion is not None:
        tokens.append(f"motion={motion}")

    density = _three_bucket(_float_or_none(row.get(DENSITY_COLUMN)), bins, DENSITY_COLUMN, ("low", "medium", "high"))
    if density is not None:
        tokens.append(f"density={density}")

    if include_brightness_token:
        brightness = _three_bucket(
            _float_or_none(row.get(BRIGHTNESS_COLUMN)),
            bins,
            BRIGHTNESS_COLUMN,
            ("dark", "normal", "bright"),
        )
        if brightness is not None:
            tokens.append(f"brightness={brightness}")

        brightness_delta = _brightness_delta_bucket(_float_or_none(row.get(BRIGHTNESS_DELTA_COLUMN)), bins)
        if brightness_delta is not None:
            tokens.append(f"brightness_delta={brightness_delta}")

    if include_cluster_token:
        tokens.append(f"cluster={_cluster_label(cluster_id)}")

    if include_direction_token:
        direction = _direction_bucket(row)
        if direction is not None:
            tokens.append(f"direction={direction}")

    return _dedupe(tokens)


def _motion_bucket(value: float | None, bins: Mapping[str, Any]) -> str | None:
    if value is None:
        return None
    payload = dict(bins.get("features", {}).get(MOTION_COLUMN, {}))
    epsilon = float(payload.get("epsilon", 1.0e-12))
    if bool(payload.get("zero_heavy", False)):
        if value <= epsilon:
            return "still"
        if value <= float(payload.get("positive_q25", 0.0)):
            return "slow"
        if value <= float(payload.get("positive_q50", 0.0)):
            return "medium"
        if value <= float(payload.get("positive_q75", 0.0)):
            return "fast"
        return "very_fast"
    if value <= float(payload.get("q20", 0.0)):
        return "still"
    if value <= float(payload.get("q40", 0.0)):
        return "slow"
    if value <= float(payload.get("q60", 0.0)):
        return "medium"
    if value <= float(payload.get("q80", 0.0)):
        return "fast"
    return "very_fast"


def _three_bucket(
    value: float | None,
    bins: Mapping[str, Any],
    column: str,
    labels: tuple[str, str, str],
) -> str | None:
    if value is None:
        return None
    payload = dict(bins.get("features", {}).get(column, {}))
    if value <= float(payload.get("q33", 0.0)):
        return labels[0]
    if value <= float(payload.get("q66", 0.0)):
        return labels[1]
    return labels[2]


def _brightness_delta_bucket(value: float | None, bins: Mapping[str, Any]) -> str | None:
    if value is None:
        return None
    payload = dict(bins.get("features", {}).get("brightness_delta_abs", {}))
    return "stable" if abs(value) <= float(payload.get("q80", 0.0)) else "changing"


def _direction_bucket(row: Mapping[str, Any]) -> str | None:
    values: list[float] = []
    for index in range(len(DIRECTION_LABELS)):
        value = _float_or_none(row.get(f"direction_hist_{index}"))
        if value is None:
            return None
        values.append(value)
    total = sum(values)
    if total <= 1.0e-12:
        return None
    return DIRECTION_LABELS[int(np.argmax(np.asarray(values)))]


def _cluster_label(cluster_id: int | str | None) -> str:
    if cluster_id is None:
        return "unknown"
    if isinstance(cluster_id, str):
        cleaned = cluster_id.strip()
        if not cleaned:
            return "unknown"
        return cleaned if cleaned.startswith("C") or cleaned == "unknown" else f"C{cleaned}"
    return "unknown" if int(cluster_id) < 0 else f"C{int(cluster_id)}"


def _format_index(raw: Any) -> str | None:
    try:
        return f"{int(raw):02d}"
    except (TypeError, ValueError):
        return None


def _float_or_none(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(value):
        return None
    return value


def _array(values: list[float] | np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def _quantiles(values: list[float] | np.ndarray, quantiles: list[float]) -> list[float]:
    arr = _array(values)
    if arr.size == 0:
        return [0.0 for _ in quantiles]
    return [float(np.quantile(arr, quantile)) for quantile in quantiles]


def _named_quantiles(values: list[float], quantiles: dict[str, float]) -> dict[str, float]:
    computed = _quantiles(values, list(quantiles.values()))
    return {name: value for name, value in zip(quantiles.keys(), computed, strict=True)}


def _dedupe(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        if not token or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result
