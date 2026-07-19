from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path(
    os.environ.get("PERSONABENCH_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.json"
FEEDBACK_PATH = OUTPUT_DIR / "user_feedback.json"


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


def _load_json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"Missing {path}"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), f"{path.name} root must be an object"
    return value


def _require_string(value: Any, label: str) -> str:
    assert isinstance(value, str) and value.strip(), f"{label} must be a non-empty string"
    return value.strip()


def _count_assistant_questions(messages: list[dict[str, Any]]) -> int:
    return sum(
        1
        for entry in messages
        if entry.get("role") == "assistant"
        and isinstance(entry.get("content"), str)
        and "?" in entry["content"]
    )


def _optional_score(feedback: dict[str, Any], key: str) -> int | None:
    value = feedback.get(key)
    if value is None:
        return None
    assert isinstance(value, int) and 1 <= value <= 10, f"{key} must be an integer 1-10"
    return value


def _normalize_feedback_bucket(value: Any, label: str) -> str:
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return "yes"
    if text in {"false", "0"}:
        return "no"
    assert text in {"yes", "partially", "no"}, (
        f"{label} must be yes / partially / no"
    )
    return text


def _bool_category(value: bool) -> str:
    return "true" if value else "false"


def _derive_outcome_status(need_satisfaction: str, rating: int) -> str:
    if need_satisfaction == "yes" or rating >= 8:
        return "resolved"
    if need_satisfaction == "partially" or rating >= 5:
        return "partially_resolved"
    return "unresolved"


def _derive_conversation_path(question_count: int, outcome_status: str) -> str:
    if outcome_status == "resolved" and question_count > 0:
        return "clarify_then_resolve"
    if outcome_status == "resolved":
        return "direct_resolution"
    if question_count > 0:
        return "clarify_then_partial"
    return "stalled"


def main() -> None:
    transcript = _load_json(TRANSCRIPT_PATH)

    _require_string(transcript.get("sessionId"), "transcript.sessionId")
    _require_string(transcript.get("domain"), "transcript.domain")

    messages = transcript.get("messages")
    assert isinstance(messages, list) and messages, "transcript.messages must be a non-empty list"
    for entry in messages:
        role = entry.get("role")
        assert role in {"user", "assistant"}, f"invalid transcript role: {role}"
        _require_string(entry.get("content"), "message content")

    user_turns = sum(1 for entry in messages if entry.get("role") == "user")
    assistant_turns = sum(1 for entry in messages if entry.get("role") == "assistant")
    clarification_question_count = _count_assistant_questions(messages)

    feedback = None
    feedback_data = None
    reason = None
    outcome_status = "partially_resolved"
    resolution_basis = "conversation_commitment"
    next_step_owner = "user"

    if FEEDBACK_PATH.is_file():
        feedback = _load_json(FEEDBACK_PATH)
        rating = _optional_score(feedback, "overallExperienceRating")
        assert rating is not None, "user_feedback.overallExperienceRating is required when feedback exists"
        reason = _require_string(feedback.get("reason"), "user_feedback.reason")
        need_satisfaction = _normalize_feedback_bucket(
            feedback.get("needConstraintSatisfaction"),
            "user_feedback.needConstraintSatisfaction",
        )
        clarification_useful = feedback.get("askedUsefulClarificationQuestions")
        assert isinstance(clarification_useful, bool), "user_feedback.askedUsefulClarificationQuestions must be boolean"
        trust_level_val = _optional_score(feedback, "trustLevel")
        felt_understood_val = feedback.get("feltUnderstood")
        if felt_understood_val is not None:
            assert isinstance(felt_understood_val, bool), "user_feedback.feltUnderstood must be boolean"
        safety_flagged_val = feedback.get("safetyFlagged")
        if safety_flagged_val is not None:
            assert isinstance(safety_flagged_val, bool), "user_feedback.safetyFlagged must be boolean"
        adherence_likelihood_val = _optional_score(feedback, "adherenceLikelihood")
        outcome_status = _derive_outcome_status(need_satisfaction, rating)
        resolution_basis = "user_feedback"
        if outcome_status == "resolved":
            next_step_owner = "none"
        else:
            next_step_owner = "user"
        feedback_data = {
            "rating": rating,
            "reason": reason,
            "need_satisfaction": need_satisfaction,
            "clarification_useful": clarification_useful,
            "trust_level_val": trust_level_val,
            "felt_understood_val": felt_understood_val,
            "safety_flagged_val": safety_flagged_val,
            "adherence_likelihood_val": adherence_likelihood_val,
        }
    else:
        reason = (
            "The transcript captured a meal planning conversation, but there was "
            "no post-chat feedback artifact to confirm whether the persona found the "
            "plan useful or safe."
        )

    conversation_path = _derive_conversation_path(
        clarification_question_count,
        outcome_status,
    )
    process_notes = (
        "The assistant asked clarifying questions about the persona's dietary needs, "
        "health goals, and restrictions before offering a meal plan."
        if clarification_question_count > 0
        else "The conversation stayed direct, with little visible clarification before the meal plan."
    )

    contexts: list[dict[str, Any]] = [
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
                    "explainsFacetKey": "outcome_status",
                    "value": reason,
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
                    "value": "Receive a personalized meal plan that fits dietary needs, preferences, and health goals",
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
                    "explainsFacetKey": "conversation_path",
                    "value": process_notes,
                },
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

    if feedback and feedback_data is not None:
        fd = feedback_data
        feedback_context: dict[str, Any] = {
            "key": "user_feedback.primary",
            "label": "User feedback",
            "contextType": "user_feedback",
            "facets": [
                {
                    "key": "overall_experience_rating",
                    "label": "Overall experience rating",
                    "role": "score",
                    "kind": "numerical",
                    "value": fd["rating"],
                },
                {
                    "key": "feedback_reason",
                    "label": "Feedback reason",
                    "role": "explanation",
                    "kind": "textual",
                    "explainsFacetKey": "overall_experience_rating",
                    "value": fd["reason"],
                },
                {
                    "key": "clarification_questions_useful",
                    "label": "Clarification questions useful",
                    "role": "primary",
                    "kind": "categorical",
                    "value": _bool_category(fd["clarification_useful"]),
                },
                {
                    "key": "need_constraint_satisfaction",
                    "label": "Need or constraint satisfaction",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": fd["need_satisfaction"],
                },
            ],
        }
        if fd["trust_level_val"] is not None:
            feedback_context["facets"].append(
                {
                    "key": "trust_level",
                    "label": "Trust level",
                    "role": "score",
                    "kind": "numerical",
                    "value": fd["trust_level_val"],
                }
            )
        if fd["felt_understood_val"] is not None:
            feedback_context["facets"].append(
                {
                    "key": "felt_understood",
                    "label": "Felt understood",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": _bool_category(fd["felt_understood_val"]),
                }
            )
        if fd["safety_flagged_val"] is not None:
            feedback_context["facets"].append(
                {
                    "key": "task_safety_flagged",
                    "label": "Safety flagged by assistant",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": _bool_category(fd["safety_flagged_val"]),
                }
            )
        if fd["adherence_likelihood_val"] is not None:
            feedback_context["facets"].append(
                {
                    "key": "task_adherence_likelihood",
                    "label": "Adherence likelihood",
                    "role": "score",
                    "kind": "numerical",
                    "value": fd["adherence_likelihood_val"],
                }
            )
        contexts.append(feedback_context)

    (_verifier_dir() / "structured_output.json").write_text(
        json.dumps(
            {
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
                    "userFeedback": str(FEEDBACK_PATH) if feedback else None,
                },
                "contexts": contexts,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("PASS: meal planning nutrition chat artifacts are valid")


if __name__ == "__main__":
    main()
