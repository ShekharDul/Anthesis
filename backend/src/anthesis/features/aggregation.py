"""Time aggregation helpers for compact musical feature curves."""

from __future__ import annotations

from itertools import pairwise

import numpy as np
from numpy.typing import NDArray


def aggregate_columns(
    values: NDArray[np.float32] | NDArray[np.float64],
    block_size: int,
    *,
    reducer: str = "median",
) -> NDArray[np.float32]:
    """Aggregate feature-by-frame data into deterministic fixed blocks."""

    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError("values must have shape (features, frames)")
    if block_size < 1:
        raise ValueError("block_size must be positive")
    rows: list[NDArray[np.float64]] = []
    for start in range(0, matrix.shape[1], block_size):
        block = matrix[:, start : start + block_size]
        if reducer == "median":
            row = np.median(block, axis=1)
        elif reducer == "mean":
            row = np.mean(block, axis=1)
        elif reducer == "max":
            row = np.max(block, axis=1)
        else:
            raise ValueError(f"Unknown reducer: {reducer}")
        rows.append(np.asarray(row, dtype=np.float64))
    return np.asarray(rows, dtype=np.float32)


def aggregate_times(times: NDArray[np.float64], block_size: int) -> NDArray[np.float32]:
    """Return the mean timestamp of each fixed frame block."""

    if times.ndim != 1 or block_size < 1:
        raise ValueError("times must be one-dimensional and block_size positive")
    centers = [
        float(np.mean(times[start : start + block_size]))
        for start in range(0, times.size, block_size)
    ]
    return np.asarray(centers, dtype=np.float32)


def aggregate_at_beats(
    frame_times: NDArray[np.float32],
    frame_values: NDArray[np.float32],
    beat_times: NDArray[np.float32],
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """Median-aggregate compact frames into intervals centered on beats."""

    if beat_times.size == 0:
        return (
            np.empty(0, dtype=np.float32),
            np.empty((0, frame_values.shape[1]), dtype=np.float32),
        )
    if beat_times.size == 1:
        return beat_times.copy(), np.median(frame_values, axis=0, keepdims=True).astype(np.float32)

    midpoints = (beat_times[:-1] + beat_times[1:]) * 0.5
    edges = np.concatenate(
        ([0.0], midpoints, [max(float(frame_times[-1]) + 1e-6, beat_times[-1])])
    )
    rows: list[NDArray[np.float32]] = []
    for start, end in pairwise(edges):
        left = int(np.searchsorted(frame_times, start, side="left"))
        right = int(np.searchsorted(frame_times, end, side="left"))
        if right <= left:
            nearest = min(left, frame_times.size - 1)
            rows.append(frame_values[nearest])
        else:
            rows.append(np.median(frame_values[left:right], axis=0).astype(np.float32))
    return beat_times.copy(), np.stack(rows)
