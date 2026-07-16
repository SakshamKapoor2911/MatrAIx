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
FEEDBACK_PATH = OUTPUT_DIR / "user_feedback.json"

DOMAIN = "telecom"
TASK_GOAL = "Check trade-in value"
PERSONA_ROLE = "customer"
CHATBOT_ROLE = "assistant"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def _verifier_dir() -> Path:
    base = (
        os.environ.get("HARBOR_VERIFIER_DIR")
        or os.environ.get("PERSONABENCH_VERIFIER_DIR")
        or "/logs/verifier"
    )
    path = Path(base)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        path = Path(__file__).resolve().parent.parent / "verifier"
        path.mkdir(parents=True, exist_ok=True)
        return path


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


def _normalize_feedback_bucket(value: Any, label: str) -> str:
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return "yes"
    if text in {"false", "0"}:
        return "no"
    if text not in {"yes", "partially", "no"}:
        fail(f"{label} must be one of yes / partially / no")
    return text


def _bool_category(value: bool) -> str:
    return "true" if value else "false"


def _count_assistant_questions(messages: list[dict[str, Any]]) -> int:
    return sum(
        1
        for entry in messages
        if entry.get("role") == CHATBOT_ROLE
        and isinstance(entry.get("content"), str)
        and "?" in entry["content"]
    )


def _derive_outcome_status_from_transcript(combined_lower: str, assistant_count: int) -> str:
    if assistant_count >= 2 and any(w in combined_lower for w in ["help", "thank", "understand", "clear"]):
        return "partially_resolved"
    return "unresolved"


def _derive_outcome_status_from_feedback(
    need_satisfaction: str,
    preference_satisfaction: str,
) -> str:
    if need_satisfaction == "yes" and preference_satisfaction == "yes":
        return "resolved"
    if need_satisfaction == "no":
        return "unresolved"
    return "partially_resolved"


def _derive_next_step_owner(combined_lower: str, outcome_status: str) -> str:
    followup_markers = (
        "if it still",
        "if it doesn't",
        "if it has not",
        "let us know",
        "check back",
    )
    if outcome_status != "resolved" or any(marker in combined_lower for marker in followup_markers):
        return "user"
    return "none"


def _derive_conversation_path(
    clarification_question_count: int,
    outcome_status: str,
) -> str:
    if outcome_status == "resolved" and clarification_question_count > 0:
        return "clarify_then_resolve"
    if outcome_status == "resolved":
        return "direct_resolution"
    if clarification_question_count > 0:
        return "clarify_then_partial"
    return "stalled"


