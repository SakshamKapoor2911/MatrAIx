from __future__ import annotations

from typing import Any, Dict, List, Tuple

from persona_eval.goal_contexts import GoalContext
from persona_eval.types import Persona, Questionnaire, SimulatorTurn, PersonaEvalTurn

_KICKOFF_USER = "Write your FIRST message to the application chatbot to start the conversation. " \
    'Respond as strict JSON: {"message": "<your opening message>"}.'

_RESPOND_USER = """Conversation so far (you = user, agent = application chatbot):
{transcript}

The agent just said:
\"\"\"{assistant}\"\"\"

Grounded items it is currently surfacing (id — title): {items}

Decide your next move IN CHARACTER. Respond as strict JSON:
{{"message": "<your next message to the agent>",
  "decision": "continue" | "satisfied" | "give_up",
  "note": "<one short private note on why>"}}
- "satisfied": the application response meets your need — you're done.
- "give_up": the agent isn't helping and you'd stop in real life.
- "continue": keep the conversation going (ask, refine, or answer).
If the agent's reply is an error or empty (e.g. "Something went wrong, please retry." or no real content), don't ignore it or change the subject: briefly acknowledge the hiccup and rephrase or retry your last request in character (usually "continue")."""

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

# Domain shown in the system prompt; the persona is domain-free, the run carries the domain.
_DEFAULT_DOMAIN = "product"


def _clamp(value: Any, low: int, high: int, default: int) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, n))


def _persona_context(persona: Persona) -> str:
    """Curated personas carry a rich free-text `context`; fixtures compose one."""
    if persona.context:
        return persona.context
    parts = [
        "Name: {}".format(persona.name),
        "Who you are: {}".format(persona.summary or "(a typical user)"),
        "What you want (preferences): {}".format(", ".join(persona.preferences) or "(open)"),
        "What you dislike: {}".format(", ".join(persona.dislikes) or "(none stated)"),
        "Your constraints: {}".format(", ".join(persona.constraints) or "(flexible)"),
        "Your goal: {}".format(persona.goal or "(find something suitable)"),
        "How you talk: {}".format(persona.communication_style or "natural and conversational"),
    ]
    return "\n".join(parts)


def _format_transcript_pairs(pairs: List[Tuple[str, str]]) -> str:
    if not pairs:
        return "(no messages yet)"
    return "\n".join("you: {}\nagent: {}".format(u, a) for u, a in pairs)


def _format_items(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "(none yet)"
    return "; ".join("{} — {}".format(i.get("id"), i.get("title") or "?") for i in items)


def _format_transcript_turns(transcript: List[PersonaEvalTurn]) -> str:
    lines: List[str] = []
    for t in transcript:
        lines.append("you: {}".format(t.user_message))
        lines.append("agent: {}".format(t.assistant_message))
        if t.recommended_items:
            lines.append("  [grounded: {}]".format(
                "; ".join("{}—{}".format(i.get("id"), i.get("title") or "?")
                          for i in t.recommended_items)))
    return "\n".join(lines) if lines else "(empty)"


class UserSimulator:
    def __init__(self, client: Any, goal_context: GoalContext, domain: str = _DEFAULT_DOMAIN) -> None:
        self._client = client
        self._goal_context = goal_context
        self._domain = domain

    def _system(self, persona: Persona, sut_description: str) -> str:
        return self._goal_context.template.format(
            domain=self._domain,
            sut_description=sut_description,
            persona_context=_persona_context(persona),
        )

    def kickoff(self, persona: Persona, sut_description: str) -> str:
        out = self._client.complete_json(self._system(persona, sut_description), _KICKOFF_USER)
        message = str(out.get("message", "")).strip()
        return message or "Hi, I need help finding a suitable answer."

    def respond(self, persona: Persona, sut_description: str,
                transcript_pairs: List[Tuple[str, str]], last_assistant_message: str,
                recommended_items: List[Dict[str, Any]]) -> SimulatorTurn:
        user = _RESPOND_USER.format(
            transcript=_format_transcript_pairs(transcript_pairs),
            assistant=last_assistant_message,
            items=_format_items(recommended_items),
        )
        out = self._client.complete_json(self._system(persona, sut_description), user)
        message = str(out.get("message", "")).strip() or "Could you tell me more?"
        decision = out.get("decision", "continue")
        if decision not in {"continue", "satisfied", "give_up"}:
            decision = "continue"
        return SimulatorTurn(message=message, decision=decision, note=str(out.get("note", "")))

    def final_feedback(self, persona: Persona, sut_description: str,
                       transcript: List[PersonaEvalTurn],
                       final_recommended_items: List[Dict[str, Any]]) -> Questionnaire:
        final_items = "; ".join(
            "{} — {}".format(i.get("id"), i.get("title") or "?") for i in final_recommended_items
        ) or "(none)"
        user = _FEEDBACK_USER.format(
            transcript=_format_transcript_turns(transcript),
            final_items=final_items,
        )
        out = self._client.complete_json(self._system(persona, sut_description), user)
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
