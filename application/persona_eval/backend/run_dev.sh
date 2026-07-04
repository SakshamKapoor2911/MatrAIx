#!/usr/bin/env bash
#
# run_dev.sh — start the PersonaEval backend (FastAPI + uvicorn) for local dev.
#
# This launches the API only. The Vite dev server for the React SPA is run
# separately (see the note at the bottom), and proxies `/api` to this process.
#
# What it does:
#   - Resolves the backend root and the eval package root regardless of the
#     directory you call it from.
#   - Puts the repo root, `environment/runtime`, `application/persona_eval`,
#     and the chatbot task API source on PYTHONPATH so that `import
#     environment...`, `import harbor...`, `import backend...`, and
#     `import recbot...` resolve
#     in-process. The service layer also injects the chatbot API path at startup,
#     but exporting it here keeps the env explicit.
#   - Runs a SINGLE uvicorn worker (the cached RecAI agent and the in-memory job
#     registry assume one process). `--reload` is opt-in via RELOAD=1 because a
#     reload spawns a child process and breaks the in-process agent cache.
#
# Usage:
#   bash application/persona_eval/backend/run_dev.sh
#   PORT=8765 RELOAD=1 bash .../backend/run_dev.sh
#
# Requirements: deps from requirements.txt installed in the canonical project
# .venv (the uv-managed Python 3.9 env — see ../README.md). This script
# execs uvicorn from that interpreter so the lazy `run_turn` import resolves.
# For REAL recommendations you also need OPENAI_API_KEY and the catalog — see
# README.md. The server boots and serves /api/health, /api/preflight and the
# catalog even without those, surfacing what is missing via /api/preflight.

set -euo pipefail

# --- resolve paths -----------------------------------------------------------
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(cd "${BACKEND_DIR}/.." && pwd)"  # application/persona_eval
REPO_ROOT="$(cd "${EVAL_DIR}/../.." && pwd)"
PERSONA_EVAL_CORE_DIR="${REPO_ROOT}/packages/persona-eval/src"
CHATBOT_API_DIR="${REPO_ROOT}/environment/task-environments/application/shared-chat-api-recommender/recommender-api"

# --- interpreter: $VENV/bin/python if VENV is set, else `python` on PATH -------
# (Python 3.9 + RecAI native — see ../README.md. Activate your venv, or
# pass VENV=/path/to/venv.)
VENV_PY="${VENV:+${VENV}/bin/}python"
if ! command -v "${VENV_PY}" >/dev/null 2>&1; then
  echo "[run_dev] ERROR: python interpreter '${VENV_PY}' not found." >&2
  echo "[run_dev]        activate your venv, or set VENV=/path/to/venv (see application/persona_eval/README.md)." >&2
  exit 1
fi

# --- load local secrets/env (gitignored) -------------------------------------
# Put OPENAI_API_KEY (and, to stay in the scripted demo, RECBOT_STUDIO_DEMO=1)
# in .env.local next to run_demo.sh (copy it from .env.local.example). It is
# gitignored and auto-loaded here so secrets never live on the command line.
ENV_LOCAL="${EVAL_DIR}/.env.local"
if [[ -f "${ENV_LOCAL}" ]]; then
  echo "[run_dev] loading ${ENV_LOCAL}"
  set -a; source "${ENV_LOCAL}"; set +a
fi

# --- config (overridable via env) --------------------------------------------
PORT="${PORT:-8765}"
HOST="${HOST:-127.0.0.1}"
APP="backend.api.app:app"

# Make `backend`, `persona_eval`, and task-owned `recbot` importable.
export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/environment/runtime:${PERSONA_EVAL_CORE_DIR}:${EVAL_DIR}:${CHATBOT_API_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

# The catalog is served from the real per-domain bundle under
# recai/InteRecAgent/resources/<domain>/ (see backend.service.bundle_catalog).
# Set INTERECAGENT_CATALOG_PATH only to pin a specific JSONL catalog instead.

RELOAD_FLAG=""
if [[ "${RELOAD:-0}" == "1" ]]; then
  RELOAD_FLAG="--reload"
  echo "[run_dev] WARNING: --reload uses a worker subprocess; the in-process" >&2
  echo "[run_dev]          RecAI agent cache will cold-start on every change." >&2
fi

echo "[run_dev] python      : ${VENV_PY}"
echo "[run_dev] backend dir : ${BACKEND_DIR}"
echo "[run_dev] PYTHONPATH  : ${REPO_ROOT}:${REPO_ROOT}/environment/runtime:${PERSONA_EVAL_CORE_DIR}:${EVAL_DIR}:${CHATBOT_API_DIR}"
echo "[run_dev] catalog     : ${INTERECAGENT_CATALOG_PATH:-(bundle default)}"
echo "[run_dev] serving     : http://${HOST}:${PORT}  (app ${APP})"
echo "[run_dev] frontend    : in another terminal, run:"
echo "[run_dev]                 cd ${EVAL_DIR}/frontend && npm install && npm run dev"
echo "[run_dev]               then open http://localhost:5173 (it proxies /api here)."

# --- launch (single worker, on the .venv interpreter) ------------------------
exec "${VENV_PY}" -m uvicorn "${APP}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --workers 1 \
  ${RELOAD_FLAG}
