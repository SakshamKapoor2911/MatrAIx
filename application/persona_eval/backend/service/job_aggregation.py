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
REPORTING_LLM_ENABLE_ENV = "PERSONAEVAL_REPORTING_ENABLE_LLM"
REPORTING_LLM_MODEL_ENV = "PERSONAEVAL_REPORTING_LLM_MODEL"
DEFAULT_REPORTING_LLM_MODEL = "openai/gpt-4o-mini"


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
                    "summaryDirectives": resolved_summary_directives,
                    "judgeDirectives": resolved_judge_directives,
                }
            elif resolved_summary_directives and not context_meta[context_key].get("summaryDirectives"):
                context_meta[context_key]["summaryDirectives"] = resolved_summary_directives
            elif resolved_judge_directives and not context_meta[context_key].get("judgeDirectives"):
                context_meta[context_key]["judgeDirectives"] = resolved_judge_directives
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
                    }
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
    fields_by_key = {field["key"]: field for field in fields}
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
            from persona_eval.self_report_task_config import (
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
    return {
        "key": normalized_key,
        "label": _feedback_label(normalized_key, prompt=str(field.prompt or "")),
        "role": _feedback_role(normalized_key, kind),
        "kind": kind,
        "value": value,
    }


def _feedback_facet_from_heuristic(raw_key: str, raw_value: Any) -> dict[str, Any] | None:
    normalized_key = _normalized_feedback_key(raw_key)
    kind = _feedback_kind_from_value(normalized_key, raw_value)
    value = _coerce_feedback_value(kind, raw_value)
    if not _has_value(value):
        return None
    return {
        "key": normalized_key,
        "label": _feedback_label(normalized_key),
        "role": _feedback_role(normalized_key, kind),
        "kind": kind,
        "value": value,
    }


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


def _aggregate_field(
    *,
    meta: dict[str, Any],
    values: list[dict[str, Any]],
    artifact_ready_trials: int,
) -> dict[str, Any]:
    kind = str(meta.get("kind") or "")
    present_entries = [entry for entry in values if _has_value(entry.get("value"))]
    missing_count = max(artifact_ready_trials - len(present_entries), 0)
    payload = {
        **meta,
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
    relationships = _aggregate_context_relationships(facets=facets, field_values=field_values)
    if relationships:
        payload["relationships"] = relationships
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
        "model": os.environ.get(REPORTING_LLM_MODEL_ENV, DEFAULT_REPORTING_LLM_MODEL).strip()
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
    model = os.environ.get(REPORTING_LLM_MODEL_ENV, DEFAULT_REPORTING_LLM_MODEL).strip() or DEFAULT_REPORTING_LLM_MODEL
    provider, bare_model = _normalize_reporting_model(model)
    if provider != "openai":
        return None
    from persona_eval.openai_client import OpenAIChatClient

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


def _aggregate_context_relationships(
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
    relationships: list[dict[str, Any]] = []
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
        relationships.append(
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
    return relationships


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
        }
    avg = mean(numbers)
    variance = mean([(value - avg) ** 2 for value in numbers]) if len(numbers) > 1 else 0.0
    return {
        "count": len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "avg": round(avg, 4),
        "std": round(math.sqrt(variance), 4),
    }


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


def _aggregate_textual(entries: list[dict[str, Any]]) -> dict[str, Any]:
    values = [str(entry.get("value") or "").strip() for entry in entries if str(entry.get("value") or "").strip()]
    unique_values = list(dict.fromkeys(values))
    samples = unique_values[:5]
    if not values:
        summary = None
    elif len(unique_values) == 1:
        summary = 'All {} available trials reported the same text: "{}"'.format(
            len(values),
            _shorten(unique_values[0]),
        )
    else:
        summary = "Collected {} text responses across {} unique values. Examples: {}".format(
            len(values),
            len(unique_values),
            "; ".join('"{}"'.format(_shorten(sample)) for sample in samples[:3]),
        )
    return {
        "count": len(values),
        "uniqueCount": len(unique_values),
        "samples": samples,
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


def _shorten(value: str, *, limit: int = 120) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"
