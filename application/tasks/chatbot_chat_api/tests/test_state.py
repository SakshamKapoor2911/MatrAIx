from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set


OUTPUT_DIR = Path(os.environ.get("MATRIX_OUTPUT_DIR", "/app/output"))
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.json"
RESULT_PATH = OUTPUT_DIR / "application_result.json"
FEEDBACK_PATH = OUTPUT_DIR / "user_feedback.json"
PERSONA_SELF_REPORT_PATH = OUTPUT_DIR / "persona_self_report.json"
RUN_METADATA_PATH = OUTPUT_DIR / "run_metadata.json"


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


def optional_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return load_json(path)


def expected_min_turns(metadata: Dict[str, Any]) -> int:
    value = metadata.get("minTurns", 3)
    try:
        turns = int(value)
    except (TypeError, ValueError):
        turns = 3
    return max(1, turns)


def validate_messages(messages: Any, *, min_turns: int) -> None:
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
    if user_turns < min_turns:
        fail("expected at least {} user turns, found {}".format(min_turns, user_turns))
    if assistant_turns < min_turns:
        fail(
            "expected at least {} assistant turns, found {}".format(
                min_turns, assistant_turns
            )
        )


def validate_grounded_items(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        fail("application_result.groundedItems must be a list")
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            fail("groundedItems[{}] must be an object".format(index))
        item_id = require_string(item.get("itemId"), "groundedItems.itemId")
        normalized.append({**item, "itemId": item_id})
    return normalized


def collect_grounded_item_ids(turns: Any) -> Set[str]:
    if not isinstance(turns, list) or not turns:
        fail("transcript.turns must contain real chatbot turn objects")

    item_ids: Set[str] = set()
    for turn_index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            fail("transcript.turns[{}] must be an object".format(turn_index))
        items = turn.get("groundedItems", turn.get("recommendedItems", []))
        if not isinstance(items, list):
            fail(
                "transcript.turns[{}].groundedItems must be a list".format(
                    turn_index
                )
            )
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                fail(
                    "transcript.turns[{}].groundedItems[{}] must be an object".format(
                        turn_index, item_index
                    )
                )
            item_id = item.get("itemId", item.get("id"))
            if item_id is not None and str(item_id).strip():
                item_ids.add(str(item_id).strip())

    return item_ids


def validate_application_grounding(
    grounded_items: List[Dict[str, Any]], grounded_item_ids: Set[str]
) -> None:
    missing = [
        item["itemId"]
        for item in grounded_items
        if item["itemId"] not in grounded_item_ids
    ]
    if missing:
        fail(
            "application_result.groundedItems must be grounded in "
            "transcript.turns groundedItems; missing ids: {}".format(
                ", ".join(missing[:5])
            )
        )


def validate_feedback(feedback: Dict[str, Any]) -> None:
    if "constraintSatisfaction" in feedback or "overallRating" in feedback:
        for key in (
            "constraintRationale",
            "preferenceRationale",
            "ratingReason",
            "clarifyingNotes",
        ):
            require_string(feedback.get(key), "user_feedback.{}".format(key))
        for key in ("constraintSatisfaction", "preferenceSatisfaction"):
            score = feedback.get(key)
            if not isinstance(score, int) or score < 1 or score > 5:
                fail("user_feedback.{} must be an integer 1-5".format(key))
        rating = feedback.get("overallRating")
        if not isinstance(rating, int) or rating < 1 or rating > 10:
            fail("user_feedback.overallRating must be an integer 1-10")
        asked = feedback.get("askedUsefulClarifyingQuestions")
        if not isinstance(asked, bool):
            fail("user_feedback.askedUsefulClarifyingQuestions must be boolean")
        return

    product_need = feedback.get(
        "productNeedSatisfaction",
        feedback.get("productNeedConstraintSatisfaction"),
    )
    if not isinstance(product_need, int) or product_need < 1 or product_need > 5:
        fail("user_feedback.productNeedSatisfaction must be an integer 1-5")
    preference = feedback.get("personalPreferenceSatisfaction")
    if not isinstance(preference, int) or preference < 1 or preference > 5:
        fail("user_feedback.personalPreferenceSatisfaction must be an integer 1-5")
    require_string(feedback.get("reason"), "user_feedback.reason")
    rating = feedback.get("overallExperienceRating")
    if not isinstance(rating, int) or rating < 1 or rating > 10:
        fail("user_feedback.overallExperienceRating must be an integer 1-10")
    asked = feedback.get("askedUsefulClarificationQuestions")
    if not isinstance(asked, bool):
        fail("user_feedback.askedUsefulClarificationQuestions must be boolean")


def main() -> int:
    transcript = load_json(TRANSCRIPT_PATH)
    result = load_json(RESULT_PATH)
    run_metadata = optional_json(RUN_METADATA_PATH)

    require_string(transcript.get("sessionId"), "transcript.sessionId")
    require_string(result.get("sessionId"), "application_result.sessionId")
    if transcript["sessionId"] != result["sessionId"]:
        fail("transcript and application result sessionId differ")

    application_id = transcript.get("applicationId")
    if application_id is not None:
        require_string(application_id, "transcript.applicationId")
        if result.get("applicationId") != application_id:
            fail("transcript and application result applicationId differ")

    domain = require_string(transcript.get("domain"), "transcript.domain")
    if result.get("domain") != domain:
        fail("transcript and application result domain differ")

    validate_messages(
        transcript.get("messages"), min_turns=expected_min_turns(run_metadata)
    )
    grounded_item_ids = collect_grounded_item_ids(transcript.get("turns"))
    grounded_items = validate_grounded_items(
        result.get("groundedItems", result.get("recommendedItems"))
    )
    validate_application_grounding(grounded_items, grounded_item_ids)

    turns_to_result = result.get("turnsToResult", result.get("turnsToRecommendation"))
    if not isinstance(turns_to_result, int) or turns_to_result < 1:
        fail("turnsToResult must be a positive integer")

    if PERSONA_SELF_REPORT_PATH.exists():
        validate_feedback(load_json(PERSONA_SELF_REPORT_PATH))
    elif FEEDBACK_PATH.exists():
        validate_feedback(load_json(FEEDBACK_PATH))

    print("PASS: chatbot application artifacts are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
