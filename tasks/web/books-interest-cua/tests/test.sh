#!/usr/bin/env bash
set -euo pipefail

logs_dir="/logs"
if [ "$(uname -s)" = "Darwin" ]; then
  logs_dir="/tmp/harbor/logs"
fi
mkdir -p "$logs_dir/verifier"

output_file="/app/output/book_interest.json"
if [ "$(uname -s)" = "Darwin" ]; then
  output_file="/Users/lume/output/book_interest.json"
fi

export OUTPUT_FILE="$output_file"

python3 <<'PY'
import json
import os
import re
import sys
from pathlib import Path

path = Path(os.environ["OUTPUT_FILE"])
price_re = re.compile(r"^£\d+\.\d{2}$")

if not path.is_file():
    sys.exit(f"missing {path}")

data = json.loads(path.read_text())
if not isinstance(data.get("interested"), bool):
    sys.exit("interested must be a boolean")

title = data.get("title", "")
if not isinstance(title, str) or not title.strip():
    sys.exit("title must be non-empty")

price = data.get("price_gbp", "")
if not isinstance(price, str) or not price_re.match(price.strip()):
    sys.exit("price_gbp must look like £12.34")

reason = data.get("reason", "")
if not isinstance(reason, str) or len(reason.strip()) < 10:
    sys.exit("reason must be at least 10 characters")
PY

if [ $? -eq 0 ]; then
  printf '1\n' > "$logs_dir/verifier/reward.txt"
else
  printf '0\n' > "$logs_dir/verifier/reward.txt"
fi
