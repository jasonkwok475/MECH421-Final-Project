#!/usr/bin/env bash
# Starts backend + frontend on macOS/Linux. Usage: ./scripts/dev.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/software/backend"
[ -d .venv ] || { python3 -m venv .venv; .venv/bin/pip install -r requirements-dev.txt; }
.venv/bin/uvicorn app.main:app --reload --port 8000 &
BACK=$!
cd "$ROOT/software/frontend"
[ -d node_modules ] || npm install
trap "kill $BACK" EXIT
npm run dev
