"""Post-conversation persona self-report (separate from objective verifier scoring)."""

from __future__ import annotations

from typing import Any, Dict, List

from persona_eval.openai_client import coerce_json
from persona_eval.types import Persona, PersonaEvalTurn, Questionnaire

_FEEDBACK_USER = """You have now FINISHED using the application chatbot. Here is the full conversation \
(you = user, agent = application chatbot):
{transcript}

Final grounded items (id — title): {final_items}

Reflecting honestly from your own point of view as this persona, fill out this \
post-use questionnaire as strict JSON (no prose outside the JSON):
{{"constraintSatisfaction": <1-5 how well your product-need/constraints were met>,
  "constraintRationale": "<short reason>",
  "preferenceSatisfaction": <1-5 how well your personal preferences were met>,
  "preferenceRationale": "<short reason>",
  "overallRating": <1-10 overall experience, in your own voice>,
  "ratingReason": "<short reason for the rating, your voice>",
  "askedUsefulClarifyingQuestions": <true|false: did the agent ask useful clarifying questions?>,
  "clarifyingNotes": "<which questions, or why not>"}}"""


def _clamp(value: Any, low: int, high: int, default: int) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _format_transcript_turns(transcript: List[PersonaEvalTurn]) -> str:
    lines: List[str] = []
    for turn in transcript:
        lines.append("you: {}".format(turn.user_message))
        lines.append("agent: {}".format(turn.assistant_message))
        if turn.recommended_items:
            lines.append(
                "  [grounded: {}]".format(
                    "; ".join(
                        "{}—{}".format(item.get("id"), item.get("title") or "?")
                        for item in turn.recommended_items
                    )
                )
            )
    return "\n".join(lines) if lines else "(empty)"


class SelfReportClient:
    def complete_json(self, system: str, user: str) -> Dict[str, Any]: ...


def final_self_report(
    client: SelfReportClient,
    *,
    system_prompt: str,
    persona: Persona,
    transcript: List[PersonaEvalTurn],
    final_recommended_items: List[Dict[str, Any]],
) -> Questionnaire:
    del persona
    final_items = "; ".join(
        "{} — {}".format(item.get("id"), item.get("title") or "?")
        for item in final_recommended_items
    ) or "(none)"
    user = _FEEDBACK_USER.format(
        transcript=_format_transcript_turns(transcript),
        final_items=final_items,
    )
    if hasattr(client, "complete_json"):
        out = client.complete_json(system_prompt, user)
    else:
        out = coerce_json(str(client))
    return Questionnaire(
        constraint_satisfaction=_clamp(out.get("constraintSatisfaction"), 1, 5, 3),
        constraint_rationale=str(out.get("constraintRationale", "")),
        preference_satisfaction=_clamp(out.get("preferenceSatisfaction"), 1, 5, 3),
        preference_rationale=str(out.get("preferenceRationale", "")),
        overall_rating=_clamp(out.get("overallRating"), 1, 10, 5),
        rating_reason=str(out.get("ratingReason", "")),
        asked_useful_clarifying_questions=bool(out.get("askedUsefulClarifyingQuestions", False)),
        clarifying_notes=str(out.get("clarifyingNotes", "")),
    )
