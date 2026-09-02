"""Deterministic harmonic/percussive source separation."""

from __future__ import annotations

from dataclasses import dataclass

import librosa
import numpy as np
from numpy.typing import NDArray

from anthesis.audio.config import SeparationConfig
from anthesis.audio.ingest import CanonicalAudio


@dataclass(frozen=True, slots=True)
class AudioComponents:
    """Spectral components produced by median-filter HPSS."""

    magnitude: NDArray[np.float32]
    harmonic_magnitude: NDArray[np.float32]
    percussive_magnitude: NDArray[np.float32]
    residual_magnitude: NDArray[np.float32]
    n_fft: int
    hop_length: int
    win_length: int
    harmonic_energy_ratio: float
    percussive_energy_ratio: float
    residual_energy_ratio: float


def _energy_ratio(component: NDArray[np.float32], original_energy: float) -> float:
    energy = float(np.sum(np.square(component, dtype=np.float64)))
    return energy / max(original_energy, np.finfo(float).eps)


def _readonly_float32(
    values: NDArray[np.float32] | NDArray[np.float64],
) -> NDArray[np.float32]:
    result = np.ascontiguousarray(values, dtype=np.float32)
    result.setflags(write=False)
    return result


def _separate_magnitudes(
    spectrum: NDArray[np.complex64], settings: SeparationConfig
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """Run exact local median neighborhoods in bounded time chunks."""

    harmonic = np.empty(spectrum.shape, dtype=np.float32)
    percussive = np.empty(spectrum.shape, dtype=np.float32)
    halo = settings.harmonic_kernel // 2
    frame_count = spectrum.shape[1]
    for start in range(0, frame_count, settings.chunk_frames):
        end = min(start + settings.chunk_frames, frame_count)
        expanded_start = max(0, start - halo)
        expanded_end = min(frame_count, end + halo)
        harmonic_chunk, percussive_chunk = librosa.decompose.hpss(
            spectrum[:, expanded_start:expanded_end],
            kernel_size=(settings.harmonic_kernel, settings.percussive_kernel),
            power=settings.power,
            margin=settings.margin,
        )
        core = slice(start - expanded_start, end - expanded_start)
        harmonic[:, start:end] = np.abs(harmonic_chunk[:, core])
        percussive[:, start:end] = np.abs(percussive_chunk[:, core])
    return harmonic, percussive


def separate_harmonic_percussive(
    audio: CanonicalAudio,
    config: SeparationConfig | None = None,
) -> AudioComponents:
    """Separate tonal, transient, and unassigned content with median filters."""

    settings = config or SeparationConfig()
    spectrum_values = librosa.stft(
        audio.samples,
        n_fft=settings.n_fft,
        hop_length=settings.hop_length,
        win_length=settings.win_length,
        window="hann",
        center=True,
        pad_mode="constant",
    )
    magnitude = _readonly_float32(np.abs(spectrum_values))
    harmonic_values, percussive_values = _separate_magnitudes(spectrum_values, settings)
    harmonic_magnitude = _readonly_float32(harmonic_values)
    percussive_magnitude = _readonly_float32(percussive_values)
    residual_values = np.maximum(magnitude - harmonic_magnitude - percussive_magnitude, 0.0)
    residual_magnitude = _readonly_float32(residual_values)
    original_energy = float(np.sum(np.square(magnitude, dtype=np.float64)))

    return AudioComponents(
        magnitude=magnitude,
        harmonic_magnitude=harmonic_magnitude,
        percussive_magnitude=percussive_magnitude,
        residual_magnitude=residual_magnitude,
        n_fft=settings.n_fft,
        hop_length=settings.hop_length,
        win_length=settings.win_length,
        harmonic_energy_ratio=_energy_ratio(harmonic_magnitude, original_energy),
        percussive_energy_ratio=_energy_ratio(percussive_magnitude, original_energy),
        residual_energy_ratio=_energy_ratio(residual_magnitude, original_energy),
    )
