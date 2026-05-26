from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VideoSource:
    dataset: str
    split: str
    video_id: str
    source_path: Path
    input_type: str


@dataclass(frozen=True)
class FrameRecord:
    dataset: str
    split: str
    video_id: str
    frame_id: int
    timestamp: float | None
    source_path: Path
    original_width: int
    original_height: int
    resized_width: int
    resized_height: int
    gray: Any


@dataclass(frozen=True)
class CellRecord:
    cell_id: str
    row: int
    col: int
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1
