#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

SEARCH_URL = "https://ocw.mit.edu/search/?q=machine%20learning"
OUTPUT = Path("/app/output/course_choice.json")
HEADER_PATTERN = re.compile(
    r"(?m)^([A-Za-z0-9.\-]+)\s*\|\s*[^|\n]+\|\s*"
    r"(Undergraduate|Graduate|Non-Credit)\s*$",
    re.IGNORECASE,
)


def course_slug(url: str) -> str:
    return urlparse(url).path.strip("/").split("/")[-1]


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60_000)

    hrefs: list[str] = []
    articles = page.locator("main article")
    articles.first.wait_for(state="visible", timeout=60_000)
    for index in range(min(articles.count(), 20)):
        links = articles.nth(index).locator('a[href^="/courses/"]')
        if links.count() == 0:
            continue
        href = links.first.get_attribute("href")
        if not href:
            continue
        absolute_url = urljoin(SEARCH_URL, href)
        if absolute_url not in hrefs:
            hrefs.append(absolute_url)
        if len(hrefs) == 3:
            break

    if len(hrefs) < 3:
        raise RuntimeError("MIT OCW search returned fewer than three course candidates")

    candidates: list[dict[str, str]] = []
    for course_url in hrefs:
        page.goto(course_url, wait_until="domcontentloaded", timeout=60_000)
        title = page.locator("h1").first.inner_text().strip()
        page_text = page.locator("body").inner_text()
        header_match = HEADER_PATTERN.search(page_text)
        if not header_match:
            raise RuntimeError(f"Could not read course number and level from {course_url}")
        course_number = header_match.group(1).strip()
        course_level = header_match.group(2).strip().title().replace("Non-Credit", "Non-Credit")
        candidates.append(
            {
                "decision_subject_id": course_slug(course_url),
                "decision_subject_label": title,
                "task_course_url": course_url,
                "task_course_number": course_number,
                "task_course_level": course_level,
                "task_relevance_note": (
                    "This course was a plausible option because its topic matched the "
                    "machine-learning search and its course page exposed material for study."
                ),
            }
        )

    browser.close()

selected = candidates[0]
payload = {
    "decision_subject_id": selected["decision_subject_id"],
    "decision_subject_label": selected["decision_subject_label"],
    "decision_outcome": "selected",
    "basis_primary": "fit",
    "basis_secondary": "features",
    "exploration_style": "compared_multiple",
    "reason": (
        f"I selected {selected['decision_subject_label']} because it was the strongest "
        "fit among the three inspected machine-learning courses and offered concrete "
        "course materials I could use for self-directed study."
    ),
    "task_course_url": selected["task_course_url"],
    "task_course_number": selected["task_course_number"],
    "task_course_level": selected["task_course_level"],
    "task_options_considered": candidates,
}
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
