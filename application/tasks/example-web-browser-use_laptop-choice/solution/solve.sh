#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://webscraper.io/test-sites/e-commerce/static/computers/laptops"
output = Path("/app/output/laptop_choice.json")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "laptop-choice"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    first_card = page.locator("div.thumbnail").first
    title = first_card.locator("a.title").first.inner_text().strip()
    price = first_card.locator("h4.price").first.inner_text().strip()
    browser.close()

payload = {
    "decision_subject_id": slugify(title),
    "decision_subject_label": title,
    "decision_outcome": "selected",
    "basis_primary": "price",
    "exploration_style": "quick_pick",
    "reason": "This model is the one I would most realistically consider because the listed price feels like the clearest first-pass filter.",
    "task_price_text": price,
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY
