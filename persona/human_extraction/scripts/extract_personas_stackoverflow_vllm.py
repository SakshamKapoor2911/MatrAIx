#!/usr/bin/env python3
"""Extract Stack Overflow respondent personas with a locally loaded vLLM model.

The profile construction, dimension chunking, and extraction prompt mirror
``persona/human_extraction/notebooks/extract_personas_stackoverflow.ipynb``.
The model is loaded directly with :class:`vllm.LLM`; no API server is needed.
The safe default is a dry run; pass ``--execute`` to load the model and run
inference.

Examples:
    python scripts/extract_personas_stackoverflow_vllm.py --year all
    python scripts/extract_personas_stackoverflow_vllm.py --year 2025 --execute
    python scripts/extract_personas_stackoverflow_vllm.py --year 2025 --execute --limit 10
    python scripts/extract_personas_stackoverflow_vllm.py --year 2025 --execute \
        --tensor-parallel-size 2 --quantization none
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence


def find_repo_root(script_path: Path) -> Path:
    """Find the MatrAIx root regardless of which repo scripts folder contains us."""
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
MISSING_TOKENS = {"", "na", "n/a", "none", "nan", "null", "<na>"}
MAX_PROFILE_CHARS = 24_000
CSV_FIELD_SIZE_LIMIT = 100_000_000

FIELDS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field_id": {"type": "string"},
                    "value": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence": {"type": "string"},
                    "description": {"type": "string"},
                    "assignment_type": {
                        "type": "string",
                        "enum": [
                            "direct",
                            "structured_claim",
                            "summary_inference",
                            "unsupported",
                        ],
                    },
                },
                "required": [
                    "field_id",
                    "value",
                    "confidence",
                    "evidence",
                    "description",
                    "assignment_type",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["fields"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class DimensionChunk:
    category: str
    dimensions: list[dict[str, Any]]


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
    parser.add_argument("--output", type=Path, default=None,
                        help="Output JSONL path; requires one specific year.")
    parser.add_argument("--start-row", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum input rows per year after --start-row.")
    parser.add_argument("--batch-profiles", type=int, default=16,
                        help="Respondents per vLLM submission/checkpoint.")
    parser.add_argument("--dimensions-per-chunk", type=int, default=50)
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
        help="vLLM worker backend. 'auto' uses vLLM's single-node default.",
    )
    parser.add_argument("--quantization", default="none",
                        help="vLLM quantization method, or 'none' (default).")
    parser.add_argument("--download-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true",
                        help="Replace existing output instead of resuming it.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Load vLLM and run inference. Without this flag, perform a dry run only.",
    )
    args = parser.parse_args(argv)

    positive = {
        "--batch-profiles": args.batch_profiles,
        "--dimensions-per-chunk": args.dimensions_per_chunk,
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


def is_present(value: Any) -> bool:
    return value is not None and str(value).strip().lower() not in MISSING_TOKENS


def normalize_prompt_text(value: Any) -> str:
    """Normalize text and remove invisible/control characters from prompts."""
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
    prefix = text[:max_chars - 3].rstrip()
    boundary = max(prefix.rfind(" "), prefix.rfind("\n"))
    if boundary >= max_chars // 2:
        prefix = prefix[:boundary].rstrip()
    return prefix + "..."


def truncate_profile(text: str, max_chars: int = MAX_PROFILE_CHARS) -> str:
    """Truncate a profile at a complete line and mark the omission explicitly."""
    if len(text) <= max_chars:
        return text
    marker = "\n[Respondent profile truncated]"
    prefix = text[:max_chars - len(marker)]
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
    unmapped = [column for column in columns
                if column != "completeness" and column not in mapping]
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
        completeness = clean_value(row["completeness"], max_chars=100)
        header.append(f"Answer completeness score: {completeness}.")

    lines = [" ".join(header)]
    for section, items in items_by_section.items():
        lines.extend(("", f"## {section}"))
        for column, label, value in items:
            lines.append(
                f"- {column} - {label}: {value}" if label != column
                else f"- {column}: {value}"
            )
    return truncate_profile("\n".join(lines))


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
    return [
        DimensionChunk(category, dims[start:start + per_chunk])
        for category, dims in by_category.items()
        for start in range(0, len(dims), per_chunk)
    ]


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
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("vLLM response contains no JSON object")
    try:
        payload = json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise ValueError(f"vLLM response contains invalid JSON: {error}") from error
    fields = payload.get("fields") if isinstance(payload, dict) else None
    if not isinstance(fields, list) or any(not isinstance(field, dict) for field in fields):
        raise ValueError("vLLM response must contain a JSON object with a fields list")
    return fields


def output_path_for_year(args: argparse.Namespace, year: int) -> Path:
    return args.output or (
        args.survey_root / DEFAULT_OUTPUT_TEMPLATE.format(year=year)
    )


def completed_row_indexes(path: Path, *, year: int, model: str) -> set[int]:
    completed: set[int] = set()
    if not path.is_file():
        return completed
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if record.get("backend") != "vllm":
                    raise ValueError("record backend is not 'vllm'")
                if record.get("year") != year:
                    raise ValueError(
                        f"record year is {record.get('year')!r}, expected {year}"
                    )
                if record.get("model") != model:
                    raise ValueError(
                        f"record model is {record.get('model')!r}, expected {model!r}"
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


def prepare_year(args: argparse.Namespace, year: int) -> YearWork:
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
        else completed_row_indexes(output_path, year=year, model=args.model)
    )
    pending_count = sum(
        1 for row_index, _ in iter_survey_rows(survey_path)
        if row_is_selected(args, row_index, completed)
    )
    return YearWork(year, survey_path, mapping, output_path, completed, pending_count)


def iter_pending_rows(
    args: argparse.Namespace, work: YearWork
) -> Iterator[tuple[int, dict[str, str]]]:
    for row_index, row in iter_survey_rows(work.survey_path):
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


def load_vllm(args: argparse.Namespace) -> tuple[Any, Any]:
    if args.download_dir is not None:
        os.environ.setdefault("HF_HOME", str(args.download_dir))
        os.environ.setdefault("HF_HUB_CACHE", str(args.download_dir))
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    try:
        from vllm import LLM, SamplingParams
        from vllm.sampling_params import StructuredOutputsParams
    except ImportError as error:
        raise RuntimeError(
            "vLLM is not installed. Install it in the GPU environment before running "
            "this script (the default dry-run mode does not require vLLM)."
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
    sampling = SamplingParams(
        temperature=0.0,
        top_p=1.0,
        max_tokens=args.max_tokens,
        seed=args.seed,
        structured_outputs=StructuredOutputsParams(json=FIELDS_JSON_SCHEMA),
    )
    return llm, sampling


def validate_cluster_environment(args: argparse.Namespace) -> None:
    """Catch common scheduler/GPU allocation mismatches before model loading."""
    # Ray may schedule workers on other nodes, so the driver's local CUDA list
    # is not a reliable view of total cluster capacity.
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
        # Older vLLM releases do not expose chat_template_kwargs.
        if "chat_template_kwargs" not in str(error):
            raise
        return llm.chat(conversations, sampling, use_tqdm=False)


def completion_details(output: Any) -> tuple[str, Any, Any]:
    """Return generated text and termination metadata from one vLLM output."""
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
    chunk_index: int,
    attempt: int,
    output: Any,
    error: Exception,
) -> None:
    """Log enough unabridged generation data to diagnose a failed chunk."""
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
        f"INVALID_GENERATION year={year} row={row_index} "
        f"chunk={chunk_index + 1} attempt={attempt} "
        f"finish_reason={finish_reason!r} stop_reason={stop_reason!r} "
        f"error={error}{details}",
        file=sys.stderr,
    )
    print("--- RAW VLLM RESPONSE BEGIN ---", file=sys.stderr)
    print(text, file=sys.stderr)
    print("--- RAW VLLM RESPONSE END ---", file=sys.stderr, flush=True)


def retry_conversation(conversation: list[dict[str, str]]) -> list[dict[str, str]]:
    """Make a corrected prompt for the one malformed chunk being retried."""
    retry = [dict(message) for message in conversation]
    retry[-1]["content"] += (
        "\n\nRETRY INSTRUCTION: The previous generation was malformed. Return one "
        "concise, complete JSON object matching the required schema. Keep the fields "
        "list sparse and omit every unsupported dimension."
    )
    return retry


def parse_generation_with_retry(
    *,
    llm: Any,
    sampling: Any,
    conversation: list[dict[str, str]],
    initial_output: Any,
    year: int,
    row_index: int,
    chunk_index: int,
) -> list[dict[str, Any]]:
    """Parse one generation, retrying only this prompt once if it is malformed."""
    output = initial_output
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            text, _, _ = completion_details(output)
            return parse_fields(text)
        except ValueError as error:
            last_error = error
            log_invalid_generation(
                year=year,
                row_index=row_index,
                chunk_index=chunk_index,
                attempt=attempt,
                output=output,
                error=error,
            )
            if attempt == 1:
                retry_outputs = run_chat(
                    llm, [retry_conversation(conversation)], sampling
                )
                if len(retry_outputs) != 1:
                    raise RuntimeError(
                        "vLLM returned "
                        f"{len(retry_outputs)} outputs while retrying one prompt"
                    )
                output = retry_outputs[0]

    raise RuntimeError(
        f"Invalid generation for year={year}, row={row_index}, "
        f"chunk={chunk_index + 1} after one retry: {last_error}"
    ) from last_error


def extract_year(
    args: argparse.Namespace,
    work: YearWork,
    chunks: list[DimensionChunk],
    llm: Any,
    sampling: Any,
) -> None:
    print(
        f"year={work.year} pending={work.pending_count:,} "
        f"chunks/respondent={len(chunks)} output={work.output_path}",
        flush=True,
    )
    if work.pending_count == 0:
        return

    processed = 0
    started = time.time()
    # Defer destructive overwrite until after vLLM has loaded successfully.
    if args.overwrite:
        work.output_path.write_text("", encoding="utf-8")
    with work.output_path.open("a", encoding="utf-8", newline="") as output_handle:
        for batch in batches(iter_pending_rows(args, work), args.batch_profiles):
            conversations: list[list[dict[str, str]]] = []
            index: list[tuple[int, int]] = []
            merged: dict[int, list[dict[str, Any]]] = {
                row_index: [] for row_index, _ in batch
            }
            # Respondent-outer/chunk-inner ordering enables prefix-cache reuse
            # across all dimension chunks for the same long respondent profile.
            for row_index, row in batch:
                profile = assemble_stackoverflow_profile(row, work.year, work.mapping)
                for chunk_index, chunk in enumerate(chunks):
                    conversations.append([
                        {"role": "user", "content": build_stackoverflow_prompt(
                            profile, chunk.dimensions
                        )}
                    ])
                    index.append((row_index, chunk_index))

            outputs = run_chat(llm, conversations, sampling)
            if len(outputs) != len(index):
                raise RuntimeError(
                    f"vLLM returned {len(outputs)} outputs for {len(index)} prompts"
                )
            for prompt_index, ((row_index, chunk_index), output) in enumerate(
                zip(index, outputs)
            ):
                fields = parse_generation_with_retry(
                    llm=llm,
                    sampling=sampling,
                    conversation=conversations[prompt_index],
                    initial_output=output,
                    year=work.year,
                    row_index=row_index,
                    chunk_index=chunk_index,
                )
                merged[row_index].extend(fields)

            for row_index, row in batch:
                record = {
                    "year": work.year,
                    "row_index": row_index,
                    "response_id": row.get("ResponseId", ""),
                    "model": args.model,
                    "backend": "vllm",
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
    args: argparse.Namespace, work_items: list[YearWork], chunks: list[DimensionChunk]
) -> int:
    total_files = 0
    total_rows = 0
    for work in work_items:
        result_files = sorted(work.survey_path.parent.glob("results*.csv"))
        if not result_files:
            raise FileNotFoundError(
                f"No results CSV files found under {work.survey_path.parent}"
            )
        for survey_path in result_files:
            validate_mapping_coverage(survey_path, work.mapping)
            rows = 0
            min_chars: int | None = None
            max_chars = 0
            first_profile: str | None = None
            for _, row in iter_survey_rows(survey_path):
                profile = assemble_stackoverflow_profile(row, work.year, work.mapping)
                if first_profile is None:
                    first_profile = profile
                profile_chars = len(profile)
                min_chars = (
                    profile_chars
                    if min_chars is None
                    else min(min_chars, profile_chars)
                )
                max_chars = max(max_chars, profile_chars)
                rows += 1
            if not rows or first_profile is None:
                raise ValueError(f"{survey_path} has no data rows")
            for chunk in chunks:
                prompt = build_stackoverflow_prompt(first_profile, chunk.dimensions)
                if first_profile not in prompt:
                    raise ValueError("Prompt construction dropped the respondent profile")
            print(
                f"PASS year={work.year} file={survey_path.name} rows={rows:,} "
                f"profile_chars={min_chars:,}..{max_chars:,}"
            )
            total_files += 1
            total_rows += rows
    print(
        f"DRY RUN PASSED: files={total_files} rows={total_rows:,} "
        f"dimension_chunks={len(chunks)} model_loaded=no"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    chunks = load_dimension_chunks(args.dimensions_per_chunk)
    work_items = [prepare_year(args, year) for year in requested_years(args.year)]
    if not args.execute:
        return dry_run(args, work_items, chunks)
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
    llm, sampling = load_vllm(args)
    print(f"Model loaded in {time.time() - started:.0f}s", flush=True)
    for work in work_items:
        extract_year(args, work, chunks, llm, sampling)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
