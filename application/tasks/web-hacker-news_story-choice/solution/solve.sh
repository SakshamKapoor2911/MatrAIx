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

url = "https://news.ycombinator.com/"

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
output = output_dir / "story_choice.json"

def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "story"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    
    first_row = page.locator("tr.athing").first
    story_id = first_row.get_attribute("id") or "1"
    title_el = first_row.locator(".titleline > a").first
    title = title_el.inner_text()
    
    subtext = page.locator("td.subtext").first
    points = subtext.locator(".score").inner_text() if subtext.locator(".score").count() > 0 else "0 points"
    comments = "0 comments"
    for a in subtext.locator("a").all():
        txt = a.inner_text()
        if "comment" in txt or "discuss" in txt:
            comments = txt
            break
            
    browser.close()

title = title.strip()
slug = slugify(title)

payload = {
    "decision_subject_id": story_id,
    "decision_subject_label": title,
    "decision_outcome": "selected",
    "basis_primary": "novelty",
    "exploration_style": "quick_pick",
    "reason": f"Selected top story '{title}' ({points}, {comments}) for tech insights.",
    "task_points": points,
    "task_comment_count": comments
}

output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"Wrote oracle output for {title} to {output}")
PY
