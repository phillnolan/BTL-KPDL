from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kpdl_preprocess.config import ConfigError
from kpdl_preprocess.utils import ensure_dir

from .feature_selection import row_to_vector
from .schema import METADATA_COLUMNS


@dataclass
class FeatureLoadResult:
    by_cell: dict[str, list[list[float]]]
    header: list[str]
    rows_read: int
    rows_loaded: int
    invalid_rows: int
    split_mismatches: int
    limit_rows: int | None


def require_files(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise ConfigError(f"Required file(s) not found: {', '.join(missing)}")


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: Any) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, default=_json_default)
        handle.write("\n")


def write_config_yaml(path: str | Path, payload: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise ConfigError("PyYAML is required to write config.yaml artifacts") from exc
    with Path(path).open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)


def validate_feature_header(path: str | Path, required_columns: list[str]) -> list[str]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
    missing = [column for column in required_columns if column not in header]
    if missing:
        raise ConfigError(f"{path} is missing required column(s): {', '.join(missing)}")
    return header


def load_features_by_cell(
    path: str | Path,
    feature_columns: list[str],
    expected_split: str,
    limit_rows: int | None = None,
) -> FeatureLoadResult:
    required_columns = METADATA_COLUMNS + feature_columns
    header = validate_feature_header(path, required_columns)
    by_cell: dict[str, list[list[float]]] = {}
    rows_read = 0
    rows_loaded = 0
    invalid_rows = 0
    split_mismatches = 0

    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if limit_rows is not None and rows_read >= limit_rows:
                break
            rows_read += 1
            if row.get("split") != expected_split:
                split_mismatches += 1
                continue
            vector = row_to_vector(row, feature_columns)
            if vector is None:
                invalid_rows += 1
                continue
            by_cell.setdefault(str(row["cell_id"]), []).append(vector.tolist())
            rows_loaded += 1

    if split_mismatches:
        raise ConfigError(f"{path} contains {split_mismatches} row(s) outside split={expected_split!r}")

    return FeatureLoadResult(
        by_cell=by_cell,
        header=header,
        rows_read=rows_read,
        rows_loaded=rows_loaded,
        invalid_rows=invalid_rows,
        split_mismatches=split_mismatches,
        limit_rows=limit_rows,
    )


def output_dir(path: str | Path) -> Path:
    return ensure_dir(path)


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
