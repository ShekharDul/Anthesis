"""Model-free song-form analysis using self-similarity and novelty."""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter1d  # type: ignore[import-untyped]
from scipy.signal import find_peaks  # type: ignore[import-untyped]

from anthesis.analysis.config import StructureConfig
from anthesis.analysis.models import StructuralSection, StructureAnalysis
from anthesis.features import FeatureTable, MusicalFeatures

STRUCTURE_COLUMNS = (
    "rms_db",
    "spectral_centroid_hz",
    "spectral_flux",
    "onset_rate_hz",
    "harmonic_ratio",
    "percussive_ratio",
    "chroma_entropy",
    "harmonic_change",
    *(f"mfcc_{index:02d}" for index in range(1, 14)),
    *(f"chroma_{index:02d}" for index in range(12)),
)


def _robust_standardize(values: NDArray[np.float32]) -> NDArray[np.float64]:
    matrix = values.astype(np.float64)
    median = np.median(matrix, axis=0, keepdims=True)
    mad = np.median(np.abs(matrix - median), axis=0, keepdims=True)
    scale = np.maximum(1.4826 * mad, 1e-6)
    return np.clip((matrix - median) / scale, -4.0, 4.0)


def _structure_matrix(frames: FeatureTable) -> NDArray[np.float64]:
    indices = [frames.columns.index(name) for name in STRUCTURE_COLUMNS]
    standardized = _robust_standardize(frames.values[:, indices])
    norms = np.linalg.norm(standardized, axis=1, keepdims=True)
    normalized = standardized / np.maximum(norms, np.finfo(float).eps)
    similarity = normalized @ normalized.T
    return np.clip((similarity + 1.0) * 0.5, 0.0, 1.0)


def _novelty_curve(similarity: NDArray[np.float64], half_window: int) -> NDArray[np.float64]:
    frame_count = similarity.shape[0]
    novelty = np.zeros(frame_count, dtype=np.float64)
    for center in range(half_window, frame_count - half_window):
        left = slice(center - half_window, center)
        right = slice(center, center + half_window)
        within_left = float(np.mean(similarity[left, left]))
        within_right = float(np.mean(similarity[right, right]))
        across = float(np.mean(similarity[left, right]))
        novelty[center] = max(0.0, (within_left + within_right) * 0.5 - across)
    maximum = float(np.max(novelty))
    if maximum > np.finfo(float).eps:
        novelty /= maximum
    return novelty


def _boundary_indices(
    novelty: NDArray[np.float64],
    frame_rate: float,
    config: StructureConfig,
) -> NDArray[np.int64]:
    minimum_distance = max(1, round(config.minimum_section_seconds * frame_rate))
    median = float(np.median(novelty))
    mad = float(np.median(np.abs(novelty - median)))
    prominence = max(config.minimum_peak_prominence, median + 0.75 * mad)
    peaks, properties = find_peaks(novelty, distance=minimum_distance, prominence=prominence)
    available = max(0, config.maximum_sections - 1)
    if peaks.size > available:
        prominences = properties["prominences"]
        selected = np.argsort(prominences)[-available:] if available else np.asarray([], dtype=int)
        peaks = np.sort(peaks[selected])
    return np.asarray(np.concatenate(([0], peaks, [novelty.size])), dtype=np.int64)


def _section_signatures(
    feature_values: NDArray[np.float32], boundaries: NDArray[np.int64]
) -> NDArray[np.float64]:
    signatures = []
    for start, end in pairwise(boundaries):
        block = feature_values[start:end]
        signatures.append(
            np.median(block, axis=0)
            if block.size
            else feature_values[min(start, feature_values.shape[0] - 1)]
        )
    matrix = np.asarray(signatures, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, np.finfo(float).eps)


