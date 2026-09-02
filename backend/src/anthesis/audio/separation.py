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
    """Time-domain components produced by median-filter HPSS."""

    harmonic: NDArray[np.float32]
    percussive: NDArray[np.float32]
    residual: NDArray[np.float32]
    spectrum: NDArray[np.complex64]
    harmonic_spectrum: NDArray[np.complex64]
    percussive_spectrum: NDArray[np.complex64]
    n_fft: int
    hop_length: int
    win_length: int
    harmonic_energy_ratio: float
    percussive_energy_ratio: float
    residual_energy_ratio: float
    reconstruction_rmse: float


def _energy_ratio(component: NDArray[np.float32], original_energy: float) -> float:
    energy = float(np.mean(np.square(component, dtype=np.float64)))
    return energy / max(original_energy, np.finfo(float).eps)


def _readonly_float32(
    values: NDArray[np.float32] | NDArray[np.float64],
) -> NDArray[np.float32]:
    result = np.ascontiguousarray(values, dtype=np.float32)
    result.setflags(write=False)
    return result


def _readonly_complex64(values: NDArray[np.complex64]) -> NDArray[np.complex64]:
    result = np.ascontiguousarray(values, dtype=np.complex64)
    result.setflags(write=False)
    return result


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
    harmonic_spectrum_values, percussive_spectrum_values = librosa.decompose.hpss(
        spectrum_values,
        kernel_size=(settings.harmonic_kernel, settings.percussive_kernel),
        power=settings.power,
        margin=settings.margin,
    )
    harmonic_values = librosa.istft(
        harmonic_spectrum_values,
        n_fft=settings.n_fft,
        hop_length=settings.hop_length,
        win_length=settings.win_length,
        center=True,
        length=audio.samples.size,
        dtype=audio.samples.dtype,
    )
    percussive_values = librosa.istft(
        percussive_spectrum_values,
        n_fft=settings.n_fft,
        hop_length=settings.hop_length,
        win_length=settings.win_length,
        center=True,
        length=audio.samples.size,
        dtype=audio.samples.dtype,
    )
    harmonic = _readonly_float32(harmonic_values)
    percussive = _readonly_float32(percussive_values)
    residual = _readonly_float32(audio.samples - harmonic - percussive)
    spectrum = _readonly_complex64(spectrum_values)
    harmonic_spectrum = _readonly_complex64(harmonic_spectrum_values)
    percussive_spectrum = _readonly_complex64(percussive_spectrum_values)

    reconstructed = harmonic.astype(np.float64) + percussive + residual
    error = reconstructed - audio.samples
    reconstruction_rmse = float(np.sqrt(np.mean(np.square(error))))
    original_energy = float(np.mean(np.square(audio.samples, dtype=np.float64)))

    return AudioComponents(
        harmonic=harmonic,
        percussive=percussive,
        residual=residual,
        spectrum=spectrum,
        harmonic_spectrum=harmonic_spectrum,
        percussive_spectrum=percussive_spectrum,
        n_fft=settings.n_fft,
        hop_length=settings.hop_length,
        win_length=settings.win_length,
        harmonic_energy_ratio=_energy_ratio(harmonic, original_energy),
        percussive_energy_ratio=_energy_ratio(percussive, original_energy),
        residual_energy_ratio=_energy_ratio(residual, original_energy),
        reconstruction_rmse=reconstruction_rmse,
    )
