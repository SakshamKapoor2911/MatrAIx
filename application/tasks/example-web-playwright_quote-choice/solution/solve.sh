#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://quotes.toscrape.com/"
output = Path("/app/output/quote_choice.json")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "quote-choice"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    quote = page.locator("div.quote").first
    quote_text = quote.locator("span.text").inner_text().strip()
    author = quote.locator("small.author").inner_text().strip()
    browser.close()

payload = {
    "decision_subject_id": f"{slugify(author)}-quote",
    "decision_subject_label": quote_text,
    "decision_outcome": "selected",
    "basis_primary": "fit",
    "exploration_style": "quick_pick",
    "reason": "This quote is the one I would most want to save because it matches the kind of message I naturally come back to.",
    "task_author": author,
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY
