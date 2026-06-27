"""Survey schema types used by PersonaEval application helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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

