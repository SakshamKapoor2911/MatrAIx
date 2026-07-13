#!/usr/bin/env python3
"""Extract Stack Overflow personas with manifest-defined structured output.

V2 uses ``schema/dimension_chunks.jsonl`` as its only chunk definition. The
safe default is a CPU-only dry run; pass ``--execute`` to load vLLM and run
inference.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence


def find_repo_root(script_path: Path) -> Path:
    script_dir = script_path.resolve().parent
    for candidate in (script_dir, *script_dir.parents):
        if (candidate / "persona" / "schema" / "dimensions.json").is_file():
            return candidate
    raise RuntimeError(
        "Could not find the MatrAIx repository root above "
        f"{script_dir}; expected persona/schema/dimensions.json"
    )


REPO_ROOT = find_repo_root(Path(__file__))
HUMAN_EXTRACTION_ROOT = REPO_ROOT / "persona" / "human_extraction"
DEFAULT_SURVEY_ROOT = HUMAN_EXTRACTION_ROOT / "data" / "stackoverflow_survey"
DIMENSIONS_JSON = REPO_ROOT / "persona" / "schema" / "dimensions.json"
DIMENSION_CHUNKS_JSONL = HUMAN_EXTRACTION_ROOT / "schema" / "dimension_chunks.jsonl"

EXPECTED_MANIFEST_VERSION = "1.0"
EXPECTED_CATALOG_SCHEMA_VERSION = "1.0"
EXPECTED_SOURCE_CATALOG_PATH = "persona/schema/dimensions.json"
EXPECTED_CHUNK_COUNT = 45
EXTRACTOR_VERSION = "stackoverflow_vllm_v2"

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

STACKOVERFLOW_2025_AI_STATUS_TO_VALUE = {
    "AIToolCurrently mostly AI": "Currently mostly AI-assisted",
    "AIToolCurrently partially AI": "Currently partially AI-assisted",
    "AIToolPlan to mostly use AI": "Plans mostly AI use",
    "AIToolPlan to partially use AI": "Plans partial AI use",
    "AIToolDon't plan to use AI for this task": "Does not plan AI use",
}
STACKOVERFLOW_2025_AI_VALUE_PRIORITY = {
    "Currently mostly AI-assisted": 5,
    "Currently partially AI-assisted": 4,
    "Plans mostly AI use": 3,
    "Plans partial AI use": 2,
    "Does not plan AI use": 1,
}
STACKOVERFLOW_2025_AI_TASK_TO_FIELD = {
    "Writing code": "ai_task_code_generation",
    "Debugging or fixing code": "ai_task_debugging_fixing",
    "Testing code": "ai_task_testing",
    "Committing and reviewing code": "ai_task_code_review",
    "Documenting code": "ai_task_documentation",
    "Creating or maintaining documentation": "ai_task_documentation",
    "Learning about a codebase": "ai_task_codebase_learning",
    "Project planning": "ai_task_project_planning",
    "Deployment and monitoring": "ai_task_deployment_monitoring",
    "Search for answers": "ai_task_search_answers",
    "Learning new concepts or technologies": "ai_task_learning_concepts",
    "Predictive analytics": "ai_task_data_generation_analytics",
    "Generating content or synthetic data": "ai_task_data_generation_analytics",
}
STACKOVERFLOW_2025_AI_TASK_FIELD_ORDER = tuple(
    dict.fromkeys(STACKOVERFLOW_2025_AI_TASK_TO_FIELD.values())
)
STACKOVERFLOW_2025_AI_TASK_FIELD_IDS = frozenset(
    STACKOVERFLOW_2025_AI_TASK_FIELD_ORDER
)
AI_HISTORY_COLUMNS = (
    "AISearchDevHaveWorkedWith",
    "AISearchHaveWorkedWith",
    "AIDevHaveWorkedWith",
)
AISELECT_ALLOWED_AGENT_FIELDS = frozenset(
    {
        "coding_agent_usage_frequency",
        "coding_agent_workflow_impact",
        "coding_agent_failure_tolerance",
    }
)
AISELECT_UNRELATED_FIELD_IDS = frozenset(
    {
        "human_help_boundary_for_ai_coding",
        "future_developer_skill_belief",
    }
)
STACKOVERFLOW_2025_RANK_FIELD_MAP = {
    "TechEndorse_1": ("coding_tool_ai_capability_importance", "importance"),
    "TechEndorse_3": ("coding_tool_api_completeness_importance", "importance"),
    "TechEndorse_8": (
        "coding_tool_reliability_latency_importance",
        "importance",
    ),
    "TechEndorse_6": ("coding_tool_open_source_importance", "importance"),
    "TechOppose_9": ("coding_tool_security_privacy_blocker", "blocker"),
    "TechOppose_16": ("coding_tool_ethics_blocker", "blocker"),
    "TechOppose_11": ("coding_tool_alternative_sensitivity", "blocker"),
    "TechOppose_13": ("coding_tool_obsolescence_blocker", "blocker"),
}
STACKOVERFLOW_2025_JOB_SAT_FIELD_MAP = {
    "JobSatPoints_2": "val_independence",
    "JobSatPoints_3": "val_community",
    "JobSatPoints_6": "val_personal_growth",
    "JobSatPoints_8": "val_security_stability",
    "JobSatPoints_13": "val_recognition",
    "JobSatPoints_14": "val_recognition",
}
STACKOVERFLOW_2025_SO_ACTION_STYLE_MAP = {
    "SO_Actions_1": "Reads / searches only",
    "SO_Actions_4": "Reads / searches only",
    "SO_Actions_3": "Votes / bookmarks",
    "SO_Actions_7": "Votes / bookmarks",
    "SO_Actions_16": "Votes / bookmarks",
    "SO_Actions_9": "Comments / discusses",
    "SO_Actions_10": "Comments / discusses",
    "SO_Actions_5": "Asks questions",
    "SO_Actions_6": "Answers questions",
}
SOFT_COMPLETION_PREFIXES = (
    "trait_",
    "cog_",
    "val_",
    "schwartz_",
    "sdt_",
    "need_",
    "big5_",
    "bfi2_",
    "mft_",
    "interpersonal_",
)
SOFT_COMPLETION_FIELD_IDS = frozenset(
    {
        "decision_style",
        "emotional_state",
        "learning_style",
    }
)
ORGANIZATION_LEVEL_COLUMNS = frozenset(
    {"OrgSize", "ProfessionalCloud", "ProfessionalTech"}
)
PERSONAL_PRACTICE_FIELD_IDS = frozenset(
    {
        "habit_backing_up_files",
        "code_testing_approach",
        "code_observability_habit",
        "debugging_strategy",
        "codebase_onboarding_style",
    }
)

DEFAULT_MODEL = "Qwen/Qwen3.6-35B-A3B"
DEFAULT_OUTPUT_TEMPLATE = "extraction_stackoverflow_v2_{year}.jsonl"
MISSING_TOKENS = {"", "na", "n/a", "none", "nan", "null", "<na>"}
MAX_PROFILE_CHARS = 36_000
MAX_EVIDENCE_CHARS = 1_200
MAX_SUMMARY_INFERENCE_CONFIDENCE = 0.7
CSV_FIELD_SIZE_LIMIT = 100_000_000
DIMENSION_ID_PATTERN = re.compile(r"[a-z][a-z0-9_]*\Z")
CHUNK_ID_PATTERN = re.compile(r"[a-z][a-z0-9_]*\Z")
BARE_NUMERIC_EVIDENCE_PATTERN = re.compile(
    r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:\s*%)?\Z"
)
BARE_CATEGORICAL_EVIDENCE = frozenset(
    {"yes", "no", "employed", "true", "false"}
)
EVIDENCE_SOURCE_CITATION_PATTERN = re.compile(
    r"(?:^|[;\n]\s*)([A-Za-z][A-Za-z0-9_']*(?: [A-Za-z][A-Za-z0-9_']*)*)"
    r"\s*(?==| - )"
)
EVIDENCE_META_REASONING_PATTERN = re.compile(
    r"\b(?:i will|i'll|let's|let me|wait|actually|re-?evaluat(?:e|ing|ion)|re-read)\b"
    r"|\b(?:the\s+)?prompt(?:['’]s)?\s+"
    r"(?:says|states|instructs|requires|asks|allows|guidance|instructions?)\b"
    r"|\b(?:i\s+(?:must|should)\s+omit|should\s+be\s+omitted)\b"
    r"|\b(?:unsupported\s+dimension|zero\s+evidence)\b",
    re.IGNORECASE,
)
WORK_LOCATION_PREFERENCE_PATTERN = re.compile(
    r"\b(?:prefer|preference|like|enjoy|favor|favour|want|would rather)\b"
    r".{0,80}\b(?:remote|office|in[- ]person|on[- ]site|hybrid)\b"
    r"|\b(?:remote|office|in[- ]person|on[- ]site|hybrid)\b"
    r".{0,80}\b(?:prefer|preference|like|enjoy|favor|favour|want|would rather)\b",
    re.IGNORECASE,
)
ASSIGNMENT_TYPES = (
    "direct",
    "structured_claim",
    "summary_inference",
    "unsupported",
)
FIELD_KEYS = frozenset(
    {
        "field_id",
        "value",
        "confidence",
        "evidence",
        "assignment_type",
    }
)


class ManifestValidationError(ValueError):
    """The checked-in chunk manifest is stale, corrupt, or inconsistent."""


@dataclass(frozen=True)
class DimensionChunk:
    chunk_id: str
    label: str
    description: str
    source_categories: tuple[str, ...]
    dimensions: tuple[dict[str, Any], ...]

    @property
    def dimension_ids(self) -> tuple[str, ...]:
        return tuple(dimension["id"] for dimension in self.dimensions)


@dataclass(frozen=True)
class DimensionManifest:
    version: str
    source_catalog_sha256: str
    chunks: tuple[DimensionChunk, ...]


@dataclass
class YearWork:
    year: int
    survey_path: Path
    mapping: dict[str, dict[str, str]]
    output_path: Path
    completed: set[int]
    pending_count: int


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year",
        choices=("all", "2023", "2024", "2025"),
        default="2025",
        help="Survey year to process (default: 2025).",
    )
    parser.add_argument("--survey-root", type=Path, default=DEFAULT_SURVEY_ROOT)
    parser.add_argument("--model", default=os.environ.get("VLLM_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path; requires one specific year.",
    )
    parser.add_argument("--start-row", type=int, default=0)
    parser.add_argument(
        "--limit", type=int, default=None, help="Maximum rows after --start-row."
    )
    parser.add_argument(
        "--batch-profiles",
        type=int,
        default=16,
        help="Respondents per same-schema vLLM call/checkpoint.",
    )
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--max-num-seqs", type=int, default=128)
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--pipeline-parallel-size", type=int, default=1)
    parser.add_argument(
        "--distributed-executor-backend",
        choices=("auto", "mp", "ray"),
        default="auto",
        help="vLLM worker backend; 'auto' uses vLLM's default.",
    )
    parser.add_argument(
        "--quantization", default="none", help="vLLM method, or 'none'."
    )
    parser.add_argument("--download-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace output instead of resuming."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Load vLLM and extract; otherwise perform a GPU-free dry run.",
    )
    args = parser.parse_args(argv)

    positive = {
        "--batch-profiles": args.batch_profiles,
        "--max-tokens": args.max_tokens,
        "--max-model-len": args.max_model_len,
        "--max-num-seqs": args.max_num_seqs,
        "--tensor-parallel-size": args.tensor_parallel_size,
        "--pipeline-parallel-size": args.pipeline_parallel_size,
    }
    for name, value in positive.items():
        if value < 1:
            parser.error(f"{name} must be at least 1")
    if args.start_row < 0:
        parser.error("--start-row must be at least 0")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if not 0 < args.gpu_memory_utilization <= 1:
        parser.error("--gpu-memory-utilization must be in (0, 1]")
    if args.output is not None and args.year == "all":
        parser.error("--output requires one specific --year")
    return args


def requested_years(value: str) -> list[int]:
    return sorted(SURVEY_FILES) if value == "all" else [int(value)]


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestValidationError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _load_json(text: str, *, source: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_object_without_duplicate_keys)
    except json.JSONDecodeError as error:
        raise ManifestValidationError(f"{source} is not valid JSON: {error}") from error


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_authoritative_catalog(path: Path) -> dict[str, Any]:
    try:
        catalog = _load_json(path.read_text(encoding="utf-8"), source=str(path))
    except FileNotFoundError as error:
        raise ManifestValidationError(f"authoritative catalog not found: {path}") from error
    if not isinstance(catalog, dict):
        raise ManifestValidationError("authoritative catalog root must be an object")
    if catalog.get("schemaVersion") != EXPECTED_CATALOG_SCHEMA_VERSION:
        raise ManifestValidationError(
            "unexpected authoritative catalog schemaVersion: "
            f"{catalog.get('schemaVersion')!r}; expected {EXPECTED_CATALOG_SCHEMA_VERSION!r}"
        )
    dimensions = catalog.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise ManifestValidationError(
            "authoritative catalog dimensions must be a non-empty array"
        )
    if catalog.get("targetDimensions") != len(dimensions):
        raise ManifestValidationError(
            "authoritative targetDimensions does not match dimensions length"
        )

    seen: set[str] = set()
    required = {"id", "label", "category", "description", "values", "index"}
    for expected_index, dimension in enumerate(dimensions, start=1):
        if not isinstance(dimension, dict):
            raise ManifestValidationError(
                f"authoritative dimension {expected_index} must be an object"
            )
        missing = required - dimension.keys()
        if missing:
            raise ManifestValidationError(
                f"authoritative dimension {expected_index} is missing {sorted(missing)}"
            )
        dimension_id = dimension["id"]
        if not isinstance(dimension_id, str) or not DIMENSION_ID_PATTERN.fullmatch(
            dimension_id
        ):
            raise ManifestValidationError(
                f"invalid authoritative dimension id at {expected_index}: {dimension_id!r}"
            )
        if dimension_id in seen:
            raise ManifestValidationError(
                f"duplicate authoritative dimension id: {dimension_id}"
            )
        seen.add(dimension_id)
        if dimension["index"] != expected_index:
            raise ManifestValidationError(
                f"authoritative dimension {dimension_id} has index "
                f"{dimension['index']!r}; expected {expected_index}"
            )
        values = dimension["values"]
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(value, str) or not value for value in values)
            or len(values) != len(set(values))
        ):
            raise ManifestValidationError(
                f"authoritative dimension {dimension_id} has invalid values"
            )
    return catalog


def _expect_nonempty_string(value: Any, *, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{location} must be a non-empty string")
    return value


def load_dimension_manifest(
    manifest_path: Path = DIMENSION_CHUNKS_JSONL,
    catalog_path: Path = DIMENSIONS_JSON,
) -> DimensionManifest:
    """Load and exhaustively validate the checked-in chunk manifest."""
    catalog = load_authoritative_catalog(catalog_path)
    authoritative_dimensions: list[dict[str, Any]] = catalog["dimensions"]
    authoritative_by_id = {
        dimension["id"]: dimension for dimension in authoritative_dimensions
    }
    authoritative_ids = set(authoritative_by_id)
    catalog_hash = canonical_sha256(catalog)

    try:
        raw_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ManifestValidationError(f"chunk manifest not found: {manifest_path}") from error
    if not raw_lines:
        raise ManifestValidationError(f"chunk manifest is empty: {manifest_path}")

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            raise ManifestValidationError(
                f"blank JSONL record at {manifest_path}:{line_number}"
            )
        record = _load_json(line, source=f"{manifest_path}:{line_number}")
        if not isinstance(record, dict):
            raise ManifestValidationError(
                f"manifest record {line_number} must be an object"
            )
        records.append(record)

    first_context = records[0].get("manifest_context")
    if not isinstance(first_context, dict):
        raise ManifestValidationError("manifest record 1 has invalid manifest_context")
    chunk_count = first_context.get("chunk_count")
    if not isinstance(chunk_count, int) or isinstance(chunk_count, bool):
        raise ManifestValidationError("manifest chunk_count must be an integer")
    if chunk_count != len(records):
        raise ManifestValidationError(
            f"manifest declares {chunk_count} chunks but contains {len(records)} records"
        )
    if chunk_count != EXPECTED_CHUNK_COUNT:
        raise ManifestValidationError(
            f"unexpected manifest chunk_count {chunk_count}; "
            f"expected {EXPECTED_CHUNK_COUNT} for manifest version "
            f"{EXPECTED_MANIFEST_VERSION}"
        )

    stable_context = {
        key: value for key, value in first_context.items() if key != "chunk_number"
    }
    if stable_context.get("manifest_version") != EXPECTED_MANIFEST_VERSION:
        raise ManifestValidationError(
            f"unexpected manifest version {stable_context.get('manifest_version')!r}; "
            f"expected {EXPECTED_MANIFEST_VERSION!r}"
        )
    source_context = stable_context.get("source_catalog")
    if not isinstance(source_context, dict):
        raise ManifestValidationError("manifest source_catalog context must be an object")
    expected_source_context = {
        "path": EXPECTED_SOURCE_CATALOG_PATH,
        "schema_version": catalog.get("schemaVersion"),
        "canonical_json_sha256": catalog_hash,
        "dimension_count": len(authoritative_dimensions),
    }
    if source_context != expected_source_context:
        raise ManifestValidationError(
            "manifest source_catalog context is stale or corrupt: "
            f"found {source_context!r}; expected {expected_source_context!r}"
        )
    grouping = stable_context.get("grouping")
    if not isinstance(grouping, dict) or not grouping:
        raise ManifestValidationError("manifest grouping context must be a non-empty object")
    required_grouping = {
        "strategy",
        "dimension_order",
        "target_size",
        "preferred_min_size",
        "preferred_max_size",
        "size_exception_policy",
    }
    if set(grouping) != required_grouping:
        raise ManifestValidationError(
            "manifest grouping context has unexpected keys: "
            f"{sorted(set(grouping) ^ required_grouping)}"
        )
    if grouping.get("dimension_order") != (
        "ascending authoritative dimension index within each chunk"
    ):
        raise ManifestValidationError("manifest has an unexpected dimension_order policy")

    chunks: list[DimensionChunk] = []
    seen_chunk_ids: set[str] = set()
    seen_dimension_ids: set[str] = set()
    required_record_keys = {
        "chunk_id",
        "label",
        "description",
        "source_categories",
        "size",
        "dimension_ids",
        "dimensions",
        "manifest_context",
    }
    allowed_record_keys = required_record_keys | {"size_exception"}

    for line_number, record in enumerate(records, start=1):
        missing_keys = required_record_keys - record.keys()
        extra_keys = record.keys() - allowed_record_keys
        if missing_keys or extra_keys:
            raise ManifestValidationError(
                f"manifest record {line_number} has missing keys {sorted(missing_keys)} "
                f"and extra keys {sorted(extra_keys)}"
            )
        context = record["manifest_context"]
        if not isinstance(context, dict):
            raise ManifestValidationError(
                f"manifest record {line_number} has invalid manifest_context"
            )
        if context.get("chunk_number") != line_number:
            raise ManifestValidationError(
                f"manifest record {line_number} declares chunk_number "
                f"{context.get('chunk_number')!r}"
            )
        comparable = {key: value for key, value in context.items() if key != "chunk_number"}
        if comparable != stable_context:
            raise ManifestValidationError(
                f"manifest context differs at record {line_number}"
            )

        chunk_id = record["chunk_id"]
        if not isinstance(chunk_id, str) or not CHUNK_ID_PATTERN.fullmatch(chunk_id):
            raise ManifestValidationError(
                f"manifest record {line_number} has invalid chunk_id {chunk_id!r}"
            )
        if chunk_id in seen_chunk_ids:
            raise ManifestValidationError(f"duplicate chunk_id: {chunk_id}")
        seen_chunk_ids.add(chunk_id)
        label = _expect_nonempty_string(record["label"], location=f"chunk {chunk_id} label")
        description = _expect_nonempty_string(
            record["description"], location=f"chunk {chunk_id} description"
        )

        source_categories = record["source_categories"]
        if (
            not isinstance(source_categories, list)
            or not source_categories
            or any(not isinstance(item, str) or not item for item in source_categories)
            or len(source_categories) != len(set(source_categories))
        ):
            raise ManifestValidationError(
                f"chunk {chunk_id} has invalid source_categories"
            )
        size = record["size"]
        dimension_ids = record["dimension_ids"]
        embedded_dimensions = record["dimensions"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 1:
            raise ManifestValidationError(f"chunk {chunk_id} has invalid size {size!r}")
        if not isinstance(dimension_ids, list) or any(
            not isinstance(item, str) for item in dimension_ids
        ):
            raise ManifestValidationError(f"chunk {chunk_id} has invalid dimension_ids")
        if not isinstance(embedded_dimensions, list) or any(
            not isinstance(item, dict) for item in embedded_dimensions
        ):
            raise ManifestValidationError(f"chunk {chunk_id} has invalid dimensions")
        if size != len(dimension_ids) or size != len(embedded_dimensions):
            raise ManifestValidationError(
                f"chunk {chunk_id} declares size {size}, has {len(dimension_ids)} IDs, "
                f"and {len(embedded_dimensions)} embedded dimensions"
            )
        embedded_ids = [dimension.get("id") for dimension in embedded_dimensions]
        if dimension_ids != embedded_ids:
            raise ManifestValidationError(
                f"chunk {chunk_id} dimension_ids do not match embedded dimensions"
            )
        if len(dimension_ids) != len(set(dimension_ids)):
            raise ManifestValidationError(
                f"chunk {chunk_id} contains duplicate dimension IDs"
            )
        duplicates_across = seen_dimension_ids.intersection(dimension_ids)
        if duplicates_across:
            raise ManifestValidationError(
                f"dimension IDs occur in multiple chunks: {sorted(duplicates_across)}"
            )

        for dimension_id, embedded in zip(dimension_ids, embedded_dimensions):
            authoritative = authoritative_by_id.get(dimension_id)
            if authoritative is None:
                raise ManifestValidationError(
                    f"chunk {chunk_id} references unknown dimension {dimension_id!r}"
                )
            if embedded != authoritative:
                raise ManifestValidationError(
                    f"chunk {chunk_id} metadata for {dimension_id} does not exactly "
                    "match persona/schema/dimensions.json"
                )
        indexes = [dimension["index"] for dimension in embedded_dimensions]
        if indexes != sorted(indexes):
            raise ManifestValidationError(
                f"chunk {chunk_id} dimensions are not in authoritative index order"
            )
        actual_categories = list(
            dict.fromkeys(dimension["category"] for dimension in embedded_dimensions)
        )
        if source_categories != actual_categories:
            raise ManifestValidationError(
                f"chunk {chunk_id} source_categories do not match its dimensions"
            )
        seen_dimension_ids.update(dimension_ids)
        chunks.append(
            DimensionChunk(
                chunk_id=chunk_id,
                label=label,
                description=description,
                source_categories=tuple(source_categories),
                dimensions=tuple(embedded_dimensions),
            )
        )

    missing = authoritative_ids - seen_dimension_ids
    extra = seen_dimension_ids - authoritative_ids
    if missing or extra or len(seen_dimension_ids) != len(authoritative_dimensions):
        raise ManifestValidationError(
            "manifest does not cover authoritative IDs exactly once: "
            f"missing={sorted(missing)[:20]}, extra={sorted(extra)[:20]}"
        )
    return DimensionManifest(
        version=EXPECTED_MANIFEST_VERSION,
        source_catalog_sha256=catalog_hash,
        chunks=tuple(chunks),
    )


def build_chunk_json_schema(chunk: DimensionChunk) -> dict[str, Any]:
    """Couple each field ID to only its own authoritative value enum."""
    branches: list[dict[str, Any]] = []
    for dimension in chunk.dimensions:
        branches.append(
            {
                "type": "object",
                "properties": {
                    "field_id": {"const": dimension["id"]},
                    "value": {"type": "string", "enum": list(dimension["values"])},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_EVIDENCE_CHARS,
                    },
                    "assignment_type": {
                        "type": "string",
                        "enum": list(ASSIGNMENT_TYPES),
                    },
                },
                "required": sorted(FIELD_KEYS),
                "additionalProperties": False,
            }
        )
    return {
        "type": "object",
        "properties": {
            "fields": {
                "type": "array",
                "maxItems": len(chunk.dimensions),
                "items": {"oneOf": branches},
            }
        },
        "required": ["fields"],
        "additionalProperties": False,
    }


def _answer_variants(answer: str) -> tuple[str, ...]:
    variants = [answer]
    if ";" in answer:
        variants.extend(part.strip() for part in answer.split(";") if part.strip())
    return tuple(dict.fromkeys(variant.casefold() for variant in variants))


def _citation_segment_has_answer(segment: str, answer: str) -> bool:
    segment_casefold = segment.casefold().strip()
    variants = _answer_variants(answer)

    def has_supported_suffix(text: str, variant: str) -> bool:
        if not text.startswith(variant):
            return False
        suffix = text[len(variant) :]
        return (
            not suffix
            or re.match(
                r"\s*(?:;|\n|\(|\[|\.\s*(?:summary\s*:|\Z)|summary\s*:)",
                suffix,
            )
            is not None
        )

    if segment_casefold.startswith("="):
        cited_answer = segment_casefold[1:].lstrip()
        return any(has_supported_suffix(cited_answer, variant) for variant in variants)
    return any(
        re.search(
            rf":\s*{re.escape(variant)}"
            rf"(?=\s*(?:\Z|;|\n|\(|\[|\.\s*(?:summary\s*:|\Z)|summary\s*:))",
            segment_casefold,
        )
        is not None
        for variant in variants
    )


def validate_evidence_style(evidence: str, *, location: str) -> None:
    """Reject overlong evidence and generated-summary deliberation leakage."""
    if len(evidence) > MAX_EVIDENCE_CHARS:
        raise ValueError(
            f"{location} must be no longer than {MAX_EVIDENCE_CHARS} characters"
        )
    summary_match = re.search(
        r"(?:\.\s*|\s+)summary\s*:\s*", evidence, re.IGNORECASE
    )
    if summary_match is None:
        return
    summary = evidence[summary_match.end() :]
    if EVIDENCE_META_REASONING_PATTERN.search(summary):
        raise ValueError(
            f"{location} contains model deliberation instead of concise evidence"
        )


def evidence_cited_columns(evidence: str) -> tuple[str, ...]:
    """Return source columns explicitly cited by an evidence string."""
    return tuple(
        dict.fromkeys(
            match.group(1).strip()
            for match in EVIDENCE_SOURCE_CITATION_PATTERN.finditer(evidence)
        )
    )


def validate_evidence_provenance(
    evidence: str, source_answers: dict[str, str], *, location: str
) -> None:
    """Require explicit, answer-consistent citations to this respondent's profile."""
    citation_matches = list(EVIDENCE_SOURCE_CITATION_PATTERN.finditer(evidence))
    citations = [match.group(1).strip() for match in citation_matches]
    if not citations:
        raise ValueError(
            f"{location} must cite at least one current respondent source column"
        )

    unknown = list(dict.fromkeys(
        column for column in citations if column not in source_answers
    ))
    if unknown:
        raise ValueError(
            f"{location} cites source columns absent from the current respondent "
            f"profile: {unknown}"
        )

    for index, (column, column_match) in enumerate(zip(citations, citation_matches)):
        segment_end = (
            citation_matches[index + 1].start()
            if index + 1 < len(citation_matches)
            else len(evidence)
        )
        citation_segment = evidence[column_match.end() : segment_end]
        if not _citation_segment_has_answer(
            citation_segment, source_answers[column]
        ):
            raise ValueError(
                f"{location} cites {column!r} without its current respondent answer"
            )


