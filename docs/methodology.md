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
