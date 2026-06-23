#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://books.toscrape.com/"
output = Path("/app/output/book_interest.json")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    title = page.locator("article.product_pod h3 a").first.inner_text().strip()
    price = page.locator("article.product_pod .price_color").first.inner_text().strip()
    browser.close()

payload = {
    "title": title,
    "price_gbp": price,
    "interested": True,
    "reason": "The listing price is acceptable and the title matches what I saw on the catalog page.",
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY
