# Shared host/docker verifier path resolution (sourced from test.sh).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRIAL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
case "${SCRIPT_DIR}" in
  */host_tests)
    VERIFIER_DIR="${TRIAL_ROOT}/verifier"
    ;;
  *)
    VERIFIER_DIR="${HARBOR_VERIFIER_DIR:-${PERSONABENCH_VERIFIER_DIR:-/logs/verifier}}"
    if ! mkdir -p "${VERIFIER_DIR}" 2>/dev/null; then
      VERIFIER_DIR="${TRIAL_ROOT}/verifier"
    fi
    ;;
esac
mkdir -p "${VERIFIER_DIR}"
