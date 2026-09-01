"""Composition of Anthesis high-level deterministic analyses."""

from __future__ import annotations

from anthesis.analysis.config import AnalysisConfig
from anthesis.analysis.expression import analyze_expression
from anthesis.analysis.fingerprint import fingerprint_audio
from anthesis.analysis.models import SongAnalysis
from anthesis.analysis.structure import analyze_structure
from anthesis.audio import CanonicalAudio
from anthesis.features import MusicalFeatures


def analyze_song(
    audio: CanonicalAudio,
    features: MusicalFeatures,
    config: AnalysisConfig | None = None,
) -> SongAnalysis:
    """Run structure, expression, and identity analysis in dependency order."""

    settings = config or AnalysisConfig()
    structure = analyze_structure(features, settings.structure)
    expression = analyze_expression(features, structure)
    fingerprint = fingerprint_audio(audio, settings.fingerprint)
    return SongAnalysis(
        structure=structure,
        expression=expression,
        fingerprint=fingerprint,
    )
