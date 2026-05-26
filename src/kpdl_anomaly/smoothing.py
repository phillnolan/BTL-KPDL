from __future__ import annotations

from collections import deque


def moving_average(values: list[float], window: int) -> list[float]:
    if window <= 1:
        return list(values)

    smoothed: list[float] = []
    active: deque[float] = deque(maxlen=window)
    total = 0.0
    for value in values:
        if len(active) == active.maxlen:
            total -= active[0]
        active.append(value)
        total += value
        smoothed.append(total / len(active))
    return smoothed
