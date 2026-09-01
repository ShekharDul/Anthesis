"""Sensory-roughness estimation from local spectral peak interactions."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def spectral_roughness(
    spectra: NDArray[np.float32],
    frequencies: NDArray[np.float64],
    *,
    peak_count: int,
    min_hz: float,
    max_hz: float,
) -> NDArray[np.float32]:
    """Estimate normalized Sethares-style pairwise sensory dissonance.

    ``spectra`` has shape ``(frames, bins)`` and should contain non-negative
    magnitudes. Only prominent local maxima participate, keeping the method
    interpretable and inexpensive at the compact feature rate.
    """

    if spectra.ndim != 2 or frequencies.ndim != 1 or spectra.shape[1] != frequencies.size:
        raise ValueError("spectra and frequency bins have incompatible shapes")
    valid = (frequencies >= min_hz) & (frequencies <= max_hz)
    selected_frequencies = frequencies[valid]
    output = np.zeros(spectra.shape[0], dtype=np.float32)

    for frame_index, spectrum in enumerate(spectra[:, valid]):
        if spectrum.size < 3 or float(np.max(spectrum)) <= np.finfo(float).eps:
            continue
        local = np.flatnonzero(
            (spectrum[1:-1] > spectrum[:-2]) & (spectrum[1:-1] >= spectrum[2:])
        ) + 1
        if local.size < 2:
            continue
        strongest = local[np.argsort(spectrum[local])[-peak_count:]]
        amplitudes = spectrum[strongest].astype(np.float64)
        amplitudes /= max(float(np.max(amplitudes)), np.finfo(float).eps)
        peak_frequencies = selected_frequencies[strongest]

        first, second = np.triu_indices(strongest.size, k=1)
        low_frequency = np.minimum(peak_frequencies[first], peak_frequencies[second])
        frequency_distance = np.abs(peak_frequencies[first] - peak_frequencies[second])
        scale = 0.24 / (0.021 * low_frequency + 19.0)
        interaction = np.exp(-3.5 * scale * frequency_distance) - np.exp(
            -5.75 * scale * frequency_distance
        )
        weights = amplitudes[first] * amplitudes[second]
        output[frame_index] = float(np.sum(weights * interaction) / max(np.sum(weights), 1e-12))

    return output
