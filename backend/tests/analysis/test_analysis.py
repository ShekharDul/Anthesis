from pathlib import Path

import numpy as np
import soundfile as sf  # type: ignore[import-untyped]

from anthesis.analysis import AnalysisConfig, StructureConfig, analyze_song, fingerprint_audio
from anthesis.audio import CanonicalAudio, load_audio, separate_harmonic_percussive
from anthesis.features import extract_musical_features


def _write_song(path: Path, root_hz: float) -> CanonicalAudio:
    sample_rate = 22_050
    duration = 12.0
    time = np.arange(round(sample_rate * duration), dtype=np.float64) / sample_rate
    section = np.floor(time / 4.0).astype(np.int64)
    middle_multiplier = np.where(section == 1, 1.5, 1.0)
    envelope = 0.55 + 0.35 * np.sin(np.pi * (time % 4.0) / 4.0)
    signal = envelope * 0.32 * np.sin(2.0 * np.pi * root_hz * middle_multiplier * time)
    signal += 0.17 * np.sin(2.0 * np.pi * root_hz * 1.25 * middle_multiplier * time)
    pulse_indices = np.arange(0, signal.size, sample_rate // 2)
    signal[pulse_indices] += 0.7
    sf.write(path, signal, sample_rate, subtype="PCM_16")
    return load_audio(path)


def test_song_analysis_is_deterministic_and_bounded(tmp_path: Path) -> None:
    audio = _write_song(tmp_path / "song.wav", 220.0)
    components = separate_harmonic_percussive(audio)
    features = extract_musical_features(audio, components)
    config = AnalysisConfig(
        structure=StructureConfig(
            novelty_half_window_seconds=2.0,
            novelty_smoothing_seconds=0.25,
            minimum_section_seconds=3.0,
        )
    )

    first = analyze_song(audio, features, config)
    second = analyze_song(audio, features, config)

    assert first.fingerprint.digest == second.fingerprint.digest
    assert first.fingerprint.seed_hex == second.fingerprint.seed_hex
    assert np.array_equal(first.expression.curves.values, second.expression.curves.values)
    assert first.structure.boundaries_seconds[0] == 0.0
    assert first.structure.boundaries_seconds[-1] == audio.duration_seconds
    assert 2 <= len(first.structure.sections) <= 4
    assert first.structure.sections[0].label == first.structure.sections[-1].label
    assert np.all(np.abs(first.expression.curves.column("valence")) <= 1.0)
    for column in first.expression.curves.columns[1:]:
        assert np.all(first.expression.curves.column(column) >= 0.0)
        assert np.all(first.expression.curves.column(column) <= 1.0)


def test_fingerprint_survives_lossless_container_change(tmp_path: Path) -> None:
    wave_path = tmp_path / "song.wav"
    wave_audio = _write_song(wave_path, 261.626)
    flac_path = tmp_path / "song.flac"
    source_samples, source_rate = sf.read(wave_path, dtype="int16")
    sf.write(flac_path, source_samples, source_rate, subtype="PCM_16")
    flac_audio = load_audio(flac_path)

    wave_fingerprint = fingerprint_audio(wave_audio)
    flac_fingerprint = fingerprint_audio(flac_audio)

    assert wave_fingerprint.seed_hex == flac_fingerprint.seed_hex
    assert wave_fingerprint.similarity(flac_fingerprint) == 1.0


def test_different_songs_produce_different_flower_seeds(tmp_path: Path) -> None:
    first = fingerprint_audio(_write_song(tmp_path / "first.wav", 196.0))
    second = fingerprint_audio(_write_song(tmp_path / "second.wav", 329.628))

    assert first.seed_hex != second.seed_hex
    assert first.similarity(second) < 0.5
