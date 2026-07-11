#!/usr/bin/env python3
"""Extract Stack Overflow respondent personas through the OpenRouter API.

The prompt and profile construction mirror
``persona/human_extraction/notebooks/extract_personas_stackoverflow.ipynb``.
The safe default is a dry run: every survey-result CSV in the requested year
directories is parsed and validated, and no HTTP request is created or sent.

Examples:
    python scripts/extract_personas_stackoverflow_api.py
    python scripts/extract_personas_stackoverflow_api.py --year 2025 --execute
    python scripts/extract_personas_stackoverflow_api.py --year 2025 --execute --limit 10
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence
import unicodedata


REPO_ROOT = Path(__file__).resolve().parents[1]
HUMAN_EXTRACTION_ROOT = REPO_ROOT / "persona" / "human_extraction"
DEFAULT_SURVEY_ROOT = HUMAN_EXTRACTION_ROOT / "data" / "stackoverflow_survey"
DEFAULT_ENV_FILE = HUMAN_EXTRACTION_ROOT / ".env"
DIMENSIONS_JSON = REPO_ROOT / "persona" / "schema" / "dimensions.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

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
DEFAULT_MODEL = "Qwen/Qwen3.6-35B-A3B"
DEFAULT_OUTPUT_TEMPLATE = "extraction_stackoverflow_{year}.jsonl"
DEFAULT_REQUEST_LOG_TEMPLATE = "extraction_openrouter_{year}_requests.jsonl"
MISSING_TOKENS = {"", "na", "n/a", "none", "nan", "null", "<na>"}
MAX_PROFILE_CHARS = 24_000
CSV_FIELD_SIZE_LIMIT = 100_000_000


@dataclass(frozen=True)
class DimensionChunk:
    category: str
    dimensions: list[dict[str, Any]]


@dataclass
class ParseStats:
    rows: int = 0
    empty_response_ids: int = 0
    truncated_profiles: int = 0
    min_profile_chars: int | None = None
    max_profile_chars: int = 0

    def add_profile(self, profile: str, *, was_truncated: bool) -> None:
        length = len(profile)
        self.rows += 1
        self.min_profile_chars = (
            length if self.min_profile_chars is None else min(self.min_profile_chars, length)
        )
        self.max_profile_chars = max(self.max_profile_chars, length)
        self.truncated_profiles += int(was_truncated)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year",
        choices=("all", "2023", "2024", "2025"),
        default="all",
        help="Survey year. Dry-run defaults to all years.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Send OpenRouter requests. Without this flag, perform a dry run only.",
    )
    parser.add_argument("--survey-root", type=Path, default=DEFAULT_SURVEY_ROOT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--model", default=os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL))
    parser.add_argument("--start-row", type=int, default=0)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum rows per year for live extraction. Dry-run always parses all rows.",
    )
    parser.add_argument("--dimensions-per-chunk", type=int, default=50)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path (only valid when one year is selected).",
    )
    parser.add_argument(
        "--request-log",
        type=Path,
        default=None,
        help="Per-chunk OpenRouter request JSONL (only valid for one specific year).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace output instead of resuming completed row indexes.",
    )
    args = parser.parse_args(argv)

    if args.start_row < 0:
        parser.error("--start-row must be at least 0")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.dimensions_per_chunk < 1:
        parser.error("--dimensions-per-chunk must be at least 1")
    if args.max_tokens < 1 or args.timeout < 1 or args.max_retries < 0:
        parser.error("token, timeout, and retry settings must be non-negative")
    if (args.output is not None or args.request_log is not None) and args.year == "all":
        parser.error("--output and --request-log require one specific --year")
    return args


def requested_years(value: str) -> list[int]:
    return sorted(SURVEY_FILES) if value == "all" else [int(value)]


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding the process environment."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0:1] == value[-1:] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


def is_present(value: Any) -> bool:
    return value is not None and str(value).strip().lower() not in MISSING_TOKENS


def clean_value(value: Any, max_chars: int = 800) -> str:
    text = str(value).strip().replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "..."
    return text


def load_mapping(path: Path) -> dict[str, dict[str, str]]:
    required = {
        "column",
        "section",
        "matched_qname",
        "response_suffix",
        "description",
    }
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing mapping columns: {sorted(missing)}")
        mapping: dict[str, dict[str, str]] = {}
        for row in reader:
            column = row["column"]
            if not column:
                raise ValueError(f"{path} contains an empty mapped column")
            if column in mapping:
                raise ValueError(f"{path} maps {column!r} more than once")
            mapping[column] = {
                "section": row.get("section") or "Other survey answers",
                "matched_qname": row.get("matched_qname") or "",
                "response_suffix": row.get("response_suffix") or "",
                "description": row.get("description") or column,
            }
    return mapping


def survey_reader(path: Path) -> tuple[csv.DictReader, Any]:
    csv.field_size_limit(CSV_FIELD_SIZE_LIMIT)
    handle = path.open("r", encoding="utf-8-sig", newline="")
    reader = csv.DictReader(handle)
    if not reader.fieldnames:
        handle.close()
        raise ValueError(f"{path} has no CSV header")
    duplicates = sorted(
        name for name in set(reader.fieldnames) if reader.fieldnames.count(name) > 1
    )
    if duplicates:
        handle.close()
        raise ValueError(f"{path} has duplicate columns: {duplicates}")
    return reader, handle


def iter_survey_rows(path: Path) -> Iterator[tuple[int, dict[str, str]]]:
    reader, handle = survey_reader(path)
    try:
        for row_index, row in enumerate(reader):
            if None in row:
                raise ValueError(
                    f"{path}, data row {row_index + 2}: more values than header columns"
                )
            if any(value is None for value in row.values()):
                raise ValueError(
                    f"{path}, data row {row_index + 2}: fewer values than header columns"
                )
            yield row_index, row  # type: ignore[misc]
    finally:
        handle.close()


def assemble_stackoverflow_profile(
    row: dict[str, Any], year: int, mapping: dict[str, dict[str, str]]
) -> tuple[str, bool]:
    items_by_section: dict[str, list[tuple[str, str, str]]] = OrderedDict()
    for column, value in row.items():
        if column == "completeness" or not is_present(value):
            continue
        mapping_entry = mapping.get(column, {})
        section = mapping_entry.get("section") or "Other survey answers"
        label = mapping_entry.get("description") or column
        items_by_section.setdefault(section, []).append(
            (column, label, clean_value(value))
        )

    response_id = row.get("ResponseId", "unknown")
    header = [
        f"Stack Overflow Developer Survey respondent profile — year={year}, "
        f"response_id={response_id}."
    ]
    completeness = row.get("completeness")
    if is_present(completeness):
        header.append(f"Answer completeness score: {completeness}.")

    lines = [" ".join(header)]
    for section, items in items_by_section.items():
        lines.extend(("", f"## {section}"))
        for column, label, value in items:
            if label != column:
                lines.append(f"- {column} — {label}: {value}")
            else:
                lines.append(f"- {column}: {value}")

    full_profile = "\n".join(lines)
    return full_profile[:MAX_PROFILE_CHARS], len(full_profile) > MAX_PROFILE_CHARS


def load_dimension_chunks(per_chunk: int) -> list[DimensionChunk]:
    schema = json.loads(DIMENSIONS_JSON.read_text(encoding="utf-8"))
    dimensions = schema.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError(f"No dimensions found in {DIMENSIONS_JSON}")

    by_category: dict[str, list[dict[str, Any]]] = OrderedDict()
    seen_ids: set[str] = set()
    for dimension in dimensions:
        dimension_id = str(dimension.get("id") or "")
        if not dimension_id or dimension_id in seen_ids:
            raise ValueError(f"Invalid or duplicate dimension id: {dimension_id!r}")
        seen_ids.add(dimension_id)
        category = str(dimension.get("category", "Uncategorized"))
        by_category.setdefault(category, []).append(dimension)

    chunks: list[DimensionChunk] = []
    for category, category_dimensions in by_category.items():
        for start in range(0, len(category_dimensions), per_chunk):
            chunks.append(
                DimensionChunk(category, category_dimensions[start : start + per_chunk])
            )
    return chunks

def normalize_prompt_text(value: Any) -> str:
    """Normalize text and remove invisible/control characters from prompts."""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    return "".join(
        character
        for character in text
        if character in "\n\t" or unicodedata.category(character) not in {"Cc", "Cf"}
    )
def build_stackoverflow_prompt(
    profile_text: str, dimensions: list[dict[str, Any]]
) -> str:
    """Build the sparse persona prompt from the source notebook."""
    profile_text = normalize_prompt_text(profile_text)
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
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", "value": "<one allowed value, copied verbatim>", "confidence": 0.0, "evidence": "<short quote copied from the respondent profile>", "description": "<1-2 sentence description of this respondent for this attribute>", "assignment_type": "direct"}]}',
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
        '- Good evidence example: "TechEndorse_1 - What attracts you to a technology or causes you to endorse it (most to least important)? | Sub-item: AI integration or AI Agent capabilities: 10".',
        "- Every emitted field MUST include a confidence between 0 and 1. Use high confidence only for direct or strong evidence.",
        "- Prefer direct and structured_claim assignments. Use summary_inference only for non-sensitive attributes backed by multiple concrete survey answers.",
        "- description: 1-2 concrete sentences describing THIS respondent for this attribute using survey evidence only. Do not add lifestyle, personality, or career interpretation beyond the evidence.",
        "- Do not infer personality, worldview, family status, sensitive identity, health, politics, religion, income, or housing from generic developer-survey answers.",
        "- Do not infer missing demographics, gender, sexuality, health, disability, family status, religion, ethnicity, politics, income, housing, or socioeconomic status from country, age, job title, technology stack, or developer role unless explicitly answered.",
        "- Do not infer personality traits, values, hobbies, habits, or relationship attributes from technology choices alone.",
        "- Do not infer generation from broad age buckets unless the bucket maps uniquely to one cohort.",
        "- Do not map generic Employment=Employed to Full-time unless full-time is explicitly stated; omit it if no allowed value matches exactly.",
        '- Treat "None of the above" and "None of these" as valid answers, not missing values.',
        '- When unsure, omit the dimension.',
        "- Return valid JSON only, with no markdown.",
        "",
        "RESPONDENT PROFILE:",
        profile_text,
        "",
        "DIMENSIONS (field_id - label - description - allowed values):",
    ]
    for dimension in dimensions:
        dimension_id = clean_value(dimension["id"], max_chars=200)
        label = clean_value(dimension.get("label", dimension_id), max_chars=300)
        description = clean_value(dimension.get("description", ""), max_chars=800)
        allowed = " | ".join(
            clean_value(value, max_chars=300) for value in dimension.get("values", [])
        )
        lines.append(
            f"- {dimension_id} - {label} - {description} - "
            f"[{allowed or '(free value)'}]"
        )
    return "\n".join(lines)


def parse_fields(text: str) -> list[dict[str, Any]]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("OpenRouter response contains no JSON object")
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise ValueError(f"OpenRouter response contains invalid JSON: {error}") from error
    fields = payload.get("fields") if isinstance(payload, dict) else None
    if not isinstance(fields, list) or any(not isinstance(field, dict) for field in fields):
        raise ValueError("OpenRouter response must contain a JSON object with a fields list")
    return fields


def openrouter_chat_completion(
    prompt: str,
    *,
    api_key: str,
    model: str,
    max_tokens: int,
    timeout: int,
    max_retries: int,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    request_data = json.dumps(payload).encode("utf-8")
    retryable_statuses = {408, 409, 429, 500, 502, 503, 504}

    for attempt in range(max_retries + 1):
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=request_data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/causalNLP/MatrAIx",
                "X-Title": "MatrAIx Stack Overflow Persona Extraction",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise RuntimeError("OpenRouter returned a non-text message")
            choice = body["choices"][0]
            request_details = {
                "generation_id": str(body.get("id") or ""),
                "requested_model": model,
                "response_model": str(body.get("model") or ""),
                "provider": str(body.get("provider") or ""),
                "finish_reason": choice.get("finish_reason"),
                "native_finish_reason": choice.get("native_finish_reason"),
                "usage": (
                    body.get("usage") if isinstance(body.get("usage"), dict) else {}
                ),
            }
            return content, request_details
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            if error.code not in retryable_statuses or attempt == max_retries:
                raise RuntimeError(f"OpenRouter HTTP {error.code}: {detail[:2000]}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == max_retries:
                raise RuntimeError(f"OpenRouter request failed: {error}") from error

        delay = min(60.0, 2.0**attempt) + random.uniform(0.0, 0.5)
        print(f"  transient OpenRouter error; retrying in {delay:.1f}s", flush=True)
        time.sleep(delay)

    raise AssertionError("unreachable")


def validate_mapping_coverage(
    survey_path: Path, mapping: dict[str, dict[str, str]]
) -> tuple[int, list[str]]:
    reader, handle = survey_reader(survey_path)
    try:
        columns = list(reader.fieldnames or [])
    finally:
        handle.close()
    unmapped = [column for column in columns if column not in mapping]
    # Completeness is a derived filter score and is intentionally not prompted.
    unmapped = [column for column in unmapped if column != "completeness"]
    return len(columns), unmapped


def dry_run(
    *, survey_root: Path, years: list[int], chunks: list[DimensionChunk]
) -> int:
    grand_total = 0
    files_checked = 0
    print("DRY RUN: parsing all survey-result CSVs; no API requests will be sent.")
    for year in years:
        year_dir = survey_root / str(year)
        mapping_path = survey_root / MAPPING_FILES[year]
        if not mapping_path.is_file():
            raise FileNotFoundError(f"Missing mapping CSV: {mapping_path}")
        mapping = load_mapping(mapping_path)
        result_files = sorted(year_dir.glob("results*.csv"))
        if not result_files:
            raise FileNotFoundError(f"No results CSV files found under {year_dir}")

        for survey_path in result_files:
            column_count, unmapped = validate_mapping_coverage(survey_path, mapping)
            if unmapped:
                raise ValueError(
                    f"{survey_path} has unmapped columns: {', '.join(unmapped)}"
                )
            stats = ParseStats()
            first_profile: str | None = None
            for _, row in iter_survey_rows(survey_path):
                profile, was_truncated = assemble_stackoverflow_profile(row, year, mapping)
                if first_profile is None:
                    first_profile = profile
                # Compile a complete prompt for every input row. Dimension
                # chunks are data-independent, so the first chunk exercises
                # the profile-varying side of every eventual request.
                row_prompt = build_stackoverflow_prompt(profile, chunks[0].dimensions)
                if profile not in row_prompt:
                    raise ValueError("Prompt construction dropped the respondent profile")
                if not is_present(row.get("ResponseId")):
                    stats.empty_response_ids += 1
                stats.add_profile(profile, was_truncated=was_truncated)

            if stats.rows == 0 or first_profile is None:
                raise ValueError(f"{survey_path} has no data rows")
            # Compile all schema chunks against a real profile. Combined with
            # the per-row check above, this covers both variable prompt axes
            # without materializing their very large Cartesian product.
            for chunk in chunks:
                prompt = build_stackoverflow_prompt(first_profile, chunk.dimensions)
                if "RESPONDENT PROFILE:" not in prompt or "DIMENSIONS (" not in prompt:
                    raise ValueError("Prompt construction validation failed")

            files_checked += 1
            grand_total += stats.rows
            print(
                f"PASS year={year} file={survey_path.name} rows={stats.rows:,} "
                f"columns={column_count} profile_chars={stats.min_profile_chars:,}.."
                f"{stats.max_profile_chars:,} truncated={stats.truncated_profiles:,} "
                f"empty_response_ids={stats.empty_response_ids:,}"
            )

    print(
        f"DRY RUN PASSED: files={files_checked} rows={grand_total:,} "
        f"dimension_chunks={len(chunks)} api_requests_sent=0"
    )
    return 0


def completed_row_indexes(path: Path) -> set[int]:
    completed: set[int] = set()
    if not path.is_file():
        return completed
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if record.get("backend") != "openrouter":
                    raise ValueError(
                        "record does not use the current backend format; choose a new "
                        "--output or use --overwrite"
                    )
                completed.add(int(record["row_index"]))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {error}") from error
    return completed


def output_path_for_year(args: argparse.Namespace, year: int) -> Path:
    if args.output is not None:
        return args.output
    return args.survey_root / DEFAULT_OUTPUT_TEMPLATE.format(year=year)


def request_log_path_for_year(
    args: argparse.Namespace, year: int, output_path: Path
) -> Path:
    if args.request_log is not None:
        return args.request_log
    if args.output is not None:
        return output_path.with_name(f"{output_path.stem}_requests.jsonl")
    return args.survey_root / DEFAULT_REQUEST_LOG_TEMPLATE.format(year=year)


def extract_year(
    args: argparse.Namespace,
    *,
    year: int,
    chunks: list[DimensionChunk],
    api_key: str,
) -> None:
    survey_path = args.survey_root / SURVEY_FILES[year]
    mapping_path = args.survey_root / MAPPING_FILES[year]
    if not survey_path.is_file():
        raise FileNotFoundError(f"Missing survey CSV: {survey_path}")
    if not mapping_path.is_file():
        raise FileNotFoundError(f"Missing mapping CSV: {mapping_path}")
    mapping = load_mapping(mapping_path)
    _, unmapped = validate_mapping_coverage(survey_path, mapping)
    if unmapped:
        raise ValueError(f"{survey_path} has unmapped columns: {', '.join(unmapped)}")

    output_path = output_path_for_year(args, year)
    request_log_path = request_log_path_for_year(args, year, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    request_log_path.parent.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        output_path.write_text("", encoding="utf-8")
        request_log_path.write_text("", encoding="utf-8")
    completed = completed_row_indexes(output_path)

    stop_before = None if args.limit is None else args.start_row + args.limit

    def is_selected(row_index: int) -> bool:
        return (
            row_index >= args.start_row
            and (stop_before is None or row_index < stop_before)
            and row_index not in completed
        )

    pending_count = sum(
        1 for row_index, _ in iter_survey_rows(survey_path) if is_selected(row_index)
    )
    print(f"Survey: {survey_path}")
    print(f"Pending respondents: {pending_count:,}; chunks/respondent: {len(chunks)}")
    print(f"Planned OpenRouter requests: {pending_count * len(chunks):,}")
    print(f"Model: {args.model}")
    print(f"Output: {output_path}")
    print(f"Request log: {request_log_path}")

    with (
        output_path.open("a", encoding="utf-8", newline="") as output_handle,
        request_log_path.open("a", encoding="utf-8", newline="") as request_log_handle,
    ):
        pending_rows = (
            (row_index, row)
            for row_index, row in iter_survey_rows(survey_path)
            if is_selected(row_index)
        )
        for respondent_number, (row_index, row) in enumerate(pending_rows, start=1):
            profile, _ = assemble_stackoverflow_profile(row, year, mapping)
            fields: list[dict[str, Any]] = []
            request_records: list[dict[str, Any]] = []
            for chunk_number, chunk in enumerate(chunks, start=1):
                print(
                    f"year={year} respondent={respondent_number}/{pending_count} "
                    f"row={row_index} chunk={chunk_number}/{len(chunks)} "
                    f"category={chunk.category}",
                    flush=True,
                )
                prompt = build_stackoverflow_prompt(profile, chunk.dimensions)
                content, request_details = openrouter_chat_completion(
                    prompt,
                    api_key=api_key,
                    model=args.model,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                    max_retries=args.max_retries,
                )
                fields.extend(parse_fields(content))
                request_records.append(
                    {
                        "year": year,
                        "row_index": row_index,
                        "response_id": row.get("ResponseId", ""),
                        "chunk_index": chunk_number,
                        "chunk_count": len(chunks),
                        "category": chunk.category,
                        "dimension_ids": [
                            dimension["id"] for dimension in chunk.dimensions
                        ],
                        "backend": "openrouter",
                        **request_details,
                    }
                )

            record = {
                "year": year,
                "row_index": row_index,
                "response_id": row.get("ResponseId", ""),
                "model": args.model,
                "backend": "openrouter",
                "fields": fields,
            }
            for request_record in request_records:
                request_log_handle.write(
                    json.dumps(request_record, ensure_ascii=False) + "\n"
                )
            request_log_handle.flush()
            output_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            output_handle.flush()
    print(f"Completed year {year}; output: {output_path}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    years = requested_years(args.year)
    chunks = load_dimension_chunks(args.dimensions_per_chunk)

    if not args.execute:
        return dry_run(survey_root=args.survey_root, years=years, chunks=chunks)

    load_dotenv(args.env_file)
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            f"OPENROUTER_API_KEY is not set (checked process environment and {args.env_file})"
        )
    for year in years:
        extract_year(args, year=year, chunks=chunks, api_key=api_key)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
