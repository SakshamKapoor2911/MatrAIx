import json
import os
from pathlib import Path

OUTPUT = (
    Path(os.environ.get("MATRIX_OUTPUT_DIR", "/app/output"))
    / "ecommerce_interaction.json"
)
PRODUCTS = {
    "desk-001": "ModDesk Compact",
    "desk-002": "FocusDesk Pro",
    "chair-001": "Align Task Chair",
    "lamp-001": "LumaBar Desk Lamp",
}
RATING_FIELDS = (
    "need_satisfaction",
    "ease_of_use",
    "overall_experience_rating",
)


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text())
    assert isinstance(data, dict), "root must be an object"
    return data


def test_output_exists():
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_selected_product_is_grounded_in_task_catalog():
    data = _load()
    product_id = data.get("selected_product_id")
    assert product_id in PRODUCTS, f"unknown product id: {product_id!r}"
    assert data.get("selected_product_name") == PRODUCTS[product_id]


def test_persona_feedback_scores_are_present():
    data = _load()
    for field in RATING_FIELDS:
        score = data.get(field)
        assert isinstance(score, int) and not isinstance(
            score, bool
        ), f"{field} must be an integer"
        assert 1 <= score <= 10, f"{field} must be 1-10"
    reason = data.get("reason")
    assert isinstance(reason, str) and len(reason.strip()) >= 20, "reason is too short"


def main() -> int:
    test_output_exists()
    test_selected_product_is_grounded_in_task_catalog()
    test_persona_feedback_scores_are_present()
    print("PASS: ecommerce web application output is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
