# Anthesis

> Turning the emotional mathematics of music into one-of-a-kind flowers.

Anthesis is a deterministic creative-coding project that analyzes a music file
with signal processing and music-information-retrieval techniques, then renders
its structure and expressive character as one concept-art flower.

Anthesis does not use generative AI. Its analysis and artwork are produced by
documented mathematics, procedural geometry, seeded algorithms, and raster
compositing.

## Project status

Anthesis 0.1.0 is complete. The deterministic analysis pipeline, MusicGenome,
botanical mapper, concept-art renderer, CLI, local API, browser workflow,
validation suite, demo, and release packaging are operational.

## Product principles

- One song produces one flower with one stem on a plain background.
- Identical canonical input in the same supported runtime produces identical output.
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

Build and run the complete local browser product:

```powershell
npm run build
.\.venv\Scripts\anthesis.exe serve
```

Open `http://127.0.0.1:8000`. Interactive API documentation is available at
`http://127.0.0.1:8000/docs`. See [CLI and local API](docs/interfaces.md) for
interface details.

For browser development with hot reload, run the API and `npm run dev` in
separate terminals. See [Browser experience](docs/web-experience.md).

To try Anthesis without finding an audio file first, see the
[deterministic demo](examples/README.md). For packaging instructions, see the
[release guide](docs/release.md).

See [Validation and operational boundaries](docs/validation.md) before exposing
the local API beyond your own machine.

## License

[MIT](LICENSE)
