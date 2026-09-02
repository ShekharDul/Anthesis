import pytest

from anthesis.audio import AudioPreprocessConfig, SeparationConfig
from anthesis.features import FeatureConfig


def test_preprocess_configuration_rejects_invalid_duration_bounds() -> None:
    with pytest.raises(ValueError, match="duration bounds"):
        AudioPreprocessConfig(min_duration_seconds=4, max_duration_seconds=2)


def test_separation_configuration_requires_odd_kernels() -> None:
    with pytest.raises(ValueError, match="odd"):
        SeparationConfig(harmonic_kernel=30)


def test_default_spectral_analysis_uses_shared_music_resolution() -> None:
    separation = SeparationConfig()
    features = FeatureConfig()

    assert separation.hop_length == features.hop_length == 1_024
    assert separation.n_fft == features.n_fft == 2_048
