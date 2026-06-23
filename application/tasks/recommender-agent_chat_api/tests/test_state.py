from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


OUTPUT_DIR = Path(os.environ.get("MATRIX_OUTPUT_DIR", "/app/output"))
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.json"
RESULT_PATH = OUTPUT_DIR / "recommendation_result.json"
FEEDBACK_PATH = OUTPUT_DIR / "user_feedback.json"


def fail(message: str) -> None:
    print("FAIL: {}".format(message), file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        fail("{} is missing".format(path))
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail("{} is not valid JSON: {}".format(path, exc))
    if not isinstance(value, dict):
        fail("{} must contain a JSON object".format(path))
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail("{} must be a non-empty string".format(label))
    return value


def validate_messages(messages: Any) -> None:
    if not isinstance(messages, list):
        fail("transcript.messages must be a list")
    user_turns = 0
    assistant_turns = 0
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            fail("transcript.messages[{}] must be an object".format(index))
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"}:
            fail("message role must be user or assistant, got {!r}".format(role))
        require_string(content, "message content")
        if role == "user":
            user_turns += 1
        else:
            assistant_turns += 1
    if user_turns < 3:
        fail("expected at least 3 user turns, found {}".format(user_turns))
    if assistant_turns < 3:
        fail("expected at least 3 assistant turns, found {}".format(assistant_turns))


def validate_recommended_items(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        fail("recommendation_result.recommendedItems must be a list")
    if not items:
        fail("recommendation_result.recommendedItems must not be empty")
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            fail("recommendedItems[{}] must be an object".format(index))
        item_id = require_string(item.get("itemId"), "recommendedItems.itemId")
        normalized.append({**item, "itemId": item_id})
    return normalized


def validate_feedback(feedback: Dict[str, Any]) -> None:
    for key in (
        "productNeedConstraintSatisfaction",
        "personalPreferenceSatisfaction",
        "reason",
    ):
        require_string(feedback.get(key), "user_feedback.{}".format(key))
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
