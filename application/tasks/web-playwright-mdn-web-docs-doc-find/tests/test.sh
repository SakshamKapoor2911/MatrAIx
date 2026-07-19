#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/verifier_env.sh"

pytest "${TESTS_DIR}/test_state.py" -v
