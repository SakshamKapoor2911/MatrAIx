from __future__ import annotations

import json
import importlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set


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


def collect_grounded_item_ids(turns: Any) -> Set[str]:
    if not isinstance(turns, list) or not turns:
        fail("transcript.turns must contain real recbot turn objects")

    item_ids: Set[str] = set()
    for turn_index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            fail("transcript.turns[{}] must be an object".format(turn_index))
        items = turn.get("recommendedItems", [])
        if not isinstance(items, list):
            fail(
                "transcript.turns[{}].recommendedItems must be a list".format(
                    turn_index
                )
            )
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                fail(
                    "transcript.turns[{}].recommendedItems[{}] must be an object".format(
                        turn_index, item_index
                    )
                )
            item_id = item.get("itemId", item.get("id"))
            if item_id is not None and str(item_id).strip():
                item_ids.add(str(item_id).strip())

    if not item_ids:
        fail("transcript.turns must include at least one recbot recommended item")
    return item_ids


def validate_recommendation_grounding(
    recommended_items: List[Dict[str, Any]], grounded_item_ids: Set[str]
) -> None:
    missing = [
        item["itemId"]
        for item in recommended_items
        if item["itemId"] not in grounded_item_ids
    ]
    if missing:
        fail(
            "recommendation_result.recommendedItems must be grounded in "
            "transcript.turns recommendedItems; missing ids: {}".format(
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


def application_scorer_configured() -> bool:
    return bool(os.environ.get("MATRIX_SCORER_PERSONA_JSON"))


def run_application_scorer() -> Path:
    package_parent = os.environ.get("MATRIX_SCORER_PACKAGE_PARENT")
    if package_parent and package_parent not in sys.path:
        sys.path.insert(0, package_parent)
    module_name = os.environ.get("MATRIX_SCORER_MODULE", "persona_eval.scoring")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        fail("could not import application scorer {}: {}".format(module_name, exc))
    scorer = getattr(module, "score_harbor_artifacts_from_env", None)
    if scorer is None:
        fail("{} must expose score_harbor_artifacts_from_env".format(module_name))
    output_path = Path(os.environ.get("MATRIX_SCORER_OUTPUT_PATH", str(FEEDBACK_PATH)))
    try:
        scorer(
            transcript_path=TRANSCRIPT_PATH,
            recommendation_path=RESULT_PATH,
            output_path=output_path,
        )
    except Exception as exc:
        fail("application scorer failed: {}".format(exc))
    if not output_path.is_file():
        fail("application scorer did not write {}".format(output_path))
    return output_path


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
    grounded_item_ids = collect_grounded_item_ids(transcript.get("turns"))
    recommended_items = validate_recommended_items(result.get("recommendedItems"))
    validate_recommendation_grounding(recommended_items, grounded_item_ids)

    turns_to_recommendation = result.get("turnsToRecommendation")
    if not isinstance(turns_to_recommendation, int) or turns_to_recommendation < 1:
        fail("turnsToRecommendation must be a positive integer")

    feedback_path = (
        run_application_scorer() if application_scorer_configured() else FEEDBACK_PATH
    )
    if feedback_path.exists():
        validate_feedback(load_json(feedback_path))

    print("PASS: recommender chat artifacts are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
