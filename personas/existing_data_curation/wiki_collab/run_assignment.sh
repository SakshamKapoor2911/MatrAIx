#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="${ROOT}/collab_kit/assignment_runner.py"

if [[ ! -f "${RUNNER}" ]]; then
  echo "ERROR: missing ${RUNNER}" >&2
  exit 2
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run --no-project python "${RUNNER}" "$@"
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 "${RUNNER}" "$@"
fi
if command -v python >/dev/null 2>&1; then
  exec python "${RUNNER}" "$@"
fi

echo "ERROR: Python 3 is required. Install python3 or uv, then rerun ./run_assignment.sh." >&2
exit 2
