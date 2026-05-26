from __future__ import annotations

from pathlib import Path

from .config import ConfigError, resolve_path
from .records import VideoSource
from .utils import sorted_natural


VIDEO_EXTENSIONS = {".avi", ".mp4", ".mov", ".mkv"}


def scan_dataset(
    config: dict,
    project_root: str | Path,
    split_filter: str | None = None,
) -> list[VideoSource]:
    data = config["data"]
    video = config["video"]
    dataset = str(data["dataset"])
    root = resolve_path(data["root"], project_root)
    input_type = str(video["input_type"])

    if not root.exists():
        raise ConfigError(f"Dataset root does not exist: {root}")

    splits = [("train", data["train_path"]), ("test", data["test_path"])]
    if split_filter:
        splits = [item for item in splits if item[0] == split_filter]
        if not splits:
            raise ConfigError(f"Unknown split: {split_filter}")

    sources: list[VideoSource] = []
    for split, split_path in splits:
        split_root = root / str(split_path)
        if not split_root.exists():
            raise ConfigError(f"Split path does not exist: {split_root}")

        if input_type == "frame_sequence":
            sources.extend(_scan_frame_sequences(dataset, split, split_root, input_type))
        elif input_type == "video":
            sources.extend(_scan_videos(dataset, split, split_root, input_type))
        else:
            raise ConfigError(f"Unsupported input_type: {input_type}")

    return sources


def _scan_frame_sequences(
    dataset: str,
    split: str,
    split_root: Path,
    input_type: str,
) -> list[VideoSource]:
    sources: list[VideoSource] = []
    for child in sorted_natural(p for p in split_root.iterdir() if p.is_dir()):
        if child.name.lower().endswith("_gt"):
            continue
        if not any(child.glob("*.tif")):
            continue
        sources.append(
            VideoSource(
                dataset=dataset,
                split=split,
                video_id=child.name,
                source_path=child,
                input_type=input_type,
            )
        )
    return sources


def _scan_videos(
    dataset: str,
    split: str,
    split_root: Path,
    input_type: str,
) -> list[VideoSource]:
    files = [
        path
        for path in split_root.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return [
        VideoSource(
            dataset=dataset,
            split=split,
            video_id=path.stem,
            source_path=path,
            input_type=input_type,
        )
        for path in sorted_natural(files)
    ]
