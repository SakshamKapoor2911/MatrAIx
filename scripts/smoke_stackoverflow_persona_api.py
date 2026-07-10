#!/usr/bin/env python3
"""Run a small Stack Overflow persona-extraction smoke test via an API endpoint."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SURVEY_ROOT = Path(
    os.environ.get(
        "STACKOVERFLOW_DATA_ROOT",
        r"D:\Yilan_Fan\study_new\AI Persona Project\Synthesize Persona\persona\curation\attribute_pool\sources\raw\global\stackoverflow_survey",
    )
)
DIMENSIONS_JSON = REPO_ROOT / "persona" / "schema" / "dimensions.json"
DEFAULT_OUT_DIR = REPO_ROOT / "persona" / "human_extraction" / "data" / "stackoverflow_api_smoke"
MISSING_TOKENS = {"", "na", "n/a", "none", "nan", "null", "<na>"}
MAX_PROFILE_CHARS = 24000

SURVEY_FILES = {
    2023: "2023/results_2023_completeness_60.csv",
    2024: "2024/results_2024_completeness_60_attention.csv",
    2025: "2025/results_2025_completeness_60.csv",
}
MAPPING_FILES = {
    2023: "2023/stackoverflow_column_mapping_2023.csv",
    2024: "2024/stackoverflow_column_mapping_2024.csv",
    2025: "2025/stackoverflow_column_mapping_2025.csv",
}
VALID_ASSIGNMENT_TYPES = {"direct", "structured_claim", "summary_inference", "unsupported"}
SUPPORTED_ASSIGNMENT_TYPES = {"direct", "structured_claim"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2025, choices=sorted(SURVEY_FILES))
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Skip this many rows from the filtered survey CSV before reading --limit rows.",
    )
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--category", default="Demographic: Core")
    parser.add_argument(
        "--all-categories",
        action="store_true",
        help="Run every persona schema category, chunked by --dims-per-chunk",
    )
    parser.add_argument("--dims-per-chunk", type=int, default=50)
    parser.add_argument(
        "--prompt-layout",
        choices=("profile-first", "dimensions-first"),
        default="profile-first",
        help=(
            "Prompt ordering for A/B tests. profile-first optimizes repeated "
            "chunks for one respondent; dimensions-first is the original layout."
        ),
    )
    parser.add_argument("--survey-root", type=Path, default=DEFAULT_SURVEY_ROOT)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.75,
        help="Keep only non-null fields with confidence at or above this threshold.",
    )
    parser.add_argument(
        "--keep-summary-inference",
        action="store_true",
        help="Keep high-confidence summary_inference fields. By default only direct and structured_claim fields are kept.",
    )
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--dry-run", action="store_true", help="Print prompt preview and exit")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def is_present(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() not in MISSING_TOKENS


def clean_value(value: Any, max_chars: int = 800) -> str:
    text = str(value).strip().replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."
    return text


def load_mapping(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return {
            row["column"]: {
                "section": row.get("section") or "Other survey answers",
                "description": row.get("description") or row["column"],
            }
            for row in reader
        }


def read_rows(path: Path, *, start: int, limit: int) -> list[dict[str, str]]:
    if start < 0:
        raise ValueError("--start must be >= 0")
    if limit < 1:
        raise ValueError("--limit must be >= 1")
    csv.field_size_limit(100_000_000)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for _ in range(start):
            next(reader, None)
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) >= limit:
                break
    return rows


def assemble_stackoverflow_profile(
    row: dict[str, Any], *, year: int, mapping: dict[str, dict[str, str]]
) -> str:
    items_by_section: dict[str, list[tuple[str, str, str]]] = OrderedDict()
    for column, value in row.items():
        if column == "completeness" or not is_present(value):
            continue
        entry = mapping.get(column, {})
        section = entry.get("section") or "Other survey answers"
        label = entry.get("description") or column
        items_by_section.setdefault(section, []).append((column, label, clean_value(value)))

    response_id = row.get("ResponseId", "unknown")
    completeness = row.get("completeness")
    header = [
        f"Stack Overflow Developer Survey respondent profile — year={year}, response_id={response_id}.",
    ]
    if is_present(completeness):
        header.append(f"Answer completeness score: {completeness}.")

    lines = [" ".join(header)]
    for section, items in items_by_section.items():
        lines.append("")
        lines.append(f"## {section}")
        for column, label, value in items:
            if label != column:
                lines.append(f"- {column} — {label}: {value}")
            else:
                lines.append(f"- {column}: {value}")
    return "\n".join(lines)[:MAX_PROFILE_CHARS]


def load_dimension_chunks(
    *,
    category: str,
    all_categories: bool,
    dims_per_chunk: int,
) -> list[tuple[str, list[dict[str, Any]]]]:
    if dims_per_chunk < 1:
        raise ValueError("--dims-per-chunk must be >= 1")
    schema = json.loads(DIMENSIONS_JSON.read_text(encoding="utf-8"))
    dimensions = schema["dimensions"]
    by_category: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for dim in dimensions:
        by_category.setdefault(str(dim.get("category", "Uncategorized")), []).append(dim)

    if all_categories:
        chunks: list[tuple[str, list[dict[str, Any]]]] = []
        for category_name, category_dims in by_category.items():
            total_parts = (len(category_dims) + dims_per_chunk - 1) // dims_per_chunk
            for index in range(0, len(category_dims), dims_per_chunk):
                part = index // dims_per_chunk + 1
                label = category_name if total_parts == 1 else f"{category_name} [{part}/{total_parts}]"
                chunks.append((label, category_dims[index : index + dims_per_chunk]))
        return chunks

    selected = [dim for dim in dimensions if dim.get("category") == category]
    if selected:
        total_parts = (len(selected) + dims_per_chunk - 1) // dims_per_chunk
        return [
            (
                category if total_parts == 1 else f"{category} [{index // dims_per_chunk + 1}/{total_parts}]",
                selected[index : index + dims_per_chunk],
            )
            for index in range(0, len(selected), dims_per_chunk)
        ]
    categories = sorted({str(dim.get("category", "Uncategorized")) for dim in dimensions})
    raise ValueError(f"Unknown category {category!r}. Available categories include: {categories[:10]}")


def build_stackoverflow_prompt(
    profile_text: str,
    dimensions: list[dict[str, Any]],
    *,
    prompt_layout: str = "profile-first",
) -> str:
    lines = [
        "You are building a persona for a single Stack Overflow Developer Survey respondent from their survey answers.",
        "",
        "The input is a structured respondent profile assembled from one survey row. It may contain evidence such as the broad categories below.",
        "These are evidence categories, not required output attributes, and they are not exhaustive across survey years.",
        "Only emit attributes from the DIMENSIONS list when directly or strongly supported by the respondent profile.",
        "- BACKGROUND: age bracket, country, education, employment, and learning history when explicitly answered.",
        "- WORK CONTEXT: developer type, years of coding, organization size, remote work, industry, purchase influence, and job satisfaction.",
        "- TECHNICAL PROFILE: languages, databases, platforms, frameworks, tools, operating systems, and development environments.",
        "- COMMUNITY BEHAVIOR: Stack Overflow visits, account status, participation, community membership, and site activities.",
        "- AI PROFILE: AI tool usage, sentiment, trust, workflow uses, perceived risks, AI agents, and free-text AI comments.",
        "- YEAR-SPECIFIC / OTHER SURVEY ANSWERS: attention checks, survey experience, technology endorsement rankings, workplace knowledge questions, tool counts, career changes, or other fields present in a given year.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim>", '
        '"confidence": 0.0, '
        '"evidence": "<short quote copied from the respondent profile>", '
        '"description": "<1-2 sentence description of this respondent for this attribute>", '
        '"assignment_type": "direct"}]}',
        "",
        "assignment_type values (Stack Overflow survey context):",
        "- direct: explicitly answered in a survey field, or a deterministic recoding of an explicit answer (for example, age bracket -> age_bracket, country -> region).",
        "- structured_claim: strongly supported by multiple concrete survey answers with little ambiguity.",
        "- summary_inference: a cautious, low-confidence inference from multiple survey answers. Use sparingly.",
        "- unsupported: not supported by the survey answers.",
        "",
        "Sparse extraction policy:",
        "- Return a sparse list: emit an object ONLY for dimensions that are clearly supported by the survey answers.",
        "- Do NOT try to cover every dimension. Missing attributes are better than weak or invented attributes.",
        "- Omit unsupported dimensions entirely. Do not emit null values and do not emit unsupported placeholder objects.",
        "- Assign a value only when the survey response directly or strongly supports that exact dimension.",
        "- If the evidence is generic, indirect, stereotypical, or only weakly associated with the dimension, omit the dimension.",
        '- If an allowed value is more specific than the survey answer, omit the dimension unless the specificity is explicit. For example, generic "Employed" does not prove "Full-time".',
        "",
        "Rules:",
        "- value MUST be exactly one of that dimension's allowed values, copied verbatim.",
        "- Every emitted field MUST include a short evidence quote copied verbatim from the respondent profile.",
        "- Evidence MUST include the original column name plus the readable question/sub-item context and the answer value.",
        '- Bad evidence examples: "10", "8", "Yes", "No", "Employed". These are bare values without the survey question context.',
        '- Good evidence example: "TechEndorse_1 — What attracts you to a technology or causes you to endorse it (most to least important)? | Sub-item: AI integration or AI Agent capabilities: 10".',
        "- Every emitted field MUST include a confidence between 0 and 1. Use high confidence only for direct or strong evidence.",
        "- Prefer direct and structured_claim assignments. Use summary_inference only for non-sensitive attributes backed by multiple concrete survey answers.",
        "- description: 1-2 concrete sentences describing THIS respondent for this attribute using survey evidence only. Do not add lifestyle, personality, or career interpretation beyond the evidence.",
        "- Do not infer personality, worldview, family status, sensitive identity, health, politics, religion, income, or housing from generic developer-survey answers.",
        "- Do not infer missing demographics, gender, sexuality, health, disability, family status, religion, ethnicity, politics, income, housing, or socioeconomic status from country, age, job title, technology stack, or developer role unless explicitly answered.",
        "- Do not infer personality traits, values, hobbies, habits, or relationship attributes from technology choices alone.",
        "- Do not infer generation from broad age buckets unless the bucket maps uniquely to one cohort.",
        "- Do not map generic Employment=Employed to Full-time unless full-time is explicitly stated; omit it if no allowed value matches exactly.",
        '- Treat "None of the above" and "None of these" as valid answers, not missing values.',
        "- When unsure, omit the dimension.",
        "- Return valid JSON only, with no markdown.",
    ]
    dimension_lines = [
        "",
        "DIMENSIONS (field_id — label — description — allowed values):",
    ]
    for dim in dimensions:
        allowed = " | ".join(str(value) for value in dim.get("values", [])) or "(free value)"
        desc = str(dim.get("description", "")).strip()
        dimension_lines.append(
            f"- {dim['id']} — {dim.get('label', dim['id'])} — {desc} — [{allowed}]"
        )

    profile_lines = ["", "RESPONDENT PROFILE:", profile_text]
    if prompt_layout == "profile-first":
        # With the respondent-outer/chunk-inner loop, all chunk requests for one
        # respondent share the long instructions + profile token prefix.
        lines.extend(profile_lines)
        lines.extend(dimension_lines)
    elif prompt_layout == "dimensions-first":
        # Original layout retained for controlled A/B performance comparisons.
        lines.extend(dimension_lines)
        lines.extend(profile_lines)
    else:
        raise ValueError(f"Unsupported prompt layout: {prompt_layout}")
    return "\n".join(lines)


def parse_fields(text: str) -> list[dict[str, Any]]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    fields = obj.get("fields") if isinstance(obj, dict) else None
    return fields if isinstance(fields, list) else []


def evidence_has_context(evidence: str) -> bool:
    stripped = evidence.strip()
    if len(stripped) < 20:
        return False
    if stripped.lower() in {"yes", "no", "true", "false", "employed"}:
        return False
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", stripped):
        return False
    # Profile lines are rendered as: Column — readable question/sub-item: answer.
    # Accept common dash variants because terminals/models may normalize them.
    has_column_question_separator = any(
        separator in stripped for separator in ("—", "–", " - ", " -- ")
    )
    return has_column_question_separator and ":" in stripped


def filter_supported_fields(
    fields: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
    *,
    min_confidence: float,
    keep_summary_inference: bool,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    dim_by_id = {str(dim["id"]): dim for dim in dimensions}
    allowed_assignment_types = set(SUPPORTED_ASSIGNMENT_TYPES)
    if keep_summary_inference:
        allowed_assignment_types.add("summary_inference")

    stats: Counter[str] = Counter()
    kept: list[dict[str, Any]] = []
    for field in fields:
        if not isinstance(field, dict):
            stats["non_dict"] += 1
            continue

        field_id = str(field.get("field_id") or "").strip()
        if field_id not in dim_by_id:
            stats["unknown_field_id"] += 1
            continue

        value = field.get("value")
        if value is None or str(value).strip().lower() in MISSING_TOKENS:
            stats["null_or_missing_value"] += 1
            continue

        assignment_type = field.get("assignment_type")
        if assignment_type not in VALID_ASSIGNMENT_TYPES:
            stats["bad_assignment_type"] += 1
            continue
        if assignment_type == "unsupported":
            stats["unsupported"] += 1
            continue
        if assignment_type not in allowed_assignment_types:
            stats["filtered_assignment_type"] += 1
            continue

        confidence = field.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            stats["bad_confidence"] += 1
            continue
        if confidence < min_confidence:
            stats["low_confidence"] += 1
            continue

        evidence = str(field.get("evidence") or "").strip()
        if not evidence:
            stats["missing_evidence"] += 1
            continue
        if not evidence_has_context(evidence):
            stats["bare_or_contextless_evidence"] += 1
            continue

        description = str(field.get("description") or "").strip()
        if not description:
            stats["missing_description"] += 1
            continue

        allowed_values = {str(allowed) for allowed in dim_by_id[field_id].get("values", [])}
        value_text = str(value).strip()
        if allowed_values and value_text not in allowed_values:
            stats["invalid_value"] += 1
            continue

        cleaned = dict(field)
        cleaned["field_id"] = field_id
        cleaned["value"] = value_text
        cleaned["confidence"] = float(confidence)
        cleaned["evidence"] = evidence
        cleaned["description"] = description
        cleaned["assignment_type"] = assignment_type
        kept.append(cleaned)

    stats["kept"] = len(kept)
    return kept, dict(stats)


def dedupe_fields(fields: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    assignment_rank = {"summary_inference": 1, "structured_claim": 2, "direct": 3}
    best_by_id: OrderedDict[str, dict[str, Any]] = OrderedDict()
    dropped = 0
    for field in fields:
        field_id = str(field.get("field_id") or "")
        current = best_by_id.get(field_id)
        if current is None:
            best_by_id[field_id] = field
            continue

        current_score = (
            assignment_rank.get(str(current.get("assignment_type")), 0),
            float(current.get("confidence") or 0),
        )
        candidate_score = (
            assignment_rank.get(str(field.get("assignment_type")), 0),
            float(field.get("confidence") or 0),
        )
        if candidate_score > current_score:
            best_by_id[field_id] = field
        dropped += 1
    return list(best_by_id.values()), dropped


def chat_completion(prompt: str, *, max_tokens: int, timeout: int) -> str:
    base_url = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("OPENAI_LLM_MODEL", "")
    missing = [
        name
        for name, value in {
            "OPENAI_BASE_URL": base_url,
            "OPENAI_API_KEY": api_key,
            "OPENAI_LLM_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {detail[:1000]}") from error
    return str(body["choices"][0]["message"]["content"])


def missing_api_environment_variables() -> list[str]:
    return [
        name
        for name in ("OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_LLM_MODEL")
        if not os.environ.get(name)
    ]


def main() -> int:
    started_at = time.monotonic()
    args = parse_args()
    if not 0 <= args.min_confidence <= 1:
        print("--min-confidence must be between 0 and 1", file=sys.stderr)
        return 2

    survey_path = args.survey_root / SURVEY_FILES[args.year]
    mapping_path = args.survey_root / MAPPING_FILES[args.year]
    if not survey_path.is_file():
        print(f"Missing survey CSV: {survey_path}", file=sys.stderr)
        return 2
    if not mapping_path.is_file():
        print(f"Missing mapping CSV: {mapping_path}", file=sys.stderr)
        return 2

    mapping = load_mapping(mapping_path)
    rows = read_rows(survey_path, start=args.start, limit=args.limit)
    chunks = load_dimension_chunks(
        category=args.category,
        all_categories=args.all_categories,
        dims_per_chunk=args.dims_per_chunk,
    )
    mode_slug = "all_categories" if args.all_categories else args.category.replace(":", "").replace(" ", "_").lower()
    layout_slug = args.prompt_layout.replace("-", "_")
    output_path = args.out or DEFAULT_OUT_DIR / f"stackoverflow_{args.year}_smoke_{args.limit}_{mode_slug}_{layout_slug}.jsonl"

    profiles = [
        assemble_stackoverflow_profile(row, year=args.year, mapping=mapping)
        for row in rows
    ]
    if args.dry_run:
        print(
            f"start={args.start} rows={len(rows)} chunks_per_row={len(chunks)} "
            f"total_prompts={len(rows) * len(chunks)}"
        )
        print(f"first_chunk={chunks[0][0]} dims={len(chunks[0][1])}")
        preview_prompt = build_stackoverflow_prompt(
            profiles[0], chunks[0][1], prompt_layout=args.prompt_layout
        )
        if args.prompt_layout == "profile-first":
            shared_prefix_end = preview_prompt.index(
                "DIMENSIONS (field_id — label — description — allowed values):"
            )
            layout_name = "instructions_profile_dimensions"
        else:
            first_dimension = f"- {chunks[0][1][0]['id']} —"
            shared_prefix_end = preview_prompt.index(first_dimension)
            layout_name = "instructions_dimensions_profile"
        print(f"prompt_layout={layout_name}")
        print(
            f"shared_prefix_chars={shared_prefix_end} "
            f"rough_shared_prefix_tokens={round(shared_prefix_end / 4)}"
        )
        print(preview_prompt[:4000])
        return 0

    missing_api_vars = missing_api_environment_variables()
    if missing_api_vars:
        print(
            "Missing environment variables: " + ", ".join(missing_api_vars),
            file=sys.stderr,
        )
        print(
            "Set them in this same terminal before running API inference.",
            file=sys.stderr,
        )
        return 2

    if output_path.exists() and not args.overwrite:
        print(f"Output already exists: {output_path}. Use --overwrite.", file=sys.stderr)
        return 2
    output_path.parent.mkdir(parents=True, exist_ok=True)

    failures = 0
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        for row, profile_text in zip(rows, profiles):
            response_id = row.get("ResponseId", "")
            merged_fields: list[dict[str, Any]] = []
            chunk_records: list[dict[str, Any]] = []
            for chunk_index, (chunk_label, dimensions) in enumerate(chunks, start=1):
                prompt = build_stackoverflow_prompt(
                    profile_text,
                    dimensions,
                    prompt_layout=args.prompt_layout,
                )
                try:
                    content = chat_completion(prompt, max_tokens=args.max_tokens, timeout=args.timeout)
                    raw_fields = parse_fields(content)
                    fields, filter_stats = filter_supported_fields(
                        raw_fields,
                        dimensions,
                        min_confidence=args.min_confidence,
                        keep_summary_inference=args.keep_summary_inference,
                    )
                    merged_fields.extend(fields)
                    chunk_records.append(
                        {
                            "chunk_index": chunk_index,
                            "category": chunk_label,
                            "dimension_count": len(dimensions),
                            "raw_field_count": len(raw_fields),
                            "field_count": len(fields),
                            "filter_stats": filter_stats,
                            "raw_response": content,
                        }
                    )
                    print(
                        f"response_id={response_id} chunk={chunk_index}/{len(chunks)} "
                        f"category={chunk_label} raw_fields={len(raw_fields)} kept_fields={len(fields)} error=False",
                        flush=True,
                    )
                except Exception as error:  # noqa: BLE001 - smoke test should keep going.
                    failures += 1
                    chunk_records.append(
                        {
                            "chunk_index": chunk_index,
                            "category": chunk_label,
                            "dimension_count": len(dimensions),
                            "raw_field_count": 0,
                            "field_count": 0,
                            "error": str(error),
                        }
                    )
                    print(
                        f"response_id={response_id} chunk={chunk_index}/{len(chunks)} "
                        f"category={chunk_label} fields=0 error=True",
                        flush=True,
                    )
            merged_fields, deduped_count = dedupe_fields(merged_fields)
            record = {
                "year": args.year,
                "response_id": response_id,
                "mode": "all_categories" if args.all_categories else "single_category",
                "requested_category": None if args.all_categories else args.category,
                "filter_config": {
                    "min_confidence": args.min_confidence,
                    "keep_summary_inference": args.keep_summary_inference,
                    "output_policy": "sparse_supported_fields_only",
                    "prompt_layout": (
                        "instructions_profile_dimensions"
                        if args.prompt_layout == "profile-first"
                        else "instructions_dimensions_profile"
                    ),
                },
                "deduped_field_count": deduped_count,
                "chunks": chunk_records,
                "fields": merged_fields,
            }
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            output_file.flush()
            print(
                f"response_id={response_id} merged_supported_fields={len(merged_fields)} "
                f"deduped={deduped_count}",
                flush=True,
            )

    print(f"Wrote {len(rows)} records to {output_path}")
    print(f"Chunk failures: {failures}")
    print(f"Elapsed seconds: {time.monotonic() - started_at:.3f}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())