from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_DECISIONS = {"continue", "satisfied", "give_up"}
DEFAULT_PERSONA_MODEL = "anthropic/claude-haiku-4-5"


@dataclass
class Persona:
    id: str
    name: str
    summary: str = ""
    context: str = ""
    source: str = ""
    preferences: List[str] = field(default_factory=list)
    dislikes: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    goal: str = ""
    communication_style: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "context": self.context,
            "source": self.source,
            "preferences": list(self.preferences),
            "dislikes": list(self.dislikes),
            "constraints": list(self.constraints),
            "goal": self.goal,
            "communicationStyle": self.communication_style,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Persona":
        # Back-compat: tolerate an old "domain" key by ignoring it.
        return cls(
            id=d["id"],
            name=d["name"],
            summary=d.get("summary", ""),
            context=d.get("context", ""),
            source=d.get("source", ""),
            preferences=list(d.get("preferences", [])),
            dislikes=list(d.get("dislikes", [])),
            constraints=list(d.get("constraints", [])),
            goal=d.get("goal", ""),
            communication_style=d.get(
                "communicationStyle", d.get("communication_style", "")
            ),
        )


@dataclass
class PersonaEvalConfig:
    domain: str
    application_id: str = "recai"
    application_context: str = ""
    engine: str = "gpt-4o-mini"
    persona_model: str = DEFAULT_PERSONA_MODEL
    ranker_mode: str = "native"
    resource_mode: str = "recai_resources"
    max_turns: int = 8
    goal_context_id: str = "scenario_default"

    def to_dict(self) -> Dict[str, Any]:
        application_context = self.application_context or self.domain
        return {
            "applicationId": self.application_id,
            "applicationContext": application_context,
            "domain": self.domain,
            "engine": self.engine,
            "personaModel": self.persona_model,
            "rankerMode": self.ranker_mode,
            "resourceMode": self.resource_mode,
            "maxTurns": self.max_turns,
            "goalContextId": self.goal_context_id,
        }


@dataclass
class SimulatorTurn:
    message: str
    decision: str
    note: str = ""

    def __post_init__(self) -> None:
        if self.decision not in _DECISIONS:
            raise ValueError("decision must be one of {}".format(sorted(_DECISIONS)))

    def to_dict(self) -> Dict[str, Any]:
        return {"message": self.message, "decision": self.decision, "note": self.note}


@dataclass
class PersonaEvalTurn:
    turn_index: int
    user_message: str
    assistant_message: str
    recommended_items: List[Dict[str, Any]] = field(default_factory=list)
    decision: str = "continue"
    duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turnIndex": self.turn_index,
            "userMessage": self.user_message,
            "assistantMessage": self.assistant_message,
            "recommendedItems": [dict(i) for i in self.recommended_items],
            "decision": self.decision,
            "durationSeconds": self.duration_seconds,
        }


@dataclass
class Questionnaire:
    constraint_satisfaction: int
    constraint_rationale: str
    preference_satisfaction: int
    preference_rationale: str
    overall_rating: int
    rating_reason: str
    asked_useful_clarifying_questions: bool
    clarifying_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraintSatisfaction": self.constraint_satisfaction,
            "constraintRationale": self.constraint_rationale,
            "preferenceSatisfaction": self.preference_satisfaction,
            "preferenceRationale": self.preference_rationale,
            "overallRating": self.overall_rating,
            "ratingReason": self.rating_reason,
            "askedUsefulClarifyingQuestions": self.asked_useful_clarifying_questions,
            "clarifyingNotes": self.clarifying_notes,
        }


@dataclass
class MetricScores:
    turns_to_recommendation: Optional[int]
    num_turns: int
    recommended_item_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turnsToRecommendation": self.turns_to_recommendation,
            "numTurns": self.num_turns,
            "recommendedItemCount": self.recommended_item_count,
        }


@dataclass
class PersonaEvalResult:
    config: PersonaEvalConfig
    persona: Persona
    sut_description: str
    transcript: List[PersonaEvalTurn]
    questionnaire: Questionnaire
    metric_scores: MetricScores
    created_at: str
    prompts: Dict[str, str] = field(default_factory=dict)

    def _final_ids(self) -> List[str]:
        for turn in reversed(self.transcript):
            if turn.recommended_items:
                return [str(i["id"]) for i in turn.recommended_items]
        return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "persona": self.persona.to_dict(),
            "sutDescription": self.sut_description,
            "transcript": [t.to_dict() for t in self.transcript],
            "recommendedItemIds": {
                "perTurn": [
                    [str(i["id"]) for i in t.recommended_items] for t in self.transcript
                ],
                "final": self._final_ids(),
            },
            "questionnaire": self.questionnaire.to_dict(),
            "metricScores": self.metric_scores.to_dict(),
            "createdAt": self.created_at,
            "prompts": dict(self.prompts),
        }
