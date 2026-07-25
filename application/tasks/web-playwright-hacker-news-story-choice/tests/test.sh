#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/verifier_env.sh"

if python3 "${TESTS_DIR}/test_state.py"; then
  echo 1 > "${VERIFIER_DIR}/reward.txt"
else
  echo 0 > "${VERIFIER_DIR}/reward.txt"
  exit 1
fi
