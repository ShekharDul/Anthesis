from pathlib import Path

import numpy as np
import pytest
import soundfile as sf  # type: ignore[import-untyped]

from anthesis.audio import AudioPreprocessConfig, load_audio
from anthesis.audio.errors import AudioLimitError, AudioNotFoundError, SilentAudioError


def _write_wave(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    sf.write(path, samples, sample_rate, subtype="FLOAT")


def test_load_audio_canonicalizes_stereo_signal_deterministically(tmp_path: Path) -> None:
    source_rate = 44_100
    silence = np.zeros(source_rate // 4)
    time = np.arange(source_rate, dtype=np.float64) / source_rate
    tone = 0.4 * np.sin(2 * np.pi * 440 * time) + 0.08
    left = np.concatenate((silence, tone, silence))
    right = np.concatenate((silence, tone * 0.55, silence))
    path = tmp_path / "stereo.wav"
    _write_wave(path, np.column_stack((left, right)), source_rate)

    first = load_audio(path)
    second = load_audio(path)

    assert first.sample_rate == 22_050
    assert 0.95 <= first.duration_seconds <= 1.15
    assert np.max(np.abs(first.samples)) == pytest.approx(0.98, abs=1e-6)
    assert np.mean(first.samples) == pytest.approx(0, abs=1e-6)
    assert 0 < first.stereo_width < 1
    assert first.trim_start_seconds > 0
    assert first.trim_end_seconds > 0
    assert first.digest == second.digest
    assert np.array_equal(first.samples, second.samples)
    assert not first.samples.flags.writeable


def test_load_audio_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AudioNotFoundError):
        load_audio(tmp_path / "missing.wav")


def test_load_audio_rejects_silence(tmp_path: Path) -> None:
    path = tmp_path / "silence.wav"
    _write_wave(path, np.zeros(44_100), 44_100)

    with pytest.raises(SilentAudioError):
        load_audio(path)


def test_load_audio_enforces_source_duration_limit(tmp_path: Path) -> None:
    path = tmp_path / "long.wav"
    _write_wave(path, np.ones(4_000), 1_000)
    config = AudioPreprocessConfig(
        target_sample_rate=8_000,
        max_duration_seconds=2,
        min_duration_seconds=1,
    )

    with pytest.raises(AudioLimitError, match="duration"):
        load_audio(path, config)
