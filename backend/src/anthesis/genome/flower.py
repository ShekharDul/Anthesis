"""Traceable mapping from MusicGenome coordinates to botanical parameters."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from anthesis.genome.models import MusicGenome

UnitFloat = Annotated[float, Field(ge=0.0, le=1.0)]


class FlowerModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class FlowerMorphology(FlowerModel):
    """Normalized geometry controls for a single bloom and stem."""

    petal_count: Annotated[int, Field(ge=5, le=34)]
    petal_layers: Annotated[int, Field(ge=1, le=5)]
    petal_length: Annotated[float, Field(ge=0.2, le=1.0)]
    petal_width: Annotated[float, Field(ge=0.12, le=0.8)]
    openness: UnitFloat
    petal_curvature: Annotated[float, Field(ge=-1.0, le=1.0)]
    radial_irregularity: Annotated[float, Field(ge=0.0, le=0.4)]
    edge_detail: UnitFloat
    center_size: Annotated[float, Field(ge=0.06, le=0.4)]
    stem_length: Annotated[float, Field(ge=0.4, le=1.0)]
    stem_thickness: Annotated[float, Field(ge=0.015, le=0.12)]
    stem_curve: Annotated[float, Field(ge=-0.5, le=0.5)]
    blossom_tilt: Annotated[float, Field(ge=-0.35, le=0.35)]


class PigmentPalette(FlowerModel):
    """HSL-like pigment coordinates for bloom, accent, stem, and background."""

    bloom_hue_degrees: Annotated[float, Field(ge=0.0, lt=360.0)]
    bloom_saturation: UnitFloat
    bloom_lightness: UnitFloat
    accent_hue_degrees: Annotated[float, Field(ge=0.0, lt=360.0)]
    accent_saturation: UnitFloat
    accent_lightness: UnitFloat
    stem_hue_degrees: Annotated[float, Field(ge=0.0, lt=360.0)]
    background_hue_degrees: Annotated[float, Field(ge=0.0, lt=360.0)]
    background_saturation: Annotated[float, Field(ge=0.0, le=0.2)]
    background_lightness: Annotated[float, Field(ge=0.75, le=1.0)]


class PaintCharacter(FlowerModel):
    """Procedural-media controls, independent of the future rasterizer."""

    wash_transparency: UnitFloat
    pigment_granulation: UnitFloat
    edge_softness: UnitFloat
    stroke_variation: UnitFloat


class FlowerBlueprint(FlowerModel):
    """Complete bounded input to deterministic geometry and paint engines."""

    version: Literal["anthesis-flower-map-v1"] = "anthesis-flower-map-v1"
    variation_seed: Annotated[int, Field(ge=0, le=0xFFFFFFFFFFFFFFFF)]
    morphology: FlowerMorphology
    palette: PigmentPalette
    paint: PaintCharacter

    @property
    def digest(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


_KEY_INDEX = {
    "C": 0,
    "C♯": 1,
    "D": 2,
    "D♯": 3,
    "E": 4,
    "F": 5,
    "F♯": 6,
    "G": 7,
    "G♯": 8,
    "A": 9,
    "A♯": 10,
    "B": 11,
}


def _clamp(value: float, low: float, high: float) -> float:
    return float(np.clip(value, low, high))


def _identity_offset(seed: str, start: int, scale: float) -> float:
    raw = int(seed[start : start + 4], 16) / 65_535.0
    return (raw * 2.0 - 1.0) * scale


def map_genome_to_flower(genome: MusicGenome) -> FlowerBlueprint:
    """Map musical meaning to macro-form and identity to restrained variation."""

    descriptors = genome.descriptors
    valence_unit = (descriptors.valence + 1.0) * 0.5
    section_count = len(genome.sections)
    key_index = _KEY_INDEX.get(genome.key, 0)
    seed = genome.identity.flower_seed
    primary_hue = (
        key_index * 30.0 + 22.0 * (descriptors.tension - 0.5) + _identity_offset(seed, 0, 4.0)
    ) % 360.0
    arc_direction = {"rising": 1.0, "falling": -1.0, "arch": 0.35}.get(genome.energy_arc, 0.0)

    morphology = FlowerMorphology(
        petal_count=int(
            np.clip(
                5 + round(13 * descriptors.formal_complexity + 8 * descriptors.rhythmic_density),
                5,
                34,
            )
        ),
        petal_layers=int(np.clip(1 + round(min(section_count, 8) / 2.5), 1, 5)),
        petal_length=_clamp(
            0.42 + 0.34 * descriptors.sublimity + 0.16 * descriptors.arousal,
            0.2,
            1.0,
        ),
        petal_width=_clamp(
            0.20 + 0.34 * descriptors.harmonicity + 0.18 * (1.0 - descriptors.brightness),
            0.12,
            0.8,
        ),
        openness=_clamp(0.2 + 0.46 * valence_unit + 0.28 * descriptors.arousal, 0.0, 1.0),
        petal_curvature=_clamp(
            0.65 * (descriptors.tension - 0.5) - 0.25 * (valence_unit - 0.5),
            -1.0,
            1.0,
        ),
        radial_irregularity=_clamp(
            0.025
            + 0.20 * descriptors.formal_complexity
            + 0.10 * descriptors.roughness
            + abs(_identity_offset(seed, 4, 0.025)),
            0.0,
            0.4,
        ),
        edge_detail=_clamp(
            0.12 + 0.50 * descriptors.roughness + 0.34 * descriptors.formal_complexity,
            0.0,
            1.0,
        ),
        center_size=_clamp(
            0.08 + 0.19 * descriptors.pulse_clarity + 0.10 * descriptors.percussiveness,
            0.06,
            0.4,
        ),
        stem_length=_clamp(
            0.52 + 0.27 * descriptors.sublimity + 0.14 * descriptors.energy, 0.4, 1.0
        ),
        stem_thickness=_clamp(
            0.025 + 0.055 * descriptors.energy + 0.025 * descriptors.percussiveness,
            0.015,
            0.12,
        ),
        stem_curve=_clamp(0.22 * arc_direction + _identity_offset(seed, 8, 0.08), -0.5, 0.5),
        blossom_tilt=_clamp(
            0.14 * arc_direction + _identity_offset(seed, 12, 0.07),
            -0.35,
            0.35,
        ),
    )
    palette = PigmentPalette(
        bloom_hue_degrees=primary_hue,
        bloom_saturation=_clamp(
            0.32 + 0.40 * descriptors.arousal + 0.18 * descriptors.tonal_clarity,
            0.0,
            1.0,
        ),
        bloom_lightness=_clamp(
            0.32 + 0.32 * valence_unit + 0.18 * descriptors.sublimity,
            0.0,
            1.0,
        ),
        accent_hue_degrees=(primary_hue + 105.0 + 75.0 * descriptors.formal_complexity) % 360.0,
        accent_saturation=_clamp(0.38 + 0.42 * descriptors.tension, 0.0, 1.0),
        accent_lightness=_clamp(0.28 + 0.32 * valence_unit, 0.0, 1.0),
        stem_hue_degrees=(105.0 + 24.0 * (descriptors.brightness - 0.5)) % 360.0,
        background_hue_degrees=(primary_hue + 180.0) % 360.0,
        background_saturation=_clamp(0.025 + 0.08 * descriptors.sublimity, 0.0, 0.2),
        background_lightness=_clamp(0.88 + 0.08 * valence_unit, 0.75, 1.0),
    )
    paint = PaintCharacter(
        wash_transparency=_clamp(0.38 + 0.42 * descriptors.sublimity, 0.0, 1.0),
        pigment_granulation=_clamp(
            0.12 + 0.48 * descriptors.roughness + 0.22 * descriptors.formal_complexity,
            0.0,
            1.0,
        ),
        edge_softness=_clamp(
            0.68 - 0.38 * descriptors.tension + 0.20 * descriptors.sublimity,
            0.0,
            1.0,
        ),
        stroke_variation=_clamp(
            0.16 + 0.48 * descriptors.dynamic_range + 0.28 * descriptors.contrast,
            0.0,
            1.0,
        ),
    )
    return FlowerBlueprint(
        variation_seed=int(seed[:16], 16),
        morphology=morphology,
        palette=palette,
        paint=paint,
    )
