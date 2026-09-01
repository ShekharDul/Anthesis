# Anthesis

> Turning the emotional mathematics of music into one-of-a-kind flowers.

Anthesis is a deterministic creative-coding project that analyzes a music file
with signal processing and music-information-retrieval techniques, then renders
its structure and expressive character as one concept-art flower.

Anthesis does not use generative AI. Its analysis and artwork are produced by
documented mathematics, procedural geometry, seeded algorithms, and raster
compositing.

## Project status

Anthesis is under active development. The initial repository foundation is in
place; the audio-analysis and rendering engines are being built incrementally.

## Product principles

- One song produces one flower with one stem on a plain background.
- Identical canonical input and analysis version produce identical output.
- Expressive similarity may create related flowers, while a separate acoustic
  identity channel preserves practical uniqueness.
- Every visual decision must be traceable to measured musical information.
- Audio processing remains local by default.
- Limitations and confidence are reported instead of hidden.

## Repository layout

```text
backend/        Python analysis engine, renderer, API, and CLI
frontend/       React and TypeScript web interface
docs/           Architecture, methodology, and project decisions
scripts/        Cross-platform development helpers
```

## Development prerequisites

- Python 3.11–3.13
- Node.js 22 or newer
- npm 10 or newer
- FFmpeg available on `PATH` for broad audio-format support

Development commands and installation instructions will be expanded as the
first executable pipeline lands.

## License

[MIT](LICENSE)
