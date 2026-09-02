$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param([scriptblock]$Command)

    & $Command
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Invoke-Checked { python -m ruff check backend/src backend/tests scripts/create_demo_audio.py }
Invoke-Checked { python -m mypy backend/src backend/tests }
Invoke-Checked { python -m pytest }
Invoke-Checked { npm run lint }
Invoke-Checked { npm run typecheck }
Invoke-Checked { npm run test }
Invoke-Checked { npm run build }
