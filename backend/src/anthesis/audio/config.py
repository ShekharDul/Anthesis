"""Configuration for deterministic audio preprocessing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioPreprocessConfig:
    """Controls canonicalization before musical analysis.

    Defaults preserve the useful musical spectrum while keeping later analysis
    tractable. Values are explicit so an analysis version can reproduce them.
    """

    target_sample_rate: int = 16_000
    min_duration_seconds: float = 1.0
    max_duration_seconds: float = 8.0 * 60.0
    max_file_size_bytes: int = 512 * 1024 * 1024
    trim_top_db: float = 55.0
    trim_frame_length: int = 2_048
    trim_hop_length: int = 512
    peak_target: float = 0.98
    silence_epsilon: float = 1e-7
    resample_type: str = "soxr_mq"

    def __post_init__(self) -> None:
        if self.target_sample_rate < 8_000:
            raise ValueError("target_sample_rate must be at least 8000 Hz")
        if not 0 < self.min_duration_seconds <= self.max_duration_seconds:
            raise ValueError("duration bounds must be positive and ordered")
        if self.max_file_size_bytes <= 0:
            raise ValueError("max_file_size_bytes must be positive")
        if self.trim_top_db <= 0:
            raise ValueError("trim_top_db must be positive")
        if self.trim_frame_length <= 0 or self.trim_hop_length <= 0:
            raise ValueError("trim frame and hop lengths must be positive")
        if self.trim_hop_length > self.trim_frame_length:
            raise ValueError("trim_hop_length cannot exceed trim_frame_length")
        if not 0 < self.peak_target <= 1:
            raise ValueError("peak_target must be in the interval (0, 1]")
        if self.silence_epsilon <= 0:
            raise ValueError("silence_epsilon must be positive")


@dataclass(frozen=True, slots=True)
class SeparationConfig:
    """Controls median-filter harmonic/percussive source separation."""

    n_fft: int = 2_048
    hop_length: int = 1_024
    win_length: int = 2_048
    harmonic_kernel: int = 31
    percussive_kernel: int = 31
    chunk_frames: int = 512
    power: float = 2.0
    margin: float = 1.0

    def __post_init__(self) -> None:
        if self.n_fft <= 0 or self.n_fft & (self.n_fft - 1):
            raise ValueError("n_fft must be a positive power of two")
        if not 0 < self.hop_length <= self.win_length <= self.n_fft:
            raise ValueError("expected 0 < hop_length <= win_length <= n_fft")
        if self.harmonic_kernel < 3 or self.percussive_kernel < 3:
            raise ValueError("HPSS kernels must contain at least three frames")
        if self.harmonic_kernel % 2 == 0 or self.percussive_kernel % 2 == 0:
            raise ValueError("HPSS kernels must be odd")
        if self.chunk_frames < max(self.harmonic_kernel, self.percussive_kernel):
            raise ValueError("chunk_frames must cover the HPSS kernels")
        if self.power <= 0:
            raise ValueError("power must be positive")
        if self.margin < 1:
            raise ValueError("margin must be at least one")
