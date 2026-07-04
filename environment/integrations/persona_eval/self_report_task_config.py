"""Load task-owned self-report schema metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from environment.integrations.persona_eval.task_content_bundle import (
    content_dir_for_task_path,
    input_dir_for_task_path,
)
from persona_eval.user_sim.self_report_contract import (
    DEFAULT_CHATBOT_SELF_REPORT_SCHEMA,
    SelfReportField,
    SelfReportSchema,
)


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_schema_yaml(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("self_report_schema.yaml must be a mapping")
    return dict(payload)


def _load_schema_from_payload(payload: dict[str, Any]) -> SelfReportSchema:
    fields = []
    for index, entry in enumerate(payload.get("fields") or []):
        item = _as_mapping(entry)
        key = _as_string(item.get("key"))
        prompt = _as_string(item.get("prompt"))
        if not key or not prompt:
            raise ValueError(
                "self_report_schema.fields[{}] requires key and prompt".format(index)
            )
        raw_choices = item.get("choices") or []
        choices = tuple(
            str(choice).strip()
            for choice in raw_choices
            if str(choice).strip()
        )
        fields.append(
            SelfReportField(
                key=key,
                prompt=prompt,
                kind=_as_string(item.get("kind")) or "string",
                required=_as_bool(item.get("required"), True),
                minimum=_as_optional_int(item.get("minimum")),
                maximum=_as_optional_int(item.get("maximum")),
                choices=choices,
            )
        )
    return SelfReportSchema(
        artifact_name=_as_string(payload.get("artifactName")) or "user_feedback.json",
        instructions=_as_string(payload.get("instructions")),
        fields=tuple(fields),
    )


def load_self_report_schema_for_task_path(
    task_path: str,
    *,
    repo_root: Path,
    fallback_to_default: bool = True,
) -> SelfReportSchema | None:
    input_dir = input_dir_for_task_path(task_path, repo_root=repo_root)
    content_dir = content_dir_for_task_path(task_path, repo_root=repo_root)
    candidates: list[Path] = []
    if input_dir is not None:
        candidates.append(input_dir / "self_report_schema.yaml")
    if content_dir is not None:
        candidates.append(content_dir / "self_report_schema.yaml")
    for candidate in candidates:
        payload = _read_schema_yaml(candidate)
        if payload is not None:
            return _load_schema_from_payload(payload)
    if fallback_to_default:
        return DEFAULT_CHATBOT_SELF_REPORT_SCHEMA
    return None
