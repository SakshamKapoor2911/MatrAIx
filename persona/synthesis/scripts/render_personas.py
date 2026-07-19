#!/usr/bin/env python3
"""Render persona assignments from JSONL, graph codes, or npy stores.

Examples:
  python persona/synthesis/scripts/render_personas.py \
    --jsonl persona/synthesis/reports/combinatorial_vs_graph_100_20260703/full_dag_graph_100.jsonl \
    --mode text --count 5

  python persona/synthesis/scripts/render_personas.py \
    --codes /tmp/personas_1000000.codes.gz --sample 100 --mode both --out sample.rendered.jsonl

  python persona/synthesis/scripts/render_personas.py \
        --npy-prefix /path/to/personas_1M \
    --index 0 --mode text
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.scripts.decode_persona_codes import (  # noqa: E402
    _iter_decoded_rows,
    _load_schema,
)
from persona.synthesis.sampler import codes_schema_path  # noqa: E402

DEFAULT_DIMS_PATH = REPO_ROOT / "persona" / "schema" / "dimensions.json"

CORE_ORDER = [
    "age_bracket",
    "gender_identity",
    "region",
    "urbanicity",
    "socioeconomic_band",
    "cultural_background",
    "primary_language",
    "english_proficiency",
    "multilingualism",
    "highest_education",
    "academic_field",
    "domain",
    "subject_specialty",
    "seniority",
    "role_function",
    "company_size",
    "years_experience",
    "life_stage",
]

BUCKETS = [
    ("Personality & values", ("Personality", "Values", "Risk & Decision")),
    ("Worldview", ("Worldview",)),
    ("Interests", ("Interests",)),
    ("Skills & tools", ("Expertise", "Skills")),
    ("Lifestyle & health", ("Health", "Behavior", "Demographic: Life", "Demographic: Family")),
    ("Learning", ("Learning",)),
    ("Developer & AI", ("Developer", "Coding", "AI")),
]

EXCLUDE_PREFIX = (
    "apple_primex_dimension_",
    "personahub_dimension_",
    "oasis_dimension_",
    "horizonbench_dimension_",
    "wildchat_",
    "pandora_",
    "personachat_",
    "synthetic_persona_chat_dimension_",
    "nemotron_",
    "wiki_",
)
EXCLUDE_CATEGORY = ("External",)
STATE_IDS = {
    "emotional_state",
    "intent",
    "query_complexity",
    "expertise_gap",
    "tone_expected",
    "trust_level",
    "safety_sensitivity",
    "time_pressure",
    "prior_context",
    "device_context",
    "modality_pref",
    "accessibility_needs",
}


def _fix_articles(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        article, word = match.group(1), match.group(2)
        letters = re.sub(r"[^A-Za-z]", "", word)
        if letters.isupper() and len(letters) >= 2:
            vowel = word[0].upper() in "AEFHILMNORSX"
        else:
            vowel = word[0].lower() in "aeiou"
        new_article = "an" if vowel else "a"
        if article[0].isupper():
            new_article = new_article.capitalize()
        return f"{new_article} {word}"

    return re.sub(r"\b([Aa]n?)\s+([A-Za-z0-9][\w\-/()]*)", repl, text)


def load_dims(path: str | Path = DEFAULT_DIMS_PATH) -> dict[str, dict[str, Any]]:
    data = json.loads(Path(path).read_text())
    return {d["id"]: d for d in data["dimensions"] if "id" in d and "values" in d}


def _is_default(value: Any, default: Any) -> bool:
    if default is None:
        return False
    if isinstance(default, list):
        return value in default
    return value == default


def _clause(dim: dict[str, Any], value: Any) -> str:
    phrase = dim.get("phrase")
    if phrase:
        return phrase.replace("{value}", str(value))
    label = dim.get("label") or dim.get("id", "attribute").replace("_", " ")
    return f"their {label[:1].lower() + label[1:]} is {value}"


def render(
    assignment: dict[str, Any],
    dims: dict[str, dict[str, Any]],
    *,
    max_clauses_per_bucket: int | None = 30,
) -> str:
    core = []
    for dim_id in CORE_ORDER:
        if dim_id in assignment and dim_id in dims:
            value = assignment[dim_id]
            if not _is_default(value, dims[dim_id].get("defaultValue")):
                core.append(_clause(dims[dim_id], value))

    lines = ["A persona " + ", ".join(core) + "."] if core else []
    used = set(CORE_ORDER) | STATE_IDS
    for title, categories in BUCKETS:
        clauses = []
        for dim_id, value in assignment.items():
            if dim_id in used or dim_id not in dims:
                continue
            if dim_id.startswith(EXCLUDE_PREFIX):
                continue
            dim = dims[dim_id]
            category = dim.get("category") or ""
            if category.startswith(EXCLUDE_CATEGORY):
                continue
            if not category.startswith(categories):
                continue
            if _is_default(value, dim.get("defaultValue")):
                continue
            clauses.append(_clause(dim, value))
            used.add(dim_id)
        if clauses:
            if max_clauses_per_bucket is not None and len(clauses) > max_clauses_per_bucket:
                omitted = len(clauses) - max_clauses_per_bucket
                clauses = clauses[:max_clauses_per_bucket]
                clauses.append(f"and {omitted} more salient attributes")
            lines.append(f"{title}: " + "; ".join(clauses) + ".")

    return _fix_articles("\n".join(lines))


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _load_npy_store(prefix: Path) -> tuple[np.ndarray, list[str], dict[str, list[Any]]]:
    matrix = np.load(str(prefix) + ".npy", mmap_mode="r")
    codebook = json.loads(Path(str(prefix) + ".codebook.json").read_text())
    return matrix, codebook["columns"], codebook["values"]


def _decode_npy_row(row: np.ndarray, columns: list[str], values: dict[str, list[Any]]) -> dict[str, Any]:
    return {column: values[column][int(row[index])] for index, column in enumerate(columns)}


def _iter_npy(prefix: Path) -> Iterator[dict[str, Any]]:
    matrix, columns, values = _load_npy_store(prefix)
    for row in matrix:
        yield _decode_npy_row(row, columns, values)


def _iter_codes(codes_path: Path, schema_path: Path | None) -> Iterator[dict[str, Any]]:
    schema = _load_schema(codes_path, schema_path)
    yield from _iter_decoded_rows(codes_path, schema)


def _selected_rows(
    rows: Iterable[dict[str, Any]],
    *,
    index: int | None,
    start: int,
    count: int | None,
    sample: int | None,
    seed: int,
) -> Iterator[tuple[int, dict[str, Any]]]:
    if sample is not None:
        rng = np.random.default_rng(seed)
        reservoir: list[tuple[int, dict[str, Any]]] = []
        for row_index, row in enumerate(rows):
            if len(reservoir) < sample:
                reservoir.append((row_index, row))
                continue
            replacement = int(rng.integers(0, row_index + 1))
            if replacement < sample:
                reservoir[replacement] = (row_index, row)
        for row_index, row in sorted(reservoir, key=lambda item: item[0]):
            yield row_index, row
        return

    stop = None if count is None else start + count
    for row_index, row in enumerate(rows):
        if index is not None:
            if row_index == index:
                yield row_index, row
                return
            if row_index > index:
                return
            continue
        if row_index < start:
            continue
        if stop is not None and row_index >= stop:
            return
        yield row_index, row


def _write_record(
    output: Any,
    *,
    mode: str,
    row_index: int,
    assignment: dict[str, Any],
    dims: dict[str, dict[str, Any]] | None,
    stdout_spacing: bool,
    max_clauses_per_bucket: int | None,
) -> None:
    if mode == "attrs":
        output.write(json.dumps(assignment, ensure_ascii=False) + "\n")
    elif mode == "text":
        assert dims is not None
        output.write(render(assignment, dims, max_clauses_per_bucket=max_clauses_per_bucket) + "\n")
        if stdout_spacing:
            output.write("\n")
    else:
        assert dims is not None
        record = {
            "index": row_index,
            "text": render(assignment, dims, max_clauses_per_bucket=max_clauses_per_bucket),
            "attrs": assignment,
        }
        output.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--jsonl", type=Path, help="attribute JSONL input")
    source.add_argument("--codes", type=Path, help="graph persona codes input (.codes or .codes.gz)")
    source.add_argument("--npy-prefix", type=Path, help="combinatorial npy store prefix")
    parser.add_argument("--schema", type=Path, default=None, help="schema sidecar for --codes")
    parser.add_argument("--dims", type=Path, default=DEFAULT_DIMS_PATH, help="dimensions JSON with phrase/defaultValue")
    parser.add_argument("--mode", choices=["attrs", "text", "both"], default="text")
    parser.add_argument("--index", type=int, default=None, help="single row index")
    parser.add_argument("--start", type=int, default=0, help="start row for range mode")
    parser.add_argument("--count", type=int, default=None, help="number of rows in range mode")
    parser.add_argument("--sample", type=int, default=None, help="random sample size; materializes selected input")
    parser.add_argument("--seed", type=int, default=0, help="seed for --sample")
    parser.add_argument(
        "--max-clauses-per-bucket",
        type=int,
        default=30,
        help="maximum rendered clauses per thematic bucket; use 0 for no limit",
    )
    parser.add_argument("--out", type=Path, default=None, help="output path; default stdout")
    args = parser.parse_args()

    if args.jsonl is not None:
        rows = _iter_jsonl(args.jsonl)
    elif args.codes is not None:
        rows = _iter_codes(args.codes, args.schema or codes_schema_path(args.codes))
    else:
        rows = _iter_npy(args.npy_prefix)

    dims = load_dims(args.dims) if args.mode in {"text", "both"} else None
    max_clauses = None if args.max_clauses_per_bucket == 0 else args.max_clauses_per_bucket
    output = args.out.open("w", encoding="utf-8") if args.out else sys.stdout
    try:
        for row_index, assignment in _selected_rows(
            rows,
            index=args.index,
            start=args.start,
            count=args.count,
            sample=args.sample,
            seed=args.seed,
        ):
            _write_record(
                output,
                mode=args.mode,
                row_index=row_index,
                assignment=assignment,
                dims=dims,
                stdout_spacing=args.out is None and args.mode == "text",
                max_clauses_per_bucket=max_clauses,
            )
    finally:
        if args.out:
            output.close()


if __name__ == "__main__":
    main()
