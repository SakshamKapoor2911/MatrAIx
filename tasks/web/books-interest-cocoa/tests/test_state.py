import json
import re
from pathlib import Path

OUTPUT = Path("/app/output/book_interest.json")
PRICE_PATTERN = re.compile(r"^£\d+\.\d{2}$")


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text())
    assert isinstance(data, dict), "root must be an object"
    return data


def test_output_exists():
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_output_schema():
    data = _load()
    title = data.get("title")
    assert isinstance(title, str) and title.strip(), "title must be non-empty"
    price = data.get("price_gbp")
    assert isinstance(price, str) and PRICE_PATTERN.match(price.strip()), (
        "price_gbp must look like £12.34"
    )
    assert isinstance(data.get("interested"), bool)
    reason = data.get("reason")
    assert isinstance(reason, str) and len(reason.strip()) >= 10, "reason is too short"
