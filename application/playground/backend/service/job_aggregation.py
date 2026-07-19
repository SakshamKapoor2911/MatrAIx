"""Structured trial evaluation artifacts and job-level aggregation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tomllib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

TRIAL_EVAL_FILENAME = "structured_output.json"
JOB_AGGREGATION_FILENAME = "aggregation.json"
REPORTING_STATUS_FILENAME = "reporting_status.json"
SCHEMA_VERSION = "1.0"
FIELD_KINDS = frozenset({"numerical", "categorical", "textual"})
SUMMARY_GROUP_BY_MODES = frozenset({"none", "categorical", "numeric_band"})
JUDGE_GROUP_BY_MODES = SUMMARY_GROUP_BY_MODES
REPORTING_LLM_ENABLE_ENV = "PLAYGROUND_REPORTING_ENABLE_LLM"
REPORTING_LLM_MODEL_ENV = "PLAYGROUND_REPORTING_LLM_MODEL"
DEFAULT_REPORTING_LLM_MODEL = "openai/gpt-4o-mini"
# Discrete selected-item titles (course/book/product names). Always exact-count;
# never TF-IDF theme-cluster even when verifiers historically tagged them textual.
DISCRETE_SUBJECT_LABEL_FACET_KEYS = frozenset(
    {
        "decision_subject_label",
        "artifact_subject_label",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def trial_evaluation_artifact_path(trial_dir: Path) -> Path:
    return trial_dir / "verifier" / TRIAL_EVAL_FILENAME


def job_aggregation_artifact_path(job_dir: Path) -> Path:
    return job_dir / JOB_AGGREGATION_FILENAME


def reporting_status_artifact_path(job_dir: Path) -> Path:
    return job_dir / REPORTING_STATUS_FILENAME


def read_trial_evaluation_artifact(trial_dir: Path) -> dict[str, Any] | None:
    path = trial_evaluation_artifact_path(trial_dir)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def read_job_aggregation_artifact(job_dir: Path) -> dict[str, Any] | None:
    path = job_aggregation_artifact_path(job_dir)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def read_reporting_status_artifact(job_dir: Path) -> dict[str, Any] | None:
    path = reporting_status_artifact_path(job_dir)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def write_job_aggregation(job_dir: Path, payload: dict[str, Any]) -> None:
    path = job_aggregation_artifact_path(job_dir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_reporting_status_artifact(job_dir: Path, payload: dict[str, Any]) -> None:
    path = reporting_status_artifact_path(job_dir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_job_aggregation(
    job_dir: Path,
    *,
    repo_root: Path | None = None,
    llm_client: Any | None = None,
    enable_llm: bool | None = None,
) -> dict[str, Any] | None:
    if not job_dir.is_dir():
        return None

    previous_payload = read_job_aggregation_artifact(job_dir)
    trial_dirs = sorted(
        [
            path
            for path in job_dir.iterdir()
            if path.is_dir() and path.name not in {"_inputs", "_generated"} and not path.name.startswith(".")
        ]
    )
    if not trial_dirs:
        return None

    field_meta: dict[str, dict[str, Any]] = {}
    field_values: dict[str, list[dict[str, Any]]] = {}
    context_meta: dict[str, dict[str, Any]] = {}
    context_facet_keys: dict[str, list[str]] = {}
    reporting_cache: dict[str, dict[str, Any]] = {}
    trial_count = len(trial_dirs)
    completed_trials = 0
    artifact_ready_trials = 0
    completed_without_artifact = 0
    pending_trials = 0

    for trial_dir in trial_dirs:
        completed = (trial_dir / "result.json").is_file()
        if completed:
            completed_trials += 1
        else:
            pending_trials += 1

        artifact = read_trial_evaluation_artifact(trial_dir)
        artifact = _enrich_trial_evaluation_with_user_feedback(
            artifact,
            trial_dir=trial_dir,
            repo_root=repo_root,
        )
        passed = False
        if isinstance(artifact, dict):
            presence = artifact.get("presenceCheck")
            if isinstance(presence, dict):
                passed = bool(presence.get("passed"))
            else:
                passed = True
        if not artifact or not passed:
            if completed:
                completed_without_artifact += 1
            continue

        artifact_ready_trials += 1
        persona_id = _trial_persona_id(trial_dir)
        reporting_config = _load_task_reporting_config(
            trial_dir=trial_dir,
            repo_root=repo_root,
            cache=reporting_cache,
        )
        for context in _iter_contexts(artifact):
            context_key = str(context.get("key") or "").strip()
            if not context_key:
                continue
            resolved_summary_directives = _resolve_summary_directives(
                context=context,
                reporting_config=reporting_config,
            )
            resolved_judge_directives = _resolve_judge_directives(
                context=context,
                reporting_config=reporting_config,
            )
            if context_key not in context_meta:
                context_meta[context_key] = {
                    "key": context_key,
                    "label": context.get("label") or context_key,
                    "contextType": context.get("contextType") or "grouped_fields",
                    "questionType": context.get("questionType"),
                    "scaleMin": context.get("scaleMin"),
                    "scaleMax": context.get("scaleMax"),
                    "scaleLabels": context.get("scaleLabels"),
                    "summaryDirectives": resolved_summary_directives,
                    "judgeDirectives": resolved_judge_directives,
                }
            else:
                if resolved_summary_directives and not context_meta[context_key].get("summaryDirectives"):
                    context_meta[context_key]["summaryDirectives"] = resolved_summary_directives
                if resolved_judge_directives and not context_meta[context_key].get("judgeDirectives"):
                    context_meta[context_key]["judgeDirectives"] = resolved_judge_directives
                if not context_meta[context_key].get("questionType") and context.get("questionType"):
                    context_meta[context_key]["questionType"] = context.get("questionType")
                if context_meta[context_key].get("scaleMin") is None and context.get("scaleMin") is not None:
                    context_meta[context_key]["scaleMin"] = context.get("scaleMin")
                if context_meta[context_key].get("scaleMax") is None and context.get("scaleMax") is not None:
                    context_meta[context_key]["scaleMax"] = context.get("scaleMax")
                if not context_meta[context_key].get("scaleLabels") and context.get("scaleLabels"):
                    context_meta[context_key]["scaleLabels"] = context.get("scaleLabels")
            for facet in _iter_facets(context):
                facet_key = str(facet.get("key") or "").strip()
                kind = str(facet.get("kind") or "").strip().lower()
                if not facet_key or kind not in FIELD_KINDS:
                    continue
                qualified_key = "{}.{}".format(context_key, facet_key)
                if qualified_key not in field_meta:
                    field_meta[qualified_key] = {
                        "key": qualified_key,
                        "facetKey": facet_key,
                        "contextKey": context_key,
                        "contextLabel": context_meta[context_key]["label"],
                        "label": facet.get("label") or facet_key,
                        "kind": kind,
                        "role": facet.get("role"),
                        "group": context_key,
                        "description": facet.get("description"),
                        "unit": facet.get("unit"),
                        "higherIsBetter": facet.get("higherIsBetter"),
                        "categories": facet.get("categories"),
                        "order": facet.get("order"),
                        "scaleMin": facet.get("scaleMin"),
                        "scaleMax": facet.get("scaleMax"),
                    }
                else:
                    existing = field_meta[qualified_key]
                    if not existing.get("categories") and facet.get("categories"):
                        existing["categories"] = facet.get("categories")
                    if existing.get("scaleMin") is None and facet.get("scaleMin") is not None:
                        existing["scaleMin"] = facet.get("scaleMin")
                    if existing.get("scaleMax") is None and facet.get("scaleMax") is not None:
                        existing["scaleMax"] = facet.get("scaleMax")
                    if not existing.get("role") and facet.get("role"):
                        existing["role"] = facet.get("role")
                    # Prefer primary over score/evidence when schema marks a hero rating.
                    if facet.get("role") == "primary":
                        existing["role"] = "primary"
                context_facet_keys.setdefault(context_key, [])
                if qualified_key not in context_facet_keys[context_key]:
                    context_facet_keys[context_key].append(qualified_key)
                field_values.setdefault(qualified_key, []).append(
                    {
                        "trialName": trial_dir.name,
                        "personaId": persona_id,
                        "value": facet.get("value"),
                    }
                )

    fields = [
        _aggregate_field(
            meta=field_meta[key],
            values=field_values.get(key, []),
            artifact_ready_trials=artifact_ready_trials,
        )
        for key in sorted(field_meta)
    ]
    _enrich_user_feedback_field_meta(field_meta)
    # Re-apply enrichment onto already-built field payloads.
    for field in fields:
        key = str(field.get("key") or "")
        enriched = field_meta.get(key)
        if not enriched:
            continue
        for attr in ("categories", "scaleMin", "scaleMax", "role"):
            if enriched.get(attr) is None:
                continue
            field[attr] = enriched.get(attr)
    fields_by_key = {field["key"]: field for field in fields}
    _enrich_survey_context_meta_from_questionnaire(
        context_meta,
        job_dir=job_dir,
        repo_root=repo_root,
    )
    contexts = [
        _aggregate_context(
            meta=context_meta[key],
            facet_keys=context_facet_keys.get(key, []),
            fields_by_key=fields_by_key,
            field_values=field_values,
        )
        for key in sorted(context_meta)
    ]
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "artifactType": "job_aggregation",
        "generatedAt": _utc_now(),
        "coverage": {
            "trialCount": trial_count,
            "completedTrials": completed_trials,
            "pendingTrials": pending_trials,
            "artifactReadyTrials": artifact_ready_trials,
            "completedWithoutArtifactTrials": completed_without_artifact,
        },
        "fields": fields,
        "contexts": contexts,
    }
    payload = _apply_llm_reporting(
        payload=payload,
        previous_payload=previous_payload,
        llm_client=llm_client,
        enable_llm=enable_llm,
    )
    payload["reporting"] = _build_reporting_view(payload)
    write_job_aggregation(job_dir, payload)
    return payload


def _enrich_trial_evaluation_with_user_feedback(
    artifact: dict[str, Any] | None,
    *,
    trial_dir: Path,
    repo_root: Path | None,
) -> dict[str, Any] | None:
    if not isinstance(artifact, dict):
        return artifact
    contexts = artifact.get("contexts")
    if isinstance(contexts, list):
        for context in contexts:
            if not isinstance(context, dict):
                continue
            if str(context.get("contextType") or "").strip() == "user_feedback":
                return artifact
    raw_feedback, artifact_path = _read_user_feedback_artifact(trial_dir)
    if raw_feedback is None:
        return artifact
    task_path = _task_path_from_trial_config(trial_dir)
    feedback_context = _synthesized_user_feedback_context(
        raw_feedback,
        task_path=task_path,
        repo_root=repo_root,
    )
    if feedback_context is None:
        return artifact
    enriched = dict(artifact)
    enriched_contexts = list(contexts) if isinstance(contexts, list) else []
    enriched_contexts.append(feedback_context)
    enriched["contexts"] = enriched_contexts
    source_artifacts = dict(enriched.get("sourceArtifacts") or {})
    if artifact_path is not None and "userFeedback" not in source_artifacts:
        source_artifacts["userFeedback"] = str(artifact_path)
    if source_artifacts:
        enriched["sourceArtifacts"] = source_artifacts
    return enriched


def _trial_persona_id(trial_dir: Path) -> str | None:
    config_path = trial_dir / "config.json"
    if not config_path.is_file():
        return None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    agent = payload.get("agent")
    if not isinstance(agent, dict):
        return None
    kwargs = agent.get("kwargs")
    if not isinstance(kwargs, dict):
        return None
    persona_path = str(kwargs.get("persona_path") or "").strip()
    if not persona_path:
        return None
    stem = Path(persona_path).stem
    if stem.startswith("persona_"):
        return stem[len("persona_") :]
    return stem or None


def _iter_fields(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    fields = artifact.get("fields")
    if not isinstance(fields, list):
        return []
    return [item for item in fields if isinstance(item, dict)]


def _iter_contexts(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    contexts = artifact.get("contexts")
    if isinstance(contexts, list):
        return [item for item in contexts if isinstance(item, dict)]

    # Backward-compatible fallback for early adopters that only wrote fields + group.
    grouped: dict[str, dict[str, Any]] = {}
    for field in _iter_fields(artifact):
        key = str(field.get("key") or "").strip()
        if not key:
            continue
        group = str(field.get("group") or key).strip()
        item = grouped.setdefault(
            group,
            {
                "key": group,
                "label": group,
                "contextType": "grouped_fields",
                "facets": [],
            },
        )
        item["facets"].append(
            {
                "key": key.split(".")[-1],
                "label": field.get("label") or key,
                "kind": field.get("kind"),
                "role": field.get("role"),
                "value": field.get("value"),
                "description": field.get("description"),
                "unit": field.get("unit"),
                "higherIsBetter": field.get("higherIsBetter"),
                "categories": field.get("categories"),
                "order": field.get("order"),
            }
        )
    return list(grouped.values())


def _iter_facets(context: dict[str, Any]) -> list[dict[str, Any]]:
    facets = context.get("facets")
    if not isinstance(facets, list):
        return []
    return [item for item in facets if isinstance(item, dict)]


def _iter_summary_directives(context: dict[str, Any]) -> list[dict[str, Any]]:
    directives = context.get("summaryDirectives")
    if not isinstance(directives, list):
        return []
    return [item for item in directives if isinstance(item, dict)]


def _iter_judge_directives(context: dict[str, Any]) -> list[dict[str, Any]]:
    directives = context.get("judgeDirectives")
    if not isinstance(directives, list):
        return []
    return [item for item in directives if isinstance(item, dict)]


def _load_task_reporting_config(
    *,
    trial_dir: Path,
    repo_root: Path | None,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    task_path = _task_path_from_trial_config(trial_dir)
    if not task_path or repo_root is None:
        return {}
    cached = cache.get(task_path)
    if cached is not None:
        return cached
    task_dir = (repo_root / task_path).resolve()
    for candidate in (task_dir / "reporting.json", task_dir / "reporting.toml"):
        if not candidate.is_file():
            continue
        try:
            if candidate.suffix == ".json":
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            else:
                payload = tomllib.loads(candidate.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            payload = {}
        if isinstance(payload, dict):
            cache[task_path] = payload
            return payload
    cache[task_path] = {}
    return {}


def _task_path_from_trial_config(trial_dir: Path) -> str | None:
    config_path = trial_dir / "config.json"
    if not config_path.is_file():
        return None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    task = payload.get("task")
    if not isinstance(task, dict):
        return None
    path = task.get("path")
    if isinstance(path, str) and path.strip():
        return path.strip().replace("\\", "/")
    return None


def _load_survey_instrument_for_job(
    job_dir: Path,
    *,
    repo_root: Path | None,
) -> Any | None:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[4]
    for trial_dir in sorted(path for path in job_dir.iterdir() if path.is_dir()):
        task_path = _task_path_from_trial_config(trial_dir)
        if not task_path:
            continue
        questionnaire_path = root / task_path / "input" / "questionnaire.yaml"
        if not questionnaire_path.is_file():
            continue
        try:
            import yaml

            raw = yaml.safe_load(questionnaire_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(raw, dict):
            continue
        try:
            from backend.service.survey_types import SurveyInstrument

            return SurveyInstrument.from_dict(raw)
        except Exception:  # noqa: BLE001
            continue
    return None


def _enrich_survey_context_meta_from_questionnaire(
    context_meta: dict[str, dict[str, Any]],
    *,
    job_dir: Path,
    repo_root: Path | None,
) -> None:
    """Attach prompt/scale metadata from questionnaire.yaml onto question contexts."""
    instrument = _load_survey_instrument_for_job(job_dir, repo_root=repo_root)
    if instrument is None:
        return
    questions = {
        str(getattr(question, "id", "") or "").strip(): question
        for question in getattr(instrument, "questions", []) or []
    }
    for context_key, meta in context_meta.items():
        if not context_key.startswith("question."):
            continue
        question_id = context_key[len("question.") :].strip()
        question = questions.get(question_id)
        if question is None:
            continue
        prompt = str(getattr(question, "prompt", "") or "").strip()
        question_type = str(getattr(question, "type", "") or "").strip().lower()
        label = str(meta.get("label") or "").strip()
        if prompt and (not label or label == question_id or label == context_key):
            meta["label"] = prompt
        if question_type and not meta.get("questionType"):
            meta["questionType"] = question_type
        if question_type == "likert":
            min_value = getattr(question, "min_value", None)
            max_value = getattr(question, "max_value", None)
            if meta.get("scaleMin") is None and min_value is not None:
                meta["scaleMin"] = int(min_value)
            if meta.get("scaleMax") is None and max_value is not None:
                meta["scaleMax"] = int(max_value)
            scale_labels = getattr(question, "scale_labels", None) or getattr(question, "scaleLabels", None)
            if not meta.get("scaleLabels") and isinstance(scale_labels, dict) and scale_labels:
                meta["scaleLabels"] = {
                    str(key): str(value)
                    for key, value in scale_labels.items()
                    if str(value).strip()
                }
        if question_type in {"single_choice", "multi_choice"} and not meta.get("choiceOptions"):
            option_rows: list[dict[str, str]] = []
            details = getattr(question, "option_details", None) or []
            if details:
                for option in details:
                    option_id = str(getattr(option, "id", "") or "").strip()
                    option_label = str(getattr(option, "label", "") or "").strip() or option_id
                    if option_id:
                        option_rows.append({"id": option_id, "label": option_label})
            else:
                for raw_option in getattr(question, "options", []) or []:
                    option_id = str(raw_option or "").strip()
                    if option_id:
                        option_rows.append({"id": option_id, "label": option_id})
            if option_rows:
                meta["choiceOptions"] = option_rows


def _read_user_feedback_artifact(trial_dir: Path) -> tuple[dict[str, Any] | None, Path | None]:
    for candidate in _user_feedback_candidates(trial_dir):
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(payload, dict):
            return payload, candidate
    return None, None


def _user_feedback_candidates(trial_dir: Path) -> list[Path]:
    candidates = [
        trial_dir / "artifacts" / "app" / "output" / "user_feedback.json",
        trial_dir / "verifier" / "user_feedback.json",
        trial_dir / "logs" / "verifier" / "user_feedback.json",
    ]
    tmp_root = trial_dir / "artifacts" / "tmp"
    if tmp_root.is_dir():
        for path in sorted(tmp_root.rglob("user_feedback.json")):
            candidates.append(path)
    return candidates


def _synthesized_user_feedback_context(
    raw_feedback: dict[str, Any],
    *,
    task_path: str | None,
    repo_root: Path | None,
) -> dict[str, Any] | None:
    schema = None
    if task_path and repo_root is not None:
        try:
            from playground.self_report_task_config import (
                load_self_report_schema_for_task_path,
            )

            schema = load_self_report_schema_for_task_path(
                task_path,
                repo_root=repo_root,
                fallback_to_default=False,
            )
        except Exception:  # noqa: BLE001
            schema = None
    facets: list[dict[str, Any]] = []
    if schema is not None and schema.fields:
        for field in schema.fields:
            if field.key not in raw_feedback:
                continue
            facet = _feedback_facet_from_schema_field(field, raw_feedback.get(field.key))
            if facet is not None:
                facets.append(facet)
    else:
        for key, value in raw_feedback.items():
            facet = _feedback_facet_from_heuristic(key, value)
            if facet is not None:
                facets.append(facet)
    if not facets:
        return None
    return {
        "key": "user_feedback.primary",
        "label": "User feedback",
        "contextType": "user_feedback",
        "facets": facets,
    }


def _feedback_facet_from_schema_field(field: Any, raw_value: Any) -> dict[str, Any] | None:
    normalized_key = _normalized_feedback_key(str(field.key))
    kind = _feedback_field_kind(str(field.kind))
    value = _coerce_feedback_value(kind, raw_value)
    if not _has_value(value):
        return None
    facet: dict[str, Any] = {
        "key": normalized_key,
        "label": _feedback_label(normalized_key, prompt=str(field.prompt or "")),
        "role": _feedback_role(normalized_key, kind),
        "kind": kind,
        "value": value,
    }
    choices = tuple(str(choice).strip() for choice in (getattr(field, "choices", ()) or ()) if str(choice).strip())
    if kind == "categorical":
        if choices:
            facet["categories"] = list(choices)
        elif str(getattr(field, "kind", "") or "").strip().lower() == "boolean":
            facet["categories"] = ["true", "false"]
    if kind == "numerical":
        minimum = getattr(field, "minimum", None)
        maximum = getattr(field, "maximum", None)
        if minimum is not None:
            facet["scaleMin"] = int(minimum)
        if maximum is not None:
            facet["scaleMax"] = int(maximum)
    return facet


def _feedback_facet_from_heuristic(raw_key: str, raw_value: Any) -> dict[str, Any] | None:
    normalized_key = _normalized_feedback_key(raw_key)
    kind = _feedback_kind_from_value(normalized_key, raw_value)
    value = _coerce_feedback_value(kind, raw_value)
    if not _has_value(value):
        return None
    facet: dict[str, Any] = {
        "key": normalized_key,
        "label": _feedback_label(normalized_key),
        "role": _feedback_role(normalized_key, kind),
        "kind": kind,
        "value": value,
    }
    if kind == "categorical":
        inventory = _default_feedback_categories(normalized_key, value)
        if inventory:
            facet["categories"] = inventory
    if kind == "numerical" and normalized_key in {
        "overall_experience_rating",
        "trust_level",
        "effort_rating",
    }:
        facet["scaleMin"] = 1
        facet["scaleMax"] = 10
    return facet


def _enrich_user_feedback_field_meta(field_meta: dict[str, dict[str, Any]]) -> None:
    """Normalize chat self-report facet roles/inventories even when trials wrote raw contexts."""
    feedback_fields = [
        meta
        for key, meta in field_meta.items()
        if str(meta.get("contextKey") or "").startswith("user_feedback")
        or str(meta.get("group") or "").startswith("user_feedback")
        or ".user_feedback." in key
        or key.startswith("user_feedback.")
    ]
    if not feedback_fields:
        return

    for meta in feedback_fields:
        facet_key = _normalized_feedback_key(str(meta.get("facetKey") or meta.get("key") or ""))
        kind = str(meta.get("kind") or "").strip().lower()
        # Always prefer the overall rating as the hero signal.
        if facet_key == "overall_experience_rating":
            meta["role"] = "primary"
            if meta.get("scaleMin") is None:
                meta["scaleMin"] = 1
            if meta.get("scaleMax") is None:
                meta["scaleMax"] = 10
            continue
        if kind == "numerical" and facet_key in {"trust_level", "effort_rating"}:
            if meta.get("scaleMin") is None:
                meta["scaleMin"] = 1
            if meta.get("scaleMax") is None:
                meta["scaleMax"] = 10
            if meta.get("role") == "primary":
                meta["role"] = "score"
            continue
        if kind == "categorical":
            if meta.get("role") == "primary":
                meta["role"] = "evidence"
            if not meta.get("categories"):
                inventory = _default_feedback_categories(facet_key, None)
                if inventory is None and "clarification" in facet_key:
                    inventory = ["true", "false"]
                if inventory:
                    meta["categories"] = inventory
        if kind == "textual" and facet_key in {"feedback_reason", "clarifying_notes", "feedback_comments"}:
            meta["role"] = "explanation"


def _default_feedback_categories(normalized_key: str, value: Any) -> list[str] | None:
    if normalized_key in {
        "need_constraint_satisfaction",
        "personal_preference_satisfaction",
        "clarity_of_next_step",
    }:
        return ["yes", "partially", "no"]
    if isinstance(value, bool) or str(value).strip().lower() in {"true", "false"}:
        return ["true", "false"]
    if normalized_key in {
        "felt_understood",
        "asked_useful_clarification_questions",
    }:
        return ["true", "false"]
    return None


def _normalized_feedback_key(raw_key: str) -> str:
    alias_map = {
        "needConstraintSatisfaction": "need_constraint_satisfaction",
        "personalPreferenceSatisfaction": "personal_preference_satisfaction",
        "overallExperienceRating": "overall_experience_rating",
        "trustLevel": "trust_level",
        "effortRating": "effort_rating",
        "clarityOfNextStep": "clarity_of_next_step",
        "feltUnderstood": "felt_understood",
        "askedUsefulClarificationQuestions": "asked_useful_clarification_questions",
        "clarifyingNotes": "clarifying_notes",
        "ratingReason": "feedback_reason",
        "comments": "feedback_comments",
    }
    if raw_key in alias_map:
        return alias_map[raw_key]
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(raw_key)).replace("-", "_").lower()
    snake = re.sub(r"__+", "_", snake).strip("_")
    if snake == "reason":
        return "feedback_reason"
    return snake


def _feedback_field_kind(field_kind: str) -> str:
    normalized = field_kind.strip().lower()
    if normalized == "integer":
        return "numerical"
    if normalized in {"enum", "boolean"}:
        return "categorical"
    return "textual"


def _feedback_kind_from_value(normalized_key: str, raw_value: Any) -> str:
    if normalized_key in {
        "overall_experience_rating",
        "trust_level",
        "effort_rating",
        "satisfaction",
        "frustration",
        "ease_of_use",
    }:
        return "numerical"
    if isinstance(raw_value, bool):
        return "categorical"
    if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
        return "numerical"
    if normalized_key.endswith("_satisfaction") or normalized_key.startswith("clarity_"):
        return "categorical"
    if any(token in normalized_key for token in ("reason", "note", "comment", "rationale", "explanation")):
        return "textual"
    return "textual" if isinstance(raw_value, str) else "categorical"


def _coerce_feedback_value(kind: str, raw_value: Any) -> Any:
    if kind == "numerical":
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            return None
        return int(round(float(raw_value)))
    if kind == "categorical":
        if isinstance(raw_value, bool):
            return "true" if raw_value else "false"
        text = str(raw_value or "").strip().lower()
        return text or None
    text = str(raw_value or "").strip()
    return text or None


def _feedback_role(normalized_key: str, kind: str) -> str:
    if normalized_key == "overall_experience_rating":
        return "primary"
    if kind == "numerical":
        return "score"
    if normalized_key == "feedback_reason" or any(
        token in normalized_key for token in ("note", "comment", "rationale", "explanation")
    ):
        return "explanation"
    if normalized_key in {"need_constraint_satisfaction", "personal_preference_satisfaction"}:
        return "evidence"
    return "evidence"


def _feedback_label(normalized_key: str, *, prompt: str = "") -> str:
    label_map = {
        "overall_experience_rating": "Overall experience rating",
        "need_constraint_satisfaction": "Need or constraint satisfaction",
        "personal_preference_satisfaction": "Personal preference satisfaction",
        "feedback_reason": "Feedback reason",
        "trust_level": "Trust level",
        "effort_rating": "Effort rating",
        "clarity_of_next_step": "Clarity of next step",
        "felt_understood": "Felt understood",
        "asked_useful_clarification_questions": "Asked useful clarifying questions",
        "clarifying_notes": "Clarifying notes",
    }
    if normalized_key in label_map:
        return label_map[normalized_key]
    if prompt.strip():
        return prompt.strip()
    return normalized_key.replace("_", " ").strip().title()


def _resolve_summary_directives(
    *,
    context: dict[str, Any],
    reporting_config: dict[str, Any],
) -> list[dict[str, Any]]:
    embedded = _iter_summary_directives(context)
    rules = reporting_config.get("contextRules")
    if not isinstance(rules, list):
        return embedded
    resolved = list(embedded)
    context_key = str(context.get("key") or "").strip()
    context_type = str(context.get("contextType") or "").strip()
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        match = rule.get("match")
        if not isinstance(match, dict):
            continue
        match_key = str(match.get("key") or "").strip()
        match_type = str(match.get("contextType") or "").strip()
        if match_key and match_key != context_key:
            continue
        if match_type and match_type != context_type:
            continue
        for directive in _iter_summary_directives(rule):
            if directive not in resolved:
                resolved.append(directive)
    return resolved


def _resolve_judge_directives(
    *,
    context: dict[str, Any],
    reporting_config: dict[str, Any],
) -> list[dict[str, Any]]:
    embedded = _iter_judge_directives(context)
    rules = reporting_config.get("contextRules")
    if not isinstance(rules, list):
        return embedded
    resolved = list(embedded)
    context_key = str(context.get("key") or "").strip()
    context_type = str(context.get("contextType") or "").strip()
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        match = rule.get("match")
        if not isinstance(match, dict):
            continue
        match_key = str(match.get("key") or "").strip()
        match_type = str(match.get("contextType") or "").strip()
        if match_key and match_key != context_key:
            continue
        if match_type and match_type != context_type:
            continue
        for directive in _iter_judge_directives(rule):
            if directive not in resolved:
                resolved.append(directive)
    return resolved


def _is_discrete_subject_label_facet(meta: dict[str, Any]) -> bool:
    facet_key = str(meta.get("facetKey") or "").strip()
    if not facet_key:
        # Fall back for callers that only set the unqualified key.
        facet_key = str(meta.get("key") or "").strip().rsplit(".", 1)[-1]
    if facet_key in DISCRETE_SUBJECT_LABEL_FACET_KEYS:
        return True
    return facet_key.endswith("_subject_label")


def _aggregate_field(
    *,
    meta: dict[str, Any],
    values: list[dict[str, Any]],
    artifact_ready_trials: int,
) -> dict[str, Any]:
    kind = str(meta.get("kind") or "").strip().lower()
    present_entries = [entry for entry in values if _has_value(entry.get("value"))]
    missing_count = max(artifact_ready_trials - len(present_entries), 0)
    # Catalog choice titles are discrete identities, not free-text themes.
    if _is_discrete_subject_label_facet(meta):
        kind = "categorical"
    else:
        # Survey choice ids are often emitted as textual strings; recover a real distribution.
        # Skip explanation/evidence roles — those are free-text even when short.
        role = str(meta.get("role") or "").strip().lower()
        if (
            kind == "textual"
            and role not in {"explanation", "evidence"}
            and _entries_look_categorical(present_entries)
        ):
            kind = "categorical"
    payload = {
        **meta,
        "kind": kind,
        "presentCount": len(present_entries),
        "missingCount": missing_count,
    }
    if kind == "numerical":
        payload["numerical"] = _aggregate_numerical(present_entries)
    elif kind == "categorical":
        payload["categorical"] = _aggregate_categorical(present_entries)
    else:
        payload["textual"] = _aggregate_textual(present_entries)
    return payload


def _entries_look_categorical(entries: list[dict[str, Any]]) -> bool:
    """True when values look like choice ids / enums, not free-text sentences."""
    if not entries:
        return False
    for entry in entries:
        raw = entry.get("value")
        if isinstance(raw, bool) or isinstance(raw, list):
            continue
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return False
        text = str(raw or "").strip()
        if not text:
            continue
        if " " in text or "\n" in text or len(text) > 64:
            return False
        # Reject sentence fragments ("Affordable.") and Title Case words without
        # id separators; keep snake/kebab ids and short lowercase/UPPER tokens.
        if any(ch in text for ch in ".!?,;:"):
            return False
        if "_" not in text and "-" not in text:
            if not (text.islower() or text.isupper()):
                return False
    return True


def _aggregate_context(
    *,
    meta: dict[str, Any],
    facet_keys: list[str],
    fields_by_key: dict[str, dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    facets = [fields_by_key[key] for key in facet_keys if key in fields_by_key]
    payload = {
        **meta,
        "facets": facets,
    }
    summaries = _aggregate_context_summaries(meta=meta, facets=facets, field_values=field_values)
    if summaries:
        payload["summaries"] = summaries
    judges = _aggregate_context_judges(meta=meta, facets=facets, field_values=field_values)
    if judges:
        payload["judges"] = judges
    cross_facet_views = _aggregate_context_cross_facet_views(
        facets=facets,
        field_values=field_values,
    )
    if cross_facet_views:
        payload["crossFacetViews"] = cross_facet_views
    return payload


def _apply_llm_reporting(
    *,
    payload: dict[str, Any],
    previous_payload: dict[str, Any] | None,
    llm_client: Any | None,
    enable_llm: bool | None,
) -> dict[str, Any]:
    previous_index = _index_previous_llm_units(previous_payload)
    llm_enabled = _reporting_llm_enabled(enable_llm)
    client = _reporting_llm_client(llm_client) if llm_enabled else None
    client_error = None
    if llm_enabled and client is None:
        client_error = "Reporting LLM client unavailable for configured model."
    for context in payload.get("contexts", []) if isinstance(payload.get("contexts"), list) else []:
        if not isinstance(context, dict):
            continue
        context_key = str(context.get("key") or "")
        summaries = context.get("summaries")
        if isinstance(summaries, list):
            for summary in summaries:
                if not isinstance(summary, dict):
                    continue
                fingerprint = _fingerprint_reporting_unit(summary)
                summary["llmFingerprint"] = fingerprint
                cached = previous_index.get(("summary", context_key, str(summary.get("id") or "")))
                if _cached_result_matches(cached, fingerprint):
                    _reuse_cached_summary(summary, cached)
                    continue
                if client is not None and str(summary.get("status") or "").startswith("ready_for_llm"):
                    _execute_summary_llm(summary, client=client)
                elif client_error and str(summary.get("status") or "").startswith("ready_for_llm"):
                    summary["status"] = "llm_failed"
                    summary["error"] = client_error
        judges = context.get("judges")
        if isinstance(judges, list):
            for judge in judges:
                if not isinstance(judge, dict):
                    continue
                fingerprint = _fingerprint_reporting_unit(judge)
                judge["llmFingerprint"] = fingerprint
                cached = previous_index.get(("judge", context_key, str(judge.get("id") or "")))
                if _cached_result_matches(cached, fingerprint):
                    _reuse_cached_judge(judge, cached)
                    continue
                if client is not None and str(judge.get("status") or "").startswith("ready_for_llm"):
                    _execute_judge_llm(judge, client=client)
                elif client_error and str(judge.get("status") or "").startswith("ready_for_llm"):
                    judge["status"] = "llm_failed"
                    judge["error"] = client_error
    return payload


def _index_previous_llm_units(previous_payload: dict[str, Any] | None) -> dict[tuple[str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    if not isinstance(previous_payload, dict):
        return index
    contexts = previous_payload.get("contexts")
    if not isinstance(contexts, list):
        return index
    for context in contexts:
        if not isinstance(context, dict):
            continue
        context_key = str(context.get("key") or "")
        for kind in ("summaries", "judges"):
            units = context.get(kind)
            if not isinstance(units, list):
                continue
            for unit in units:
                if not isinstance(unit, dict):
                    continue
                label = "summary" if kind == "summaries" else "judge"
                index[(label, context_key, str(unit.get("id") or ""))] = unit
    return index


def _cached_result_matches(cached: dict[str, Any] | None, fingerprint: str) -> bool:
    if not isinstance(cached, dict):
        return False
    if str(cached.get("llmFingerprint") or "") != fingerprint:
        return False
    return str(cached.get("status") or "") in {"llm_completed", "llm_failed"}


def _reuse_cached_summary(current: dict[str, Any], cached: dict[str, Any]) -> None:
    current["status"] = cached.get("status")
    current["error"] = cached.get("error")
    current["overall"] = cached.get("overall")
    cached_buckets = {
        str(bucket.get("bucket") or ""): bucket
        for bucket in cached.get("buckets", [])
        if isinstance(bucket, dict)
    }
    for bucket in current.get("buckets", []) if isinstance(current.get("buckets"), list) else []:
        cached_bucket = cached_buckets.get(str(bucket.get("bucket") or ""))
        if not cached_bucket:
            continue
        bucket["summary"] = cached_bucket.get("summary")
        bucket["summaryType"] = cached_bucket.get("summaryType")


def _reuse_cached_judge(current: dict[str, Any], cached: dict[str, Any]) -> None:
    current["status"] = cached.get("status")
    current["error"] = cached.get("error")
    current["overall"] = cached.get("overall")
    current["overallAssessment"] = cached.get("overallAssessment")
    cached_buckets = {
        str(bucket.get("bucket") or ""): bucket
        for bucket in cached.get("buckets", [])
        if isinstance(bucket, dict)
    }
    for bucket in current.get("buckets", []) if isinstance(current.get("buckets"), list) else []:
        cached_bucket = cached_buckets.get(str(bucket.get("bucket") or ""))
        if not cached_bucket:
            continue
        bucket["assessment"] = cached_bucket.get("assessment")
        bucket["signals"] = cached_bucket.get("signals")


def _build_reporting_view(payload: dict[str, Any]) -> dict[str, Any]:
    llm_units = list(_iter_llm_reporting_units(payload))
    status_counts = Counter(
        str(unit.get("status") or "unknown")
        for _, unit in llm_units
    )
    total_units = len(llm_units)
    summary_units = sum(1 for kind, _ in llm_units if kind == "summary")
    judge_units = sum(1 for kind, _ in llm_units if kind == "judge")
    ready_units = status_counts.get("ready_for_llm", 0)
    completed_units = status_counts.get("llm_completed", 0)
    failed_units = status_counts.get("llm_failed", 0)
    return {
        "status": _reporting_overall_status(
            total_units=total_units,
            ready_units=ready_units,
            completed_units=completed_units,
            failed_units=failed_units,
        ),
        "llmEnabled": _reporting_llm_enabled(None),
        "model": (
            os.environ.get(REPORTING_LLM_MODEL_ENV)
            or DEFAULT_REPORTING_LLM_MODEL
        ).strip()
        or DEFAULT_REPORTING_LLM_MODEL,
        "totalUnits": total_units,
        "summaryUnits": summary_units,
        "judgeUnits": judge_units,
        "readyUnits": ready_units,
        "completedUnits": completed_units,
        "failedUnits": failed_units,
        "updatedAt": payload.get("generatedAt"),
    }


def _iter_llm_reporting_units(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    contexts = payload.get("contexts")
    if not isinstance(contexts, list):
        return []
    units: list[tuple[str, dict[str, Any]]] = []
    for context in contexts:
        if not isinstance(context, dict):
            continue
        summaries = context.get("summaries")
        if isinstance(summaries, list):
            for summary in summaries:
                if not isinstance(summary, dict):
                    continue
                kind = str(summary.get("summaryKind") or "").strip().lower()
                status = str(summary.get("status") or "").strip().lower()
                if kind.startswith("llm_") or status.startswith("ready_for_llm") or status.startswith("llm_"):
                    units.append(("summary", summary))
        judges = context.get("judges")
        if isinstance(judges, list):
            for judge in judges:
                if not isinstance(judge, dict):
                    continue
                kind = str(judge.get("judgeKind") or "").strip().lower()
                status = str(judge.get("status") or "").strip().lower()
                if kind.startswith("llm_") or status.startswith("ready_for_llm") or status.startswith("llm_"):
                    units.append(("judge", judge))
    return units


def _reporting_overall_status(
    *,
    total_units: int,
    ready_units: int,
    completed_units: int,
    failed_units: int,
) -> str:
    if total_units <= 0:
        return "not_applicable"
    if completed_units == total_units:
        return "completed"
    if failed_units == total_units:
        return "failed"
    if ready_units == total_units:
        return "ready"
    if completed_units > 0 and failed_units > 0 and ready_units > 0:
        return "partial_with_errors"
    if completed_units > 0 and failed_units > 0:
        return "completed_with_errors"
    if completed_units > 0 and ready_units > 0:
        return "partial"
    if failed_units > 0 and ready_units > 0:
        return "failed"
    return "ready"


def _reporting_llm_enabled(enable_llm: bool | None) -> bool:
    if enable_llm is not None:
        return enable_llm
    raw = os.environ.get(REPORTING_LLM_ENABLE_ENV, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _reporting_llm_client(client: Any | None) -> Any | None:
    if client is not None:
        return client
    model = (
        os.environ.get(REPORTING_LLM_MODEL_ENV)
        or DEFAULT_REPORTING_LLM_MODEL
    ).strip() or DEFAULT_REPORTING_LLM_MODEL
    provider, bare_model = _normalize_reporting_model(model)
    if provider != "openai":
        return None
    from playground.openai_client import OpenAIChatClient

    return OpenAIChatClient(model=bare_model, temperature=0.2)


def _normalize_reporting_model(model: str) -> tuple[str, str]:
    normalized = model.strip()
    if "/" in normalized:
        provider, bare = normalized.split("/", 1)
        return provider, bare
    return "openai", normalized


def _fingerprint_reporting_unit(unit: dict[str, Any]) -> str:
    payload = {
        "id": unit.get("id"),
        "title": unit.get("title"),
        "targetFacetKey": unit.get("targetFacetKey"),
        "groupByFacetKey": unit.get("groupByFacetKey"),
        "groupByMode": unit.get("groupByMode"),
        "summaryKind": unit.get("summaryKind"),
        "judgeKind": unit.get("judgeKind"),
        "instruction": unit.get("instruction"),
        "prompt": unit.get("prompt"),
        "rubric": unit.get("rubric"),
        "signals": unit.get("signals"),
        "buckets": unit.get("buckets"),
        "overall": unit.get("overall"),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _execute_summary_llm(summary: dict[str, Any], *, client: Any) -> None:
    system = (
        "You are an evaluation reporting assistant. Summarize grouped user text samples "
        "concisely and return strict JSON."
    )
    instruction = str(summary.get("instruction") or "").strip()
    user = json.dumps(
        {
            "task": "Summarize grouped text buckets for a completed evaluation job.",
            "title": summary.get("title"),
            "instruction": instruction or "Summarize each bucket faithfully without inventing new facts.",
            "buckets": summary.get("buckets"),
            "expectedOutput": {
                "overallSummary": "string",
                "bucketSummaries": [{"bucket": "string", "summary": "string"}],
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        result = client.complete_json(system, user)
    except Exception as exc:  # noqa: BLE001
        summary["status"] = "llm_failed"
        summary["error"] = str(exc)
        return
    overall_summary = str(result.get("overallSummary") or "").strip()
    if overall_summary:
        overall = summary.get("overall")
        if isinstance(overall, dict):
            overall["summary"] = overall_summary
            overall["summaryType"] = "llm"
    bucket_summaries = {
        str(item.get("bucket") or ""): str(item.get("summary") or "").strip()
        for item in result.get("bucketSummaries", [])
        if isinstance(item, dict)
    }
    for bucket in summary.get("buckets", []) if isinstance(summary.get("buckets"), list) else []:
        value = bucket_summaries.get(str(bucket.get("bucket") or ""))
        if value:
            bucket["summary"] = value
            bucket["summaryType"] = "llm"
    summary["status"] = "llm_completed"
    summary.pop("error", None)


def _execute_judge_llm(judge: dict[str, Any], *, client: Any) -> None:
    system = (
        "You are an evaluation judge. Inspect grouped samples, apply the provided rubric "
        "and signals, and return strict JSON."
    )
    user = json.dumps(
        {
            "task": "Judge grouped evaluation samples.",
            "title": judge.get("title"),
            "prompt": judge.get("prompt"),
            "rubric": judge.get("rubric"),
            "signals": judge.get("signals"),
            "buckets": judge.get("buckets"),
            "expectedOutput": {
                "overallAssessment": "string",
                "bucketAssessments": [
                    {
                        "bucket": "string",
                        "assessment": "string",
                        "signals": [
                            {"key": "string", "present": True, "evidence": "string"}
                        ],
                    }
                ],
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        result = client.complete_json(system, user)
    except Exception as exc:  # noqa: BLE001
        judge["status"] = "llm_failed"
        judge["error"] = str(exc)
        return
    overall_assessment = str(result.get("overallAssessment") or "").strip()
    if overall_assessment:
        judge["overallAssessment"] = overall_assessment
    bucket_results = {
        str(item.get("bucket") or ""): item
        for item in result.get("bucketAssessments", [])
        if isinstance(item, dict)
    }
    for bucket in judge.get("buckets", []) if isinstance(judge.get("buckets"), list) else []:
        raw = bucket_results.get(str(bucket.get("bucket") or ""))
        if not raw:
            continue
        assessment = str(raw.get("assessment") or "").strip()
        if assessment:
            bucket["assessment"] = assessment
        signals = []
        for signal in raw.get("signals", []):
            if not isinstance(signal, dict):
                continue
            key = str(signal.get("key") or "").strip()
            if not key:
                continue
            signals.append(
                {
                    "key": key,
                    "present": bool(signal.get("present")),
                    "evidence": str(signal.get("evidence") or "").strip() or None,
                }
            )
        if signals:
            bucket["signals"] = signals
    judge["status"] = "llm_completed"
    judge.pop("error", None)


def _aggregate_context_summaries(
    *,
    meta: dict[str, Any],
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    facet_lookup = {str(facet.get("facetKey") or facet.get("key")): facet for facet in facets}
    directives = meta.get("summaryDirectives")
    if not isinstance(directives, list):
        return []
    summaries: list[dict[str, Any]] = []
    for index, directive in enumerate(directives):
        summary = _aggregate_summary_directive(
            directive=directive,
            index=index,
            context_key=str(meta.get("key") or ""),
            facet_lookup=facet_lookup,
            field_values=field_values,
        )
        if summary:
            summaries.append(summary)
    return summaries


def _aggregate_summary_directive(
    *,
    directive: dict[str, Any],
    index: int,
    context_key: str,
    facet_lookup: dict[str, dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    target_facet_key = str(directive.get("targetFacetKey") or "").strip()
    if not target_facet_key:
        return None
    target_field = facet_lookup.get(target_facet_key)
    if target_field is None or target_field.get("kind") != "textual":
        return None
    group_by_mode = str(directive.get("groupByMode") or "none").strip().lower()
    if group_by_mode not in SUMMARY_GROUP_BY_MODES:
        group_by_mode = "none"
    group_by_facet_key = str(directive.get("groupByFacetKey") or "").strip() or None
    group_by_field = facet_lookup.get(group_by_facet_key) if group_by_facet_key else None
    target_entries = [
        entry
        for entry in field_values.get(str(target_field.get("key")), [])
        if _has_value(entry.get("value")) and entry.get("trialName") is not None
    ]
    if not target_entries:
        return None

    bucket_map: dict[str, list[dict[str, Any]]] = {}
    if group_by_mode == "none" or group_by_field is None:
        bucket_map["All"] = target_entries
    elif group_by_mode == "categorical":
        group_entries = {
            str(entry.get("trialName")): _categorical_key(entry.get("value"))
            for entry in field_values.get(str(group_by_field.get("key")), [])
            if entry.get("trialName") is not None and _has_value(entry.get("value"))
        }
        for entry in target_entries:
            trial_name = str(entry.get("trialName"))
            bucket = group_entries.get(trial_name)
            if bucket is None:
                continue
            bucket_map.setdefault(bucket, []).append(entry)
    else:
        bands = _normalize_numeric_bands(directive.get("bands"))
        if not bands:
            return None
        group_entries = {
            str(entry.get("trialName")): entry.get("value")
            for entry in field_values.get(str(group_by_field.get("key")), [])
            if entry.get("trialName") is not None and _has_value(entry.get("value"))
        }
        for entry in target_entries:
            trial_name = str(entry.get("trialName"))
            bucket = _match_numeric_band(group_entries.get(trial_name), bands)
            if bucket is None:
                continue
            bucket_map.setdefault(bucket, []).append(entry)

    overall = _aggregate_textual(target_entries)
    buckets = [
        {
            "bucket": bucket,
            "count": len(entries),
            "samples": overall_bucket.get("samples"),
            "summary": overall_bucket.get("summary"),
            "summaryType": overall_bucket.get("summaryType"),
        }
        for bucket, entries in sorted(
            bucket_map.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
        for overall_bucket in [_aggregate_textual(entries)]
    ]
    if not buckets:
        return None
    target_label = str(target_field.get("label") or target_facet_key)
    group_by_label = str(group_by_field.get("label") or group_by_facet_key or "All")
    summary_kind = str(directive.get("summaryKind") or "bucketed_text").strip()
    return {
        "id": str(directive.get("id") or "{}.summary_{}".format(context_key, index + 1)),
        "title": str(directive.get("title") or "{} by {}".format(target_label, group_by_label)),
        "targetFacetKey": target_facet_key,
        "groupByFacetKey": group_by_facet_key,
        "groupByMode": group_by_mode,
        "summaryKind": summary_kind,
        "instruction": directive.get("instruction"),
        "status": "ready_for_llm" if summary_kind.startswith("llm_") else "heuristic",
        "overall": overall,
        "buckets": buckets,
    }


def _aggregate_context_judges(
    *,
    meta: dict[str, Any],
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    facet_lookup = {str(facet.get("facetKey") or facet.get("key")): facet for facet in facets}
    directives = meta.get("judgeDirectives")
    if not isinstance(directives, list):
        return []
    judges: list[dict[str, Any]] = []
    for index, directive in enumerate(directives):
        judge = _aggregate_judge_directive(
            directive=directive,
            index=index,
            context_key=str(meta.get("key") or ""),
            facet_lookup=facet_lookup,
            field_values=field_values,
        )
        if judge:
            judges.append(judge)
    return judges


def _aggregate_judge_directive(
    *,
    directive: dict[str, Any],
    index: int,
    context_key: str,
    facet_lookup: dict[str, dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    target_facet_key = str(directive.get("targetFacetKey") or "").strip()
    if not target_facet_key:
        return None
    target_field = facet_lookup.get(target_facet_key)
    if target_field is None:
        return None
    group_by_mode = str(directive.get("groupByMode") or "none").strip().lower()
    if group_by_mode not in JUDGE_GROUP_BY_MODES:
        group_by_mode = "none"
    group_by_facet_key = str(directive.get("groupByFacetKey") or "").strip() or None
    group_by_field = facet_lookup.get(group_by_facet_key) if group_by_facet_key else None
    target_entries = [
        entry
        for entry in field_values.get(str(target_field.get("key")), [])
        if _has_value(entry.get("value")) and entry.get("trialName") is not None
    ]
    if not target_entries:
        return None

    bucket_map: dict[str, list[dict[str, Any]]] = {}
    if group_by_mode == "none" or group_by_field is None:
        bucket_map["All"] = target_entries
    elif group_by_mode == "categorical":
        group_entries = {
            str(entry.get("trialName")): _categorical_key(entry.get("value"))
            for entry in field_values.get(str(group_by_field.get("key")), [])
            if entry.get("trialName") is not None and _has_value(entry.get("value"))
        }
        for entry in target_entries:
            trial_name = str(entry.get("trialName"))
            bucket = group_entries.get(trial_name)
            if bucket is None:
                continue
            bucket_map.setdefault(bucket, []).append(entry)
    else:
        bands = _normalize_numeric_bands(directive.get("bands"))
        if not bands:
            return None
        group_entries = {
            str(entry.get("trialName")): entry.get("value")
            for entry in field_values.get(str(group_by_field.get("key")), [])
            if entry.get("trialName") is not None and _has_value(entry.get("value"))
        }
        for entry in target_entries:
            trial_name = str(entry.get("trialName"))
            bucket = _match_numeric_band(group_entries.get(trial_name), bands)
            if bucket is None:
                continue
            bucket_map.setdefault(bucket, []).append(entry)

    buckets = [
        {
            "bucket": bucket,
            "count": len(entries),
            "samples": _sample_values(entries, limit=3),
        }
        for bucket, entries in sorted(
            bucket_map.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]
    if not buckets:
        return None
    target_label = str(target_field.get("label") or target_facet_key)
    group_by_label = str(group_by_field.get("label") or group_by_facet_key or "All")
    judge_kind = str(directive.get("judgeKind") or "llm_signal_judge").strip()
    return {
        "id": str(directive.get("id") or "{}.judge_{}".format(context_key, index + 1)),
        "title": str(directive.get("title") or "{} judge by {}".format(target_label, group_by_label)),
        "targetFacetKey": target_facet_key,
        "groupByFacetKey": group_by_facet_key,
        "groupByMode": group_by_mode,
        "judgeKind": judge_kind,
        "prompt": directive.get("prompt"),
        "rubric": directive.get("rubric"),
        "signals": _normalize_signals(directive.get("signals")),
        "status": "ready_for_llm" if judge_kind.startswith("llm_") else "heuristic",
        "overall": {
            "count": len(target_entries),
            "samples": _sample_values(target_entries, limit=5),
        },
        "buckets": buckets,
    }


def _aggregate_context_cross_facet_views(
    *,
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    primary = next(
        (
            facet
            for facet in facets
            if facet.get("kind") == "categorical" and str(facet.get("role") or "") == "primary"
        ),
        None,
    )
    if primary is None:
        return []
    primary_entries = {
        str(entry.get("trialName")): _categorical_key(entry.get("value"))
        for entry in field_values.get(str(primary.get("key")), [])
        if entry.get("trialName") is not None and _has_value(entry.get("value"))
    }
    cross_facet_views: list[dict[str, Any]] = []
    for facet in facets:
        if facet.get("kind") != "textual":
            continue
        role = str(facet.get("role") or "")
        if role not in {"explanation", "evidence", "supporting_text"}:
            continue
        buckets: dict[str, list[str]] = {}
        for entry in field_values.get(str(facet.get("key")), []):
            trial_name = str(entry.get("trialName") or "")
            bucket = primary_entries.get(trial_name)
            value = str(entry.get("value") or "").strip()
            if not bucket or not value:
                continue
            buckets.setdefault(bucket, []).append(value)
        if not buckets:
            continue
        cross_facet_views.append(
            {
                "type": "text_by_primary_category",
                "primaryFacetKey": primary.get("key"),
                "textFacetKey": facet.get("key"),
                "buckets": [
                    {
                        "category": category,
                        "count": len(values),
                        "samples": list(dict.fromkeys(values))[:3],
                    }
                    for category, values in sorted(
                        buckets.items(),
                        key=lambda item: (-len(item[1]), item[0]),
                    )
                ],
            }
        )
    return cross_facet_views


def _normalize_numeric_bands(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        normalized.append(
            {
                "label": label,
                "min": item.get("min"),
                "max": item.get("max"),
            }
        )
    return normalized


def _normalize_signals(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    signals: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        signals.append(
            {
                "key": key,
                "label": item.get("label") or key,
                "valueType": item.get("valueType"),
                "description": item.get("description"),
            }
        )
    return signals


def _match_numeric_band(value: Any, bands: list[dict[str, Any]]) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    for band in bands:
        lower = band.get("min")
        upper = band.get("max")
        if lower is not None and numeric < float(lower):
            continue
        if upper is not None and numeric > float(upper):
            continue
        return str(band["label"])
    return None


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return True


def _aggregate_numerical(entries: list[dict[str, Any]]) -> dict[str, Any]:
    numbers: list[float] = []
    for entry in entries:
        raw = entry.get("value")
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)):
            numbers.append(float(raw))
    if not numbers:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "avg": None,
            "std": None,
            "counts": [],
        }
    avg = mean(numbers)
    variance = mean([(value - avg) ** 2 for value in numbers]) if len(numbers) > 1 else 0.0
    value_counts: Counter[str] = Counter()
    for value in numbers:
        # Prefer integer labels for likert-style whole numbers.
        key = str(int(value)) if float(value).is_integer() else str(value)
        value_counts[key] += 1
    ranked_counts = [
        {"value": value, "count": count}
        for value, count in sorted(
            value_counts.items(),
            key=lambda item: (
                float(item[0]) if _is_number(item[0]) else 0.0,
                item[0],
            ),
        )
    ]
    return {
        "count": len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "avg": round(avg, 4),
        "std": round(math.sqrt(variance), 4),
        "counts": ranked_counts,
    }


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _aggregate_categorical(entries: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for entry in entries:
        raw = entry.get("value")
        if isinstance(raw, list):
            for item in raw:
                counts[_categorical_key(item)] += 1
        else:
            counts[_categorical_key(raw)] += 1
    ranked = [
        {"value": value, "count": count}
        for value, count in counts.most_common()
    ]
    return {
        "count": sum(counts.values()),
        "distinctCount": len(counts),
        "counts": ranked,
    }


def _categorical_key(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "(missing)"
    return str(value)


_MAX_FREE_TEXT_THEMES = 6
# Generic English function words only — domain terms are handled by TF-IDF IDF.
_TFIDF_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "with",
        "without",
    }
)


def _normalize_text_theme(value: str) -> str:
    compact = " ".join(str(value or "").lower().split())
    compact = re.sub(r"[^\w\s]", "", compact)
    return compact.strip()


def _tfidf_terms(value: str) -> list[str]:
    tokens: list[str] = []
    for raw in _normalize_text_theme(value).split():
        if len(raw) <= 1 or raw in _TFIDF_STOPWORDS:
            continue
        token = raw
        # Light plural normalization only (not domain aliases).
        if len(token) > 4 and token.endswith("es") and not token.endswith(("ss", "ous", "ies")):
            token = token[:-2]
        elif len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is", "ous", "ing")):
            token = token[:-1]
        if len(token) > 1 and token not in _TFIDF_STOPWORDS:
            tokens.append(token)
    terms = list(tokens)
    for index in range(len(tokens) - 1):
        terms.append("{} {}".format(tokens[index], tokens[index + 1]))
    return terms


def _tfidf_vectors(documents: list[str]) -> list[list[float]]:
    """Lightweight TF-IDF (unigram + bigram), L2-normalized. Fast for survey-scale n."""
    docs_terms = [_tfidf_terms(document) for document in documents]
    document_frequency: Counter[str] = Counter()
    for terms in docs_terms:
        document_frequency.update(set(terms))
    vocabulary = sorted(document_frequency.keys())
    if not vocabulary:
        return [[0.0] for _ in documents]
    index = {term: position for position, term in enumerate(vocabulary)}
    n_docs = len(documents)
    matrix: list[list[float]] = []
    for terms in docs_terms:
        tf_counts = Counter(terms)
        length = max(1, sum(tf_counts.values()))
        row = [0.0] * len(vocabulary)
        for term, count in tf_counts.items():
            idf = math.log((1.0 + n_docs) / (1.0 + document_frequency[term])) + 1.0
            row[index[term]] = (count / length) * idf
        norm = math.sqrt(sum(value * value for value in row)) or 1.0
        matrix.append([value / norm for value in row])
    return matrix


def _cosine_similarity_matrix(vectors: list[list[float]]) -> list[list[float]]:
    n = len(vectors)
    sim = [[0.0] * n for _ in range(n)]
    for i in range(n):
        sim[i][i] = 1.0
        left = vectors[i]
        for j in range(i + 1, n):
            right = vectors[j]
            score = sum(a * b for a, b in zip(left, right))
            # Numerical guard.
            score = 0.0 if score < 0 else (1.0 if score > 1.0 else score)
            sim[i][j] = score
            sim[j][i] = score
    return sim


def _average_linkage_labels(sim: list[list[float]], k: int) -> list[int]:
    """Greedy average-linkage clustering down to k clusters."""
    n = len(sim)
    if n == 0:
        return []
    k = max(1, min(k, n))
    clusters: list[list[int]] = [[index] for index in range(n)]
    while len(clusters) > k:
        best_i = 0
        best_j = 1
        best_score = -1.0
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                total = 0.0
                pairs = 0
                for left in clusters[i]:
                    for right in clusters[j]:
                        total += sim[left][right]
                        pairs += 1
                score = total / pairs if pairs else 0.0
                if score > best_score:
                    best_score = score
                    best_i = i
                    best_j = j
        merged = clusters[best_i] + clusters[best_j]
        clusters = [cluster for index, cluster in enumerate(clusters) if index not in {best_i, best_j}]
        clusters.append(merged)
    labels = [0] * n
    for label, members in enumerate(clusters):
        for index in members:
            labels[index] = label
    return labels


def _agglomerative_merge_heights(sim: list[list[float]]) -> list[float]:
    """Average-linkage merge similarities from n clusters down to 1."""
    n = len(sim)
    if n <= 1:
        return []
    clusters: list[list[int]] = [[index] for index in range(n)]
    heights: list[float] = []
    while len(clusters) > 1:
        best_i = 0
        best_j = 1
        best_score = -1.0
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                total = 0.0
                pairs = 0
                for left in clusters[i]:
                    for right in clusters[j]:
                        total += sim[left][right]
                        pairs += 1
                score = total / pairs if pairs else 0.0
                if score > best_score:
                    best_score = score
                    best_i = i
                    best_j = j
        heights.append(best_score)
        merged = clusters[best_i] + clusters[best_j]
        clusters = [cluster for index, cluster in enumerate(clusters) if index not in {best_i, best_j}]
        clusters.append(merged)
    return heights


def _choose_optimal_theme_labels(sim: list[list[float]], weights: list[int]) -> list[int]:
    """
    Choose k from the largest drop in agglomerative merge similarity
    (dendrogram gap). This is data-driven and avoids silhouette's bias
    toward too many clusters on short TF-IDF texts.
    """
    del weights
    n = len(sim)
    if n <= 1:
        return [0] * n

    heights = _agglomerative_merge_heights(sim)
    # heights[m] = similarity used to go from (n-m) -> (n-m-1) clusters.
    best_merges = n - 1
    best_gap = float("-inf")
    for merge_count in range(1, n):
        prev_height = heights[merge_count - 1]
        next_height = heights[merge_count] if merge_count < len(heights) else 0.0
        gap = prev_height - next_height
        k_after = n - merge_count
        if k_after < 1 or k_after > _MAX_FREE_TEXT_THEMES:
            continue
        # Prefer clearer gaps; tiny ties break toward fewer themes.
        score = gap + 0.01 * (1.0 / k_after)
        if score > best_gap:
            best_gap = score
            best_merges = merge_count

    gap_k = max(1, min(_MAX_FREE_TEXT_THEMES, n - best_merges))
    return _average_linkage_labels(sim, gap_k)


def _cluster_text_values(values: list[str]) -> list[dict[str, Any]]:
    """Cluster free-text answers with TF-IDF cosine similarity and automatic k."""
    cleaned = [" ".join(str(value or "").split()).strip() for value in values]
    cleaned = [text for text in cleaned if text]
    if not cleaned:
        return []

    # Collapse exact normalized duplicates first (punctuation/case only).
    seed_buckets: dict[str, dict[str, Any]] = {}
    for text in cleaned:
        key = _normalize_text_theme(text) or text.lower()
        bucket = seed_buckets.get(key)
        if bucket is None:
            bucket = {"count": 0, "label_counts": Counter(), "representative": text}
            seed_buckets[key] = bucket
        bucket["count"] += 1
        bucket["label_counts"][text] += 1

    seeds = list(seed_buckets.values())
    n = len(seeds)
    if n == 1:
        label_counts: Counter[str] = seeds[0]["label_counts"]
        ordered = sorted(label_counts.items(), key=lambda item: (-item[1], len(item[0]), item[0]))
        return [
            {
                "value": ordered[0][0],
                "count": int(seeds[0]["count"]),
                "samples": [text for text, _count in ordered[:3]],
            }
        ]

    documents = []
    for seed in seeds:
        label_counts = seed["label_counts"]
        ordered = sorted(label_counts.items(), key=lambda item: (-item[1], len(item[0]), item[0]))
        documents.append(ordered[0][0])
        seed["representative"] = ordered[0][0]

    vectors = _tfidf_vectors(documents)
    sim = _cosine_similarity_matrix(vectors)
    weights = [int(seed["count"]) for seed in seeds]
    labels = _choose_optimal_theme_labels(sim, weights)

    merged: dict[int, dict[str, Any]] = {}
    for index, label in enumerate(labels):
        bucket = merged.get(label)
        if bucket is None:
            bucket = {"count": 0, "label_counts": Counter()}
            merged[label] = bucket
        bucket["count"] += int(seeds[index]["count"])
        bucket["label_counts"].update(seeds[index]["label_counts"])

    ranked: list[dict[str, Any]] = []
    for bucket in merged.values():
        label_counts = bucket["label_counts"]
        ordered = sorted(label_counts.items(), key=lambda item: (-item[1], len(item[0]), item[0]))
        ranked.append(
            {
                "value": ordered[0][0],
                "count": int(bucket["count"]),
                "samples": [text for text, _count in ordered[:3]],
            }
        )
    ranked.sort(key=lambda item: (-int(item["count"]), str(item["value"])))
    return ranked


def _prose_theme_summary(answer_count: int, ranked_counts: list[dict[str, Any]]) -> str | None:
    """Write a short narrative rollup — theme chips carry the full inventory."""
    if answer_count <= 0 or not ranked_counts:
        return None
    if len(ranked_counts) == 1:
        return 'All {} answers converge on one theme: "{}".'.format(
            answer_count,
            str(ranked_counts[0]["value"]),
        )

    primary = ranked_counts[0]
    secondary = ranked_counts[1]
    primary_count = int(primary["count"])
    secondary_count = int(secondary["count"])
    primary_label = str(primary["value"])
    secondary_label = str(secondary["value"])
    smaller = ranked_counts[2:]
    smaller_answers = sum(int(item["count"]) for item in smaller)

    if primary_count + secondary_count >= max(2, int(round(answer_count * 0.65))):
        summary = (
            'Across {} answers, the dominant themes are "{}" ({}) and "{}" ({}).'.format(
                answer_count,
                primary_label,
                primary_count,
                secondary_label,
                secondary_count,
            )
        )
        if smaller_answers > 0:
            summary = summary[:-1] + ", with {} more in {} smaller theme{}.".format(
                smaller_answers,
                len(smaller),
                "" if len(smaller) == 1 else "s",
            )
        return summary

    summary = (
        'Across {} answers, responses form {} themes. The largest is "{}" ({}), '
        'followed by "{}" ({}).'.format(
            answer_count,
            len(ranked_counts),
            primary_label,
            primary_count,
            secondary_label,
            secondary_count,
        )
    )
    if smaller_answers > 0:
        summary += " The remaining {} answers fall into {} smaller theme{}.".format(
            smaller_answers,
            len(smaller),
            "" if len(smaller) == 1 else "s",
        )
    return summary


def _aggregate_textual(entries: list[dict[str, Any]]) -> dict[str, Any]:
    values = [str(entry.get("value") or "").strip() for entry in entries if str(entry.get("value") or "").strip()]
    ranked_counts = _cluster_text_values(values)
    unique_count = len(ranked_counts)
    # One representative sample per theme (not a global top-N dump).
    samples = [str(item["value"]) for item in ranked_counts[:8]]
    summary = _prose_theme_summary(len(values), ranked_counts)
    return {
        "count": len(values),
        "uniqueCount": unique_count,
        "samples": samples,
        "counts": ranked_counts,
        "summary": summary,
        "summaryType": "heuristic" if summary else None,
    }


def _sample_values(entries: list[dict[str, Any]], *, limit: int) -> list[str]:
    values: list[str] = []
    for entry in entries:
        rendered = _value_to_sample_string(entry.get("value"))
        if not rendered:
            continue
        if rendered in values:
            continue
        values.append(rendered)
        if len(values) >= limit:
            break
    return values


def _value_to_sample_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _shorten(value)
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        return _shorten(json.dumps(value, ensure_ascii=False, sort_keys=True))
    except TypeError:
        return _shorten(str(value))


def _shorten(value: str, *, limit: int = 2000) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"
