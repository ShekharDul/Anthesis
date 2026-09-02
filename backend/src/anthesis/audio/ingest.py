"""Load arbitrary supported recordings into Anthesis canonical audio."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf  # type: ignore[import-untyped]
from numpy.typing import NDArray

from anthesis.audio.config import AudioPreprocessConfig
from anthesis.audio.errors import (
    AudioDecodeError,
    AudioLimitError,
    AudioNotFoundError,
    AudioTooShortError,
    SilentAudioError,
)

CANONICAL_AUDIO_VERSION = "anthesis-audio-v2"


@dataclass(frozen=True, slots=True)
class SourceAudioInfo:
    """Metadata recorded before Anthesis modifies the waveform."""

    path: str
    format: str
    subtype: str
    sample_rate: int
    channels: int
    frames: int
    duration_seconds: float
    file_size_bytes: int


@dataclass(frozen=True, slots=True)
class CanonicalAudio:
    """Normalized, trimmed, mono audio consumed by every later stage."""

    samples: NDArray[np.float32]
    sample_rate: int
    source: SourceAudioInfo
    trim_start_seconds: float
    trim_end_seconds: float
    normalization_gain: float
    stereo_width: float
    digest: str
    version: str = CANONICAL_AUDIO_VERSION

    @property
    def duration_seconds(self) -> float:
        return self.samples.size / self.sample_rate


def _source_info(path: Path, config: AudioPreprocessConfig) -> SourceAudioInfo:
    if not path.is_file():
        raise AudioNotFoundError(f"Audio file does not exist: {path}")

    file_size = path.stat().st_size
    if file_size > config.max_file_size_bytes:
        raise AudioLimitError(
            f"Audio file is {file_size} bytes; limit is {config.max_file_size_bytes} bytes"
        )

    try:
        info = sf.info(path)
    except (RuntimeError, TypeError, ValueError) as exc:
        raise AudioDecodeError(f"Could not inspect audio file: {path}") from exc

    if info.channels < 1 or info.samplerate < 1 or info.frames < 1:
        raise AudioDecodeError("Audio metadata contains no decodable signal")

    return SourceAudioInfo(
        path=str(path.resolve()),
        format=info.format,
        subtype=info.subtype,
        sample_rate=info.samplerate,
        channels=info.channels,
        frames=info.frames,
        duration_seconds=info.frames / info.samplerate,
        file_size_bytes=file_size,
    )


def _decode(path: Path) -> NDArray[np.float32]:
    try:
        samples, _ = sf.read(path, dtype="float32", always_2d=True)
    except (RuntimeError, TypeError, ValueError) as exc:
        raise AudioDecodeError(f"Could not decode audio file: {path}") from exc

    waveform = np.asarray(samples, dtype=np.float32)
    if waveform.ndim != 2 or waveform.shape[0] == 0 or waveform.shape[1] == 0:
        raise AudioDecodeError("Decoded audio has an invalid shape")
    if not np.isfinite(waveform).all():
        raise AudioDecodeError("Decoded audio contains non-finite samples")
    return waveform


def _measure_stereo_width(waveform: NDArray[np.float32]) -> float:
    if waveform.shape[1] < 2:
        return 0.0
    left = waveform[:, 0].astype(np.float64)
    right = waveform[:, 1].astype(np.float64)
    mid_rms = float(np.sqrt(np.mean(np.square((left + right) * 0.5))))
    side_rms = float(np.sqrt(np.mean(np.square((left - right) * 0.5))))
    return float(np.clip(side_rms / (mid_rms + side_rms + np.finfo(float).eps), 0.0, 1.0))


def _canonical_digest(samples: NDArray[np.float32], sample_rate: int) -> str:
    quantized = np.rint(np.clip(samples, -1.0, 1.0) * 32_767).astype("<i2", copy=False)
    digest = hashlib.sha256()
    digest.update(CANONICAL_AUDIO_VERSION.encode("ascii"))
    digest.update(sample_rate.to_bytes(4, "little", signed=False))
    digest.update(quantized.tobytes(order="C"))
    return digest.hexdigest()


def load_audio(
    audio_path: str | Path,
    config: AudioPreprocessConfig | None = None,
) -> CanonicalAudio:
    """Decode and canonicalize an audio file deterministically.

    The canonical signal is mono, DC-centered, resampled, silence-trimmed,
    peak-normalized, contiguous, float32, and read-only.
    """

    settings = config or AudioPreprocessConfig()
    path = Path(audio_path).expanduser()
    source = _source_info(path, settings)
    decoded = _decode(path)
    decoded_duration = decoded.shape[0] / source.sample_rate
    if decoded_duration > settings.max_duration_seconds:
        raise AudioLimitError(
            f"Audio duration is {decoded_duration:.2f}s; "
            f"limit is {settings.max_duration_seconds:.2f}s"
        )
    source = replace(
        source,
        frames=decoded.shape[0],
        duration_seconds=decoded_duration,
    )
    stereo_width = _measure_stereo_width(decoded)

    mono = np.mean(decoded, axis=1, dtype=np.float64)
    if float(np.max(np.abs(mono))) <= settings.silence_epsilon:
        raise SilentAudioError("Audio contains no usable signal")

    if source.sample_rate != settings.target_sample_rate:
        mono = librosa.resample(
            mono,
            orig_sr=source.sample_rate,
            target_sr=settings.target_sample_rate,
            res_type=settings.resample_type,
            fix=True,
            scale=False,
        )

    trimmed, trim_indices = librosa.effects.trim(
        mono,
        top_db=settings.trim_top_db,
        ref=np.max,
        frame_length=settings.trim_frame_length,
        hop_length=settings.trim_hop_length,
    )
    trimmed = np.asarray(trimmed, dtype=np.float64)
    duration = trimmed.size / settings.target_sample_rate
    if duration < settings.min_duration_seconds:
        raise AudioTooShortError(
            f"Usable audio duration is {duration:.2f}s; minimum is "
            f"{settings.min_duration_seconds:.2f}s"
        )

    # Center only the retained signal. Centering before trimming would turn
    # digital silence into a non-zero plateau when the music has DC offset.
    trimmed -= float(np.mean(trimmed))
    peak = float(np.max(np.abs(trimmed)))
    if peak <= settings.silence_epsilon:
        raise SilentAudioError("Audio became silent after canonicalization")
    gain = settings.peak_target / peak
    canonical = np.ascontiguousarray(trimmed * gain, dtype=np.float32)
    canonical.setflags(write=False)

    trim_start = float(trim_indices[0] / settings.target_sample_rate)
    trim_end = float((mono.size - trim_indices[1]) / settings.target_sample_rate)
    return CanonicalAudio(
        samples=canonical,
        sample_rate=settings.target_sample_rate,
        source=source,
        trim_start_seconds=trim_start,
        trim_end_seconds=trim_end,
        normalization_gain=gain,
        stereo_width=stereo_width,
        digest=_canonical_digest(canonical, settings.target_sample_rate),
    )
