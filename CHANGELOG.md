# Changelog

## Unreleased

- Rebalanced analysis around the research-backed features that directly drive emotion and form.
- Replaced quadratic landmark pairing with a bounded musical-window search.
- Reduced harmonic-separation memory with overlapped spectral chunks and magnitude-only outputs.
- Corrected misleading MP3 header durations using the decoded signal length.
- Reduced canonical analysis to the modeled 6 kHz spectrum and accelerated resampling.

## 0.1.0 - 2026-09-02

- Added deterministic audio decoding, validation, feature extraction, and MusicGenome analysis.
- Added traceable music-to-botanical mapping and a seeded concept-art flower renderer.
- Added CLI analysis and generation workflows with PNG and JSON outputs.
- Added a local FastAPI service and complete React browser experience.
- Added bounded processing, safe uploads, browser security headers, and operational guidance.
- Added golden determinism, artifact-integrity, API, renderer, and browser tests.
- Added a dependency-free demo song generator and unified production serving.
