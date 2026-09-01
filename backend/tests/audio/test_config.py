import pytest

from anthesis.audio import AudioPreprocessConfig, SeparationConfig


def test_preprocess_configuration_rejects_invalid_duration_bounds() -> None:
    with pytest.raises(ValueError, match="duration bounds"):
        AudioPreprocessConfig(min_duration_seconds=4, max_duration_seconds=2)


def test_separation_configuration_requires_odd_kernels() -> None:
    with pytest.raises(ValueError, match="odd"):
        SeparationConfig(harmonic_kernel=30)
