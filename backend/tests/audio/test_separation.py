from pathlib import Path

import numpy as np
import pytest
import soundfile as sf  # type: ignore[import-untyped]

from anthesis.audio import CanonicalAudio, load_audio, separate_harmonic_percussive


def _canonical_signal(tmp_path: Path, name: str, samples: np.ndarray) -> CanonicalAudio:
    path = tmp_path / name
    sf.write(path, samples, 22_050, subtype="FLOAT")
    return load_audio(path)


def test_hpss_identifies_sustained_tone_as_harmonic(tmp_path: Path) -> None:
    time = np.arange(44_100, dtype=np.float64) / 22_050
    audio = _canonical_signal(tmp_path, "tone.wav", 0.5 * np.sin(2 * np.pi * 440 * time))

    components = separate_harmonic_percussive(audio)

    assert components.harmonic_energy_ratio > components.percussive_energy_ratio * 20
    assert components.reconstruction_rmse < 1e-7


def test_hpss_identifies_impulses_as_percussive(tmp_path: Path) -> None:
    impulses = np.zeros(44_100, dtype=np.float64)
    impulses[::2_205] = 0.9
    audio = _canonical_signal(tmp_path, "clicks.wav", impulses)

    components = separate_harmonic_percussive(audio)

    assert components.percussive_energy_ratio > components.harmonic_energy_ratio * 5
    assert components.reconstruction_rmse < 1e-7
    assert not components.harmonic.flags.writeable
    assert not components.percussive.flags.writeable
    assert not components.residual.flags.writeable
    assert not components.spectrum.flags.writeable
    assert not components.harmonic_spectrum.flags.writeable
    assert not components.percussive_spectrum.flags.writeable


def test_hpss_reconstructs_mixed_signal(tmp_path: Path) -> None:
    time = np.arange(44_100, dtype=np.float64) / 22_050
    mixed = 0.35 * np.sin(2 * np.pi * 220 * time)
    mixed[::5_512] += 0.7
    audio = _canonical_signal(tmp_path, "mixed.wav", mixed)

    components = separate_harmonic_percussive(audio)
    reconstructed = components.harmonic + components.percussive + components.residual

    assert reconstructed == pytest.approx(audio.samples, abs=2e-7)
