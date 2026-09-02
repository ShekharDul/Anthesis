import base64
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import NoReturn

import numpy as np
import pytest
import soundfile as sf  # type: ignore[import-untyped]
from fastapi.testclient import TestClient
from PIL import Image

import anthesis.api as api_module
from anthesis.api import create_app
from anthesis.audio.errors import SilentAudioError


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
    assert health.headers["cache-control"] == "no-store"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert "/api/v1/generate" in schema.json()["paths"]


def test_built_web_experience_is_served_without_hiding_api(tmp_path: Path) -> None:
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<h1>Anthesis</h1>", encoding="utf-8")

    with TestClient(create_app(web_directory=web)) as client:
        homepage = client.get("/")
        health = client.get("/api/v1/health")

    assert homepage.status_code == 200
    assert "<h1>Anthesis</h1>" in homepage.text
    assert health.status_code == 200


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


def test_upload_limit_is_enforced_while_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_module, "MAX_WEB_UPLOAD_BYTES", 8)
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/analyze",
            files={"audio": ("large.wav", b"123456789", "audio/wav")},
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "upload_too_large"


def test_decode_errors_do_not_disclose_temporary_paths() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/analyze",
            files={"audio": ("broken.wav", b"not an audio container", "audio/wav")},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "AudioDecodeError"
    assert "anthesis-upload" not in response.json()["message"]


def test_processing_concurrency_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    release = threading.Event()
    both_started = threading.Event()
    lock = threading.Lock()
    started = 0

    def slow_analysis(_path: Path) -> NoReturn:
        nonlocal started
        with lock:
            started += 1
            if started == 2:
                both_started.set()
        release.wait(timeout=2)
        raise SilentAudioError("test signal")

    monkeypatch.setattr(api_module, "analyze_file", slow_analysis)
    monkeypatch.setattr(api_module, "PROCESSING_SLOT_TIMEOUT_SECONDS", 0.05)
    with TestClient(create_app()) as client, ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            client.post,
            "/api/v1/analyze",
            files={"audio": ("first.wav", b"staged", "audio/wav")},
        )
        second = pool.submit(
            client.post,
            "/api/v1/analyze",
            files={"audio": ("second.wav", b"staged", "audio/wav")},
        )
        assert both_started.wait(timeout=2)
        busy = client.post(
            "/api/v1/analyze",
            files={"audio": ("third.wav", b"staged", "audio/wav")},
        )
        release.set()
        assert first.result(timeout=2).status_code == 422
        assert second.result(timeout=2).status_code == 422

    assert busy.status_code == 503
    assert busy.headers["retry-after"] == "2"
    assert busy.json()["detail"]["code"] == "processor_busy"
