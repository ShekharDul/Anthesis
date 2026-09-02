"""Configuration for the Anthesis musical feature engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeatureConfig:
    """Controls time-frequency resolution and compact feature sampling."""

    n_fft: int = 2_048
    hop_length: int = 1_024
    n_mels: int = 40
    n_mfcc: int = 6
    output_rate_hz: float = 2.0
    silence_db: float = -45.0
    roughness_peak_count: int = 20
    roughness_min_hz: float = 40.0
    roughness_max_hz: float = 6_000.0

    def __post_init__(self) -> None:
        if self.n_fft <= 0 or self.n_fft & (self.n_fft - 1):
            raise ValueError("n_fft must be a positive power of two")
        if not 0 < self.hop_length <= self.n_fft:
            raise ValueError("hop_length must be between one and n_fft")
        if self.n_mels < 16 or self.n_mfcc < 1 or self.n_mfcc > self.n_mels:
            raise ValueError("expected 16 <= n_mels and 1 <= n_mfcc <= n_mels")
        if self.output_rate_hz <= 0:
            raise ValueError("output_rate_hz must be positive")
        if self.silence_db >= 0:
            raise ValueError("silence_db must be negative")
        if self.roughness_peak_count < 2:
            raise ValueError("roughness_peak_count must be at least two")
        if not 0 < self.roughness_min_hz < self.roughness_max_hz:
            raise ValueError("roughness frequency bounds must be positive and ordered")
