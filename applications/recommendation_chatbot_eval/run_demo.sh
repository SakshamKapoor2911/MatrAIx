#!/usr/bin/env bash
# Start RecBot Studio: serves the API + the built SPA at http://HOST:PORT
# (single origin). Ctrl-C to stop.
#
#   ./run_demo.sh                  # uses `python` on PATH (activate your venv first)
#   VENV=/path/to/venv ./run_demo.sh
#   HOST=0.0.0.0 PORT=8800 ./run_demo.sh
#
# See README.md for the full setup (venv, frontend build, resources, API key).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

# Optional: load local secrets (e.g. OPENAI_API_KEY) from .env.local if present.
if [[ -f .env.local ]]; then set -a; . ./.env.local; set +a; fi

# Python interpreter: $VENV/bin/python if VENV is set, else `python` on PATH
# (activate the project venv first — see RECAI_ENV_NOTES.md).
PY="${VENV:+$VENV/bin/}python"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"
export PYTHONPATH="${PYTHONPATH:-.}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

if [[ ! -d frontend/dist ]]; then
  echo "[run_demo] frontend/dist not found — build it first:" >&2
  echo "             (cd frontend && npm install && npm run build)" >&2
  exit 1
fi

echo "[run_demo] serving on http://${HOST}:${PORT}  (Ctrl-C to stop)"
exec "$PY" -m uvicorn backend.api.app:app --host "$HOST" --port "$PORT"
