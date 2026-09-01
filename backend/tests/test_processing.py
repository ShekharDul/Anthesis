import hashlib
from io import BytesIO
from pathlib import Path

import numpy as np
import soundfile as sf  # type: ignore[import-untyped]
from PIL import Image

from anthesis.processing import ProcessingConfig, generate_file
from anthesis.rendering import RenderConfig


def _write_music(path: Path) -> None:
    sample_rate = 22_050
    duration = 4.0
    time = np.arange(round(sample_rate * duration), dtype=np.float64) / sample_rate
    signal = 0.46 * np.sin(2.0 * np.pi * 220.0 * time)
    signal += 0.22 * np.sin(2.0 * np.pi * 330.0 * time)
    signal[np.arange(0, signal.size, sample_rate // 2)] += 0.72
    sf.write(path, signal, sample_rate, subtype="PCM_16")


def test_end_to_end_processing_produces_consistent_manifest_and_png(tmp_path: Path) -> None:
    audio_path = tmp_path / "music.wav"
    _write_music(audio_path)
    config = ProcessingConfig(
        render=RenderConfig(width=192, height=256, supersampling=1, paper_grain=0.01)
    )

    first = generate_file(audio_path, config)
    second = generate_file(audio_path, config)
    image = Image.open(BytesIO(first.png))

    assert first.png == second.png
    assert first.manifest == second.manifest
    assert first.manifest.image_sha256 == hashlib.sha256(first.png).hexdigest()
    assert first.manifest.analysis_digest == first.manifest.analysis.digest
    assert first.manifest.analysis.genome.identity.exact_audio_digest
    assert first.manifest.width == 192
    assert image.size == (192, 256)
