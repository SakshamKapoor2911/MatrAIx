"""Normalize task-owned self-report artifacts into the shared UI questionnaire."""

from __future__ import annotations

from typing import Any, Dict

from persona_eval.types import Questionnaire
from persona_eval.user_sim.self_report_contract import (
    DEFAULT_CHATBOT_SELF_REPORT_SCHEMA,
    coerce_self_report_payload,
    field_keys,
    merge_extra_fields,
)


def _coerce_score(value: Any, default: int) -> int:
    text = str(value or "").strip().lower()
    if text == "yes":
        return 5
    if text == "partially":
        return 3
    if text == "no":
        return 1
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(5, number))


def _coerce_overall(value: Any, default: int = 5) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(10, number))


def questionnaire_from_feedback(feedback: Dict[str, Any]) -> Questionnaire:
    normalized_feedback = coerce_self_report_payload(
        feedback,
        DEFAULT_CHATBOT_SELF_REPORT_SCHEMA,
    )
    extra_feedback = merge_extra_fields(
        feedback,
        exclude=set(field_keys(DEFAULT_CHATBOT_SELF_REPORT_SCHEMA)),
    )
    artifact_payload = {
        **normalized_feedback,
        **extra_feedback,
    }
    reason = str(normalized_feedback.get("reason") or "")
    clarifying_notes = str(normalized_feedback.get("clarifyingNotes") or reason)
    return Questionnaire(
        constraint_satisfaction=_coerce_score(
            normalized_feedback.get("needConstraintSatisfaction"), 3
        ),
        constraint_rationale=reason,
        preference_satisfaction=_coerce_score(
            normalized_feedback.get(
                "personalPreferenceSatisfaction",
                normalized_feedback.get("needConstraintSatisfaction"),
            ),
            3,
        ),
        preference_rationale=reason,
        overall_rating=_coerce_overall(
            normalized_feedback.get("overallExperienceRating")
        ),
        rating_reason=reason,
        asked_useful_clarifying_questions=bool(
            normalized_feedback.get("askedUsefulClarificationQuestions", False)
        ),
        clarifying_notes=clarifying_notes,
        extra_fields=extra_feedback,
        artifact_payload=artifact_payload,
    )
