"""Translate analysis outputs into the portable MusicGenome schema."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from anthesis.analysis import SongAnalysis
from anthesis.audio import CanonicalAudio
from anthesis.features import MusicalFeatures
from anthesis.genome.config import GenomeConfig
from anthesis.genome.models import (
    ExpressivePoint,
    GenomeIdentity,
    GenomeProvenance,
    GenomeSection,
    GlobalDescriptors,
    MusicGenome,
)


def _unit(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _trajectory_indices(size: int, maximum: int) -> NDArray[np.int64]:
    if size <= maximum:
        return np.arange(size, dtype=np.int64)
    return np.unique(np.rint(np.linspace(0, size - 1, maximum)).astype(np.int64))


def _descriptors(features: MusicalFeatures, analysis: SongAnalysis) -> GlobalDescriptors:
    globals_ = features.globals
    expression = analysis.expression.summaries
    return GlobalDescriptors(
        energy=_unit((globals_["mean_rms_db"] + 45.0) / 40.0),
        dynamic_range=_unit(globals_["std_rms_db"] / 18.0),
        tempo=_unit((globals_["tempo_bpm"] - 45.0) / 135.0),
        pulse_clarity=_unit(globals_["pulse_clarity"]),
        rhythmic_density=_unit(globals_["mean_onset_rate_hz"] / 8.0),
        brightness=_unit(globals_["mean_spectral_centroid_hz"] / 6_000.0),
        harmonicity=_unit(globals_["mean_harmonic_ratio"]),
        percussiveness=_unit(globals_["mean_percussive_ratio"]),
        roughness=_unit(globals_["mean_spectral_roughness"] / 0.2),
        tonal_clarity=_unit(globals_["key_strength"]),
        formal_complexity=_unit(analysis.structure.complexity_score),
        recurrence=_unit(analysis.structure.recurrence_score),
        contrast=_unit(analysis.structure.contrast_score),
        valence=float(np.clip(expression["mean_valence"], -1.0, 1.0)),
        arousal=_unit(expression["mean_arousal"]),
        tension=_unit(expression["mean_tension"]),
        sublimity=_unit(expression["mean_sublimity"]),
        confidence=_unit(expression["mean_confidence"]),
    )


def _validate_inputs(
    audio: CanonicalAudio,
    features: MusicalFeatures,
    analysis: SongAnalysis,
) -> None:
    tolerance = 1.0 / audio.sample_rate
    if abs(features.globals["duration_seconds"] - audio.duration_seconds) > tolerance:
        raise ValueError("features and canonical audio have different durations")
    if abs(analysis.fingerprint.duration_seconds - audio.duration_seconds) > tolerance:
        raise ValueError("analysis and canonical audio have different durations")
    if analysis.fingerprint.exact_audio_digest != audio.digest:
        raise ValueError("analysis fingerprint belongs to different canonical audio")


def build_music_genome(
    audio: CanonicalAudio,
    features: MusicalFeatures,
    analysis: SongAnalysis,
    config: GenomeConfig | None = None,
) -> MusicGenome:
    """Build a deterministic renderer-independent representation of one song."""

    settings = config or GenomeConfig()
    _validate_inputs(audio, features, analysis)
    duration = audio.duration_seconds
    sections = tuple(
        GenomeSection(
            index=section.index,
            label=section.label,
            start=_unit(section.start_seconds / duration),
            end=_unit(section.end_seconds / duration),
            novelty=_unit(section.novelty),
            contrast=_unit(section.contrast),
            recurrence=_unit(section.recurrence),
        )
        for section in analysis.structure.sections
    )
    curves = analysis.expression.curves
    indices = _trajectory_indices(curves.times.size, settings.maximum_trajectory_points)
    trajectory = tuple(
        ExpressivePoint(
            position=_unit(float(curves.times[index]) / duration),
            valence=float(curves.column("valence")[index]),
            arousal=float(curves.column("arousal")[index]),
            tension=float(curves.column("tension")[index]),
            complexity=float(curves.column("complexity")[index]),
            sublimity=float(curves.column("sublimity")[index]),
            confidence=float(curves.column("overall_confidence")[index]),
        )
        for index in indices
    )
    fingerprint = analysis.fingerprint
    return MusicGenome(
        key=features.labels.get("key", "unknown"),
        mode=features.labels.get("mode", "ambiguous"),
        dominant_affect=analysis.expression.labels["dominant_affect"],
        energy_arc=analysis.expression.labels["energy_arc"],
        descriptors=_descriptors(features, analysis),
        sections=sections,
        trajectory=trajectory,
        identity=GenomeIdentity(
            flower_seed=fingerprint.seed_hex,
            exact_audio_digest=fingerprint.exact_audio_digest,
            landmark_signature=fingerprint.signature,
        ),
        provenance=GenomeProvenance(
            source_format=audio.source.format,
            duration_seconds=duration,
            sample_rate=audio.sample_rate,
            audio_version=audio.version,
            feature_version=features.version,
            structure_version=analysis.structure.version,
            expression_version=analysis.expression.version,
            fingerprint_version=fingerprint.version,
            analysis_version=analysis.version,
        ),
    )
