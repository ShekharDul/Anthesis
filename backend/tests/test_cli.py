from pathlib import Path

import numpy as np
import pytest
import soundfile as sf  # type: ignore[import-untyped]
from PIL import Image

from anthesis.cli import main
from anthesis.processing import GenerationManifest


def _write_tone(path: Path) -> None:
    sample_rate = 22_050
    time = np.arange(sample_rate * 2, dtype=np.float64) / sample_rate
    signal = 0.5 * np.sin(2.0 * np.pi * 293.665 * time)
    signal[np.arange(0, signal.size, sample_rate // 2)] += 0.6
    sf.write(path, signal, sample_rate, subtype="PCM_16")


def test_cli_reports_missing_audio_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = main(["analyze", str(tmp_path / "missing.wav")])

    assert result == 1
    captured = capsys.readouterr()
    assert "does not exist" in captured.err
    assert "Traceback" not in captured.err


def test_cli_generate_writes_png_and_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "music.wav"
    image_path = tmp_path / "flower.png"
    manifest_path = tmp_path / "flower.json"
    _write_tone(source)

    result = main(
        [
            "generate",
            str(source),
            "--output",
            str(image_path),
            "--analysis",
            str(manifest_path),
            "--width",
            "256",
            "--height",
            "320",
            "--supersampling",
            "1",
        ]
    )
    manifest = GenerationManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    assert result == 0
    assert Image.open(image_path).size == (256, 320)
    assert manifest.width == 256
    assert "Flower:" in capsys.readouterr().out
