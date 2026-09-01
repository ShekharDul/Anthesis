"""Immutable outputs of high-level Anthesis analysis."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from anthesis.features import FeatureTable


@dataclass(frozen=True, slots=True)
class StructuralSection:
    """One contiguous segment in the detected musical form."""

    index: int
    label: str
    start_seconds: float
    end_seconds: float
    novelty: float
    contrast: float
    recurrence: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True, slots=True)
class StructureAnalysis:
    """Compact representation of musical boundaries and recurrence."""

    novelty: FeatureTable
    sections: tuple[StructuralSection, ...]
    recurrence_score: float
    contrast_score: float
    complexity_score: float
    version: str = "anthesis-structure-v1"

    @property
    def boundaries_seconds(self) -> tuple[float, ...]:
        starts = tuple(section.start_seconds for section in self.sections)
        return (*starts, self.sections[-1].end_seconds)


@dataclass(frozen=True, slots=True)
class ExpressiveAnalysis:
    """Time-varying expressive estimates with uncertainty and summaries."""

    curves: FeatureTable
    summaries: Mapping[str, float]
    labels: Mapping[str, str]
    version: str = "anthesis-expression-v1"

    def __post_init__(self) -> None:
        numeric = {key: float(value) for key, value in self.summaries.items()}
        if not all(np.isfinite(value) for value in numeric.values()):
            raise ValueError("expressive summaries cannot contain non-finite values")
        object.__setattr__(self, "summaries", MappingProxyType(numeric))
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


@dataclass(frozen=True, slots=True, order=True)
class Landmark:
    """One robust pair of time-frequency peaks."""

    time_frame: int
    hash32: int
    anchor_bin: int
    target_bin: int
    delta_frames: int


@dataclass(frozen=True, slots=True)
class AcousticFingerprint:
    """Robust constellation identity plus an exact canonical provenance hash."""

    landmarks: tuple[Landmark, ...]
    signature: tuple[int, ...]
    seed_hex: str
    exact_audio_digest: str
    duration_seconds: float
    version: str = "anthesis-fingerprint-v1"

    def similarity(self, other: AcousticFingerprint) -> float:
        """Jaccard similarity of robust pair hashes, independent of timestamps."""

        own_hashes = {landmark.hash32 for landmark in self.landmarks}
        other_hashes = {landmark.hash32 for landmark in other.landmarks}
        union = own_hashes | other_hashes
        if not union:
            return 1.0 if not own_hashes and not other_hashes else 0.0
        return len(own_hashes & other_hashes) / len(union)

    @property
    def digest(self) -> str:
        digest = hashlib.sha256(self.version.encode("ascii"))
        digest.update(bytes.fromhex(self.seed_hex))
        for landmark in self.landmarks:
            digest.update(landmark.hash32.to_bytes(4, "little", signed=False))
            digest.update(landmark.time_frame.to_bytes(4, "little", signed=False))
        return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class SongAnalysis:
    """Complete high-level analysis consumed by the future MusicGenome."""

    structure: StructureAnalysis
    expression: ExpressiveAnalysis
    fingerprint: AcousticFingerprint
    version: str = "anthesis-song-analysis-v1"