def _section_labels(signatures: NDArray[np.float64], threshold: float) -> tuple[str, ...]:
    prototypes: list[NDArray[np.float64]] = []
    labels: list[str] = []
    for signature in signatures:
        if prototypes:
            similarities = np.asarray([float(np.dot(signature, item)) for item in prototypes])
            best = int(np.argmax(similarities))
            if similarities[best] >= threshold:
                labels.append(chr(ord("A") + best))
                continue
        prototypes.append(signature)
        labels.append(chr(ord("A") + len(prototypes) - 1))
    return tuple(labels)


def analyze_structure(
    features: MusicalFeatures,
    config: StructureConfig | None = None,
) -> StructureAnalysis:
    """Detect section boundaries, recurrence, contrast, and formal complexity."""

    settings = config or StructureConfig()
    frames = features.frames
    frame_rate = 1.0 / float(np.median(np.diff(frames.times))) if frames.times.size > 1 else 2.0
    half_window = max(1, round(settings.novelty_half_window_seconds * frame_rate))
    similarity = _structure_matrix(frames)
    novelty = _novelty_curve(similarity, min(half_window, max(1, frames.times.size // 3)))
    sigma = settings.novelty_smoothing_seconds * frame_rate
    if sigma > 0:
        novelty = gaussian_filter1d(novelty, sigma=sigma, mode="nearest")
        maximum = float(np.max(novelty))
        if maximum > np.finfo(float).eps:
            novelty /= maximum

    boundaries = _boundary_indices(novelty, frame_rate, settings)
    selected_indices = [frames.columns.index(name) for name in STRUCTURE_COLUMNS]
    selected_values = _robust_standardize(frames.values[:, selected_indices]).astype(np.float32)
    signatures = _section_signatures(selected_values, boundaries)
    labels = _section_labels(signatures, settings.recurrence_threshold)
    section_similarity = np.clip(signatures @ signatures.T, -1.0, 1.0)

    sections: list[StructuralSection] = []
    duration = float(features.globals["duration_seconds"])
    for index, (start, end) in enumerate(pairwise(boundaries)):
        start_seconds = (
            0.0 if start == 0 else float(frames.times[min(start, frames.times.size - 1)])
        )
        end_seconds = duration if end >= frames.times.size else float(frames.times[end])
        contrast = 0.0 if index == 0 else float(1.0 - section_similarity[index - 1, index]) * 0.5
        recurrence_candidates = np.delete(section_similarity[index], index)
        recurrence = float(np.max(recurrence_candidates)) if recurrence_candidates.size else 0.0
        boundary_novelty = float(novelty[start]) if start < novelty.size else 0.0
        sections.append(
            StructuralSection(
                index=index,
                label=labels[index],
                start_seconds=start_seconds,
                end_seconds=max(end_seconds, start_seconds),
                novelty=boundary_novelty,
                contrast=float(np.clip(contrast, 0.0, 1.0)),
                recurrence=float(np.clip((recurrence + 1.0) * 0.5, 0.0, 1.0)),
            )
        )

    recurrence_mask = ~np.eye(similarity.shape[0], dtype=bool)
    recurrence_score = (
        float(np.mean(similarity[recurrence_mask])) if np.any(recurrence_mask) else 0.0
    )
    contrast_score = (
        float(np.mean([section.contrast for section in sections[1:]])) if len(sections) > 1 else 0.0
    )
    label_diversity = len(set(labels)) / max(len(labels), 1)
    complexity = float(
        np.clip(0.45 * label_diversity + 0.35 * contrast_score + 0.20 * np.mean(novelty), 0.0, 1.0)
    )

    # Ensure exact contiguity after converting discrete frame boundaries to seconds.
    for index in range(1, len(sections)):
        sections[index] = replace(sections[index], start_seconds=sections[index - 1].end_seconds)
    novelty_table = FeatureTable(
        times=frames.times,
        values=novelty[:, None].astype(np.float32),
        columns=("structural_novelty",),
        units=("normalized",),
    )
    return StructureAnalysis(
        novelty=novelty_table,
        sections=tuple(sections),
        recurrence_score=float(np.clip(recurrence_score, 0.0, 1.0)),
        contrast_score=contrast_score,
        complexity_score=complexity,
    )
