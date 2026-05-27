from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        import yaml
    except ImportError as exc:
        raise ConfigError(
            "PyYAML is required to read YAML config files. "
            "Install dependencies with: python -m pip install -r src/requirements.txt"
        ) from exc

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a mapping: {config_path}")

    _validate_config(data)
    return data


def _validate_config(config: dict[str, Any]) -> None:
    required_sections = ["data", "video", "grid", "cube", "features"]
    missing = [section for section in required_sections if section not in config]
    if missing:
        raise ConfigError(f"Missing config section(s): {', '.join(missing)}")

    data = config["data"]
    for key in ["dataset", "root", "train_path", "test_path"]:
        if key not in data:
            raise ConfigError(f"Missing data.{key}")

    video = config["video"]
    if video.get("input_type") not in {"frame_sequence", "video"}:
        raise ConfigError("video.input_type must be 'frame_sequence' or 'video'")

    for key in ["resize_width", "resize_height"]:
        if int(video.get(key, 0)) <= 0:
            raise ConfigError(f"video.{key} must be a positive integer")

    grid = config["grid"]
    if int(grid.get("rows", 0)) <= 0 or int(grid.get("cols", 0)) <= 0:
        raise ConfigError("grid.rows and grid.cols must be positive integers")

    cube = config["cube"]
    if int(cube.get("length", 0)) <= 1:
        raise ConfigError("cube.length must be greater than 1")
    if int(cube.get("stride", 0)) <= 0:
        raise ConfigError("cube.stride must be a positive integer")

    features = config["features"]
    motion_method = str(features.get("motion_method", "frame_diff")).lower()
    supported_motion_methods = {"frame_diff", "frame_difference", "farneback", "optical_flow", "flow"}
    if motion_method not in supported_motion_methods:
        raise ConfigError(
            "features.motion_method must be one of: frame_diff, farneback, optical_flow"
        )
    if int(features.get("direction_bins", 8)) <= 0:
        raise ConfigError("features.direction_bins must be a positive integer")


def get_nested(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def copy_config(config: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(config)


def resolve_path(path_value: str | Path, project_root: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return Path(project_root).resolve() / path
