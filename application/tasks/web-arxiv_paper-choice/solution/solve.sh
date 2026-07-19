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

url = "https://arxiv.org/list/cs.AI/recent"

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
output = output_dir / "paper_choice.json"

def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "paper"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    
    first_dt = page.locator("dt").first
    arxiv_id = first_dt.locator("a[title='Abstract']").inner_text().replace("arXiv:", "").strip()
    
    first_dd = page.locator("dd").first
    title = first_dd.locator(".list-title").inner_text().replace("Title:", "").strip()
    authors = first_dd.locator(".list-authors").inner_text().replace("Authors:", "").strip()
    
    browser.close()

title = title.strip()
slug = slugify(title)

payload = {
    "decision_subject_id": arxiv_id,
    "decision_subject_label": title,
    "decision_outcome": "selected",
    "basis_primary": "fit",
    "exploration_style": "quick_pick",
    "reason": f"Selected recent AI preprint '{title}' by {authors}.",
    "task_primary_category": "cs.AI",
    "task_paper_authors": authors
}

output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"Wrote oracle output for {title} to {output}")
PY
