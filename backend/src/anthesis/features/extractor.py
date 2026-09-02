"""End-to-end extraction of interpretable musical measurements."""

from __future__ import annotations

from typing import Final

import librosa
import numpy as np
from numpy.typing import NDArray

from anthesis.audio import AudioComponents, CanonicalAudio, separate_harmonic_percussive
from anthesis.features.aggregation import aggregate_at_beats, aggregate_columns, aggregate_times
from anthesis.features.config import FeatureConfig
from anthesis.features.models import FeatureTable, MusicalFeatures
from anthesis.features.roughness import spectral_roughness
from anthesis.features.tonality import chroma_entropy, estimate_tonality, harmonic_change

_EPSILON: Final[float] = float(np.finfo(np.float32).eps)


def _align_frames(values: NDArray[np.float32], frame_count: int) -> NDArray[np.float32]:
    """Trim or edge-pad feature rows to the shared STFT frame count."""

    if values.shape[1] == frame_count:
        return values
    if values.shape[1] > frame_count:
        return values[:, :frame_count]
    if values.shape[1] == 0:
        return np.zeros((values.shape[0], frame_count), dtype=np.float32)
    return np.pad(values, ((0, 0), (0, frame_count - values.shape[1])), mode="edge")


def _frame_peaks(
    samples: NDArray[np.float32],
    *,
    n_fft: int,
    hop_length: int,
    frame_count: int,
) -> NDArray[np.float32]:
    padded = np.pad(samples, n_fft // 2, mode="constant")
    framed = librosa.util.frame(padded, frame_length=n_fft, hop_length=hop_length)
    peaks = np.max(np.abs(framed), axis=0, keepdims=True).astype(np.float32)
    return _align_frames(peaks, frame_count)


def _spectral_flux(magnitude: NDArray[np.float32]) -> NDArray[np.float32]:
    normalized = magnitude / np.maximum(np.sum(magnitude, axis=0, keepdims=True), _EPSILON)
    positive_difference = np.maximum(np.diff(normalized, axis=1), 0.0)
    flux = np.sqrt(np.sum(np.square(positive_difference), axis=0))
    return np.asarray(np.concatenate(([0.0], flux))[None, :], dtype=np.float32)


def _predominant_pitch(
    harmonic_magnitude: NDArray[np.float32],
    *,
    sample_rate: int,
    n_fft: int,
    hop_length: int,
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    pitches, magnitudes = librosa.piptrack(
        S=harmonic_magnitude,
        sr=sample_rate,
        n_fft=n_fft,
        hop_length=hop_length,
        fmin=40.0,
        fmax=min(5_000.0, sample_rate * 0.45),
        threshold=0.1,
    )
    strongest = np.argmax(magnitudes, axis=0)
    indices = np.arange(magnitudes.shape[1])
    peak_magnitude = magnitudes[strongest, indices]
    pitch = pitches[strongest, indices]
    pitch = np.where(peak_magnitude > _EPSILON, pitch, 0.0)
    confidence = peak_magnitude / np.maximum(np.sum(magnitudes, axis=0), _EPSILON)
    return (
        np.asarray(pitch[None, :], dtype=np.float32),
        np.asarray(confidence[None, :], dtype=np.float32),
    )


def _component_ratios(
    components: AudioComponents,
    *,
    n_fft: int,
    hop_length: int,
    frame_count: int,
) -> NDArray[np.float32]:
    component_rms = []
    for samples in (components.harmonic, components.percussive, components.residual):
        rms = librosa.feature.rms(
            y=samples,
            frame_length=n_fft,
            hop_length=hop_length,
            center=True,
        ).astype(np.float32)
        component_rms.append(_align_frames(rms, frame_count))
    energies = np.square(np.concatenate(component_rms, axis=0))
    ratios = energies / np.maximum(np.sum(energies, axis=0, keepdims=True), _EPSILON)
    return np.asarray(ratios, dtype=np.float32)


def _pulse_clarity(
    onset_envelope: NDArray[np.float32], sample_rate: int, hop_length: int
) -> float:
    win_length = min(384, max(8, onset_envelope.size))
    tempogram = librosa.feature.tempogram(
        onset_envelope=onset_envelope,
        sr=sample_rate,
        hop_length=hop_length,
        win_length=win_length,
        center=True,
    )
    if tempogram.shape[0] < 2:
        return 0.0
    normalized = tempogram[1:] / np.maximum(tempogram[:1], _EPSILON)
    return float(np.clip(np.median(np.max(normalized, axis=0)), 0.0, 1.0))


def _beat_regularity(beat_times: NDArray[np.float32]) -> float:
    intervals = np.diff(beat_times.astype(np.float64))
    if intervals.size < 2 or float(np.mean(intervals)) <= 0:
        return 0.0
    coefficient_of_variation = float(np.std(intervals) / np.mean(intervals))
    return float(np.clip(1.0 - coefficient_of_variation, 0.0, 1.0))


def _tempo_and_beats(
    onset_envelope: NDArray[np.float32], sample_rate: int, hop_length: int
) -> tuple[float, NDArray[np.float32]]:
    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_envelope,
        sr=sample_rate,
        hop_length=hop_length,
        units="frames",
        trim=False,
    )
    tempo_values = np.asarray(tempo).reshape(-1)
    tempo_bpm = float(tempo_values[0]) if tempo_values.size else 0.0
    times = librosa.frames_to_time(beat_frames, sr=sample_rate, hop_length=hop_length)
    return tempo_bpm, np.asarray(times, dtype=np.float32)


def extract_musical_features(
    audio: CanonicalAudio,
    components: AudioComponents | None = None,
    config: FeatureConfig | None = None,
) -> MusicalFeatures:
    """Extract compact frame-, beat-, and recording-level musical features."""

    settings = config or FeatureConfig()
    separated = components or separate_harmonic_percussive(audio)
    sample_rate = audio.sample_rate

    can_reuse_spectra = (
        separated.n_fft == settings.n_fft
        and separated.hop_length == settings.hop_length
        and separated.win_length == settings.n_fft
    )
    if can_reuse_spectra:
        spectrum = separated.spectrum
        harmonic_spectrum = separated.harmonic_spectrum
        percussive_spectrum = separated.percussive_spectrum
    else:
        spectrum = librosa.stft(
            audio.samples,
            n_fft=settings.n_fft,
            hop_length=settings.hop_length,
            win_length=settings.n_fft,
            window="hann",
            center=True,
            pad_mode="constant",
        )
        harmonic_spectrum = librosa.stft(
            separated.harmonic,
            n_fft=settings.n_fft,
            hop_length=settings.hop_length,
            win_length=settings.n_fft,
            window="hann",
            center=True,
            pad_mode="constant",
        )
        percussive_spectrum = librosa.stft(
            separated.percussive,
            n_fft=settings.n_fft,
            hop_length=settings.hop_length,
            win_length=settings.n_fft,
            window="hann",
            center=True,
            pad_mode="constant",
        )
    magnitude = np.asarray(np.abs(spectrum), dtype=np.float32)
    harmonic_magnitude = np.asarray(np.abs(harmonic_spectrum), dtype=np.float32)
    percussive_magnitude = np.asarray(np.abs(percussive_spectrum), dtype=np.float32)
    frame_count = magnitude.shape[1]

    rms = librosa.feature.rms(S=magnitude, frame_length=settings.n_fft).astype(np.float32)
    rms_db = librosa.amplitude_to_db(rms, ref=np.max, top_db=100).astype(np.float32)
    crest = _frame_peaks(
        audio.samples,
        n_fft=settings.n_fft,
        hop_length=settings.hop_length,
        frame_count=frame_count,
    ) / np.maximum(rms, _EPSILON)
    centroid = librosa.feature.spectral_centroid(S=magnitude, sr=sample_rate).astype(np.float32)
    bandwidth = librosa.feature.spectral_bandwidth(S=magnitude, sr=sample_rate).astype(np.float32)
    rolloff = librosa.feature.spectral_rolloff(
        S=magnitude, sr=sample_rate, roll_percent=settings.rolloff_percent
    ).astype(np.float32)
    flatness = librosa.feature.spectral_flatness(S=magnitude).astype(np.float32)
    flux = _spectral_flux(magnitude)
    onset_envelope = librosa.onset.onset_strength(
        S=librosa.amplitude_to_db(percussive_magnitude, ref=np.max),
        sr=sample_rate,
        hop_length=settings.hop_length,
        center=True,
    ).astype(np.float32)
    onset_envelope = _align_frames(onset_envelope[None, :], frame_count)[0]
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_envelope,
        sr=sample_rate,
        hop_length=settings.hop_length,
        units="frames",
        backtrack=False,
        normalize=True,
    )
    onset_indicator = np.zeros((1, frame_count), dtype=np.float32)
    onset_indicator[0, onset_frames[onset_frames < frame_count]] = 1.0

    pitch, pitch_confidence = _predominant_pitch(
        harmonic_magnitude,
        sample_rate=sample_rate,
        n_fft=settings.n_fft,
        hop_length=settings.hop_length,
    )
    chroma = librosa.feature.chroma_stft(
        S=np.square(harmonic_magnitude),
        sr=sample_rate,
        n_fft=settings.n_fft,
        hop_length=settings.hop_length,
        norm=1,
    ).astype(np.float32)
    mel_power = librosa.feature.melspectrogram(
        S=np.square(magnitude),
        sr=sample_rate,
        n_mels=settings.n_mels,
    )
    mfcc = librosa.feature.mfcc(
        S=librosa.power_to_db(mel_power, ref=np.max),
        n_mfcc=settings.n_mfcc,
    ).astype(np.float32)
    component_ratios = _component_ratios(
        separated,
        n_fft=settings.n_fft,
        hop_length=settings.hop_length,
        frame_count=frame_count,
    )
    silence = (rms_db <= settings.silence_db).astype(np.float32)

    frame_rate = sample_rate / settings.hop_length
    block_size = max(1, round(frame_rate / settings.output_rate_hz))
    high_rate_times = librosa.frames_to_time(
        np.arange(frame_count), sr=sample_rate, hop_length=settings.hop_length
    )
    compact_times = aggregate_times(np.asarray(high_rate_times, dtype=np.float64), block_size)

    continuous = np.asarray(
        np.concatenate(
            (
                rms_db,
                crest,
                centroid,
                bandwidth,
                rolloff,
                flatness,
                flux,
                pitch,
                pitch_confidence,
                component_ratios,
            ),
            axis=0,
        ),
        dtype=np.float32,
    )
    compact_continuous = aggregate_columns(continuous, block_size, reducer="median")
    compact_onset_strength = aggregate_columns(onset_envelope[None, :], block_size, reducer="max")
    compact_onset_rate = aggregate_columns(onset_indicator, block_size, reducer="mean")
    compact_onset_rate *= frame_rate
    compact_silence = aggregate_columns(silence, block_size, reducer="mean")
    compact_mfcc = aggregate_columns(mfcc, block_size, reducer="median")
    compact_chroma_rows = aggregate_columns(chroma, block_size, reducer="mean")
    compact_chroma = np.asarray(compact_chroma_rows.T, dtype=np.float32)
    compact_chroma /= np.maximum(np.sum(compact_chroma, axis=0, keepdims=True), _EPSILON)
    tonnetz = librosa.feature.tonnetz(chroma=compact_chroma).astype(np.float32)
    entropy = chroma_entropy(compact_chroma)[None, :]
    change = harmonic_change(compact_chroma)[None, :]

    compact_spectra = aggregate_columns(magnitude, block_size, reducer="mean")
    frequencies = librosa.fft_frequencies(sr=sample_rate, n_fft=settings.n_fft)
    roughness = spectral_roughness(
        compact_spectra,
        np.asarray(frequencies, dtype=np.float64),
        peak_count=settings.roughness_peak_count,
        min_hz=settings.roughness_min_hz,
        max_hz=settings.roughness_max_hz,
    )[:, None]

    columns = (
        "rms_db",
        "crest_factor",
        "spectral_centroid_hz",
        "spectral_bandwidth_hz",
        "spectral_rolloff_hz",
        "spectral_flatness",
        "spectral_flux",
        "predominant_pitch_hz",
        "pitch_confidence",
        "harmonic_ratio",
        "percussive_ratio",
        "residual_ratio",
        "onset_strength",
        "onset_rate_hz",
        "silence_ratio",
        *(f"mfcc_{index + 1:02d}" for index in range(settings.n_mfcc)),
        *(f"chroma_{pitch_class:02d}" for pitch_class in range(12)),
        *(f"tonnetz_{dimension + 1:02d}" for dimension in range(6)),
        "chroma_entropy",
        "harmonic_change",
        "spectral_roughness",
    )
    units = (
        "dB",
        "ratio",
        "Hz",
        "Hz",
        "Hz",
        "ratio",
        "distance",
        "Hz",
        "ratio",
        "ratio",
        "ratio",
        "ratio",
        "strength",
        "events/s",
        "ratio",
        *("coefficient" for _ in range(settings.n_mfcc)),
        *("probability" for _ in range(12)),
        *("coordinate" for _ in range(6)),
        "normalized bits",
        "cosine distance",
        "roughness",
    )
    values = np.concatenate(
        (
            compact_continuous,
            compact_onset_strength,
            compact_onset_rate,
            compact_silence,
            compact_mfcc,
            compact_chroma_rows,
            tonnetz.T,
            entropy.T,
            change.T,
            roughness,
        ),
        axis=1,
    ).astype(np.float32)
    frames = FeatureTable(times=compact_times, values=values, columns=columns, units=units)

    tempo_bpm, beat_times = _tempo_and_beats(onset_envelope, sample_rate, settings.hop_length)
    beat_times = beat_times[beat_times <= frames.times[-1] + 1e-6]
    beat_table_times, beat_values = aggregate_at_beats(frames.times, frames.values, beat_times)
    beats = FeatureTable(
        times=beat_table_times,
        values=beat_values,
        columns=columns,
        units=units,
    )

    tonality = estimate_tonality(compact_chroma)
    global_values: dict[str, float] = {
        "duration_seconds": audio.duration_seconds,
        "tempo_bpm": tempo_bpm,
        "beat_count": float(beat_times.size),
        "beat_regularity": _beat_regularity(beat_times),
        "pulse_clarity": _pulse_clarity(onset_envelope, sample_rate, settings.hop_length),
        "key_strength": tonality.strength,
        "mode_evidence": tonality.mode_evidence,
        "major_strength": tonality.major_strength,
        "minor_strength": tonality.minor_strength,
        "stereo_width": audio.stereo_width,
    }
    for index, name in enumerate(columns):
        global_values[f"mean_{name}"] = float(np.mean(values[:, index]))
        global_values[f"std_{name}"] = float(np.std(values[:, index]))

    return MusicalFeatures(
        frames=frames,
        beats=beats,
        globals=global_values,
        labels={"key": tonality.key, "mode": tonality.mode},
    )
