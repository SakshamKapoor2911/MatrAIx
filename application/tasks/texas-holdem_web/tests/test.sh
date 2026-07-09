#!/bin/bash
set -uo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"

if ! command -v uvx >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh
  source "$HOME/.local/bin/env"
fi

# Copy scenario definitions into tests dir so verifier can load them
SCENARIOS_SRC="${SCRIPT_DIR}/../../environment/task-environments/application/texas-holdem_web/holdem-web/scenarios"
if [ -d "${SCENARIOS_SRC}" ]; then
  cp -r "${SCENARIOS_SRC}" "${TESTS_DIR}/scenarios"
fi

if uvx \
  --with pytest==8.4.1 \
  --with pytest-json-ctrf==0.3.5 \
  pytest --ctrf "${VERIFIER_DIR}/ctrf.json" "${TESTS_DIR}/test_state.py" -rA; then
  echo 1 > "${VERIFIER_DIR}/reward.txt"
else
  echo 0 > "${VERIFIER_DIR}/reward.txt"
fi
