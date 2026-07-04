#!/usr/bin/env bash
# Install InteRecAgent + native resource bundles + parquet catalogs for PersonaEval.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required." >&2
  exit 1
fi

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

echo "==> RecAI native setup (api root: $ROOT)"
"$PYTHON" scripts/setup_recai_resources.py "$@"
