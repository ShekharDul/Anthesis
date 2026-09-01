# Anthesis

> Turning the emotional mathematics of music into one-of-a-kind flowers.

Anthesis is a deterministic creative-coding project that analyzes a music file
with signal processing and music-information-retrieval techniques, then renders
its structure and expressive character as one concept-art flower.

Anthesis does not use generative AI. Its analysis and artwork are produced by
documented mathematics, procedural geometry, seeded algorithms, and raster
compositing.

## Project status

The deterministic analysis pipeline, MusicGenome, botanical mapper, concept-art
renderer, CLI, local API, and browser workflow are operational. Final hardening
and release validation are under active development.

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

Create a virtual environment and install the backend and frontend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
npm install
```

Run all local checks from an activated virtual environment with
`scripts/check.ps1` on Windows or `scripts/check.sh` on macOS and Linux.

Generate a flower and its inspectable analysis:

```powershell
.\.venv\Scripts\anthesis.exe generate .\song.wav --output .\flower.png
```

Run the local API and open its interactive documentation at
`http://127.0.0.1:8000/docs`:

```powershell
.\.venv\Scripts\anthesis.exe serve
```

See [CLI and local API](docs/interfaces.md) for interface details.

For the browser workflow, run the API as above and start Vite in a second
terminal with `npm run dev`. See [Browser experience](docs/web-experience.md).

## License

[MIT](LICENSE)