def validate_chunk_payload(
    payload: Any,
    chunk: DimensionChunk,
    source_answers: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Strictly validate one decoded response against its current chunk."""
    if not isinstance(payload, dict):
        raise ValueError("response root must be a JSON object")
    if set(payload) != {"fields"}:
        raise ValueError("response root must contain exactly the 'fields' key")
    fields = payload["fields"]
    if not isinstance(fields, list):
        raise ValueError("response fields must be a list")
    if len(fields) > len(chunk.dimensions):
        raise ValueError(
            f"response has {len(fields)} fields for a {len(chunk.dimensions)}-dimension chunk"
        )

    allowed_values = {
        dimension["id"]: set(dimension["values"]) for dimension in chunk.dimensions
    }
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for position, field in enumerate(fields):
        location = f"fields[{position}]"
        if not isinstance(field, dict):
            raise ValueError(f"{location} must be an object")
        keys = set(field)
        if keys != FIELD_KEYS:
            missing = sorted(FIELD_KEYS - keys)
            extra = sorted(keys - FIELD_KEYS)
            raise ValueError(
                f"{location} has missing keys {missing} and extra keys {extra}"
            )
        field_id = field["field_id"]
        if not isinstance(field_id, str) or field_id not in allowed_values:
            raise ValueError(
                f"{location}.field_id {field_id!r} is not in chunk {chunk.chunk_id}"
            )
        if field_id in seen:
            raise ValueError(f"duplicate field_id in chunk output: {field_id}")
        seen.add(field_id)
        value = field["value"]
        if not isinstance(value, str) or value not in allowed_values[field_id]:
            raise ValueError(
                f"{location} has invalid value {value!r} for field_id {field_id!r}"
            )
        confidence = field["confidence"]
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError(f"{location}.confidence must be a finite number in [0, 1]")
        if not isinstance(field["evidence"], str) or not field["evidence"].strip():
            raise ValueError(f"{location}.evidence must be a non-empty string")
        evidence = field["evidence"].strip()
        validate_evidence_style(evidence, location=f"{location}.evidence")
        if (
            BARE_NUMERIC_EVIDENCE_PATTERN.fullmatch(evidence)
            or evidence.casefold() in BARE_CATEGORICAL_EVIDENCE
        ):
            raise ValueError(
                f"{location}.evidence must include source context, not only "
                f"the bare answer {evidence!r}"
            )
        if source_answers is not None:
            validate_evidence_provenance(
                evidence, source_answers, location=f"{location}.evidence"
            )
        if field["assignment_type"] not in ASSIGNMENT_TYPES:
            raise ValueError(
                f"{location}.assignment_type {field['assignment_type']!r} is invalid"
            )
        cited_columns = set(evidence_cited_columns(evidence))
        if field["assignment_type"] == "summary_inference":
            if len(cited_columns) < 2:
                raise ValueError(
                    f"{location}.summary_inference must cite at least two "
                    "independent source columns"
                )
            if confidence > MAX_SUMMARY_INFERENCE_CONFIDENCE:
                raise ValueError(
                    f"{location}.summary_inference confidence must be at most "
                    f"{MAX_SUMMARY_INFERENCE_CONFIDENCE}"
                )
        is_language_field = field_id in {
            "primary_language",
            "english_proficiency",
            "multilingualism",
        } or field_id.startswith("lang_")
        if is_language_field and "Country" in cited_columns:
            raise ValueError(
                f"{location} cannot infer language from Country or residence"
            )
        validated.append(dict(field))
    return validated


def parse_and_validate_generation(
    text: str, chunk: DimensionChunk, source_answers: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"vLLM response is not exactly one JSON value: {error}") from error
    return validate_chunk_payload(payload, chunk, source_answers)


def salvage_chunk_payload(
    payload: Any,
    chunk: DimensionChunk,
    source_answers: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Keep independently valid fields and handle duplicates deterministically."""
    if not isinstance(payload, dict) or set(payload) != {"fields"}:
        raise ValueError("response root is not salvageable")
    fields = payload["fields"]
    if not isinstance(fields, list):
        raise ValueError("response fields value is not a salvageable list")

    valid_by_id: OrderedDict[str, list[tuple[int, dict[str, Any]]]] = OrderedDict()
    issues: list[str] = []
    for position, field in enumerate(fields):
        try:
            validated = validate_chunk_payload(
                {"fields": [field]}, chunk, source_answers
            )[0]
        except (IndexError, ValueError) as error:
            issues.append(f"fields[{position}] dropped: {error}")
            continue
        valid_by_id.setdefault(validated["field_id"], []).append(
            (position, validated)
        )

    kept: list[tuple[int, dict[str, Any]]] = []
    for field_id, occurrences in valid_by_id.items():
        if len(occurrences) == 1:
            kept.append(occurrences[0])
            continue
        first = occurrences[0][1]
        if all(field == first for _, field in occurrences[1:]):
            kept.append(occurrences[0])
            issues.append(
                f"field_id {field_id!r}: collapsed {len(occurrences)} exact duplicates"
            )
        else:
            issues.append(
                f"field_id {field_id!r}: dropped {len(occurrences)} conflicting duplicates"
            )
    kept.sort(key=lambda item: item[0])
    return [field for _, field in kept], issues


def parse_and_salvage_generation(
    text: str,
    chunk: DimensionChunk,
    source_answers: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"vLLM response is not exactly one JSON value: {error}") from error
    return salvage_chunk_payload(payload, chunk, source_answers)


def is_present(value: Any) -> bool:
    return value is not None and str(value).strip().lower() not in MISSING_TOKENS


def normalize_prompt_text(value: Any) -> str:
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    return "".join(
        character
        for character in text
        if character in "\n\t" or unicodedata.category(character) not in {"Cc", "Cf"}
    )


def clean_value(value: Any, max_chars: int = 800) -> str:
    text = normalize_prompt_text(value).strip()
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(text) <= max_chars:
        return text
    prefix = text[: max_chars - 3].rstrip()
    boundary = max(prefix.rfind(" "), prefix.rfind("\n"))
    if boundary >= max_chars // 2:
        prefix = prefix[:boundary].rstrip()
    return prefix + "..."


def truncate_profile(text: str, max_chars: int = MAX_PROFILE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    marker = "\n[Respondent profile truncated]"
    prefix = text[: max_chars - len(marker)]
    line_end = prefix.rfind("\n")
    if line_end > 0:
        prefix = prefix[:line_end]
    return prefix.rstrip() + marker


def load_mapping(path: Path) -> dict[str, dict[str, str]]:
    required = {"column", "section", "matched_qname", "response_suffix", "description"}
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
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed CSV data row at {path}:{row_index + 2}")
            yield row_index, row  # type: ignore[misc]
    finally:
        handle.close()


def validate_mapping_coverage(
    survey_path: Path, mapping: dict[str, dict[str, str]]
) -> None:
    reader, handle = survey_reader(survey_path)
    try:
        columns = list(reader.fieldnames or [])
    finally:
        handle.close()
    unmapped = [
        column for column in columns if column != "completeness" and column not in mapping
    ]
    if unmapped:
        raise ValueError(f"{survey_path} has unmapped columns: {', '.join(unmapped)}")


def assemble_stackoverflow_profile(
    row: dict[str, Any], year: int, mapping: dict[str, dict[str, str]]
) -> str:
    items_by_section: dict[str, list[tuple[str, str, str]]] = OrderedDict()
    for column, value in row.items():
        if column == "completeness" or not is_present(value):
            continue
        entry = mapping.get(column, {})
        clean_column = clean_value(column, max_chars=200)
        section = clean_value(
            entry.get("section") or "Other survey answers", max_chars=200
        )
        label = clean_value(entry.get("description") or column, max_chars=1_200)
        items_by_section.setdefault(section, []).append(
            (clean_column, label, clean_value(value))
        )

    response_id = clean_value(row.get("ResponseId", "unknown"), max_chars=200)
    header = [
        f"Stack Overflow Developer Survey respondent profile - year={year}, "
        f"response_id={response_id}."
    ]
    if is_present(row.get("completeness")):
        header.append(
            f"Answer completeness score: {clean_value(row['completeness'], max_chars=100)}."
        )
    lines = [" ".join(header)]
    for section, items in items_by_section.items():
        lines.extend(("", f"## {section}"))
        for column, label, value in items:
            lines.append(
                f"- {column} - {label}: {value}"
                if label != column
                else f"- {column}: {value}"
            )
    return truncate_profile("\n".join(lines))


def visible_profile_source_answers(
    row: dict[str, Any], profile_text: str
) -> dict[str, str]:
    """Index only source answers whose complete profile line survived truncation."""
    source_answers: dict[str, str] = {}
    for column, value in row.items():
        if column == "completeness" or not is_present(value):
            continue
        clean_column = clean_value(column, max_chars=200)
        if (
            f"\n- {clean_column}:" not in profile_text
            and f"\n- {clean_column} -" not in profile_text
        ):
            continue
        source_answers[clean_column] = clean_value(value)
    return source_answers


def parse_positive_integer_rank(value: Any) -> int | None:
    """Parse a positive integral survey rank without accepting arbitrary scores."""
    if not is_present(value):
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d+", text) is None:
        return None
    rank = int(text)
    return rank if rank > 0 else None


def map_2025_rank_value(rank: int, scale: str) -> str:
    """Map 2025 ordinal ranks to fixed five-level persona value scales."""
    if scale == "importance":
        if rank <= 2:
            return "Critical"
        if rank <= 5:
            return "High"
        if rank <= 9:
            return "Moderate"
        if rank <= 12:
            return "Low"
        return "Not a factor"
    if scale == "blocker":
        if rank == 1:
            return "Hard blocker"
        if rank <= 3:
            return "Major concern"
        if rank <= 7:
            return "Moderate concern"
        if rank <= 12:
            return "Minor concern"
        return "Not a concern"
    raise ValueError(f"unknown 2025 rank scale: {scale}")


def extract_2025_rank_fields(
    row: dict[str, Any], year: int, mapping: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    """Deterministically map selected 2025 ranks to schema-compatible fields."""
    if year != 2025:
        return []
    fields: list[dict[str, Any]] = []
    for column, (field_id, scale) in STACKOVERFLOW_2025_RANK_FIELD_MAP.items():
        rank = parse_positive_integer_rank(row.get(column))
        if rank is None:
            continue
        entry = mapping.get(column, {})
        label = clean_value(entry.get("description") or column, max_chars=1_000)
        evidence = f"{column} - {label}: {rank}"
        fields.append(
            {
                "field_id": field_id,
                "value": map_2025_rank_value(rank, scale),
                "confidence": 1.0,
                "evidence": evidence,
                "assignment_type": "direct",
            }
        )
    return fields


def map_2025_job_satisfaction_rank(rank: int) -> str:
    """Map a 2025 job-satisfaction rank to the shared personal-value scale."""
    if rank <= 3:
        return "Core value"
    if rank <= 6:
        return "Important"
    if rank <= 10:
        return "Moderate"
    if rank <= 13:
        return "Minor"
    return "Irrelevant"


def extract_2025_job_satisfaction_fields(
    row: dict[str, Any], year: int, mapping: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    """Map only near-isomorphic 2025 job-satisfaction ranks to value fields."""
    if year != 2025:
        return []
    candidates: dict[str, list[tuple[int, str]]] = {}
    for column, field_id in STACKOVERFLOW_2025_JOB_SAT_FIELD_MAP.items():
        rank = parse_positive_integer_rank(row.get(column))
        if rank is None:
            continue
        label = clean_value(
            mapping.get(column, {}).get("description") or column,
            max_chars=1_000,
        )
        candidates.setdefault(field_id, []).append(
            (rank, f"{column} - {label}: {rank}")
        )
    fields: list[dict[str, Any]] = []
    for field_id, ranked_evidence in candidates.items():
        rank, evidence = min(ranked_evidence, key=lambda item: item[0])
        fields.append(
            {
                "field_id": field_id,
                "value": map_2025_job_satisfaction_rank(rank),
                "confidence": 0.9,
                "evidence": evidence,
                "assignment_type": "structured_claim",
            }
        )
    return fields


def extract_2025_stackoverflow_participation_field(
    row: dict[str, Any], year: int, mapping: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    """Map explicit non-participation or the top-ranked 2025 SO action to style."""
    if year != 2025:
        return []
    participation = row.get("SOPartFreq")
    if is_present(participation) and "never participated" in str(
        participation
    ).casefold():
        label = clean_value(
            mapping.get("SOPartFreq", {}).get("description") or "SOPartFreq",
            max_chars=1_000,
        )
        return [
            {
                "field_id": "stackoverflow_participation_style",
                "value": "Does not participate",
                "confidence": 1.0,
                "evidence": f"SOPartFreq - {label}: {clean_value(participation)}",
                "assignment_type": "direct",
            }
        ]

    candidates: list[tuple[int, str, str]] = []
    for column, style in STACKOVERFLOW_2025_SO_ACTION_STYLE_MAP.items():
        rank = parse_positive_integer_rank(row.get(column))
        if rank is None:
            continue
        label = clean_value(
            mapping.get(column, {}).get("description") or column,
            max_chars=1_000,
        )
        candidates.append((rank, style, f"{column} - {label}: {rank}"))
    if not candidates:
        return []
    rank, style, evidence = min(candidates, key=lambda item: item[0])
    return [
        {
            "field_id": "stackoverflow_participation_style",
            "value": style,
            "confidence": 0.9,
            "evidence": evidence,
            "assignment_type": "summary_inference",
        }
    ]


def reconcile_ai_fields(
    fields: list[dict[str, Any]],
    row: dict[str, Any],
    mapping: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Resolve generic-AI fan-out and current-vs-past AI usage conflicts."""
    ai_select = row.get("AISelect")
    no_current_or_planned_ai = is_present(ai_select) and str(ai_select).strip().casefold() == (
        "no, and i don't plan to"
    )
    reconciled: list[dict[str, Any]] = []
    for original in fields:
        field = dict(original)
        field_id = str(field["field_id"])
        citations = set(evidence_cited_columns(str(field.get("evidence", ""))))
        only_generic_ai_select = citations == {"AISelect"}

        unrelated_agent_completion = (
            field_id.startswith("coding_agent_")
            and field_id not in AISELECT_ALLOWED_AGENT_FIELDS
        )
        if only_generic_ai_select and (
            unrelated_agent_completion
            or field_id.startswith("coding_tool_")
            or field_id.startswith("tool_")
            or field_id in AISELECT_UNRELATED_FIELD_IDS
        ):
            continue

        if only_generic_ai_select and (
            field_id in {"att_ai", "coding_ai_usage_frequency"}
            or field_id.startswith("ai_task_")
        ):
            field["assignment_type"] = "summary_inference"
        reconciled.append(field)

    past_use_columns = [
        column for column in AI_HISTORY_COLUMNS if is_present(row.get(column))
    ]
    if not no_current_or_planned_ai or not past_use_columns:
        return reconciled

    history_column = past_use_columns[0]
    history_answer = clean_value(row[history_column])
    summary_evidence = (
        f"AISelect={clean_value(ai_select)}; "
        f"{history_column}={history_answer}. Summary: The respondent reports specific "
        "past-year AI-tool use but no current use or future adoption plan, supporting "
        "a tried-but-not-active status."
    )
    replacement = {
        "field_id": "coding_ai_usage_frequency",
        "value": "Tried but not active",
        "confidence": 0.95,
        "evidence": summary_evidence[:MAX_EVIDENCE_CHARS],
        "assignment_type": "summary_inference",
    }
    return [
        field
        for field in reconciled
        if field["field_id"] != "coding_ai_usage_frequency"
    ] + [replacement]


def filter_semantic_overreach(
    fields: list[dict[str, Any]], row: dict[str, Any]
) -> list[dict[str, Any]]:
    """Drop recurring cross-construct completions that prompts alone do not prevent."""
    filtered: list[dict[str, Any]] = []
    for field in fields:
        field_id = str(field["field_id"])
        value = str(field["value"])
        citations = set(evidence_cited_columns(str(field.get("evidence", ""))))

        intent_only_programming_skill = (
            field_id.startswith("prog_")
            and "LanguageWantToWorkWith" in citations
            and "LanguageHaveWorkedWith" not in citations
        )
        country_based_cultural_identity = (
            field_id.startswith("cult_") and "Country" in citations
        )
        country_based_mobility = (
            field_id == "lifex_geographic_mobility" and "Country" in citations
        )
        retirement_without_retirement_answer = (
            field_id == "seniority"
            and value == "Retired"
            and not any(
                "retired" in str(answer).casefold()
                for answer in row.values()
                if is_present(answer)
            )
        )
        nonparticipation_without_never_answer = (
            field_id == "stackoverflow_participation_style"
            and value == "Does not participate"
            and "never participated" not in str(row.get("SOPartFreq", "")).casefold()
        )
        git_nonuse_without_git_answer = (
            field_id == "tool_git"
            and value == "Never used"
            and not any(
                re.search(r"\bgit\b", str(row.get(column, "")), re.IGNORECASE)
                for column in citations
            )
        )
        organization_only_personal_practice = (
            field_id in PERSONAL_PRACTICE_FIELD_IDS
            and citations
            and citations <= ORGANIZATION_LEVEL_COLUMNS
        )
        is_soft_completion = field_id in SOFT_COMPLETION_FIELD_IDS or field_id.startswith(
            SOFT_COMPLETION_PREFIXES
        )
        one_source_soft_completion = (
            field.get("assignment_type") == "summary_inference"
            and is_soft_completion
            and len(citations) < 2
        )
        work_location_attitude_without_preference = (
            field_id
            in {"att_remote_work", "att_working_from_office", "pref_work_location"}
            and not any(
                WORK_LOCATION_PREFERENCE_PATTERN.search(str(row.get(column, "")))
                for column in citations
                if is_present(row.get(column))
            )
        )

        if any(
            (
                intent_only_programming_skill,
                country_based_cultural_identity,
                country_based_mobility,
                retirement_without_retirement_answer,
                nonparticipation_without_never_answer,
                git_nonuse_without_git_answer,
                organization_only_personal_practice,
                one_source_soft_completion,
                work_location_attitude_without_preference,
            )
        ):
            continue
        filtered.append(field)
    return filtered


def extract_2025_ai_task_fields(
    row: dict[str, Any], year: int, mapping: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    """Deterministically map the 2025 AITool matrix to persona task fields."""
    if year != 2025:
        return []

    candidates: dict[str, list[tuple[str, str]]] = {}
    for column, target_value in STACKOVERFLOW_2025_AI_STATUS_TO_VALUE.items():
        raw_value = row.get(column)
        if not is_present(raw_value):
            continue
        entry = mapping.get(column, {})
        clean_column = clean_value(column, max_chars=200)
        label = clean_value(entry.get("description") or column, max_chars=1_200)
        clean_raw_value = clean_value(raw_value)
        evidence = (
            f"{clean_column} - {label}: {clean_raw_value}"
            if label != clean_column
            else f"{clean_column}: {clean_raw_value}"
        )
        for item in str(raw_value).split(";"):
            task = unicodedata.normalize("NFKC", item).strip()
            field_id = STACKOVERFLOW_2025_AI_TASK_TO_FIELD.get(task)
            if field_id is not None:
                candidates.setdefault(field_id, []).append((target_value, evidence))

    fields: list[dict[str, Any]] = []
    for field_id in STACKOVERFLOW_2025_AI_TASK_FIELD_ORDER:
        field_candidates = candidates.get(field_id)
        if not field_candidates:
            continue
        selected_value = max(
            (value for value, _ in field_candidates),
            key=STACKOVERFLOW_2025_AI_VALUE_PRIORITY.__getitem__,
        )
        evidence_parts = list(dict.fromkeys(evidence for _, evidence in field_candidates))
        fields.append(
            {
                "field_id": field_id,
                "value": selected_value,
                "confidence": 1.0,
                "evidence": "; ".join(evidence_parts),
                "assignment_type": "direct",
            }
        )
    return fields


def overlay_deterministic_fields(
    generated_fields: list[dict[str, Any]],
    deterministic_fields: list[dict[str, Any]],
    reserved_field_ids: frozenset[str],
) -> list[dict[str, Any]]:
    """Replace model-generated reserved fields with deterministic assignments."""
    return [
        field
        for field in generated_fields
        if field["field_id"] not in reserved_field_ids
    ] + deterministic_fields


def drop_unsupported_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Defensively keep unsupported placeholders out of final JSONL records."""
    return [
        field for field in fields if field.get("assignment_type") != "unsupported"
    ]


def build_stackoverflow_prompt(
    profile_text: str, chunk: DimensionChunk, year: int
) -> str:
    """Build a compact, high-precision sparse prompt for one manifest chunk."""
    profile_text = normalize_prompt_text(profile_text)
    if year == 2024:
        year_specific_guidance = [
            "- 2024: JobSatPoints_* are allocated points, not ranks; larger values mean a larger contribution within that question.",
            "- 2024: TechEndorse is select-all, not ranked.",
        ]
    elif year == 2025:
        year_specific_guidance = [
            "- 2025: TechEndorse_*, TechOppose_*, JobSatPoints_*, and SO_Actions_* are ordinal ranks; smaller numbers rank higher.",
            "- 2025: A rank is relative order, not an absolute intensity, skill, personality, or behavior score.",
            "- 2025: Direct deterministic mappings are applied outside the model. Do not use ranks for other dimensions unless the ranked item measures that exact construct.",
        ]
    else:
        year_specific_guidance = [
            "- 2023: Do not treat a number as a rank unless its question explicitly defines it as one.",
        ]
    lines = [
        "You are building a persona for a single Stack Overflow Developer Survey respondent from their survey answers.",
        "",
        "Only emit attributes from CURRENT CHUNK DIMENSIONS that are directly or strongly supported by the respondent profile. If clear evidence is absent, omit the dimension.",
        "",
        "Return ONLY one JSON object matching the supplied structured-output schema (no markdown, no commentary), with this shape:",
        '{"fields": [{"field_id": "<one id from CURRENT CHUNK DIMENSIONS below>", "value": "<one allowed value, copied verbatim>", "confidence": 0.0, "evidence": "<grounded quote or faithful summary with source columns and answer values>", "assignment_type": "direct"}]}',
        "",
        "assignment_type values:",
        "- direct: explicitly answered in a survey field, or a deterministic recoding of an explicit answer into an exactly matching allowed value.",
        "- structured_claim: strongly supported by concrete answers that measure the same construct, with little ambiguity.",
        "- summary_inference: a cautious, low-confidence inference from at least two independent answers that strongly constrain the same construct. Use very sparingly.",
        "",
        "Sparse extraction policy:",
        "- Return only clearly supported dimensions. Missing attributes are better than weak or invented attributes; an empty fields list is correct.",
        "- Do not optimize for coverage, complete the persona, or choose a merely plausible allowed value. When unsure, omit.",
        "- Generic, indirect, stereotypical, topical, or weakly associated evidence is insufficient. Multiple weak proxies do not become strong evidence.",
        "- Do not fan one broad answer out across loosely related fields. Each field needs its own same-construct evidence.",
        "- Summary inference is exceptional: require at least two independent, directionally consistent, same-construct answers; repeated facets of one answer do not count.",
        "- Omit unsupported fields entirely. Do not emit null or unsupported placeholders, and do not infer negative values from missing evidence.",
        "- Worked-with, used, and select-all inventories provide positive evidence only. An option not selected or not listed is unknown, not evidence of non-use, no familiarity, or no proficiency.",
        "- Never emit prog_*=None, fam_*=None, or tool_*=Never used merely because the named technology is absent from a worked-with or used list.",
        "- If an allowed value is more specific than the answer, omit it. Generic Employment=Employed does not prove Full-time.",
        "",
        "High-precision rules:",
        "- Intent is not experience; task use is not mastery; tenure or job title is not proof of skill; current status or work location is not attitude or preference.",
        "- Country supports region only. Do not infer language, culture, nationality, migration, childhood, adversity, or personal history from residence.",
        "- Technology names must match exactly: C# is not C. Worked-with establishes use, not Expert or Master proficiency.",
        "- Overall AI use, non-use, sentiment, or future interest does not identify per-task AI behavior. Use explicit task-level answers only.",
        "- A rank supports only the construct named by the ranked item. Do not convert ranks into skills, personality, psychometrics, habits, health, or unrelated preferences.",
        "- Do not infer personality, cognitive style, broad values, moral foundations, health, emotion, lifestyle, hobbies, habits, family, sensitive identity, politics, religion, income, or housing unless the survey directly measures that construct.",
        "- Organization practices describe the work environment, not the respondent's personal practice, unless a respondent-level answer explicitly connects them.",
        "",
        "Output rules:",
        "- value MUST be exactly one allowed value, copied verbatim; use each field_id at most once.",
        "- For a numeric answer mapped to a range-valued dimension, treat every range endpoint literally and select the range that contains the exact cited number.",
        '- For example, years_experience evidence of 10 maps to "6-10", not "11-20"; evidence of 11 maps to "11-20", not "6-10".',
        "- If several survey fields could support one dimension, choose the field whose question best matches the dimension, cite that field in evidence, and make the output value consistent with the cited answer.",
        "- Never move a numeric answer into an adjacent range based on job title, seniority, age, or an overall impression of the respondent.",
        "- Before returning JSON, verify that the specific numeric answer used to support a range-valued dimension falls within the selected allowed-value range.",
        "- Every emitted field MUST include grounded evidence supported by the current respondent profile. Evidence may be a short source quote or a faithful summary of one or more concrete answers.",
        "- Evidence must preserve numbers, rank direction, time frame, and negation. It must not add assumptions or merely restate the persona conclusion.",
        "- Evidence MUST identify each supporting original column and actual answer value.",
        "- Never cite a source column or answer that is absent from the current RESPONDENT PROFILE. Prompt instructions, format templates, and CURRENT CHUNK DIMENSIONS are not evidence sources.",
        '- Canonical direct-evidence format: "<ORIGINAL_COLUMN_NAME> - <READABLE_QUESTION_OR_SUBITEM>: <ACTUAL_ANSWER_VALUE>".',
        '- Canonical summary-evidence format: "<COLUMN_1>=<ANSWER_1>; <COLUMN_2>=<ANSWER_2>. Summary: <faithful summary supported by both answers>".',
        f"- Keep evidence at or below {MAX_EVIDENCE_CHARS} characters and use at most one concise Summary sentence. Never include deliberation or prompt discussion.",
        "- Every field needs confidence from 0 to 1. High confidence is only for direct or uniquely strong same-construct evidence; summary_inference should normally be low confidence.",
        '- Treat "None of the above" and "None of these" as valid answers, not missing values.',
        "- Return valid JSON only, with no markdown.",
        "",
        f"SURVEY-YEAR INTERPRETATION RULES FOR {year}:",
        *year_specific_guidance,
        "",
        "RESPONDENT PROFILE:",
        profile_text,
        "",
        f"CURRENT CHUNK: {chunk.chunk_id} - {chunk.label}",
        f"CHUNK CONCEPT: {chunk.description}",
        "Only the field IDs listed below exist for this request. Do not emit IDs from any other chunk.",
        "",
        "CURRENT CHUNK DIMENSIONS (field_id - label - description - allowed values):",
    ]
    for dimension in chunk.dimensions:
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


def output_path_for_year(args: argparse.Namespace, year: int) -> Path:
    return args.output or args.survey_root / DEFAULT_OUTPUT_TEMPLATE.format(year=year)


def completed_row_indexes(
    path: Path, *, year: int, model: str, manifest: DimensionManifest
) -> set[int]:
    completed: set[int] = set()
    if not path.is_file():
        return completed
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                expected = {
                    "backend": "vllm",
                    "extractor_version": EXTRACTOR_VERSION,
                    "year": year,
                    "model": model,
                    "manifest_version": manifest.version,
                    "source_catalog_sha256": manifest.source_catalog_sha256,
                }
                for key, value in expected.items():
                    if record.get(key) != value:
                        raise ValueError(
                            f"record {key} is {record.get(key)!r}, expected {value!r}"
                        )
                completed.add(int(record["row_index"]))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {error}") from error
    return completed


def row_is_selected(args: argparse.Namespace, row_index: int, completed: set[int]) -> bool:
    stop_before = None if args.limit is None else args.start_row + args.limit
    return (
        row_index >= args.start_row
        and (stop_before is None or row_index < stop_before)
        and row_index not in completed
    )


def prepare_year(
    args: argparse.Namespace, year: int, manifest: DimensionManifest
) -> YearWork:
    survey_path = args.survey_root / SURVEY_FILES[year]
    mapping_path = args.survey_root / MAPPING_FILES[year]
    if not survey_path.is_file():
        raise FileNotFoundError(f"Missing survey CSV: {survey_path}")
    if not mapping_path.is_file():
        raise FileNotFoundError(f"Missing mapping CSV: {mapping_path}")
    mapping = load_mapping(mapping_path)
    validate_mapping_coverage(survey_path, mapping)
    output_path = output_path_for_year(args, year)
    if args.execute:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = (
        set()
        if args.overwrite or not args.execute
        else completed_row_indexes(
            output_path, year=year, model=args.model, manifest=manifest
        )
    )
    pending_count = 0
    stop_before = None if args.limit is None else args.start_row + args.limit
    for row_index, _ in iter_survey_rows(survey_path):
        if stop_before is not None and row_index >= stop_before:
            break
        if row_is_selected(args, row_index, completed):
            pending_count += 1
    return YearWork(year, survey_path, mapping, output_path, completed, pending_count)


def iter_pending_rows(
    args: argparse.Namespace, work: YearWork
) -> Iterator[tuple[int, dict[str, str]]]:
    stop_before = None if args.limit is None else args.start_row + args.limit
    for row_index, row in iter_survey_rows(work.survey_path):
        if stop_before is not None and row_index >= stop_before:
            break
        if row_is_selected(args, row_index, work.completed):
            yield row_index, row


def batches(iterator: Iterator[Any], size: int) -> Iterator[list[Any]]:
    batch: list[Any] = []
    for item in iterator:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def load_vllm(
    args: argparse.Namespace, schemas: dict[str, dict[str, Any]]
) -> tuple[Any, dict[str, Any]]:
    if args.download_dir is not None:
        os.environ.setdefault("HF_HOME", str(args.download_dir))
        os.environ.setdefault("HF_HUB_CACHE", str(args.download_dir))
        os.environ.setdefault("HF_XET_CACHE", str(args.download_dir / "xet"))
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    try:
        from vllm import LLM, SamplingParams
        from vllm.sampling_params import StructuredOutputsParams
    except ImportError as error:
        raise RuntimeError(
            "vLLM is not installed. Install it in the GPU environment before using "
            "--execute; dry-run mode does not import vLLM."
        ) from error

    kwargs: dict[str, Any] = {
        "model": args.model,
        "dtype": args.dtype,
        "tensor_parallel_size": args.tensor_parallel_size,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "max_model_len": args.max_model_len,
        "max_num_seqs": args.max_num_seqs,
        "enable_prefix_caching": True,
        "language_model_only": True,
        "trust_remote_code": True,
        "seed": args.seed,
    }
    if args.pipeline_parallel_size != 1:
        kwargs["pipeline_parallel_size"] = args.pipeline_parallel_size
    if args.distributed_executor_backend != "auto":
        kwargs["distributed_executor_backend"] = args.distributed_executor_backend
    if args.download_dir is not None:
        kwargs["download_dir"] = str(args.download_dir)
    if args.quantization.lower() != "none":
        kwargs["quantization"] = args.quantization
    llm = LLM(**kwargs)
    sampling_by_chunk = build_sampling_params_by_chunk(
        args,
        schemas,
        sampling_params_class=SamplingParams,
        structured_outputs_class=StructuredOutputsParams,
    )
    return llm, sampling_by_chunk


def build_sampling_params_by_chunk(
    args: argparse.Namespace,
    schemas: dict[str, dict[str, Any]],
    *,
    sampling_params_class: Any,
    structured_outputs_class: Any,
) -> dict[str, Any]:
    """Create a distinct guided-decoding configuration for every chunk."""
    return {
        chunk_id: sampling_params_class(
            temperature=0.0,
            top_p=1.0,
            max_tokens=args.max_tokens,
            seed=args.seed,
            structured_outputs=structured_outputs_class(json=schema),
        )
        for chunk_id, schema in schemas.items()
    }


def validate_cluster_environment(args: argparse.Namespace) -> None:
    if args.distributed_executor_backend == "ray":
        return
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if not visible:
        return
    if visible == "-1":
        raise RuntimeError("CUDA_VISIBLE_DEVICES=-1 exposes no GPUs to vLLM")
    visible_devices = [device.strip() for device in visible.split(",") if device.strip()]
    required = args.tensor_parallel_size * args.pipeline_parallel_size
    if required > len(visible_devices):
        raise RuntimeError(
            f"vLLM parallel sizes require {required} GPUs, but CUDA_VISIBLE_DEVICES "
            f"exposes only {len(visible_devices)} ({visible!r})"
        )


def run_chat(llm: Any, conversations: list[Any], sampling: Any) -> list[Any]:
    try:
        return llm.chat(
            conversations,
            sampling,
            chat_template_kwargs={"enable_thinking": False},
            use_tqdm=False,
        )
    except TypeError as error:
        if "chat_template_kwargs" not in str(error):
            raise
        return llm.chat(conversations, sampling, use_tqdm=False)


def completion_details(output: Any) -> tuple[str, Any, Any]:
    try:
        completion = output.outputs[0]
    except (AttributeError, IndexError, TypeError) as error:
        raise ValueError("vLLM output contains no completion") from error
    text = getattr(completion, "text", None)
    if not isinstance(text, str):
        raise ValueError("vLLM completion text is missing or is not a string")
    return (
        text,
        getattr(completion, "finish_reason", None),
        getattr(completion, "stop_reason", None),
    )


def log_invalid_generation(
    *,
    year: int,
    row_index: int,
    chunk: DimensionChunk,
    attempt: int,
    output: Any,
    error: Exception,
) -> None:
    try:
        text, finish_reason, stop_reason = completion_details(output)
    except ValueError as details_error:
        text = repr(output)
        finish_reason = None
        stop_reason = None
        details = f"; output inspection failed: {details_error}"
    else:
        details = ""
    print(
        f"INVALID_GENERATION year={year} row={row_index} chunk={chunk.chunk_id} "
        f"attempt={attempt} finish_reason={finish_reason!r} "
        f"stop_reason={stop_reason!r} error={error}{details}",
        file=sys.stderr,
    )
    print("--- RAW VLLM RESPONSE BEGIN ---", file=sys.stderr)
    print(text, file=sys.stderr)
    print("--- RAW VLLM RESPONSE END ---", file=sys.stderr, flush=True)


def retry_conversation(conversation: list[dict[str, str]]) -> list[dict[str, str]]:
    retry = [dict(message) for message in conversation]
    retry[-1]["content"] += (
        "\n\nRETRY: Return one valid JSON object matching the supplied schema. "
        "Keep only direct or strongly same-construct fields and omit every weak, "
        "proxy-based, or unsupported field; an empty fields list is valid. "
        "Do not replace rejected fields. Use summary_inference very sparingly, only "
        "with at least two independent same-construct sources and low confidence. "
        "Evidence must cite present source columns and their actual values faithfully."
        f" Keep evidence at or below {MAX_EVIDENCE_CHARS} characters and include no "
        "deliberation or prompt discussion."
    )
    return retry


def log_salvaged_generation(
    *,
    year: int,
    row_index: int,
    chunk: DimensionChunk,
    kept_count: int,
    issues: list[str],
) -> None:
    print(
        f"SALVAGED_GENERATION year={year} row={row_index} chunk={chunk.chunk_id} "
        f"kept={kept_count} issues={json.dumps(issues, ensure_ascii=False)}",
        file=sys.stderr,
        flush=True,
    )


def log_skipped_generation(
    *,
    year: int,
    row_index: int,
    chunk: DimensionChunk,
    error: Exception | None,
) -> None:
    print(
        f"SKIPPED_GENERATION year={year} row={row_index} chunk={chunk.chunk_id} "
        f"fields=[] error={error}",
        file=sys.stderr,
        flush=True,
    )


def parse_generation_with_retry(
    *,
    llm: Any,
    sampling: Any,
    chunk: DimensionChunk,
    conversation: list[dict[str, str]],
    initial_output: Any,
    year: int,
    row_index: int,
    source_answers: dict[str, str],
) -> list[dict[str, Any]]:
    output = initial_output
    last_error: Exception | None = None
    for attempt in (1, 2):
        text: str | None = None
        try:
            text, _, _ = completion_details(output)
            return parse_and_validate_generation(text, chunk, source_answers)
        except ValueError as error:
            last_error = error
            log_invalid_generation(
                year=year,
                row_index=row_index,
                chunk=chunk,
                attempt=attempt,
                output=output,
                error=error,
            )
            if text is not None:
                try:
                    fields, issues = parse_and_salvage_generation(
                        text, chunk, source_answers
                    )
                except ValueError:
                    pass
                else:
                    log_salvaged_generation(
                        year=year,
                        row_index=row_index,
                        chunk=chunk,
                        kept_count=len(fields),
                        issues=issues,
                    )
                    if fields:
                        return fields
            if attempt == 1:
                retry_outputs = run_chat(
                    llm, [retry_conversation(conversation)], sampling
                )
                if len(retry_outputs) != 1:
                    raise RuntimeError(
                        f"vLLM returned {len(retry_outputs)} outputs retrying one prompt"
                    )
                output = retry_outputs[0]
    log_skipped_generation(
        year=year,
        row_index=row_index,
        chunk=chunk,
        error=last_error,
    )
    return []


def merge_validated_fields(
    merged: list[dict[str, Any]], fields: list[dict[str, Any]], seen: set[str]
) -> None:
    duplicate_ids = [field["field_id"] for field in fields if field["field_id"] in seen]
    if duplicate_ids:
        raise ValueError(
            f"duplicate field_id across merged chunk outputs: {sorted(set(duplicate_ids))}"
        )
    merged.extend(fields)
    seen.update(field["field_id"] for field in fields)


def generate_profile_batch(
    *,
    llm: Any,
    chunks: Sequence[DimensionChunk],
    sampling_by_chunk: dict[str, Any],
    profiles: dict[int, str],
    source_answers_by_row: dict[int, dict[str, str]],
    year: int,
) -> dict[int, list[dict[str, Any]]]:
    """Generate chunk-outer batches so every vLLM call has exactly one schema."""
    merged = {row_index: [] for row_index in profiles}
    seen = {row_index: set() for row_index in profiles}
    row_indexes = list(profiles)
    for chunk in chunks:
        try:
            sampling = sampling_by_chunk[chunk.chunk_id]
        except KeyError as error:
            raise RuntimeError(
                f"missing structured sampling parameters for chunk {chunk.chunk_id}"
            ) from error
        conversations = [
            [
                {
                    "role": "user",
                    "content": build_stackoverflow_prompt(
                        profiles[row_index], chunk, year
                    ),
                }
            ]
            for row_index in row_indexes
        ]
        outputs = run_chat(llm, conversations, sampling)
        if len(outputs) != len(row_indexes):
            raise RuntimeError(
                f"vLLM returned {len(outputs)} outputs for {len(row_indexes)} prompts "
                f"in chunk {chunk.chunk_id}"
            )
        for row_index, conversation, output in zip(
            row_indexes, conversations, outputs
        ):
            fields = parse_generation_with_retry(
                llm=llm,
                sampling=sampling,
                chunk=chunk,
                conversation=conversation,
                initial_output=output,
                year=year,
                row_index=row_index,
                source_answers=source_answers_by_row[row_index],
            )
            merge_validated_fields(merged[row_index], fields, seen[row_index])
    return merged


def extract_year(
    args: argparse.Namespace,
    work: YearWork,
    manifest: DimensionManifest,
    llm: Any,
    sampling_by_chunk: dict[str, Any],
) -> None:
    print(
        f"year={work.year} pending={work.pending_count:,} "
        f"chunks/respondent={len(manifest.chunks)} output={work.output_path}",
        flush=True,
    )
    if work.pending_count == 0:
        return
    processed = 0
    started = time.time()
    if args.overwrite:
        work.output_path.write_text("", encoding="utf-8")
    with work.output_path.open("a", encoding="utf-8", newline="") as output_handle:
        for batch in batches(iter_pending_rows(args, work), args.batch_profiles):
            profiles = {
                row_index: assemble_stackoverflow_profile(row, work.year, work.mapping)
                for row_index, row in batch
            }
            source_answers_by_row = {
                row_index: visible_profile_source_answers(row, profiles[row_index])
                for row_index, row in batch
            }
            merged = generate_profile_batch(
                llm=llm,
                chunks=manifest.chunks,
                sampling_by_chunk=sampling_by_chunk,
                profiles=profiles,
                source_answers_by_row=source_answers_by_row,
                year=work.year,
            )
            for row_index, row in batch:
                deterministic_ai_fields = extract_2025_ai_task_fields(
                    row, work.year, work.mapping
                )
                deterministic_rank_fields = extract_2025_rank_fields(
                    row, work.year, work.mapping
                )
                deterministic_job_fields = extract_2025_job_satisfaction_fields(
                    row, work.year, work.mapping
                )
                deterministic_so_fields = (
                    extract_2025_stackoverflow_participation_field(
                        row, work.year, work.mapping
                    )
                )
                deterministic_fields = (
                    deterministic_ai_fields
                    + deterministic_rank_fields
                    + deterministic_job_fields
                    + deterministic_so_fields
                )
                reserved_field_ids = (
                    STACKOVERFLOW_2025_AI_TASK_FIELD_IDS
                    if work.year == 2025
                    else frozenset()
                ) | frozenset(
                    field["field_id"]
                    for field in (
                        deterministic_rank_fields
                        + deterministic_job_fields
                        + deterministic_so_fields
                    )
                )
                final_fields = overlay_deterministic_fields(
                    merged[row_index],
                    deterministic_fields,
                    reserved_field_ids,
                )
                final_fields = reconcile_ai_fields(
                    final_fields, row, work.mapping
                )
                final_fields = filter_semantic_overreach(final_fields, row)
                final_fields = drop_unsupported_fields(final_fields)
                record = {
                    "year": work.year,
                    "row_index": row_index,
                    "response_id": row.get("ResponseId", ""),
                    "model": args.model,
                    "backend": "vllm",
                    "extractor_version": EXTRACTOR_VERSION,
                    "manifest_version": manifest.version,
                    "source_catalog_sha256": manifest.source_catalog_sha256,
                    "fields": final_fields,
                }
                output_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            output_handle.flush()
            os.fsync(output_handle.fileno())

            processed += len(batch)
            elapsed = max(time.time() - started, 1e-9)
            rate = processed / elapsed
            eta = (work.pending_count - processed) / max(rate, 1e-9)
            print(
                f"year={work.year} {processed:,}/{work.pending_count:,} "
                f"({100 * processed / work.pending_count:.1f}%) "
                f"{rate:.2f} respondents/s ETA={eta / 3600:.1f}h",
                flush=True,
            )


def dry_run(
    args: argparse.Namespace,
    work_items: list[YearWork],
    manifest: DimensionManifest,
    schemas: dict[str, dict[str, Any]],
) -> int:
    branch_count = 0
    for chunk in manifest.chunks:
        schema = schemas[chunk.chunk_id]
        branches = schema["properties"]["fields"]["items"]["oneOf"]
        if len(branches) != len(chunk.dimensions):
            raise ValueError(f"schema branch count mismatch for {chunk.chunk_id}")
        validate_chunk_payload({"fields": []}, chunk)
        branch_count += len(branches)

    for work in work_items:
        try:
            row_index, row = next(iter_pending_rows(args, work))
        except StopIteration:
            print(
                f"PASS year={work.year} pending=0 output={work.output_path} "
                "prompt_sample=not-needed"
            )
            continue
        profile = assemble_stackoverflow_profile(row, work.year, work.mapping)
        for chunk in manifest.chunks:
            prompt = build_stackoverflow_prompt(profile, chunk, work.year)
            if profile not in prompt or chunk.chunk_id not in prompt:
                raise ValueError(f"prompt validation failed for chunk {chunk.chunk_id}")
        print(
            f"PASS year={work.year} sample_row={row_index} pending={work.pending_count:,} "
            f"profile_chars={len(profile):,}"
        )
    print(
        f"DRY RUN PASSED: manifest_version={manifest.version} "
        f"chunks={len(manifest.chunks)} schema_branches={branch_count} "
        f"dimensions={branch_count} model_loaded=no"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = load_dimension_manifest()
    schemas = {
        chunk.chunk_id: build_chunk_json_schema(chunk) for chunk in manifest.chunks
    }
    work_items = [
        prepare_year(args, year, manifest) for year in requested_years(args.year)
    ]
    if not args.execute:
        return dry_run(args, work_items, manifest, schemas)
    if not any(work.pending_count for work in work_items):
        print("Nothing to do; all selected rows are already complete.")
        return 0

    validate_cluster_environment(args)
    print(
        f"Loading local vLLM model {args.model!r} "
        f"(tensor_parallel_size={args.tensor_parallel_size}, "
        f"pipeline_parallel_size={args.pipeline_parallel_size}, "
        f"quantization={args.quantization})...",
        flush=True,
    )
    started = time.time()
    llm, sampling_by_chunk = load_vllm(args, schemas)
    print(f"Model loaded in {time.time() - started:.0f}s", flush=True)
    for work in work_items:
        extract_year(args, work, manifest, llm, sampling_by_chunk)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ManifestValidationError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
