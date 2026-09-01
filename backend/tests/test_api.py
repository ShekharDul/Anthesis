import base64
from io import BytesIO

import numpy as np
import soundfile as sf  # type: ignore[import-untyped]
from fastapi.testclient import TestClient
from PIL import Image

from anthesis.api import create_app


def _wave_bytes(*, silent: bool = False) -> bytes:
    sample_rate = 22_050
    time = np.arange(sample_rate * 2, dtype=np.float64) / sample_rate
    signal = np.zeros_like(time) if silent else 0.5 * np.sin(2.0 * np.pi * 261.626 * time)
    if not silent:
        signal[np.arange(0, signal.size, sample_rate // 2)] += 0.6
    buffer = BytesIO()
    sf.write(buffer, signal, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def test_health_and_openapi_are_available() -> None:
    with TestClient(create_app()) as client:
        health = client.get("/api/v1/health")
        schema = client.get("/openapi.json")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "/api/v1/generate" in schema.json()["paths"]


def test_generate_returns_image_and_manifest() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/generate?width=256&height=320&supersampling=1",
            files={"audio": ("music.wav", _wave_bytes(), "audio/wav")},
        )

    payload = response.json()
    png = base64.b64decode(payload["image"]["base64"], validate=True)
    image = Image.open(BytesIO(png))
    assert response.status_code == 200
    assert payload["image"]["media_type"] == "image/png"
    assert payload["manifest"]["width"] == 256
    assert image.size == (256, 320)


def test_audio_errors_are_safe_and_structured() -> None:
    with TestClient(create_app()) as client:
        empty = client.post(
            "/api/v1/analyze",
            files={"audio": ("empty.wav", b"", "audio/wav")},
        )
        silent = client.post(
            "/api/v1/analyze",
            files={"audio": ("silent.wav", _wave_bytes(silent=True), "audio/wav")},
        )

    assert empty.status_code == 400
    assert empty.json()["detail"]["code"] == "empty_upload"
    assert silent.status_code == 422
    assert silent.json()["code"] == "SilentAudioError"
