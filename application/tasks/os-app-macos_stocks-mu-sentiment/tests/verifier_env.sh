# Canonical verifier output path resolution (sourced from tests/test.sh).
#
# Production paths:
#   - Harbor / Playground trial: HARBOR_VERIFIER_DIR -> jobs/.../trial/verifier/
#   - Docker sandbox: default /logs/verifier (mounted, then collected to trial/)
#
# Do not fall back to <task-root>/verifier — that is local-dev leakage.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VERIFIER_DIR="${HARBOR_VERIFIER_DIR:-/logs/verifier}"
if ! mkdir -p "${VERIFIER_DIR}" 2>/dev/null; then
  echo "error: cannot create verifier directory: ${VERIFIER_DIR}" >&2
  echo "Set HARBOR_VERIFIER_DIR to jobs/<job>/<trial>/verifier for local harness runs." >&2
  exit 1
fi
mkdir -p "${VERIFIER_DIR}"
