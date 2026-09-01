"""Immutable representations produced by the musical feature engine."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray


def _readonly_float32(values: NDArray[np.float32] | NDArray[np.float64]) -> NDArray[np.float32]:
    result = np.ascontiguousarray(values, dtype=np.float32)
    result.setflags(write=False)
    return result


@dataclass(frozen=True, slots=True)
class FeatureTable:
    """A named, unit-aware feature matrix aligned to musical time."""

    times: NDArray[np.float32]
    values: NDArray[np.float32]
    columns: tuple[str, ...]
    units: tuple[str, ...]

    def __post_init__(self) -> None:
        times = _readonly_float32(self.times)
        values = _readonly_float32(self.values)
        if times.ndim != 1:
            raise ValueError("times must be one-dimensional")
        if values.ndim != 2:
            raise ValueError("values must be a two-dimensional matrix")
        if values.shape != (times.size, len(self.columns)):
            raise ValueError("feature matrix shape does not match times and columns")
        if len(self.units) != len(self.columns):
            raise ValueError("every feature column must declare a unit")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("feature column names must be unique")
        if not np.isfinite(times).all() or not np.isfinite(values).all():
            raise ValueError("feature tables cannot contain non-finite values")
        if times.size > 1 and np.any(np.diff(times) <= 0):
            raise ValueError("feature times must increase strictly")
        object.__setattr__(self, "times", times)
        object.__setattr__(self, "values", values)

    def column(self, name: str) -> NDArray[np.float32]:
        """Return a read-only view of one named feature."""

        try:
            index = self.columns.index(name)
        except ValueError as exc:
            raise KeyError(name) from exc
        result = self.values[:, index]
        result.setflags(write=False)
        return result

    def aggregate_intervals(self, boundaries_seconds: Sequence[float]) -> FeatureTable:
        """Median-aggregate rows inside user-supplied section boundaries."""

        boundaries = np.asarray(boundaries_seconds, dtype=np.float64)
        if boundaries.ndim != 1 or boundaries.size < 2:
            raise ValueError("at least two section boundaries are required")
        if not np.isfinite(boundaries).all() or np.any(np.diff(boundaries) <= 0):
            raise ValueError("section boundaries must be finite and strictly increasing")

        rows: list[NDArray[np.float32]] = []
        centers: list[float] = []
        for start, end in pairwise(boundaries):
            left = int(np.searchsorted(self.times, start, side="left"))
            right = int(np.searchsorted(self.times, end, side="left"))
            if right <= left:
                nearest = min(left, self.times.size - 1)
                rows.append(self.values[nearest])
            else:
                rows.append(np.median(self.values[left:right], axis=0).astype(np.float32))
            centers.append(float((start + end) * 0.5))

        return FeatureTable(
            times=np.asarray(centers, dtype=np.float32),
            values=np.stack(rows),
            columns=self.columns,
            units=self.units,
        )


@dataclass(frozen=True, slots=True)
class MusicalFeatures:
    """Compact frame, beat, and global measurements for one recording."""

    frames: FeatureTable
    beats: FeatureTable
    globals: Mapping[str, float]
    labels: Mapping[str, str]
    version: str = "anthesis-features-v1"

    def __post_init__(self) -> None:
        numeric = {key: float(value) for key, value in self.globals.items()}
        if not all(np.isfinite(value) for value in numeric.values()):
            raise ValueError("global features cannot contain non-finite values")
        object.__setattr__(self, "globals", MappingProxyType(numeric))
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))

    @property
    def digest(self) -> str:
        """Hash all compact measurements for determinism regression tests."""

        digest = hashlib.sha256(self.version.encode("ascii"))
        for table in (self.frames, self.beats):
            digest.update("\0".join(table.columns).encode("utf-8"))
            digest.update(table.times.astype("<f4", copy=False).tobytes())
            digest.update(table.values.astype("<f4", copy=False).tobytes())
        for key, numeric_value in sorted(self.globals.items()):
            digest.update(key.encode("utf-8"))
            digest.update(np.asarray(numeric_value, dtype="<f8").tobytes())
        for key, label_value in sorted(self.labels.items()):
            digest.update(key.encode("utf-8"))
            digest.update(label_value.encode("utf-8"))
        return digest.hexdigest()