def validate_messages(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    messages = data.get("messages")
    if not isinstance(messages, list) or not messages:
        fail("transcript.messages must be a non-empty list")
    allowed_roles = {PERSONA_ROLE, CHATBOT_ROLE}
    for entry in messages:
        if entry.get("role") not in allowed_roles:
            fail(f"invalid transcript message role: {entry.get('role')}")
        require_string(entry.get("content"), "message content")
    combined = " ".join(str(entry["content"]) for entry in messages)
    return messages, combined


def validate_feedback(feedback: dict[str, Any]) -> None:
    for key in ("needConstraintSatisfaction", "personalPreferenceSatisfaction"):
        if feedback.get(key) in (None, ""):
            fail(f"user_feedback.{key} must be present")
    require_string(feedback.get("reason"), "user_feedback.reason")
    rating = feedback.get("overallExperienceRating")
    if not isinstance(rating, int) or rating < 1 or rating > 10:
        fail("user_feedback.overallExperienceRating must be an integer 1-10")
    asked = feedback.get("askedUsefulClarificationQuestions")
    if not isinstance(asked, bool):
        fail("user_feedback.askedUsefulClarificationQuestions must be boolean")


def build_evaluation_payload(
    messages: list[dict[str, Any]],
    combined: str,
    feedback: dict[str, Any] | None,
) -> dict[str, Any]:
    combined_lower = combined.lower()
    persona_count = sum(1 for message in messages if message["role"] == PERSONA_ROLE)
    chatbot_count = sum(1 for message in messages if message["role"] == CHATBOT_ROLE)
    clarification_question_count = _count_assistant_questions(messages)

    rating: int | None = None
    need_satisfaction: str | None = None
    preference_satisfaction: str | None = None
    clarification_useful: str | None = None
    feedback_reason: str | None = None

    if feedback is not None:
        validate_feedback(feedback)
        rating = int(feedback["overallExperienceRating"])
        need_satisfaction = _normalize_feedback_bucket(
            feedback.get("needConstraintSatisfaction"),
            "user_feedback.needConstraintSatisfaction",
        )
        preference_satisfaction = _normalize_feedback_bucket(
            feedback.get("personalPreferenceSatisfaction"),
            "user_feedback.personalPreferenceSatisfaction",
        )
        clarification_useful = _bool_category(
            bool(feedback.get("askedUsefulClarificationQuestions"))
        )
        feedback_reason = require_string(feedback.get("reason"), "user_feedback.reason")
        outcome_status = _derive_outcome_status_from_feedback(
            need_satisfaction,
            preference_satisfaction,
        )
        resolution_basis = "user_feedback"
        outcome_reason = feedback_reason
        next_step_owner = _derive_next_step_owner(combined_lower, outcome_status)
    else:
        outcome_status = _derive_outcome_status_from_transcript(combined_lower, chatbot_count)
        resolution_basis = "conversation_commitment"
        next_step_owner = _derive_next_step_owner(combined_lower, outcome_status)
        outcome_reason = (
            f"The conversation with the {DOMAIN} chatbot was productive but did not reach "
            f"a definitive resolution within the chat."
            if chatbot_count >= 2
            else f"The conversation with the {DOMAIN} chatbot was too brief to reach resolution."
        )

    conversation_path = _derive_conversation_path(
        clarification_question_count,
        outcome_status,
    )
    process_notes = (
        f"The conversation engaged with the {DOMAIN} chatbot over {len(messages)} messages "
        f"({persona_count} user, {chatbot_count} assistant)."
    )

    payload: dict[str, Any] = {
        "schemaVersion": "1.0",
        "artifactType": "personabench.trial_evaluation",
        "taskType": "chatbot",
        "presenceCheck": {
            "passed": True,
            "requiredArtifacts": ["transcript.json"],
            "missingArtifacts": [],
        },
        "sourceArtifacts": {
            "transcript": str(TRANSCRIPT_PATH),
            "userFeedback": str(FEEDBACK_PATH) if feedback is not None else None,
        },
        "contexts": [
            {
                "key": "task_outcome.primary",
                "label": "Task outcome",
                "contextType": "task_outcome",
                "facets": [
                    {
                        "key": "outcome_status",
                        "label": "Outcome status",
                        "role": "primary",
                        "kind": "categorical",
                        "value": outcome_status,
                    },
                    {
                        "key": "resolution_basis",
                        "label": "Resolution basis",
                        "role": "primary",
                        "kind": "categorical",
                        "value": resolution_basis,
                    },
                    {
                        "key": "outcome_reason",
                        "label": "Outcome reason",
                        "role": "explanation",
                        "kind": "textual",
                        "value": outcome_reason,
                    },
                    {
                        "key": "next_step_owner",
                        "label": "Next step owner",
                        "role": "evidence",
                        "kind": "categorical",
                        "value": next_step_owner,
                    },
                    {
                        "key": "task_goal_label",
                        "label": "Task goal",
                        "role": "evidence",
                        "kind": "textual",
                        "value": TASK_GOAL,
                    },
                ],
            },
            {
                "key": "conversation_summary.primary",
                "label": "Conversation summary",
                "contextType": "conversation_summary",
                "facets": [
                    {
                        "key": "conversation_path",
                        "label": "Conversation path",
                        "role": "primary",
                        "kind": "categorical",
                        "value": conversation_path,
                    },
                    {
                        "key": "process_notes",
                        "label": "Process notes",
                        "role": "explanation",
                        "kind": "textual",
                        "value": process_notes,
                    },
                    {
                        "key": "user_turn_count",
                        "label": "User turn count",
                        "role": "score",
                        "kind": "numerical",
                        "value": persona_count,
                    },
                    {
                        "key": "assistant_turn_count",
                        "label": "Assistant turn count",
                        "role": "score",
                        "kind": "numerical",
                        "value": chatbot_count,
                    },
                    {
                        "key": "message_count",
                        "label": "Message count",
                        "role": "score",
                        "kind": "numerical",
                        "value": len(messages),
                    },
                    {
                        "key": "clarification_question_count",
                        "label": "Clarification question count",
                        "role": "score",
                        "kind": "numerical",
                        "value": clarification_question_count,
                    },
                ],
            },
        ],
    }

    if feedback is not None and rating is not None and feedback_reason is not None:
        payload["contexts"].append(
            {
                "key": "user_feedback.primary",
                "label": "User feedback",
                "contextType": "user_feedback",
                "facets": [
                    {
                        "key": "overall_experience_rating",
                        "label": "Overall experience rating",
                        "role": "score",
                        "kind": "numerical",
                        "value": rating,
                    },
                    {
                        "key": "feedback_reason",
                        "label": "Feedback reason",
                        "role": "explanation",
                        "kind": "textual",
                        "value": feedback_reason,
                    },
                    {
                        "key": "clarification_questions_useful",
                        "label": "Clarification questions useful",
                        "role": "primary",
                        "kind": "categorical",
                        "value": clarification_useful,
                    },
                    {
                        "key": "need_constraint_satisfaction",
                        "label": "Need or constraint satisfaction",
                        "role": "evidence",
                        "kind": "categorical",
                        "value": need_satisfaction,
                    },
                    {
                        "key": "personal_preference_satisfaction",
                        "label": "Preference satisfaction",
                        "role": "evidence",
                        "kind": "categorical",
                        "value": preference_satisfaction,
                    },
                ],
            }
        )

    return payload


def main() -> int:
    transcript = load_json(TRANSCRIPT_PATH)
    messages, combined = validate_messages(transcript)
    feedback = load_json(FEEDBACK_PATH) if FEEDBACK_PATH.is_file() else None
    payload = build_evaluation_payload(messages, combined, feedback)
    (_verifier_dir() / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"PASS: {DOMAIN} chatbot artifacts are valid")
    return 0


def test_transcript_exists() -> None:
    assert TRANSCRIPT_PATH.is_file(), f"Missing {TRANSCRIPT_PATH}"


def test_transcript_schema() -> None:
    transcript = load_json(TRANSCRIPT_PATH)
    messages, combined = validate_messages(transcript)
    feedback = load_json(FEEDBACK_PATH) if FEEDBACK_PATH.is_file() else None
    payload = build_evaluation_payload(messages, combined, feedback)
    assert payload["contexts"], "evaluation contexts must not be empty"
    assert any(
        context.get("contextType") == "task_outcome" for context in payload["contexts"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
