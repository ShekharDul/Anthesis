"""Transparent key, mode, and harmonic-complexity measurements."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

PITCH_CLASSES = ("C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B")

# Krumhansl-Kessler probe-tone profiles, normalized during correlation.
MAJOR_PROFILE = np.asarray(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    dtype=np.float64,
)
MINOR_PROFILE = np.asarray(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=np.float64,
)


@dataclass(frozen=True, slots=True)
class TonalityEstimate:
    key: str
    mode: str
    strength: float
    mode_evidence: float
    major_strength: float
    minor_strength: float


def chroma_entropy(chroma: NDArray[np.float32]) -> NDArray[np.float32]:
    """Normalized Shannon entropy for each chroma frame."""

    probabilities = chroma / np.maximum(
        np.sum(chroma, axis=0, keepdims=True), np.finfo(float).eps
    )
    entropy = -np.sum(
        probabilities * np.log2(np.maximum(probabilities, np.finfo(float).eps)), axis=0
    )
    return np.asarray(entropy / np.log2(12), dtype=np.float32)


def harmonic_change(chroma: NDArray[np.float32]) -> NDArray[np.float32]:
    """Cosine distance between successive normalized chroma vectors."""

    norms = np.linalg.norm(chroma, axis=0, keepdims=True)
    normalized = chroma / np.maximum(norms, np.finfo(float).eps)
    similarity = np.sum(normalized[:, 1:] * normalized[:, :-1], axis=0)
    change = np.concatenate(([0.0], 1.0 - np.clip(similarity, -1.0, 1.0)))
    return np.asarray(change, dtype=np.float32)


def _correlation(left: NDArray[np.float64], right: NDArray[np.float64]) -> float:
    left_centered = left - np.mean(left)
    right_centered = right - np.mean(right)
    denominator = np.linalg.norm(left_centered) * np.linalg.norm(right_centered)
    if denominator <= np.finfo(float).eps:
        return 0.0
    return float(np.dot(left_centered, right_centered) / denominator)


def estimate_tonality(chroma: NDArray[np.float32]) -> TonalityEstimate:
    """Estimate key and mode by rotating transparent probe-tone profiles."""

    distribution = np.mean(chroma, axis=1, dtype=np.float64)
    major_scores = np.asarray(
        [_correlation(distribution, np.roll(MAJOR_PROFILE, root)) for root in range(12)]
    )
    minor_scores = np.asarray(
        [_correlation(distribution, np.roll(MINOR_PROFILE, root)) for root in range(12)]
    )
    major_root = int(np.argmax(major_scores))
    minor_root = int(np.argmax(minor_scores))
    major = float(major_scores[major_root])
    minor = float(minor_scores[minor_root])
    if max(major, minor) < 0.05:
        key = "unknown"
        mode = "ambiguous"
        strength = max(major, minor)
    elif major >= minor:
        key = PITCH_CLASSES[major_root]
        mode = "major"
        strength = major
    else:
        key = PITCH_CLASSES[minor_root]
        mode = "minor"
        strength = minor
    mode_evidence = 0.0
    if mode != "ambiguous":
        mode_evidence = (major - minor) / max(
            abs(major) + abs(minor), np.finfo(float).eps
        )
    return TonalityEstimate(
        key=key,
        mode=mode,
        strength=float(np.clip(strength, -1.0, 1.0)),
        mode_evidence=float(np.clip(mode_evidence, -1.0, 1.0)),
        major_strength=major,
        minor_strength=minor,
    )
