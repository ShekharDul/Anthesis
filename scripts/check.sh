#!/usr/bin/env sh
set -eu

python -m ruff check backend/src backend/tests scripts/create_demo_audio.py
python -m mypy backend/src backend/tests
python -m pytest
npm run lint
npm run typecheck
npm run test
npm run build
