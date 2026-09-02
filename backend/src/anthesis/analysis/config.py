"""Configuration for high-level deterministic song analysis."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class StructureConfig:
    """Controls self-similarity novelty segmentation."""

    novelty_half_window_seconds: float = 4.0
    novelty_smoothing_seconds: float = 1.0
    minimum_section_seconds: float = 4.0
    maximum_sections: int = 16
    minimum_peak_prominence: float = 0.05
    recurrence_threshold: float = 0.80

    def __post_init__(self) -> None:
        if self.novelty_half_window_seconds <= 0 or self.novelty_smoothing_seconds < 0:
            raise ValueError("novelty windows must be positive")
        if self.minimum_section_seconds <= 0:
            raise ValueError("minimum_section_seconds must be positive")
        if self.maximum_sections < 1:
            raise ValueError("maximum_sections must be positive")
        if self.minimum_peak_prominence < 0:
            raise ValueError("minimum_peak_prominence cannot be negative")
        if not 0 < self.recurrence_threshold <= 1:
            raise ValueError("recurrence_threshold must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class FingerprintConfig:
    """Controls landmark extraction and constellation hashing."""

    n_fft: int = 2_048
    hop_length: int = 512
    peak_neighborhood_frequency: int = 9
    peak_neighborhood_time: int = 7
    peaks_per_second: int = 24
    minimum_peak_db: float = -55.0
    minimum_pair_seconds: float = 0.10
    maximum_pair_seconds: float = 3.0
    fanout: int = 5
    signature_size: int = 128

    def __post_init__(self) -> None:
        if self.n_fft <= 0 or self.n_fft & (self.n_fft - 1):
            raise ValueError("n_fft must be a positive power of two")
        if not 0 < self.hop_length <= self.n_fft:
            raise ValueError("hop_length must be between one and n_fft")
        if self.peak_neighborhood_frequency < 3 or self.peak_neighborhood_time < 3:
            raise ValueError("peak neighborhoods must be at least three bins")
        if self.peaks_per_second < 1 or self.fanout < 1 or self.signature_size < 1:
            raise ValueError("peak count, fanout, and signature size must be positive")
        if not 0 <= self.minimum_pair_seconds < self.maximum_pair_seconds:
            raise ValueError("fingerprint pair durations must be non-negative and ordered")


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """Groups every high-level analysis configuration."""

    structure: StructureConfig = field(default_factory=StructureConfig)
    fingerprint: FingerprintConfig = field(default_factory=FingerprintConfig)
