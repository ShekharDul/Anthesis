$ErrorActionPreference = "Stop"

python -m ruff check backend/src backend/tests
python -m mypy backend/src backend/tests
python -m pytest
npm run lint
npm run typecheck
npm run test
npm run build
