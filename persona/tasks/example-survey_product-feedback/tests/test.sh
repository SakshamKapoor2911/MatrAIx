#!/bin/bash
set -euo pipefail

if ! command -v uvx >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

UVX_BASE=(uvx --with pytest==8.4.1 --with pyyaml==6.0.2)

# Schema hard gate — missing/invalid output is an agent failure, not a scored behavior.
if ! "${UVX_BASE[@]}" --with pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_state.py -rA; then
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

# Valid behavioral output → reward follows probe grounding (declined/continued paths).
# When PERSONABENCH_PROBE_DIMENSION is unset, grounding is skipped and reward = 1 (adhoc smoke).
if "${UVX_BASE[@]}" pytest /tests/test_grounding.py -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
