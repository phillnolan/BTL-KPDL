from __future__ import annotations

from .records import CellRecord


def generate_grid(width: int, height: int, rows: int, cols: int, ignore_cells: list[str] | None = None) -> list[CellRecord]:
    ignored = set(ignore_cells or [])
    cells: list[CellRecord] = []
    for row in range(rows):
        y1 = round(row * height / rows)
        y2 = round((row + 1) * height / rows)
        for col in range(cols):
            x1 = round(col * width / cols)
            x2 = round((col + 1) * width / cols)
            cell_id = f"{row:02d}_{col:02d}"
            if cell_id in ignored:
                continue
            cells.append(CellRecord(cell_id=cell_id, row=row, col=col, x1=x1, y1=y1, x2=x2, y2=y2))
    return cells


def grid_to_json(cells: list[CellRecord], width: int, height: int, rows: int, cols: int) -> dict:
    return {
        "resized_width": width,
        "resized_height": height,
        "rows": rows,
        "cols": cols,
        "num_cells": len(cells),
        "cells": [
            {
                "cell_id": cell.cell_id,
                "row": cell.row,
                "col": cell.col,
                "x1": cell.x1,
                "y1": cell.y1,
                "x2": cell.x2,
                "y2": cell.y2,
                "width": cell.width,
                "height": cell.height,
            }
            for cell in cells
        ],
    }
