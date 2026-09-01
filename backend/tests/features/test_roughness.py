import numpy as np

from anthesis.features.roughness import spectral_roughness


def test_close_spectral_partials_are_rougher_than_an_octave() -> None:
    frequencies = np.arange(0, 2_001, 10, dtype=np.float64)
    close = np.zeros((1, frequencies.size), dtype=np.float32)
    octave = np.zeros_like(close)
    close[0, 44] = close[0, 48] = 1
    octave[0, 44] = octave[0, 88] = 1

    close_value = spectral_roughness(
        close, frequencies, peak_count=8, min_hz=40, max_hz=2_000
    )[0]
    octave_value = spectral_roughness(
        octave, frequencies, peak_count=8, min_hz=40, max_hz=2_000
    )[0]

    assert close_value > octave_value
