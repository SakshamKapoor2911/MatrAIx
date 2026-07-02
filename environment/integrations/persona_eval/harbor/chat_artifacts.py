"""Pure helpers for Harbor chat task artifacts (no Harbor runtime imports)."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from persona_eval.types import PersonaEvalConfig, PersonaEvalResult


def harbor_chat_config_from_env() -> PersonaEvalConfig:
    """Build eval config from ``MATRIX_CHATBOT_*`` environment variables."""
    domain = os.environ.get("MATRIX_CHATBOT_DOMAIN", "movie").strip() or "movie"
    application_id = os.environ.get("MATRIX_CHATBOT_APPLICATION_ID", "recai").strip() or "recai"
    application_context = (
        os.environ.get("MATRIX_CHATBOT_APPLICATION_CONTEXT", "").strip() or domain
    )
    max_turns_raw = os.environ.get("MATRIX_CHATBOT_MAX_TURNS", "8")
    try:
        max_turns = max(3, int(max_turns_raw))
    except ValueError:
        max_turns = 8
    goal_context_id = (
        os.environ.get("MATRIX_CHATBOT_GOAL_CONTEXT_ID", "scenario_default").strip()
        or "scenario_default"
    )
    persona_model = (
        os.environ.get("MATRIX_CHATBOT_PERSONA_MODEL", "").strip()
        or os.environ.get("MATRIX_PERSONA_MODEL", "").strip()
        or "anthropic/claude-haiku-4-5"
    )
    engine = os.environ.get("MATRIX_CHATBOT_ENGINE", "gpt-4o-mini").strip() or "gpt-4o-mini"
    return PersonaEvalConfig(
        domain=domain,
        application_id=application_id,
        application_context=application_context,
        engine=engine,
        persona_model=persona_model,
        max_turns=max_turns,
        goal_context_id=goal_context_id,
    )


def default_chat_api_url(application_id: str) -> str:
    if application_id == "finance_openbb":
        return "http://finance-chatbot:8000"
    if application_id == "medical_assistant":
        return "http://medical-chatbot:8000"
    return "http://rec-agent-api:8000"


def chat_api_url_from_env(application_id: str) -> str:
    return (
        os.environ.get("MATRIX_CHATBOT_API_URL", "").strip()
        or default_chat_api_url(application_id)
    )


def _rating_label(score: int) -> str:
    if score >= 4:
        return "yes"
    if score >= 3:
        return "partially"
    return "no"


def harbor_artifacts_from_result(
    result: PersonaEvalResult,
    *,
    session_id: str,
    domain: str,
) -> Dict[str, Dict[str, Any]]:
    """Map a PersonaEval result into Harbor chat task artifact payloads."""
    messages: List[Dict[str, str]] = []
    for turn in result.transcript:
        messages.append({"role": "user", "content": turn.user_message})
        messages.append({"role": "assistant", "content": turn.assistant_message})

    final_items: List[Dict[str, str]] = []
    for turn in reversed(result.transcript):
        if turn.recommended_items:
            final_items = [
                {
                    "itemId": str(item.get("id") or item.get("itemId") or ""),
                    "title": str(item.get("title") or ""),
                }
                for item in turn.recommended_items
                if str(item.get("id") or item.get("itemId") or "").strip()
            ]
            break

    transcript_payload = {
        "sessionId": session_id,
        "domain": domain,
        "messages": messages,
        "turns": [turn.to_dict() for turn in result.transcript],
    }
    recommendation_payload = {
        "sessionId": session_id,
        "domain": domain,
        "recommendedItems": final_items,
        "turnsToRecommendation": result.metric_scores.turns_to_recommendation
        or len(result.transcript),
    }
    questionnaire = result.questionnaire
    feedback_payload = {
        "productNeedConstraintSatisfaction": _rating_label(questionnaire.constraint_satisfaction),
        "personalPreferenceSatisfaction": _rating_label(questionnaire.preference_satisfaction),
        "overallExperienceRating": questionnaire.overall_rating,
        "reason": questionnaire.rating_reason or questionnaire.constraint_rationale,
        "askedUsefulClarificationQuestions": questionnaire.asked_useful_clarifying_questions,
    }
    return {
        "transcript.json": transcript_payload,
        "recommendation_result.json": recommendation_payload,
        "user_feedback.json": feedback_payload,
    }
