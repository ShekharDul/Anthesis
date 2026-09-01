"""Configuration for compact MusicGenome construction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GenomeConfig:
    """Controls serialization density without changing musical analysis."""

    maximum_trajectory_points: int = 256

    def __post_init__(self) -> None:
        if self.maximum_trajectory_points < 2:
            raise ValueError("maximum_trajectory_points must be at least two")
