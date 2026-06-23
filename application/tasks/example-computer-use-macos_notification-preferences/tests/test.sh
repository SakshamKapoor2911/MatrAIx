#!/usr/bin/env bash
set -euo pipefail

logs_dir="/logs"
if [ "$(uname -s)" = "Darwin" ]; then
  logs_dir="/tmp/harbor/logs"
fi
mkdir -p "$logs_dir/verifier"

python3 <<'PY'
import json
import sys
from pathlib import Path

path = Path("/tmp/matraix-macos-notification-preferences/decision.json")
if not path.is_file():
    sys.exit(f"missing {path}")

data = json.loads(path.read_text())
if not isinstance(data.get("keep_notifications_on"), bool):
    sys.exit("keep_notifications_on must be a boolean")
app = data.get("app_reviewed", "")
if not isinstance(app, str) or not app.strip():
    sys.exit("app_reviewed must be a non-empty string")
reason = data.get("reason", "")
if not isinstance(reason, str) or len(reason.strip()) < 10:
    sys.exit("reason must be at least 10 characters")
PY

if [ $? -eq 0 ]; then
  printf '1\n' > "$logs_dir/verifier/reward.txt"
else
  printf '0\n' > "$logs_dir/verifier/reward.txt"
fi
