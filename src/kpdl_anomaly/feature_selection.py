from __future__ import annotations

from collections.abc import Mapping

import numpy as np


def row_to_vector(row: Mapping[str, str], feature_columns: list[str]) -> np.ndarray | None:
    values: list[float] = []
    try:
        for column in feature_columns:
            values.append(float(row[column]))
    except (KeyError, TypeError, ValueError):
        return None
    vector = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(vector)):
        return None
    return vector
