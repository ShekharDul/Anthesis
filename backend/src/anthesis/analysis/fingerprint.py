"""Robust spectral-landmark identity for canonical recordings."""

from __future__ import annotations

import hashlib
import struct

import librosa
import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import maximum_filter  # type: ignore[import-untyped]

from anthesis.analysis.config import FingerprintConfig
from anthesis.analysis.models import AcousticFingerprint, Landmark
from anthesis.audio import CanonicalAudio


def _spectral_peaks(
    audio: CanonicalAudio,
    config: FingerprintConfig,
    magnitude: NDArray[np.float32] | None = None,
) -> NDArray[np.float64]:
    if magnitude is None:
        magnitude = np.asarray(
            np.abs(
                librosa.stft(
                    audio.samples,
                    n_fft=config.n_fft,
                    hop_length=config.hop_length,
                    window="hann",
                    center=True,
                    pad_mode="constant",
                )
            ),
            dtype=np.float32,
        )
    decibels = librosa.amplitude_to_db(magnitude, ref=np.max, top_db=80.0)
    neighborhood = maximum_filter(
        decibels,
        size=(config.peak_neighborhood_frequency, config.peak_neighborhood_time),
        mode="nearest",
    )
    coordinates = np.argwhere((decibels == neighborhood) & (decibels >= config.minimum_peak_db))
    if coordinates.size == 0:
        return np.empty((0, 3), dtype=np.float64)

    candidates = np.column_stack(
        (coordinates[:, 1], coordinates[:, 0], decibels[coordinates[:, 0], coordinates[:, 1]])
    ).astype(np.float64)
    frames_per_second = audio.sample_rate / config.hop_length
    selected: list[NDArray[np.float64]] = []
    second_buckets = np.floor(candidates[:, 0] / frames_per_second).astype(np.int64)
    for bucket in np.unique(second_buckets):
        bucket_rows = candidates[second_buckets == bucket]
        strongest = np.argsort(bucket_rows[:, 2])[-config.peaks_per_second :]
        selected.extend(bucket_rows[strongest])
    return np.asarray(sorted(selected, key=lambda row: (row[0], row[1])), dtype=np.float64)


def _pair_hash(anchor_bin: int, target_bin: int, delta_frames: int) -> int:
    payload = struct.pack("<III", anchor_bin, target_bin, delta_frames)
    return int.from_bytes(hashlib.blake2s(payload, digest_size=4).digest(), "little")


def _landmarks(
    peaks: NDArray[np.float64],
    audio: CanonicalAudio,
    config: FingerprintConfig,
) -> tuple[Landmark, ...]:
    minimum_delta = max(
        1, round(config.minimum_pair_seconds * audio.sample_rate / config.hop_length)
    )
    maximum_delta = max(
        minimum_delta,
        round(config.maximum_pair_seconds * audio.sample_rate / config.hop_length),
    )
    result: list[Landmark] = []
    peak_frames = peaks[:, 0]
    for anchor_index, anchor in enumerate(peaks):
        first = max(
            anchor_index + 1,
            int(np.searchsorted(peak_frames, anchor[0] + minimum_delta, side="left")),
        )
        last = int(np.searchsorted(peak_frames, anchor[0] + maximum_delta, side="right"))
        if first >= last:
            continue
        candidates = peaks[first:last]
        order = np.lexsort((-candidates[:, 2], candidates[:, 0]))[: config.fanout]
        for target in candidates[order]:
            anchor_frame = int(anchor[0])
            target_delta = int(target[0]) - anchor_frame
            anchor_bin = int(anchor[1])
            target_bin = int(target[1])
            result.append(
                Landmark(
                    time_frame=anchor_frame,
                    hash32=_pair_hash(anchor_bin, target_bin, target_delta),
                    anchor_bin=anchor_bin,
                    target_bin=target_bin,
                    delta_frames=target_delta,
                )
            )
    return tuple(sorted(result))


def fingerprint_audio(
    audio: CanonicalAudio,
    config: FingerprintConfig | None = None,
    *,
    magnitude: NDArray[np.float32] | None = None,
) -> AcousticFingerprint:
    """Create a repeatable constellation fingerprint and flower seed."""

    settings = config or FingerprintConfig()
    landmarks = _landmarks(_spectral_peaks(audio, settings, magnitude), audio, settings)
    signature = tuple(
        sorted({landmark.hash32 for landmark in landmarks})[: settings.signature_size]
    )
    seed = hashlib.blake2b(digest_size=16, person=b"anthesis-seed")
    seed.update(struct.pack("<I", round(audio.duration_seconds * 10.0)))
    for hash32 in signature:
        seed.update(hash32.to_bytes(4, "little", signed=False))
    # Robust landmarks relate alternate recordings; exact canonical identity
    # prevents distinct inputs with similar landmarks from sharing a flower.
    seed.update(bytes.fromhex(audio.digest))
    return AcousticFingerprint(
        landmarks=landmarks,
        signature=signature,
        seed_hex=seed.hexdigest(),
        exact_audio_digest=audio.digest,
        duration_seconds=audio.duration_seconds,
    )
