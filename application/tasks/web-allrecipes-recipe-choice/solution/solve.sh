#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

SEARCH_URL = "https://www.allrecipes.com/search?q=chicken"
OUTPUT = Path("/app/output/recipe_choice.json")
RECIPE_PATH = re.compile(r"^/recipe/([1-9]\d*)/([a-z0-9]+(?:-[a-z0-9]+)*)/$")
DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def recipe_id(url: str) -> str:
    match = RECIPE_PATH.fullmatch(urlparse(url).path)
    if not match:
        raise RuntimeError(f"Unexpected Allrecipes recipe URL: {url}")
    return match.group(1)


def labeled_value(page_text: str, label: str) -> str:
    match = re.search(rf"(?m)^{re.escape(label)}:\s*\n\s*([^\n]+)\s*$", page_text)
    if not match:
        raise RuntimeError(f"Could not read {label} from recipe page")
    return match.group(1).strip()


def open_recipe_page(page, recipe_url: str) -> None:
    for attempt in range(3):
        if attempt:
            page.wait_for_timeout(2_000 * attempt)
        page.goto(recipe_url, wait_until="domcontentloaded", timeout=60_000)
        if page.locator("main h1").count() > 0:
            return
    raise RuntimeError(
        f"Allrecipes did not expose a recipe heading for {recipe_url}; "
        f"last page title was {page.title()!r}"
    )


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    search_context = browser.new_context(user_agent=DESKTOP_USER_AGENT, locale="en-US")
    page = search_context.new_page()
    page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60_000)

    hrefs: list[str] = []
    links = page.locator('main a[href*="/recipe/"]')
    links.first.wait_for(state="visible", timeout=60_000)
    for index in range(min(links.count(), 100)):
        href = links.nth(index).get_attribute("href")
        if not href:
            continue
        absolute_url = urljoin(SEARCH_URL, href)
        parsed = urlparse(absolute_url)
        if parsed.scheme != "https" or parsed.netloc != "www.allrecipes.com":
            continue
        if not RECIPE_PATH.fullmatch(parsed.path):
            continue
        canonical_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if canonical_url not in hrefs:
            hrefs.append(canonical_url)
        if len(hrefs) == 3:
            break

    if len(hrefs) < 3:
        raise RuntimeError("Allrecipes search returned fewer than three recipe candidates")
    search_context.close()

    candidates: list[dict[str, object]] = []
    for recipe_url in hrefs:
        recipe_context = browser.new_context(user_agent=DESKTOP_USER_AGENT, locale="en-US")
        page = recipe_context.new_page()
        open_recipe_page(page, recipe_url)
        title = page.locator("main h1").first.inner_text().strip()
        page_text = page.locator("main").inner_text()
        total_time = labeled_value(page_text, "Total Time")
        servings_text = labeled_value(page_text, "Servings")
        if not servings_text.isdigit() or int(servings_text) <= 0:
            raise RuntimeError(f"Unexpected servings value on {recipe_url}: {servings_text}")
        candidates.append(
            {
                "decision_subject_id": recipe_id(recipe_url),
                "decision_subject_label": title,
                "task_recipe_url": recipe_url,
                "task_total_time_text": total_time,
                "task_servings": int(servings_text),
                "task_relevance_note": (
                    "This was a plausible option because its recipe page provided "
                    "ingredients, preparation steps, total time, and serving information "
                    "for a realistic comparison."
                ),
            }
        )
        recipe_context.close()

    browser.close()

selected = candidates[0]
payload = {
    "decision_subject_id": selected["decision_subject_id"],
    "decision_subject_label": selected["decision_subject_label"],
    "decision_outcome": "selected",
    "basis_primary": "fit",
    "basis_secondary": "convenience",
    "exploration_style": "compared_multiple",
    "reason": (
        f"I selected {selected['decision_subject_label']} because it was the strongest "
        "overall fit among the three inspected recipes and its stated time and serving "
        "information made it practical for an upcoming meal."
    ),
    "task_recipe_url": selected["task_recipe_url"],
    "task_total_time_text": selected["task_total_time_text"],
    "task_servings": selected["task_servings"],
    "task_options_considered": candidates,
}
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
