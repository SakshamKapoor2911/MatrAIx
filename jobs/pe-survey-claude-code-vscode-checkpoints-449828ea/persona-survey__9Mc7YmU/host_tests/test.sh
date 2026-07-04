#!/usr/bin/env bash
set -euo pipefail

VERIFIER_DIR="${HARBOR_VERIFIER_DIR:-${PERSONABENCH_VERIFIER_DIR:-/logs/verifier}}"
mkdir -p "${VERIFIER_DIR}"

if python3 /tests/test_state.py; then
  echo 1 > "${VERIFIER_DIR}/reward.txt"
else
  echo 0 > "${VERIFIER_DIR}/reward.txt"
  exit 1
fi
