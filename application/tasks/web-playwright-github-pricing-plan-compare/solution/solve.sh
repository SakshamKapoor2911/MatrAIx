#!/bin/bash
set -euo pipefail

export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

if command -v uvx >/dev/null 2>&1; then
  uvx --with playwright playwright install chromium >/dev/null 2>&1 || true
  PYTHON_CMD="uvx --with playwright python"
else
  PYTHON_CMD="python3"
fi

$PYTHON_CMD - <<'PY'
import os
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

url = "https://github.com/pricing"

def get_output_dir() -> Path:
    if os.environ.get("HARBOR_OUTPUT_DIR"):
        p = Path(os.environ["HARBOR_OUTPUT_DIR"])
        p.mkdir(parents=True, exist_ok=True)
        return p
    try:
        p = Path("/app/output")
        p.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        p = Path("output")
        p.mkdir(parents=True, exist_ok=True)
        return p

output_dir = get_output_dir()
output = output_dir / "plan_compare.json"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    
    page_title = page.title()
    browser.close()

payload = {
    "decision_subject_id": "team",
    "decision_subject_label": "Team",
    "decision_outcome": "selected",
    "basis_primary": "features",
    "exploration_style": "compared_multiple",
    "options_considered_count": 3,
    "comparison_axes": ["price", "features", "security"],
    "reason": "Selected Team plan ($4/user/month) as it includes collaboration tools and higher Actions quota required for dev teams.",
    "task_rejected_options": "Free (lacks required team management features) and Enterprise (exceeds team budget)."
}

output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"Wrote oracle output to {output}")
PY
