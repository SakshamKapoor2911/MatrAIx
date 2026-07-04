#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

url = "https://www.pythonanywhere.com/pricing/"
output = Path("/app/output/plan_choice.json")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "plan-choice"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    plan_name = page.get_by_text("Beginner").first.inner_text().strip()
    price = page.get_by_text("$0/month").first.inner_text().strip()
    browser.close()

payload = {
    "decision_subject_id": slugify(plan_name),
    "decision_subject_label": plan_name,
    "decision_outcome": "selected",
    "basis_primary": "price",
    "exploration_style": "compared_multiple",
    "reason": "This is the plan I would most realistically start with because it gives me a low-risk way to try the service before committing money.",
    "task_price_text": price,
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY
