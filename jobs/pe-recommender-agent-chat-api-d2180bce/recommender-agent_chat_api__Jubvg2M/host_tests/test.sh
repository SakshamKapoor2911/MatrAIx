#!/usr/bin/env bash
set -euo pipefail

VERIFIER_DIR="${HARBOR_VERIFIER_DIR:-${PERSONABENCH_VERIFIER_DIR:-/logs/verifier}}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
mkdir -p "${VERIFIER_DIR}"

if python3 "${TESTS_DIR}/test_state.py"; then
  echo 1 > "${VERIFIER_DIR}/reward.txt"
else
  echo 0 > "${VERIFIER_DIR}/reward.txt"
  exit 1
fi
