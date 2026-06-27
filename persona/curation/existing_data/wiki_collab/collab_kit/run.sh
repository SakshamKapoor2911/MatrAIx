#!/usr/bin/env bash
#
# Convenience wrapper. Runs the harness from the kit directory so `import solver`
# and `import conformance` resolve. All args pass through to harness.py.
#
#   ./run.sh --tasks sample/tasks.jsonl --dimensions sample/dimensions.json \
#            --out results.jsonl --backend mock
#
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${HERE}"
exec python3 harness.py "$@"
