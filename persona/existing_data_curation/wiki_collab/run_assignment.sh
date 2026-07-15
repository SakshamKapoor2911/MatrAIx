#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="${ROOT}/collab_kit/assignment_runner.py"

if [[ ! -f "${RUNNER}" ]]; then
  echo "ERROR: missing ${RUNNER}" >&2
  exit 2
fi

find_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      if "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
        printf '%s\n' "${candidate}"
        return 0
      fi
    fi
  done
  return 1
}

if PYTHON_BIN="$(find_python)"; then
  exec "${PYTHON_BIN}" "${RUNNER}" "$@"
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run --no-project --python '>=3.10' python "${RUNNER}" "$@"
fi

echo "ERROR: Python 3.10+ is required. Install python3 or uv, then rerun ./run_assignment.sh." >&2
exit 2
