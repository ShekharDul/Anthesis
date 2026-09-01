"""Explainable acoustic estimates of a recording's expressed emotion."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter1d  # type: ignore[import-untyped]

from anthesis.analysis.models import ExpressiveAnalysis, StructureAnalysis
from anthesis.features import FeatureTable, MusicalFeatures

EXPRESSION_COLUMNS = (
    "valence",
    "arousal",
    "tension",
    "complexity",
    "sublimity",
    "vitality",
    "unease",
    "valence_confidence",
    "arousal_confidence",
    "overall_confidence",
)


def _unit(values: NDArray[np.float32] | NDArray[np.float64]) -> NDArray[np.float64]:
    """Robustly scale a within-song cue to zero through one."""

    numeric = values.astype(np.float64)
    low, high = np.percentile(numeric, (10.0, 90.0))
    if high - low <= np.finfo(float).eps:
        return np.full(numeric.shape, 0.5, dtype=np.float64)
    return np.asarray(np.clip((numeric - low) / (high - low), 0.0, 1.0), dtype=np.float64)


def _smooth(values: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.asarray(
        gaussian_filter1d(values, sigma=1.0, axis=0, mode="nearest"),
        dtype=np.float64,
    )


def _affect_label(valence: float, arousal: float) -> str:
    if arousal >= 0.58:
        return "bright-energy" if valence >= 0.0 else "charged-tension"
    if arousal <= 0.42:
        return "calm-warmth" if valence >= 0.0 else "quiet-melancholy"
    return "balanced" if abs(valence) < 0.2 else ("gentle-light" if valence > 0 else "pensive")


def _arc_label(arousal: NDArray[np.float64]) -> str:
    third = max(1, arousal.size // 3)
    start = float(np.mean(arousal[:third]))
    middle = float(np.mean(arousal[third:-third])) if arousal.size > 2 * third else start
    end = float(np.mean(arousal[-third:]))
    if middle > max(start, end) + 0.12:
        return "arch"
    if end > start + 0.12:
        return "rising"
    if start > end + 0.12:
        return "falling"
    return "steady"


def analyze_expression(
    features: MusicalFeatures,
    structure: StructureAnalysis,
) -> ExpressiveAnalysis:
    """Estimate expressed affect from documented, inspectable acoustic cues.

    These are musical-expression estimates, not claims about a listener's
    internal state. Every curve is a fixed weighted combination of features.
    """

    frames = features.frames
    energy = np.clip((frames.column("rms_db") + 45.0) / 40.0, 0.0, 1.0)
    brightness = np.clip(frames.column("spectral_centroid_hz") / 6_000.0, 0.0, 1.0)
    flux = _unit(frames.column("spectral_flux"))
    onset = np.clip(frames.column("onset_rate_hz") / 8.0, 0.0, 1.0)
    percussive = np.clip(frames.column("percussive_ratio"), 0.0, 1.0)
    harmonic = np.clip(frames.column("harmonic_ratio"), 0.0, 1.0)
    residual = np.clip(frames.column("residual_ratio"), 0.0, 1.0)
    entropy = np.clip(frames.column("chroma_entropy"), 0.0, 1.0)
    change = np.clip(frames.column("harmonic_change") * 0.5, 0.0, 1.0)
    roughness = _unit(frames.column("spectral_roughness"))
    flatness = np.clip(frames.column("spectral_flatness") * 4.0, 0.0, 1.0)

    tempo = np.clip((features.globals.get("tempo_bpm", 0.0) - 45.0) / 135.0, 0.0, 1.0)
    pulse = np.clip(features.globals.get("pulse_clarity", 0.0), 0.0, 1.0)
    regularity = np.clip(features.globals.get("beat_regularity", 0.0), 0.0, 1.0)
    key_strength = np.clip(features.globals.get("key_strength", 0.0), 0.0, 1.0)
    mode = np.clip(features.globals.get("mode_evidence", 0.0), -1.0, 1.0)
    silence = np.clip(frames.column("silence_ratio"), 0.0, 1.0)
    pitch_confidence = np.clip(frames.column("pitch_confidence"), 0.0, 1.0)

    arousal = (
        0.28 * energy
        + 0.18 * tempo
        + 0.17 * onset
        + 0.14 * flux
        + 0.11 * brightness
        + 0.07 * percussive
        + 0.05 * pulse
    )
    consonance = 1.0 - roughness
    valence = np.clip(
        0.34 * mode * key_strength
        + 0.22 * (consonance - 0.5) * 2.0
        + 0.16 * (1.0 - change - 0.5) * 2.0
        + 0.14 * (brightness - 0.5) * 2.0
        + 0.14 * (energy - 0.5) * 2.0,
        -1.0,
        1.0,
    )
    tension = np.clip(
        0.28 * roughness
        + 0.23 * change
        + 0.18 * entropy
        + 0.14 * flux
        + 0.10 * onset
        + 0.07 * residual,
        0.0,
        1.0,
    )
    complexity = np.clip(
        0.25 * entropy
        + 0.20 * change
        + 0.18 * flatness
        + 0.14 * flux
        + 0.08 * onset
        + 0.15 * structure.complexity_score,
        0.0,
        1.0,
    )
    sublimity = np.clip(
        harmonic * consonance * (0.55 + 0.45 * key_strength) * (1.0 - 0.55 * tension),
        0.0,
        1.0,
    )
    vitality = np.clip(arousal * (0.7 + 0.3 * np.maximum(valence, 0.0)), 0.0, 1.0)
    unease = np.clip(tension * (0.7 + 0.3 * np.maximum(-valence, 0.0)), 0.0, 1.0)

    valence_confidence = np.clip(
        (0.34 * key_strength + 0.28 * pitch_confidence + 0.24 * harmonic + 0.14 * (1.0 - residual))
        * (1.0 - 0.5 * silence),
        0.0,
        1.0,
    )
    arousal_confidence = np.clip(
        (0.30 * pulse + 0.25 * regularity + 0.25 * (1.0 - silence) + 0.20 * energy),
        0.0,
        1.0,
    )
    overall_confidence = (valence_confidence + arousal_confidence) * 0.5

    values = _smooth(
        np.column_stack(
            (
                valence,
                arousal,
                tension,
                complexity,
                sublimity,
                vitality,
                unease,
                valence_confidence,
                arousal_confidence,
                overall_confidence,
            )
        )
    )
    values[:, 0] = np.clip(values[:, 0], -1.0, 1.0)
    values[:, 1:] = np.clip(values[:, 1:], 0.0, 1.0)
    curves = FeatureTable(
        times=frames.times,
        values=values.astype(np.float32),
        columns=EXPRESSION_COLUMNS,
        units=("signed", *("normalized" for _ in EXPRESSION_COLUMNS[1:])),
    )

    mean_valence = float(np.mean(values[:, 0]))
    mean_arousal = float(np.mean(values[:, 1]))
    climax_index = int(np.argmax(0.7 * values[:, 1] + 0.3 * values[:, 2]))
    third = max(1, values.shape[0] // 3)
    resolution = float(np.mean(values[-third:, 2]) - np.mean(values[:third, 2]))
    summaries = {
        "mean_valence": mean_valence,
        "mean_arousal": mean_arousal,
        "mean_tension": float(np.mean(values[:, 2])),
        "mean_complexity": float(np.mean(values[:, 3])),
        "mean_sublimity": float(np.mean(values[:, 4])),
        "mean_confidence": float(np.mean(values[:, 9])),
        "emotional_volatility": float(np.mean(np.abs(np.diff(values[:, :3], axis=0))))
        if values.shape[0] > 1
        else 0.0,
        "climax_seconds": float(frames.times[climax_index]),
        "climax_strength": float(values[climax_index, 1]),
        "tension_resolution": float(np.clip(-resolution, -1.0, 1.0)),
    }
    return ExpressiveAnalysis(
        curves=curves,
        summaries=summaries,
        labels={
            "dominant_affect": _affect_label(mean_valence, mean_arousal),
            "energy_arc": _arc_label(values[:, 1]),
        },
    )
