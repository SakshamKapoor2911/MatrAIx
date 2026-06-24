#!/usr/bin/env python3
"""Assign Wikipedia persona seed records to persona template fields with an LLM.

This is the second stage after fetch_wikipedia_persona_seeds.py:

1. Fetch deterministic Wikipedia/Wikidata evidence.
2. Ask an LLM to assign persona template fields using only that evidence.

The output preserves the original seed record, adds per-field evidence and
confidence, and fills dimension values only when confidence is high enough.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_PROMPT = BASE_DIR / "prompts" / "wiki_persona_field_assignment.md"
DEFAULT_OUTPUT = BASE_DIR / "outputs" / "wiki_persona_field_assignments.jsonl"

DEFAULT_TARGET_FIELDS = [
    "source_entity_type",
    "region",
    "gender_identity",
    "age_bracket",
    "age",
    "birth_year",
    "death_year",
    "age_at_death",
    "domain",
    "subject_specialty",
    "role_function",
    "primary_language",
    "known_for_or_source_work",
    "creator",
    "urbanicity",
    "socioeconomic_band",
    "seniority",
    "highest_education",
    "years_experience",
    "company_size",
    "marital_status",
    "children",
    "emotional_state",
    "intent",
    "personality_big5_openness",
    "personality_big5_conscientiousness",
    "personality_big5_extraversion",
    "personality_big5_agreeableness",
    "personality_big5_neuroticism",
]

ALLOWED_ASSIGNMENT_TYPES = {
    "direct",
    "structured_claim",
    "summary_inference",
    "unsupported",
}


def log(message: str) -> None:
    print(f"[assign_wikipedia_persona_fields] {message}", file=sys.stderr)


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no} is not a JSON object")
            rows.append(value)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def compact_record(record: dict[str, Any], text_limit: int) -> dict[str, Any]:
    metadata = record.get("metadata") or {}
    persona = record.get("persona") or {}
    dimensions = persona.get("dimensions") or {}
    evidence = persona.get("source_evidence") or {}

    description = persona.get("description")
    if isinstance(description, str) and len(description) > text_limit:
        description = description[: text_limit - 3].rstrip() + "..."

    return {
        "metadata": {
            "id": metadata.get("id"),
            "entity_type": metadata.get("entity_type"),
            "wikidata_qid": metadata.get("wikidata_qid"),
            "wikipedia_title": metadata.get("wikipedia_title"),
            "wikipedia_language": metadata.get("wikipedia_language"),
        },
        "persona": {
            "name": persona.get("name"),
            "title": persona.get("title"),
            "description": description,
            "dimensions": dimensions,
            "source_evidence": evidence,
        },
    }


def build_prompt(
    *,
    prompt_template: str,
    record: dict[str, Any],
    target_fields: list[str],
    text_limit: int,
) -> str:
    payload = {
        "target_fields": target_fields,
        "record": compact_record(record, text_limit),
    }
    return (
        prompt_template.rstrip()
        + "\n\nAssign only the requested target fields.\n"
        + "Input:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()

    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end < start:
            raise
        value = json.loads(stripped[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("LLM output must be a JSON object")
    return value


def run_claude(
    *,
    prompt: str,
    claude_bin: str,
    model: str,
    max_budget_usd: float | None,
    timeout: int,
) -> dict[str, Any]:
    cmd = [
        claude_bin,
        "-p",
        "--model",
        model,
        "--output-format",
        "text",
        "--max-turns",
        "1",
        "--tools",
        "",
        "--no-session-persistence",
    ]
    if max_budget_usd is not None:
        cmd.extend(["--max-budget-usd", str(max_budget_usd)])
    cmd.append(prompt)

    result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            "Claude command failed with exit code "
            f"{result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return extract_json_object(result.stdout)


def normalize_assignment(value: dict[str, Any], field: str) -> dict[str, Any]:
    raw_confidence = value.get("confidence", 0.0)
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    assignment_type = str(value.get("assignment_type", "unsupported")).strip()
    if assignment_type not in ALLOWED_ASSIGNMENT_TYPES:
        assignment_type = "unsupported"

    assigned_value = value.get("value")
    if isinstance(assigned_value, str) and not assigned_value.strip():
        assigned_value = None
    if assignment_type == "unsupported":
        assigned_value = None
        confidence = min(confidence, 0.2)

    return {
        "field": field,
        "value": assigned_value,
        "evidence_quotes": normalize_string_list(value.get("evidence_quotes")),
        "confidence": confidence,
        "assignment_type": assignment_type,
    }


def validate_assignments(payload: dict[str, Any], target_fields: list[str]) -> list[dict[str, Any]]:
    raw_assignments = payload.get("field_assignments", [])
    if not isinstance(raw_assignments, list):
        raise ValueError("LLM output field_assignments must be a list")

    by_field: dict[str, dict[str, Any]] = {}
    for raw in raw_assignments:
        if not isinstance(raw, dict):
            continue
        field = str(raw.get("field", "")).strip()
        if field in target_fields:
            by_field[field] = normalize_assignment(raw, field)

    normalized: list[dict[str, Any]] = []
    for field in target_fields:
        normalized.append(
            by_field.get(
                field,
                {
                    "field": field,
                    "value": None,
                    "evidence_quotes": [],
                    "confidence": 0.0,
                    "assignment_type": "unsupported",
                },
            )
        )
    return normalized


def apply_assignments(
    record: dict[str, Any],
    assignments: list[dict[str, Any]],
    *,
    min_confidence: float,
    overwrite_existing: bool,
) -> dict[str, Any]:
    enriched = copy.deepcopy(record)
    persona = enriched.setdefault("persona", {})
    dimensions = persona.setdefault("dimensions", {})

    applied_fields: list[str] = []
    for assignment in assignments:
        value = assignment.get("value")
        field = assignment["field"]
        confidence = assignment.get("confidence", 0.0)
        if value is None or confidence < min_confidence:
            continue
        if not overwrite_existing and dimensions.get(field) not in (None, "", []):
            continue
        dimensions[field] = value
        applied_fields.append(field)

    persona["llm_field_assignments"] = assignments
    persona["llm_assignment_summary"] = {
        "applied_fields": applied_fields,
        "min_confidence": min_confidence,
        "overwrite_existing": overwrite_existing,
    }
    return enriched


def dry_run_assignments(record: dict[str, Any], target_fields: list[str]) -> list[dict[str, Any]]:
    dimensions = (record.get("persona") or {}).get("dimensions") or {}
    assignments: list[dict[str, Any]] = []
    for field in target_fields:
        value = dimensions.get(field)
        assignments.append(
            {
                "field": field,
                "value": value if value not in ("", [], None) else None,
                "evidence_quotes": [],
                "confidence": 1.0 if value not in ("", [], None) else 0.0,
                "assignment_type": "structured_claim" if value not in ("", [], None) else "unsupported",
            }
        )
    return assignments


def parse_target_fields(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_TARGET_FIELDS
    fields = [field.strip() for field in value.split(",") if field.strip()]
    if not fields:
        raise ValueError("--target-fields cannot be empty")
    return fields


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Input wiki persona seed JSONL.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--target-fields", help="Comma-separated target field names.")
    parser.add_argument("--text-limit", type=int, default=1600)
    parser.add_argument("--min-confidence", type=float, default=0.75)
    parser.add_argument("--overwrite-existing-values", action="store_true")
    parser.add_argument("--backend", choices=["claude_code", "dry_run"], default="claude_code")
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--max-budget-usd", type=float, default=0.15)
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    if args.text_limit <= 0:
        raise ValueError("--text-limit must be positive")
    if not 0 <= args.min_confidence <= 1:
        raise ValueError("--min-confidence must be between 0 and 1")
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"{args.output} exists; use --overwrite")

    target_fields = parse_target_fields(args.target_fields)
    rows = read_jsonl(args.input, limit=args.limit)
    prompt_template = args.prompt.read_text(encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as out_fh:
        for index, row in enumerate(rows, start=1):
            record_id = (row.get("metadata") or {}).get("id", f"record_{index}")
            log(f"Assigning fields for {record_id}")
            if args.backend == "dry_run":
                assignments = dry_run_assignments(row, target_fields)
            else:
                prompt = build_prompt(
                    prompt_template=prompt_template,
                    record=row,
                    target_fields=target_fields,
                    text_limit=args.text_limit,
                )
                payload = run_claude(
                    prompt=prompt,
                    claude_bin=args.claude_bin,
                    model=args.model,
                    max_budget_usd=args.max_budget_usd,
                    timeout=args.timeout,
                )
                assignments = validate_assignments(payload, target_fields)

            enriched = apply_assignments(
                row,
                assignments,
                min_confidence=args.min_confidence,
                overwrite_existing=args.overwrite_existing_values,
            )
            out_fh.write(json.dumps(enriched, ensure_ascii=False) + "\n")
            out_fh.flush()

    log(f"Wrote {len(rows)} enriched record(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
