from __future__ import annotations

import numpy as np


def summarize_distances(distances: np.ndarray, percentile: float, threshold_floor: float) -> dict[str, float]:
    if distances.size == 0:
        return {
            "distance_mean": 0.0,
            "distance_std": 0.0,
            "distance_p95": 0.0,
            "distance_p99": 0.0,
            "threshold": 0.0,
        }

    threshold = float(np.percentile(distances, percentile))
    if threshold_floor > 0.0:
        threshold = max(threshold, threshold_floor)

    return {
        "distance_mean": float(np.mean(distances)),
        "distance_std": float(np.std(distances)),
        "distance_p95": float(np.percentile(distances, 95.0)),
        "distance_p99": float(np.percentile(distances, 99.0)),
        "threshold": threshold,
    }


def distance_to_score(distance: float, threshold: float) -> float:
    if threshold <= 0.0:
        return 0.0 if abs(distance) <= 1.0e-12 else 1.0
    return float(min(distance / threshold, 2.0) / 2.0)
