"""Strict, portable, versioned MusicGenome schema."""

from __future__ import annotations

import hashlib
import json
from itertools import pairwise
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

UnitFloat = Annotated[float, Field(ge=0.0, le=1.0)]
SignedFloat = Annotated[float, Field(ge=-1.0, le=1.0)]
Hex32 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]
Hex64 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class GenomeModel(BaseModel):
    """Shared immutability and strict parsing for public genome records."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class GlobalDescriptors(GenomeModel):
    """Normalized global musical coordinates used by visual mappings."""

    energy: UnitFloat
    dynamic_range: UnitFloat
    tempo: UnitFloat
    pulse_clarity: UnitFloat
    rhythmic_density: UnitFloat
    brightness: UnitFloat
    harmonicity: UnitFloat
    percussiveness: UnitFloat
    roughness: UnitFloat
    tonal_clarity: UnitFloat
    formal_complexity: UnitFloat
    recurrence: UnitFloat
    contrast: UnitFloat
    valence: SignedFloat
    arousal: UnitFloat
    tension: UnitFloat
    sublimity: UnitFloat
    confidence: UnitFloat


class GenomeSection(GenomeModel):
    """One normalized structural interval."""

    index: Annotated[int, Field(ge=0)]
    label: Annotated[str, StringConstraints(min_length=1, max_length=8)]
    start: UnitFloat
    end: UnitFloat
    novelty: UnitFloat
    contrast: UnitFloat
    recurrence: UnitFloat

    @model_validator(mode="after")
    def validate_interval(self) -> GenomeSection:
        if self.end <= self.start:
            raise ValueError("section end must follow its start")
        return self


class ExpressivePoint(GenomeModel):
    """A point on the normalized expressive trajectory."""

    position: UnitFloat
    valence: SignedFloat
    arousal: UnitFloat
    tension: UnitFloat
    complexity: UnitFloat
    sublimity: UnitFloat
    confidence: UnitFloat


class GenomeIdentity(GenomeModel):
    """Exact identity and robust similarity material kept conceptually separate."""

    flower_seed: Hex32
    exact_audio_digest: Hex64
    landmark_signature: Annotated[tuple[int, ...], Field(max_length=512)]

    @field_validator("landmark_signature")
    @classmethod
    def validate_signature(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if any(value < 0 or value > 0xFFFFFFFF for value in values):
            raise ValueError("landmark hashes must be unsigned 32-bit integers")
        if tuple(sorted(set(values))) != values:
            raise ValueError("landmark signature must be sorted and unique")
        return values


class GenomeProvenance(GenomeModel):
    """Version and source facts required to reproduce a genome."""

    source_format: str
    duration_seconds: Annotated[float, Field(gt=0.0)]
    sample_rate: Annotated[int, Field(gt=0)]
    audio_version: str
    feature_version: str
    structure_version: str
    expression_version: str
    fingerprint_version: str
    analysis_version: str


class MusicGenome(GenomeModel):
    """Renderer-independent musical representation consumed by flower systems."""

    schema_version: Literal["anthesis-genome-v1"] = "anthesis-genome-v1"
    key: str
    mode: str
    dominant_affect: str
    energy_arc: str
    descriptors: GlobalDescriptors
    sections: tuple[GenomeSection, ...]
    trajectory: tuple[ExpressivePoint, ...]
    identity: GenomeIdentity
    provenance: GenomeProvenance

    @model_validator(mode="after")
    def validate_sequences(self) -> MusicGenome:
        if not self.sections:
            raise ValueError("a genome requires at least one structural section")
        if len(self.trajectory) < 2:
            raise ValueError("a genome requires at least two expressive points")
        if any(left.position >= right.position for left, right in pairwise(self.trajectory)):
            raise ValueError("trajectory positions must increase strictly")
        if self.sections[0].start != 0.0 or self.sections[-1].end != 1.0:
            raise ValueError("sections must span the complete normalized duration")
        for left, right in pairwise(self.sections):
            if abs(left.end - right.start) > 1e-6:
                raise ValueError("sections must be contiguous")
        return self

    @property
    def digest(self) -> str:
        """Stable content digest for caching and determinism checks."""

        payload = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
