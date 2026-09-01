from pathlib import Path

import numpy as np
import pytest
import soundfile as sf  # type: ignore[import-untyped]
from pydantic import ValidationError

from anthesis.analysis import analyze_song
from anthesis.audio import load_audio, separate_harmonic_percussive
from anthesis.features import extract_musical_features
from anthesis.genome import (
    GenomeConfig,
    GlobalDescriptors,
    MusicGenome,
    build_music_genome,
    map_genome_to_flower,
)


def _pipeline(tmp_path: Path, frequency: float) -> MusicGenome:
    sample_rate = 22_050
    duration = 7.0
    time = np.arange(round(sample_rate * duration), dtype=np.float64) / sample_rate
    envelope = 0.45 + 0.4 * time / duration
    signal = envelope * np.sin(2.0 * np.pi * frequency * time)
    signal += 0.25 * np.sin(2.0 * np.pi * frequency * 1.5 * time)
    signal[np.arange(0, signal.size, sample_rate // 2)] += 0.65
    path = tmp_path / f"song-{frequency}.wav"
    sf.write(path, signal, sample_rate, subtype="PCM_16")
    audio = load_audio(path)
    features = extract_musical_features(audio, separate_harmonic_percussive(audio))
    analysis = analyze_song(audio, features)
    return build_music_genome(
        audio,
        features,
        analysis,
        GenomeConfig(maximum_trajectory_points=8),
    )


def test_genome_is_deterministic_portable_and_private(tmp_path: Path) -> None:
    first = _pipeline(tmp_path, 220.0)
    second = _pipeline(tmp_path, 220.0)
    serialized = first.model_dump_json()
    restored = MusicGenome.model_validate_json(serialized, strict=True)

    assert first == second == restored
    assert first.digest == second.digest == restored.digest
    assert 2 <= len(first.trajectory) <= 8
    assert first.sections[0].start == 0.0
    assert first.sections[-1].end == 1.0
    assert "song-220.0.wav" not in serialized
    assert all(0.0 <= point.position <= 1.0 for point in first.trajectory)


def test_flower_mapping_is_bounded_traceable_and_identity_preserving(tmp_path: Path) -> None:
    genome = _pipeline(tmp_path, 261.626)
    first = map_genome_to_flower(genome)
    second = map_genome_to_flower(genome)
    complex_descriptors = genome.descriptors.model_copy(
        update={"formal_complexity": 1.0, "roughness": 1.0}
    )
    complex_genome = genome.model_copy(update={"descriptors": complex_descriptors})
    complex_flower = map_genome_to_flower(complex_genome)

    assert first == second
    assert first.digest == second.digest
    assert first.variation_seed == int(genome.identity.flower_seed[:16], 16)
    assert complex_flower.morphology.petal_count >= first.morphology.petal_count
    assert complex_flower.morphology.edge_detail >= first.morphology.edge_detail
    assert 0.0 <= first.palette.bloom_hue_degrees < 360.0
    assert 5 <= first.morphology.petal_count <= 34


def test_distinct_audio_keeps_distinct_flower_identity(tmp_path: Path) -> None:
    first_genome = _pipeline(tmp_path, 196.0)
    second_genome = _pipeline(tmp_path, 329.628)
    first_flower = map_genome_to_flower(first_genome)
    second_flower = map_genome_to_flower(second_genome)

    assert first_genome.identity.flower_seed != second_genome.identity.flower_seed
    assert first_flower.variation_seed != second_flower.variation_seed
    assert first_flower.digest != second_flower.digest


def test_schema_rejects_out_of_range_descriptors() -> None:
    with pytest.raises(ValidationError):
        GlobalDescriptors(
            energy=1.1,
            dynamic_range=0.5,
            tempo=0.5,
            pulse_clarity=0.5,
            rhythmic_density=0.5,
            brightness=0.5,
            harmonicity=0.5,
            percussiveness=0.5,
            roughness=0.5,
            tonal_clarity=0.5,
            formal_complexity=0.5,
            recurrence=0.5,
            contrast=0.5,
            valence=0.0,
            arousal=0.5,
            tension=0.5,
            sublimity=0.5,
            confidence=0.5,
        )

    with pytest.raises(ValueError, match="at least two"):
        GenomeConfig(maximum_trajectory_points=1)
