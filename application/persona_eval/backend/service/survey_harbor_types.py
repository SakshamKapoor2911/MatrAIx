"""Harbor example-survey task types for PersonaEval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SurveyHarborTask:
    id: str
    title: str
    description: str
    task_path: str
    instrument_id: str
    profile_markdown: str = ""
    survey_kind: str = "contributing"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "taskPath": self.task_path,
            "instrumentId": self.instrument_id,
            "profileMarkdown": self.profile_markdown or None,
            "surveyKind": self.survey_kind,
        }
