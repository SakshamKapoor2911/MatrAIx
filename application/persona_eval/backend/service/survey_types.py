"""Survey schema types used by PersonaEval application helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from persona_eval.types import DEFAULT_PERSONA_MODEL, Persona
except ModuleNotFoundError:  # repo-root imports use the package-qualified path
    from application.persona_eval.persona_eval.types import DEFAULT_PERSONA_MODEL, Persona

QUESTION_TYPES = {"likert", "single_choice", "multi_choice", "free_text"}


@dataclass
class SurveyQuestion:
    """One question in a persona survey instrument."""

    id: str
    prompt: str
    type: str = "likert"
    options: list[str] = field(default_factory=list)
    min_value: int | None = None
    max_value: int | None = None
    construct: str = ""
    required: bool = True

    def __post_init__(self) -> None:
        if self.type not in QUESTION_TYPES:
            raise ValueError(
                "question type must be one of {}".format(sorted(QUESTION_TYPES))
            )
        if self.type == "likert":
            if self.min_value is None:
                self.min_value = 1
            else:
                self.min_value = int(self.min_value)
            if self.max_value is None:
                self.max_value = 5
            else:
                self.max_value = int(self.max_value)
            if self.min_value >= self.max_value:
                raise ValueError("likert min_value must be less than max_value")
        if self.type in {"single_choice", "multi_choice"} and not self.options:
            raise ValueError("{} questions require options".format(self.type))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SurveyQuestion":
        return cls(
            id=str(data["id"]),
            prompt=str(data["prompt"]),
            type=str(data.get("type", "likert")),
            options=[str(option) for option in data.get("options", [])],
            min_value=data.get("minValue", data.get("min_value")),
            max_value=data.get("maxValue", data.get("max_value")),
            construct=str(data.get("construct", "")),
            required=bool(data.get("required", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "type": self.type,
            "options": list(self.options),
            "minValue": self.min_value,
            "maxValue": self.max_value,
            "construct": self.construct,
            "required": self.required,
        }


@dataclass
class SurveyInstrument:
    """A named set of survey questions."""

    id: str
    title: str
    description: str = ""
    questions: list[SurveyQuestion] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SurveyInstrument":
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data.get("description", "")),
            questions=[SurveyQuestion.from_dict(q) for q in data.get("questions", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "questions": [question.to_dict() for question in self.questions],
        }


@dataclass
class SurveyEvalConfig:
    """Runtime config for local survey evaluation."""

    persona_model: str = DEFAULT_PERSONA_MODEL
    mode: str = "local_persona_survey"
    require_rationale: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "personaModel": self.persona_model,
            "mode": self.mode,
            "requireRationale": self.require_rationale,
        }


@dataclass
class SurveyAnswer:
    """One simulated persona answer to a survey question."""

    question_id: str
    value: Any
    rationale: str = ""
    confidence: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SurveyAnswer":
        question_id = str(data.get("questionId", data.get("question_id", ""))).strip()
        if not question_id:
            raise ValueError("answer.questionId is required")
        confidence = data.get("confidence")
        if confidence is not None:
            try:
                confidence = max(0.0, min(1.0, float(confidence)))
            except (TypeError, ValueError):
                confidence = None
        return cls(
            question_id=question_id,
            value=data.get("value"),
            rationale=str(data.get("rationale", "")),
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "questionId": self.question_id,
            "value": self.value,
            "rationale": self.rationale,
            "confidence": self.confidence,
        }


@dataclass
class TrajectoryEvent:
    """One event in a survey/web evaluation trajectory."""

    timestamp: str
    actor: str
    action: str
    context: dict[str, Any] = field(default_factory=dict)
    outcome: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "context": dict(self.context),
            "outcome": dict(self.outcome),
        }


@dataclass
class SurveyMetrics:
    """Aggregate survey completion metrics."""

    num_questions: int
    num_answered: int
    mean_likert: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "numQuestions": self.num_questions,
            "numAnswered": self.num_answered,
            "meanLikert": self.mean_likert,
        }


@dataclass
class SurveyEvalResult:
    """Full local survey evaluation result."""

    config: SurveyEvalConfig
    persona: Persona
    instrument: SurveyInstrument
    answers: list[SurveyAnswer]
    trajectory: list[TrajectoryEvent]
    metrics: SurveyMetrics
    created_at: str
    prompts: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "persona": self.persona.to_dict(),
            "instrument": self.instrument.to_dict(),
            "trajectory": [event.to_dict() for event in self.trajectory],
            "answers": [answer.to_dict() for answer in self.answers],
            "metrics": self.metrics.to_dict(),
            "createdAt": self.created_at,
            "prompts": dict(self.prompts),
        }
