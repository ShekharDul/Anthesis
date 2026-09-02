"""End-to-end orchestration from an audio path to Anthesis deliverables."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from anthesis.analysis import AnalysisConfig, analyze_song
from anthesis.audio import (
    AudioPreprocessConfig,
    SeparationConfig,
    load_audio,
    separate_harmonic_percussive,
)
from anthesis.features import FeatureConfig, extract_musical_features
from anthesis.genome import (
    FlowerBlueprint,
    GenomeConfig,
    MusicGenome,
    build_music_genome,
    map_genome_to_flower,
)
from anthesis.rendering import (
    RENDERER_VERSION,
    RenderConfig,
    generate_flower_geometry,
    render_png_bytes,
)


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    """Explicit configuration for every deterministic processing stage."""

    audio: AudioPreprocessConfig = field(default_factory=AudioPreprocessConfig)
    separation: SeparationConfig = field(default_factory=SeparationConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    genome: GenomeConfig = field(default_factory=GenomeConfig)
    render: RenderConfig = field(default_factory=RenderConfig)


class ProcessingModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class AnalysisDocument(ProcessingModel):
    """Portable renderer input and its traceable musical representation."""

    schema_version: Literal["anthesis-analysis-document-v1"] = "anthesis-analysis-document-v1"
    genome: MusicGenome
    flower: FlowerBlueprint

    @property
    def digest(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class GenerationManifest(ProcessingModel):
    """Metadata accompanying a rendered PNG."""

    schema_version: Literal["anthesis-generation-v1"] = "anthesis-generation-v1"
    analysis: AnalysisDocument
    analysis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    geometry_version: str
    geometry_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    renderer_version: str
    width: int = Field(ge=128, le=4_096)
    height: int = Field(ge=128, le=4_096)
    image_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_analysis_digest(self) -> GenerationManifest:
        if self.analysis_digest != self.analysis.digest:
            raise ValueError("analysis_digest does not match the embedded analysis")
        return self


@dataclass(frozen=True, slots=True)
class GeneratedFlower:
    """In-memory PNG and the JSON manifest that describes it."""

    png: bytes
    manifest: GenerationManifest

    def __post_init__(self) -> None:
        if not self.png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("generated image is not a PNG")
        if hashlib.sha256(self.png).hexdigest() != self.manifest.image_sha256:
            raise ValueError("image_sha256 does not match the generated PNG")


def analyze_file(
    audio_path: str | Path,
    config: ProcessingConfig | None = None,
) -> AnalysisDocument:
    """Run the complete listening pipeline without rasterizing an image."""

    settings = config or ProcessingConfig()
    audio = load_audio(audio_path, settings.audio)
    components = separate_harmonic_percussive(audio, settings.separation)
    features = extract_musical_features(audio, components, settings.features)
    del components
    analysis = analyze_song(audio, features, settings.analysis)
    genome = build_music_genome(audio, features, analysis, settings.genome)
    flower = map_genome_to_flower(genome)
    return AnalysisDocument(genome=genome, flower=flower)


def generate_file(
    audio_path: str | Path,
    config: ProcessingConfig | None = None,
) -> GeneratedFlower:
    """Analyze an audio file and render its deterministic flower PNG."""

    settings = config or ProcessingConfig()
    document = analyze_file(audio_path, settings)
    geometry = generate_flower_geometry(document.flower)
    png = render_png_bytes(document.flower, settings.render)
    return GeneratedFlower(
        png=png,
        manifest=GenerationManifest(
            analysis=document,
            analysis_digest=document.digest,
            geometry_version=geometry.version,
            geometry_digest=geometry.digest,
            renderer_version=RENDERER_VERSION,
            width=settings.render.width,
            height=settings.render.height,
            image_sha256=hashlib.sha256(png).hexdigest(),
        ),
    )
