from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from persona_eval.types import DEFAULT_PERSONA_MODEL, Persona


@dataclass(frozen=True)
class WebEvalTask:
    id: str
    title: str
    site_name: str
    site_url: str
    task_path: Path
    description: str
    output_artifact: str = "ecommerce_interaction.json"
    submission_profile: str = "persona_eval_final_json"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "siteName": self.site_name,
            "siteUrl": self.site_url,
            "description": self.description,
            "outputArtifact": self.output_artifact,
            "submissionProfile": self.submission_profile,
        }


@dataclass(frozen=True)
class WebEvalConfig:
    persona_model: str = DEFAULT_PERSONA_MODEL
    mode: str = "local_persona_web"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "personaModel": self.persona_model,
            "mode": self.mode,
        }


@dataclass(frozen=True)
class WebEvalResultArtifact:
    selected_product_id: str
    selected_product_name: str
    need_satisfaction: int
    ease_of_use: int
    information_quality: int
    overall_quality: int
    reason: str
    created_at: str
    valid: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any], *, created_at: str) -> "WebEvalResultArtifact":
        selected_product_id = str(
            data.get("selected_product_id", data.get("selectedProductId", ""))
        ).strip()
        selected_product_name = str(
            data.get("selected_product_name", data.get("selectedProductName", ""))
        ).strip()
        if not selected_product_id:
            selected_product_id = "local:selected"
        if not selected_product_name:
            selected_product_name = "Selected option"

        return cls(
            selected_product_id=selected_product_id,
            selected_product_name=selected_product_name,
            need_satisfaction=_score(data, "need_satisfaction", "needSatisfaction", 5),
            ease_of_use=_score(data, "ease_of_use", "easeOfUse", 5),
            information_quality=_score(
                data, "information_quality", "informationQuality", 5
            ),
            overall_quality=_score(data, "overall_quality", "overallQuality", 5),
            reason=str(data.get("reason") or "The persona completed the task and provided a short experience report."),
            created_at=created_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selectedProductId": self.selected_product_id,
            "selectedProductName": self.selected_product_name,
            "needSatisfaction": self.need_satisfaction,
            "easeOfUse": self.ease_of_use,
            "informationQuality": self.information_quality,
            "overallQuality": self.overall_quality,
            "overallExperienceRating": self.overall_quality,
            "reason": self.reason,
            "createdAt": self.created_at,
            "valid": self.valid,
        }


@dataclass(frozen=True)
class WebTrace:
    events: List[Dict[str, Any]]
    raw: Dict[str, Any]
    screenshots_dir: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [dict(event) for event in self.events],
            "raw": dict(self.raw),
        }


@dataclass(frozen=True)
class WebEvalResult:
    config: WebEvalConfig
    persona: Persona
    task: WebEvalTask
    web_result: WebEvalResultArtifact
    trace: WebTrace
    created_at: str
    prompts: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "persona": {
                "id": self.persona.id,
                "name": self.persona.name,
                "context": self.persona.context,
            },
            "task": self.task.to_dict(),
            "webResult": self.web_result.to_dict(),
            "trace": self.trace.to_dict(),
            "createdAt": self.created_at,
            "prompts": dict(self.prompts),
        }


def _score(data: Dict[str, Any], snake: str, camel: str, default: int) -> int:
    value = data.get(snake, data.get(camel, default))
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = default
    return max(1, min(10, score))
