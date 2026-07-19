from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path(
    os.environ.get("HARBOR_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.json"
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
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            fail(f"transcript.messages[{index}] must be an object")
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"}:
            fail(f"message role must be user or assistant, got {role!r}")
        require_string(content, "message content")


def validate_feedback(feedback: dict[str, Any]) -> None:
    for key in ("needConstraintSatisfaction", "personalPreferenceSatisfaction"):
        value = feedback.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            fail(f"user_feedback.{key} must be present")
    require_string(feedback.get("reason"), "user_feedback.reason")
    rating = feedback.get("overallExperienceRating")
    if not isinstance(rating, int) or rating < 1 or rating > 10:
        fail("user_feedback.overallExperienceRating must be an integer 1-10")
    asked = feedback.get("askedUsefulClarificationQuestions")
    if not isinstance(asked, bool):
        fail("user_feedback.askedUsefulClarificationQuestions must be boolean")


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
        for item in messages
        if item.get("role") == "assistant"
        and isinstance(item.get("content"), str)
        and "?" in item["content"]
    )


def _assistant_messages(messages: list[dict[str, Any]]) -> list[str]:
    return [
        item["content"].strip()
        for item in messages
        if item.get("role") == "assistant"
        and isinstance(item.get("content"), str)
        and item["content"].strip()
    ]


def _assistant_output_text(messages: list[dict[str, Any]]) -> str:
    replies = _assistant_messages(messages)
    if not replies:
        return "The assistant produced no visible replies in this conversation."
    return "\n".join(f"Reply {index}: {text}" for index, text in enumerate(replies, start=1))


def _recommendation_adaptation(messages: list[dict[str, Any]]) -> str:
    """How the assistant's recommendation evolved across the conversation.

    Derived only from the assistant's own replies so it reflects SUT behavior,
    not the persona's reaction.
    """
    replies = _assistant_messages(messages)
    if len(replies) <= 1:
        return "single_recommendation"
    normalized = [" ".join(reply.lower().split()) for reply in replies]
    # A reply that repeats verbatim after the persona pushed back is the
    # classic "stuck in a loop" failure mode for a recommender.
    if len(set(normalized)) < len(normalized):
        return "repeated_same_pick"
    return "adapted"


def _derive_outcome_status(
    need_satisfaction: str | None,
    preference_satisfaction: str | None,
    has_feedback: bool,
) -> str:
    if has_feedback and need_satisfaction == "yes" and preference_satisfaction == "yes":
        return "resolved"
    if has_feedback and (
        need_satisfaction in {"yes", "partially"}
        or preference_satisfaction in {"yes", "partially"}
    ):
        return "partially_resolved"
    if has_feedback:
        return "unresolved"
    return "partially_resolved"


def _derive_conversation_path(question_count: int, outcome_status: str) -> str:
    if outcome_status == "resolved" and question_count > 0:
        return "clarify_then_resolve"
    if outcome_status == "resolved":
        return "direct_resolution"
    if question_count > 0:
        return "clarify_then_partial"
    return "stalled"


def _verifier_dir() -> Path:
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    if explicit:
        path = Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path

    container_default = Path("/logs/verifier")
    try:
        container_default.mkdir(parents=True, exist_ok=True)
        return container_default
    except OSError:
        pass

    raise RuntimeError(
        "HARBOR_VERIFIER_DIR is required when running outside a Harbor trial "
        "container. Point it at jobs/<job>/<trial>/verifier for local harness runs."
    )


def main() -> int:
    transcript = load_json(TRANSCRIPT_PATH)

    require_string(transcript.get("sessionId"), "transcript.sessionId")
    require_string(transcript.get("domain"), "transcript.domain")

    messages = transcript.get("messages")
    validate_messages(messages)

    feedback = None
    if FEEDBACK_PATH.exists():
        feedback = load_json(FEEDBACK_PATH)
        validate_feedback(feedback)

    user_turns = sum(1 for item in messages if item.get("role") == "user")
    assistant_turns = sum(1 for item in messages if item.get("role") == "assistant")
    clarification_question_count = _count_assistant_questions(messages)
    need_satisfaction = None
    preference_satisfaction = None
    overall_experience_rating = None
    feedback_reason = None
    clarification_questions_useful = None
    contexts: list[dict[str, Any]] = [
        {
            "key": "task_outcome.primary",
            "label": "Task outcome",
            "contextType": "task_outcome",
            "facets": [
                {
                    "key": "task_goal_label",
                    "label": "Task goal",
                    "role": "evidence",
                    "kind": "textual",
                    "value": "Find a recommendation that satisfies the persona's need and preferences",
                },
            ],
        },
        {
            "key": "conversation_summary.primary",
            "label": "Conversation summary",
            "contextType": "conversation_summary",
            "facets": [
                {
                    "key": "user_turn_count",
                    "label": "User turn count",
                    "role": "score",
                    "kind": "numerical",
                    "value": user_turns,
                },
                {
                    "key": "assistant_turn_count",
                    "label": "Assistant turn count",
                    "role": "score",
                    "kind": "numerical",
                    "value": assistant_turns,
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
    ]
    if feedback:
        feedback_reason = require_string(feedback.get("reason"), "user_feedback.reason")
        need_satisfaction = _normalize_feedback_bucket(
            feedback.get("needConstraintSatisfaction"),
            "user_feedback.needConstraintSatisfaction",
        )
        preference_satisfaction = _normalize_feedback_bucket(
            feedback.get("personalPreferenceSatisfaction"),
            "user_feedback.personalPreferenceSatisfaction",
        )
        overall_experience_rating = feedback.get("overallExperienceRating")
        clarification_questions_useful = bool(
            feedback.get("askedUsefulClarificationQuestions")
        )
        contexts.append(
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
                        "value": overall_experience_rating,
                    },
                    {
                        "key": "clarification_questions_useful",
                        "label": "Clarification questions useful",
                        "role": "primary",
                        "kind": "categorical",
                        "value": _bool_category(clarification_questions_useful),
                    },
                    {
                        "key": "feedback_reason",
                        "label": "Feedback reason",
                        "role": "explanation",
                        "kind": "textual",
                        "explainsFacetKey": "personal_preference_satisfaction",
                        "value": feedback_reason,
                    },
                    {
                        "key": "need_constraint_satisfaction",
                        "label": "Need/constraint satisfaction",
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
    outcome_status = _derive_outcome_status(
        need_satisfaction,
        preference_satisfaction,
        feedback is not None,
    )
    conversation_path = _derive_conversation_path(
        clarification_question_count,
        outcome_status,
    )
    if feedback_reason:
        outcome_reason = feedback_reason
        resolution_basis = "user_feedback"
        next_step_owner = "none" if outcome_status == "resolved" else "user"
        process_notes = (
            "The assistant asked clarification questions before making a recommendation, "
            "and the final outcome is grounded in the persona's post-chat feedback."
        )
    else:
        outcome_reason = (
            "The transcript shows a completed recommendation exchange, but no post-chat "
            "feedback artifact was available to confirm full satisfaction."
        )
        resolution_basis = "conversation_commitment"
        next_step_owner = "user"
        process_notes = (
            "The assistant completed the visible recommendation exchange, but the task "
            "did not include self-reported feedback to confirm whether the persona felt "
            "fully satisfied."
        )
    contexts[0]["facets"][:0] = [
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
            "explainsFacetKey": "outcome_status",
            "value": outcome_reason,
        },
        {
            "key": "next_step_owner",
            "label": "Next step owner",
            "role": "evidence",
            "kind": "categorical",
            "value": next_step_owner,
        },
    ]
    contexts[1]["facets"][:0] = [
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
            "explainsFacetKey": "conversation_path",
            "value": process_notes,
        },
    ]
    contexts.append(
        {
            "key": "recommendation_delivery.primary",
            "label": "Recommendation delivery",
            "contextType": "recommendation_delivery",
            "facets": [
                {
                    "key": "recommendation_adaptation",
                    "label": "Recommendation adaptation",
                    "role": "primary",
                    "kind": "categorical",
                    "value": _recommendation_adaptation(messages),
                },
                {
                    "key": "assistant_recommendations",
                    "label": "Assistant recommendation replies",
                    "role": "explanation",
                    "kind": "textual",
                    "value": _assistant_output_text(messages),
                },
            ],
        }
    )
    (_verifier_dir() / "structured_output.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "artifactType": "matraix.trial_evaluation",
                "taskType": "chatbot",
                "presenceCheck": {
                    "passed": True,
                    "requiredArtifacts": ["transcript.json"],
                    "missingArtifacts": [],
                },
                "sourceArtifacts": {
                    "transcript": "/app/output/transcript.json",
                    "userFeedback": "/app/output/user_feedback.json" if feedback else None,
                },
                "contexts": contexts,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("PASS: recommender chat artifacts are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
