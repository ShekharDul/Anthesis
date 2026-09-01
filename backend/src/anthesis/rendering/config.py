"""Configuration for deterministic concept-art output."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RenderConfig:
    """Canvas and quality controls that do not alter flower identity."""

    width: int = 900
    height: int = 1_200
    supersampling: int = 2
    paper_grain: float = 0.018

    def __post_init__(self) -> None:
        if not 128 <= self.width <= 4_096 or not 128 <= self.height <= 4_096:
            raise ValueError("render dimensions must be between 128 and 4096 pixels")
        if not 1 <= self.supersampling <= 4:
            raise ValueError("supersampling must be between one and four")
        if not 0.0 <= self.paper_grain <= 0.08:
            raise ValueError("paper_grain must be between zero and 0.08")
