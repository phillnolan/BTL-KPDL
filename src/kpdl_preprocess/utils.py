from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


def ensure_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def natural_key(value: str | Path) -> list[object]:
    text = Path(value).name if isinstance(value, Path) else str(value)
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def sorted_natural(paths: Iterable[Path]) -> list[Path]:
    return sorted(paths, key=natural_key)


def stem_to_frame_id(path: Path, fallback: int) -> int:
    match = re.search(r"\d+", path.stem)
    return int(match.group(0)) if match else fallback


def bool_config(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)
