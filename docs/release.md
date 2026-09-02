# Release guide

## Verify

Run the complete backend and frontend suite:

```powershell
.\scripts\check.ps1
```

## Build and run the local product

```powershell
npm run build
.\.venv\Scripts\anthesis.exe serve
```

Open `http://127.0.0.1:8000`. The API remains available under `/api/v1` and its
interactive documentation under `/docs`.

## Build the Python distribution

```powershell
.\.venv\Scripts\python.exe -m pip wheel --no-deps --wheel-dir artifacts/release .
```

The Python wheel contains the engine, renderer, API, and CLI. The source release
also serves the built browser app from `frontend/dist`; run `npm run build`
before `anthesis serve`. Release archives should include both the source tree and
the built frontend.

## Release contract

- Version: `0.1.0`
- Python: 3.11–3.13
- Node.js: 22+
- Local bind address: `127.0.0.1`
- Generated files: excluded from version control under `artifacts/`
