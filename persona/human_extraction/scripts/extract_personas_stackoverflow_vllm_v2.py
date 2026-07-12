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

DEFAULT_MODEL = "Qwen/Qwen3.6-35B-A3B"
DEFAULT_OUTPUT_TEMPLATE = "extraction_stackoverflow_v2_{year}.jsonl"
MISSING_TOKENS = {"", "na", "n/a", "none", "nan", "null", "<na>"}
MAX_PROFILE_CHARS = 36_000
CSV_FIELD_SIZE_LIMIT = 100_000_000
DIMENSION_ID_PATTERN = re.compile(r"[a-z][a-z0-9_]*\Z")
CHUNK_ID_PATTERN = re.compile(r"[a-z][a-z0-9_]*\Z")
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
                    "evidence": {"type": "string", "minLength": 1},
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


def validate_chunk_payload(payload: Any, chunk: DimensionChunk) -> list[dict[str, Any]]:
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
        if field["assignment_type"] not in ASSIGNMENT_TYPES:
            raise ValueError(
                f"{location}.assignment_type {field['assignment_type']!r} is invalid"
            )
        validated.append(dict(field))
    return validated


def parse_and_validate_generation(text: str, chunk: DimensionChunk) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"vLLM response is not exactly one JSON value: {error}") from error
    return validate_chunk_payload(payload, chunk)


def salvage_chunk_payload(
    payload: Any, chunk: DimensionChunk
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
            validated = validate_chunk_payload({"fields": [field]}, chunk)[0]
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
    text: str, chunk: DimensionChunk
) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"vLLM response is not exactly one JSON value: {error}") from error
    return salvage_chunk_payload(payload, chunk)


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


def build_stackoverflow_prompt(profile_text: str, chunk: DimensionChunk) -> str:
    """Build V1's detailed sparse-extraction prompt for one manifest chunk."""
    profile_text = normalize_prompt_text(profile_text)
    lines = [
        "You are building a persona for a single Stack Overflow Developer Survey respondent from their survey answers.",
        "",
        "The input is a structured respondent profile assembled from one survey row. It may contain information about a broad range of dimensions about the respondent.",
        "Only emit attributes from the CURRENT CHUNK DIMENSIONS list when directly or strongly supported by the respondent profile.",
        "If the respondent profile does not contain information about a dimension, omit the dimension.",
        "",
        "Return ONLY one JSON object matching the supplied structured-output schema (no markdown, no commentary), with this shape:",
        '{"fields": [{"field_id": "<one id from CURRENT CHUNK DIMENSIONS below>", "value": "<one allowed value, copied verbatim>", "confidence": 0.0, "evidence": "<short quote copied from the respondent profile>", "assignment_type": "direct"}]}',
        "",
        "assignment_type values (Stack Overflow survey context):",
        "- direct: explicitly answered in a survey field, or a deterministic recoding of an explicit answer into an exactly matching allowed value.",
        "- structured_claim: strongly supported by multiple concrete survey answers with little ambiguity.",
        "- summary_inference: a cautious, low-confidence inference from multiple survey answers. Use sparingly."
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
        "- Read survey question and answer context carefully to determine the most specific and accurate value for each dimension.",
        "- Be especially careful when surveyanswer is given in a numerical scale, such as a Likert scale or a scale of 1 to 10. YOU MUST follow related question and answer definitions to determine the most specific and accurate value for the dimension.",
        "- value MUST be exactly one of that dimension's allowed values, copied verbatim.",
        "- Use each field_id at most once.",
        "- If multiple allowed values for one field_id are directly supported, emit exactly one.",
        "- Choose the value with the strongest and most specific evidence. If still tied, choose the first supported value in that dimension's listed allowed-values order.",
        "- A value chosen by catalog-order tie-breaking MUST use assignment_type summary_inference and confidence no greater than 0.6.",
        "- Every emitted field MUST include a short evidence quote copied verbatim from the respondent profile.",
        "- Evidence for a tie-broken field MUST include only the survey evidence supporting the selected value.",
        "- Evidence MUST include the original column name plus the readable question/sub-item context and the answer value.",
        '- Bad evidence examples: "10", "8", "Yes", "No", "Employed". These are bare values without the survey question context.',
        '- Good evidence example: "TechEndorse_1 - What attracts you to a technology or causes you to endorse it (most to least important)? | Sub-item: AI integration or AI Agent capabilities: 10".',
        "- Every emitted field MUST include a confidence between 0 and 1. Use high confidence only for direct or strong evidence.",
        "- Prefer direct and structured_claim assignments. Use summary_inference only for non-sensitive attributes backed by multiple concrete survey answers.",
        "- Do not infer personality, worldview, family status, sensitive identity, health, politics, religion, income, or housing from generic developer-survey answers.",
        "- Do not infer missing demographics, gender, sexuality, health, disability, family status, religion, ethnicity, politics, income, housing, or socioeconomic status from country, age, job title, technology stack, or developer role unless explicitly answered.",
        "- Do not infer personality traits, values, hobbies, habits, or relationship attributes from technology choices alone.",
        "- Do not infer generation from broad age buckets unless the bucket maps uniquely to one cohort.",
        '- Treat "None of the above" and "None of these" as valid answers, not missing values.',
        "- When unsure, omit the dimension.",
        "- Return valid JSON only, with no markdown.",
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
        "\n\nRETRY: The previous response failed strict validation. Return one complete "
        "JSON object matching this chunk's supplied schema. Keep fields sparse, use "
        "each field ID at most once, and omit unsupported dimensions. If multiple "
        "allowed values for one field ID are supported, choose the strongest and "
        "most specific one; if still tied, choose the first supported value in the "
        "listed allowed-values order, use assignment_type summary_inference with "
        "confidence no greater than 0.6, and cite only evidence for that value."
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
) -> list[dict[str, Any]]:
    output = initial_output
    last_error: Exception | None = None
    for attempt in (1, 2):
        text: str | None = None
        try:
            text, _, _ = completion_details(output)
            return parse_and_validate_generation(text, chunk)
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
                    fields, issues = parse_and_salvage_generation(text, chunk)
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
                    "content": build_stackoverflow_prompt(profiles[row_index], chunk),
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
            merged = generate_profile_batch(
                llm=llm,
                chunks=manifest.chunks,
                sampling_by_chunk=sampling_by_chunk,
                profiles=profiles,
                year=work.year,
            )
            for row_index, row in batch:
                record = {
                    "year": work.year,
                    "row_index": row_index,
                    "response_id": row.get("ResponseId", ""),
                    "model": args.model,
                    "backend": "vllm",
                    "extractor_version": EXTRACTOR_VERSION,
                    "manifest_version": manifest.version,
                    "source_catalog_sha256": manifest.source_catalog_sha256,
                    "fields": merged[row_index],
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
            prompt = build_stackoverflow_prompt(profile, chunk)
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
