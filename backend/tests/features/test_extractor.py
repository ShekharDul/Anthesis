from pathlib import Path

import numpy as np
import pytest
import soundfile as sf  # type: ignore[import-untyped]

from anthesis.audio import AudioComponents, CanonicalAudio, load_audio, separate_harmonic_percussive
from anthesis.features import extract_musical_features


def _musical_fixture(tmp_path: Path) -> tuple[CanonicalAudio, AudioComponents]:
    sample_rate = 22_050
    duration = 6.0
    time = np.arange(round(sample_rate * duration), dtype=np.float64) / sample_rate
    signal = 0.32 * np.sin(2 * np.pi * 440 * time)
    signal += 0.16 * np.sin(2 * np.pi * 554.365 * time)
    signal += 0.20 * np.sin(2 * np.pi * 659.255 * time)
    beat_samples = np.arange(0, signal.size, sample_rate // 2)
    signal[beat_samples] += 0.9
    path = tmp_path / "a-major-120bpm.wav"
    sf.write(path, signal, sample_rate, subtype="FLOAT")
    audio = load_audio(path)
    return audio, separate_harmonic_percussive(audio)


def test_feature_engine_extracts_finite_multiscale_measurements(tmp_path: Path) -> None:
    audio, components = _musical_fixture(tmp_path)

    features = extract_musical_features(audio, components)

    assert 10 <= features.frames.times.size <= 14
    assert features.frames.values.shape[1] >= 45
    assert features.beats.times.size >= 8
    assert np.isfinite(features.frames.values).all()
    assert np.isfinite(features.beats.values).all()
    assert 95 <= features.globals["tempo_bpm"] <= 135
    assert features.globals["pulse_clarity"] > 0
    assert features.labels["key"] == "A"
    assert features.labels["mode"] == "major"
    assert np.median(features.frames.column("predominant_pitch_hz")) == pytest.approx(
        440, abs=15
    )


def test_feature_engine_is_deterministic_and_supports_section_aggregation(tmp_path: Path) -> None:
    audio, components = _musical_fixture(tmp_path)

    first = extract_musical_features(audio, components)
    second = extract_musical_features(audio, components)
    sections = first.frames.aggregate_intervals([0, 2, 4, 6])

    assert first.digest == second.digest
    assert np.array_equal(first.frames.values, second.frames.values)
    assert sections.values.shape == (3, first.frames.values.shape[1])


def test_feature_engine_reuses_separation_spectra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audio, components = _musical_fixture(tmp_path)

    def unexpected_stft(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("feature extraction recomputed a shared STFT")

    monkeypatch.setattr("anthesis.features.extractor.librosa.stft", unexpected_stft)

    features = extract_musical_features(audio, components)

    assert features.frames.times.size > 0
