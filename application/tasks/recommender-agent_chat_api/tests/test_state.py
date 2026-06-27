from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path(
    os.environ.get("PERSONABENCH_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.json"
RESULT_PATH = OUTPUT_DIR / "recommendation_result.json"
FEEDBACK_PATH = OUTPUT_DIR / "user_feedback.json"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail(f"{path} is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a non-empty string")
    return value


def validate_messages(messages: Any) -> None:
    if not isinstance(messages, list):
        fail("transcript.messages must be a list")
    user_turns = 0
    assistant_turns = 0
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            fail(f"transcript.messages[{index}] must be an object")
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"}:
            fail(f"message role must be user or assistant, got {role!r}")
        require_string(content, "message content")
        if role == "user":
            user_turns += 1
        else:
            assistant_turns += 1
    if user_turns < 3:
        fail(f"expected at least 3 user turns, found {user_turns}")
    if assistant_turns < 3:
        fail(f"expected at least 3 assistant turns, found {assistant_turns}")


def validate_recommended_items(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        fail("recommendation_result.recommendedItems must be a list")
    if not items:
        fail("recommendation_result.recommendedItems must not be empty")
    normalized = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            fail(f"recommendedItems[{index}] must be an object")
        item_id = require_string(item.get("itemId"), "recommendedItems.itemId")
        normalized.append({**item, "itemId": item_id})
    return normalized


def validate_feedback(feedback: dict[str, Any]) -> None:
    for key in (
        "productNeedConstraintSatisfaction",
        "personalPreferenceSatisfaction",
        "reason",
    ):
        require_string(feedback.get(key), f"user_feedback.{key}")
    rating = feedback.get("overallExperienceRating")
    if not isinstance(rating, int) or rating < 1 or rating > 10:
        fail("user_feedback.overallExperienceRating must be an integer 1-10")
    asked = feedback.get("askedUsefulClarificationQuestions")
    if not isinstance(asked, bool):
        fail("user_feedback.askedUsefulClarificationQuestions must be boolean")


def main() -> int:
    transcript = load_json(TRANSCRIPT_PATH)
    result = load_json(RESULT_PATH)

    require_string(transcript.get("sessionId"), "transcript.sessionId")
    require_string(result.get("sessionId"), "recommendation_result.sessionId")
    if transcript["sessionId"] != result["sessionId"]:
        fail("transcript and recommendation result sessionId differ")

    domain = require_string(transcript.get("domain"), "transcript.domain")
    if result.get("domain") != domain:
        fail("transcript and recommendation result domain differ")

    validate_messages(transcript.get("messages"))
    validate_recommended_items(result.get("recommendedItems"))

    turns_to_recommendation = result.get("turnsToRecommendation")
    if not isinstance(turns_to_recommendation, int) or turns_to_recommendation < 1:
        fail("turnsToRecommendation must be a positive integer")

    if FEEDBACK_PATH.exists():
        validate_feedback(load_json(FEEDBACK_PATH))

    print("PASS: recommender chat artifacts are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
