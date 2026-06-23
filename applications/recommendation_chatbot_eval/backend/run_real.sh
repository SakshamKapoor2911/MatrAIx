#!/usr/bin/env bash
# run_real.sh -- launch RecBot Studio API in REAL mode (in-repo InteRecAgent + OpenAI).
#
# Thin wrapper over run_dev.sh: it pins the REAL-mode knobs (native ranker,
# recai_resources resource mode), points the HuggingFace caches at /mira (the
# home disk is quota-limited), then hands off to run_dev.sh which execs uvicorn
# on the canonical project .venv (uv-managed Python 3.9 — see RECAI_ENV_NOTES.md).
#
# The whole stack now lives in ONE interpreter: the harness (FastAPI, pydantic
# v2) and the in-repo RecAI engine share the .venv. The RecAI checkout resolves
# in-repo via recbot/paths.py (recai/InteRecAgent) — no external root needed.
#
# Prereqs:
#   - the project .venv provisioned per RECAI_ENV_NOTES.md (torch 1.13.1 CPU,
#     unirec, sentence-transformers 2.2.2, fastapi/pydantic v2, ...)
#   - OPENAI_API_KEY in <repo>/.env.local   (gitignored; loaded by run_dev.sh)
#
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# REAL-mode knobs: native ranker + recai_resources resources (the only
# supported combination — see RECAI_ENV_NOTES.md).
export INTERECAGENT_RANKER_MODE="native"
export INTERECAGENT_RESOURCE_MODE="recai_resources"
export INTERECAGENT_TIMEOUT_SECONDS="${INTERECAGENT_TIMEOUT_SECONDS:-900}"

# HuggingFace / sentence-transformers caches MUST live on /mira (home disk is
# quota-limited). sentence-transformers downloads thenlper/gte-base (~833 MB).
export HF_HOME="${HF_HOME:-/mira/u/qianfengwen/.cache/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/mira/u/qianfengwen/.cache/huggingface/hub}"
export SENTENCE_TRANSFORMERS_HOME="${SENTENCE_TRANSFORMERS_HOME:-/mira/u/qianfengwen/.cache/torch/sentence_transformers}"
export TOKENIZERS_PARALLELISM=false

unset RECBOT_STUDIO_DEMO  # REAL mode: route turns to llm4crs, not the scripted demo.

echo "[run_real] ranker     : ${INTERECAGENT_RANKER_MODE}"
echo "[run_real] resources  : ${INTERECAGENT_RESOURCE_MODE}"
echo "[run_real] HF_HOME    : ${HF_HOME}"
echo "[run_real] OPENAI key : (loaded from .env.local by run_dev.sh)"

# Hand off to run_dev.sh, which loads .env.local and execs uvicorn on the .venv.
exec bash "${BACKEND_DIR}/run_dev.sh"
