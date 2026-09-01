# Methodology

Anthesis estimates expressive information communicated by an audio recording.
It does not claim to determine the private feeling of every listener.

## Planned measurement families

- Dynamics: loudness, dynamic range, crest factor, accents, and trajectories
- Rhythm: tempo, onset density, pulse clarity, regularity, and syncopation
- Harmony: chroma, mode evidence, tonal stability, roughness, and tension
- Timbre: centroid, bandwidth, rolloff, flux, flatness, and cepstral shape
- Melody: predominant pitch, range, direction, contour, and interval behavior
- Articulation: silence ratio, attack character, and duration proxies
- Texture: harmonic, percussive, and residual balance; density and sparsity
- Form: recurrence, novelty, boundaries, contrast, climax, and resolution
- Expectation: local uncertainty and event surprisal

## Canonical audio

Every recording first enters a versioned deterministic representation:

1. inspect and decode with libsndfile without invoking a shell;
2. downmix channels while retaining a stereo-width descriptor;
3. remove DC offset and resample to 22,050 Hz with high-quality SoX resampling;
4. trim leading and trailing silence relative to the recording's own peak;
5. center again and peak-normalize to 0.98;
6. hash quantized canonical PCM for exact-run provenance.

The current limits are 512 MiB and fifteen minutes. MP3, WAV, FLAC, OGG and
other formats exposed by the installed libsndfile build are accepted.

The canonical signal is then separated into harmonic and percussive components
with median-filter HPSS. This deterministic technique classifies horizontal
spectrogram structures as tonal and vertical structures as transient. Any
unassigned reconstruction remainder is retained explicitly.

## Compact musical features

The feature engine first works at the STFT rate and then robustly aggregates
measurements onto an approximately 2 Hz timeline. It retains:

- relative RMS and crest factor for dynamics;
- onset strength, onset rate, tempo, pulse clarity and beat regularity;
- spectral centroid, bandwidth, rolloff, flatness, flux and thirteen MFCCs;
- predominant pitch and its spectral confidence;
- normalized chroma, key/mode evidence, chroma entropy and harmonic change;
- six tonal-centroid coordinates;
- harmonic, percussive and residual energy proportions;
- silence proportion and Sethares-style spectral roughness.

The same compact measurements are median-aggregated between detected beats.
An interval aggregation method accepts future structural boundaries without
coupling feature extraction to the next stage's segmentation algorithm.

Measurements are retained as time-varying curves before robust summary. The
initial expressive model will be transparent and manually specified. It will
combine multiple cues, attach confidence, and expose its limitations.

## Identity and uniqueness

Emotional measurements cannot provide identity: different songs can express
similar emotions. Anthesis therefore uses a separate, robust spectral-landmark
fingerprint to seed bounded micro-geometry. This makes visual collision
negligible in practice while preserving meaningful similarity at the level of
the overall flower.

## Validation

The project will test deterministic reruns, stability across common encodings,
feature behavior under controlled audio transformations, collision resistance,
and blind song–flower matching by human listeners.
