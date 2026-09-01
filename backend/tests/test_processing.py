import hashlib
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf  # type: ignore[import-untyped]
from PIL import Image

from anthesis.processing import GeneratedFlower, ProcessingConfig, generate_file
from anthesis.rendering import RenderConfig

EXPECTED_AUDIO_DIGEST = "126e9b6c001e303136d60cc74eafce552baa7ec0edc497942a19aac269d6c94a"
EXPECTED_GENOME_DIGEST = "c6a7835de88dde01b30a1766370a91f9c8540db336c830066b980f52c97b670e"
EXPECTED_ANALYSIS_DIGEST = "ec2f056fe3d1699f40eb9f44f9962146c3a86ab968b2fc77b8c77340f41280ea"
EXPECTED_GEOMETRY_DIGEST = "4791a8e83c38b2654c8280b8a4633a6acb17807d1b800be22b67f81bcc9fe156"
EXPECTED_IMAGE_DIGEST = "6e6499808219406fa472cd369b2ea675509a0cf5bafafc8185304a89e3b5a36f"


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

    # Intentional version lock: update only when a documented algorithm or
    # renderer version changes, never to conceal accidental output drift.
    assert first.manifest.analysis.genome.identity.exact_audio_digest == EXPECTED_AUDIO_DIGEST
    assert first.manifest.analysis.genome.digest == EXPECTED_GENOME_DIGEST
    assert first.manifest.analysis_digest == EXPECTED_ANALYSIS_DIGEST
    assert first.manifest.geometry_digest == EXPECTED_GEOMETRY_DIGEST
    assert first.manifest.image_sha256 == EXPECTED_IMAGE_DIGEST

    with pytest.raises(ValueError, match="not a PNG"):
        GeneratedFlower(png=b"corrupted", manifest=first.manifest)
