#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

SOURCE_URL = "https://www.notion.com/pricing"
OUTPUT = Path("/app/output/notion_plan_comparison.json")
PLAN_IDS = {
    "Free": "free",
    "Plus": "plus",
    "Business": "business",
    "Enterprise": "enterprise",
}


def plan_summary(page, label: str) -> tuple[str, str]:
    accessible_name = re.compile(
        rf"^{re.escape(label)}(?:\s+Recommended)?$",
        re.IGNORECASE,
    )
    heading = page.get_by_role("heading", name=accessible_name).first
    heading.wait_for(state="visible", timeout=60_000)
    text = heading.evaluate(
        """element => {
          let node = element.parentElement;
          while (node && node !== document.body) {
            const text = (node.innerText || "").trim();
            const hasPrice = /\\$\\s*\\d|Custom pricing/i.test(text);
            const hasAudience = /(^|\\n)For\\s+/m.test(text);
            if (hasPrice && hasAudience && text.length < 1600) {
              return text;
            }
            node = node.parentElement;
          }
          return "";
        }"""
    )
    if not text:
        raise RuntimeError(f"Could not locate the {label} plan summary")

    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    price_index = next(
        (
            index
            for index, line in enumerate(lines)
            if re.search(r"\$\s*\d", line) or line.lower() == "custom pricing"
        ),
        -1,
    )
    target_index = next(
        (index for index, line in enumerate(lines) if line.startswith("For ")),
        -1,
    )
    price = (
        " ".join(lines[price_index:target_index])
        if 0 <= price_index < target_index
        else ""
    )
    target = lines[target_index] if target_index >= 0 else ""
    if not price or not target:
        raise RuntimeError(
            f"Could not extract price and audience text for {label}: {lines!r}"
        )
    return price, target


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(locale="en-US")
    page.goto(SOURCE_URL, wait_until="domcontentloaded", timeout=60_000)

    monthly = page.get_by_text("Pay monthly", exact=True).first
    monthly.wait_for(state="visible", timeout=60_000)
    monthly.click()

    candidates: list[dict[str, str]] = []
    for label, stable_id in PLAN_IDS.items():
        price, target = plan_summary(page, label)
        candidates.append(
            {
                "decision_subject_id": stable_id,
                "decision_subject_label": label,
                "task_price_text": price,
                "task_target_text": target,
                "task_relevance_note": (
                    "This was a plausible comparison option because its standard "
                    "monthly price, intended audience, and visible features could "
                    "be weighed against the user's realistic context."
                ),
            }
        )

    page.get_by_text("Plans and features", exact=True).first.wait_for(
        state="visible", timeout=60_000
    )
    browser.close()

selected = next(
    candidate
    for candidate in candidates
    if candidate["decision_subject_id"] == "plus"
)
payload = {
    "decision_subject_id": selected["decision_subject_id"],
    "decision_subject_label": selected["decision_subject_label"],
    "decision_outcome": "selected",
    "basis_primary": "fit",
    "basis_secondary": "price",
    "exploration_style": "compared_multiple",
    "reason": (
        "I selected Plus because its standard monthly plan is aimed at small "
        "teams and professionals and offers a practical collaboration upgrade "
        "over Free without assuming the administration and security needs of "
        "a growing business or enterprise."
    ),
    "task_billing_mode": "monthly",
    "task_source_url": SOURCE_URL,
    "task_price_text": selected["task_price_text"],
    "task_target_text": selected["task_target_text"],
    "task_options_considered": candidates,
}
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
