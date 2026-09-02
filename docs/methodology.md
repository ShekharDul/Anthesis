# Methodology

Anthesis estimates expressive information communicated by an audio recording.
It does not claim to determine the private feeling of every listener.

## Measurement families

- Dynamics: loudness, dynamic range, accents, and trajectories
- Rhythm: tempo, onset density, pulse clarity, regularity, and syncopation
- Harmony: chroma, mode evidence, tonal stability, roughness, and tension
- Timbre: centroid, flux, flatness, and compact cepstral shape
- Tonal focus: harmonic peak concentration and key confidence
- Articulation: silence ratio, attack character, and duration proxies
- Texture: harmonic, percussive, and residual balance; density and sparsity
- Form: recurrence, novelty, boundaries, contrast, climax, and resolution
- Expectation: local uncertainty and event surprisal

## Canonical audio

Every recording first enters a versioned deterministic representation:

1. inspect and decode with libsndfile without invoking a shell;
2. downmix channels while retaining a stereo-width descriptor;
3. remove DC offset and resample to 16,000 Hz with medium-quality SoX analysis resampling;
4. trim leading and trailing silence relative to the recording's own peak;
5. center again and peak-normalize to 0.98;
6. hash quantized canonical PCM for exact-run provenance.

The current limits are 512 MiB and eight minutes. MP3, WAV, FLAC, OGG and
other formats exposed by the installed libsndfile build are accepted.

The canonical signal is then separated into harmonic and percussive components
with median-filter HPSS. This deterministic technique classifies horizontal
spectrogram structures as tonal and vertical structures as transient. Any
unassigned reconstruction remainder is retained explicitly. Separation and
feature extraction share one 2,048-sample STFT with a 1,024-sample hop instead
of transforming the same song repeatedly. At 16,000 Hz this retains a 64 ms
observation step and the complete modeled spectrum through 6 kHz before compact
aggregation.

## Compact musical features

The feature engine first works at that STFT rate and then robustly aggregates
measurements onto an approximately 2 Hz timeline. It retains:

- relative RMS and its trajectory for dynamics;
- onset strength, onset rate, tempo, pulse clarity and beat regularity;
- spectral centroid, flatness, flux and six compact MFCCs;
- harmonic spectral concentration as tonal confidence;
- normalized chroma, key/mode evidence, chroma entropy and harmonic change;
- harmonic, percussive and residual energy proportions;
- silence proportion and Sethares-style spectral roughness.

The same compact measurements are median-aggregated between detected beats.
An interval aggregation method accepts future structural boundaries without
coupling feature extraction to the next stage's segmentation algorithm.

Measurements are retained as time-varying curves before robust summary.

## Form and expressive trajectories

Song form is estimated from a cosine self-similarity matrix over robustly
standardized dynamics, timbre, harmony, and chroma features. A local novelty
curve compares the similarity inside adjacent windows with the similarity
across them. Prominent, sufficiently separated peaks become section
boundaries; median section signatures identify recurring passages.

The expressive layer uses fixed, documented weighted combinations rather than
a learned model:

- arousal combines energy, tempo, onset rate, flux, brightness, percussion,
  and pulse clarity;
- valence combines mode evidence, tonal strength, consonance, harmonic
  stability, brightness, and energy;
- tension combines roughness, harmonic change, chroma entropy, flux, onset
  activity, and residual texture;
- complexity, sublimity, vitality, and unease are derived from the same
  inspectable cues and detected formal complexity.

All curves are gently smoothed on the compact timeline and remain available
alongside their summaries. Valence and arousal receive separate confidence
curves. Tonal clarity, pitch confidence, harmonic balance, pulse clarity,
beat regularity, silence, and signal energy determine those confidences.
These values describe expression in the recording; they do not infer a
listener's private emotional state.

## Identity and uniqueness

Emotional measurements cannot provide identity: different songs can express
similar emotions. Anthesis therefore uses a separate, robust spectral-landmark
fingerprint to seed bounded micro-geometry. This makes visual collision
negligible in practice while preserving meaningful similarity at the level of
the overall flower.

The fingerprint retains up to twelve stable local maxima per second from a
log-magnitude spectrogram, pairs each peak only with candidates inside its
fixed musical time window, and hashes anchor frequency, target frequency, and
time difference. Four neighbors per anchor are sufficient for the similarity
signature without an all-to-all scan. The signature, duration, and exact
canonical PCM digest generate a 128-bit procedural seed. This keeps robust
recording similarity separate from the exact identity material that prevents
distinct canonical inputs from sharing a flower in practice.

## Validation

The project will test deterministic reruns, stability across common encodings,
feature behavior under controlled audio transformations, collision resistance,
and blind song–flower matching by human listeners.
