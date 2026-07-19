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

url = "https://www.nps.gov/yell/index.htm"

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
output = output_dir / "park_compare.json"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    
    hero_title = page.locator("a.Hero-title").first.inner_text() if page.locator("a.Hero-title").count() > 0 else "Yellowstone National Park"
    browser.close()

payload = {
    "decision_subject_id": "yell",
    "decision_subject_label": hero_title.strip(),
    "decision_outcome": "selected",
    "basis_primary": "features",
    "exploration_style": "compared_multiple",
    "options_considered_count": 2,
    "comparison_axes": ["activities", "scenery", "accessibility"],
    "reason": f"Selected {hero_title.strip()} over Yosemite due to wider variety of geothermal features and wildlife viewing opportunities.",
    "task_rejected_options": "Yosemite National Park"
}

output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"Wrote oracle output for {hero_title} to {output}")
PY
