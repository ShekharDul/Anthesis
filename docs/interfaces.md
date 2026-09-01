# CLI and local API

Both interfaces call the same `anthesis.processing` orchestration layer. The
pipeline decodes audio, separates components, extracts features, analyzes
structure and expression, builds the MusicGenome, maps botanical traits, and
optionally renders the PNG.

## Command line

After installing the project in its virtual environment:

```powershell
anthesis analyze .\song.wav --output .\song.anthesis.json
anthesis generate .\song.wav --output .\flower.png --analysis .\flower.json
anthesis serve --host 127.0.0.1 --port 8000
```

`generate` defaults to a 900 × 1200 PNG with 2× supersampling. Width and height
may be set between 256 and 2048; supersampling may be set from 1 through 3.
Combinations producing a working canvas over 20 million pixels are rejected.
Image and JSON writes are atomic so interrupted writes do not leave partial
deliverables.

## HTTP API

The versioned local endpoints are:

- `GET /api/v1/health`
- `POST /api/v1/analyze`
- `POST /api/v1/generate?width=900&height=1200&supersampling=2`

Both POST endpoints accept one multipart field named `audio`. `analyze` returns
the MusicGenome and flower blueprint. `generate` additionally returns a
generation manifest and a base64-encoded PNG. Interactive documentation is at
`/docs` while the server is running.

Web uploads are streamed in 1 MiB chunks into a unique temporary directory,
limited to 100 MiB, and deleted after success or failure. The decoded audio
duration and signal checks still apply. Expected audio failures return a safe
structured error without a traceback or local path disclosure.
