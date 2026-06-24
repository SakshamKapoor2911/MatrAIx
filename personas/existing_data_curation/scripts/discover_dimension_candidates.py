#!/usr/bin/env python3
"""Discover raw persona dimension candidates from curated JSONL records.

This script is intentionally append-only: it asks an LLM to propose raw
dimension candidates from batches of source records, without deduplication or
canonical-schema mapping. Large generated outputs should stay out of git unless
they are small examples.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_PROMPT = BASE_DIR / "prompts" / "dimension_candidate_discovery.md"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "dimension_candidates"


def log(message: str) -> None:
    print(f"[discover_dimension_candidates] {message}", file=sys.stderr)


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


def batched(items: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def trim_text(value: Any, max_chars: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def row_id(row: dict[str, Any], fallback: int) -> str:
    for key in ("conversation_id", "utterance_id", "user_id", "study_id", "id"):
        value = row.get(key)
        if value is not None:
            return str(value)
    return f"row_{fallback}"


def compact_for_prism_conversation(
    row: dict[str, Any],
    *,
    row_index: int,
    text_limit: int,
) -> dict[str, Any]:
    user_turns: list[dict[str, Any]] = []
    response_scores: list[dict[str, Any]] = []
    for item in row.get("conversation_history") or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role == "user":
            user_turns.append(
                {
                    "turn": item.get("turn"),
                    "content": trim_text(item.get("content"), text_limit),
                }
            )
        elif role == "model":
            response_scores.append(
                {
                    "turn": item.get("turn"),
                    "model_provider": item.get("model_provider"),
                    "model_name": item.get("model_name"),
                    "score": item.get("score"),
                    "if_chosen": item.get("if_chosen"),
                    "within_turn_id": item.get("within_turn_id"),
                }
            )

    return {
        "source_row_id": row_id(row, row_index),
        "user_id": row.get("user_id"),
        "conversation_id": row.get("conversation_id"),
        "conversation_type": row.get("conversation_type"),
        "opening_prompt": trim_text(row.get("opening_prompt"), text_limit),
        "user_turns": user_turns,
        "open_feedback": trim_text(row.get("open_feedback"), text_limit),
        "performance_attributes": row.get("performance_attributes"),
        "choice_attributes": row.get("choice_attributes"),
        "response_score_summary": response_scores[:8],
    }


def compact_generic_row(
    row: dict[str, Any],
    *,
    row_index: int,
    text_limit: int,
) -> dict[str, Any]:
    compact: dict[str, Any] = {"source_row_id": row_id(row, row_index)}
    for key, value in row.items():
        if key in {
            "conversation_history",
            "model_response",
            "system_string",
            "generated_datetime",
            "timing_duration_mins",
            "timing_duration_s",
            "consent",
            "consent_age",
        }:
            continue
        if isinstance(value, str):
            compact[key] = trim_text(value, text_limit)
        else:
            compact[key] = value
    return compact


def compact_row(
    row: dict[str, Any],
    *,
    source_config: str,
    row_index: int,
    text_limit: int,
) -> dict[str, Any]:
    if source_config == "conversations":
        return compact_for_prism_conversation(row, row_index=row_index, text_limit=text_limit)
    return compact_generic_row(row, row_index=row_index, text_limit=text_limit)


def build_prompt(
    *,
    prompt_template: str,
    dataset_id: str,
    source_config: str,
    batch_id: str,
    records: list[dict[str, Any]],
    max_candidates: int,
) -> str:
    payload = {
        "dataset_id": dataset_id,
        "source_config": source_config,
        "batch_id": batch_id,
        "max_candidates": max_candidates,
        "records": records,
    }
    return (
        prompt_template.rstrip()
        + "\n\n"
        + f"Return at most {max_candidates} high-signal candidates for this batch.\n"
        + "Batch input:\n"
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


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any] | None:
    label = str(candidate.get("dimension_label", "")).strip()
    if not label:
        return None
    confidence = candidate.get("confidence", 0.5)
    try:
        confidence_float = float(confidence)
    except (TypeError, ValueError):
        confidence_float = 0.5
    confidence_float = max(0.0, min(1.0, confidence_float))
    return {
        "dimension_label": label,
        "definition": str(candidate.get("definition", "")).strip(),
        "supported_by": str(candidate.get("supported_by", "")).strip(),
        "source_fields": normalize_string_list(candidate.get("source_fields")),
        "evidence_quotes": normalize_string_list(candidate.get("evidence_quotes")),
        "possible_values": normalize_string_list(candidate.get("possible_values")),
        "value_type": str(candidate.get("value_type", "unknown")).strip() or "unknown",
        "granularity": str(candidate.get("granularity", "unknown")).strip() or "unknown",
        "confidence": confidence_float,
    }


def run_claude(
    *,
    prompt: str,
    claude_bin: str,
    model: str,
    max_budget_usd: float | None,
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

    result = subprocess.run(cmd, text=True, capture_output=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(
            "Claude command failed with exit code "
            f"{result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return extract_json_object(result.stdout)


def validate_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = payload.get("dimension_candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("LLM output field dimension_candidates must be a list")
    normalized: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        item = normalize_candidate(candidate)
        if item is not None:
            normalized.append(item)
    return normalized


def read_completed_batch_ids(path: Path) -> set[str]:
    completed: set[str] = set()
    if not path.exists():
        return completed
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as err:
                raise ValueError(f"{path}:{line_no} is not valid JSON") from err
            if isinstance(value, dict) and value.get("batch_id"):
                completed.add(str(value["batch_id"]))
    return completed


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Input JSONL file.")
    parser.add_argument("--dataset", default="prism_alignment", help="Dataset identifier.")
    parser.add_argument("--source-config", default="conversations", help="Source config name.")
    parser.add_argument("--batch-size", type=int, default=10, help="Records per LLM batch.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum input rows to read.")
    parser.add_argument("--max-batches", type=int, default=None, help="Maximum batches to run.")
    parser.add_argument("--max-candidates", type=int, default=12, help="Candidates per batch.")
    parser.add_argument("--text-limit", type=int, default=600, help="Max chars per text field.")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT, help="Prompt template.")
    parser.add_argument("--output", type=Path, default=None, help="Output JSONL path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output file first.")
    parser.add_argument("--resume", action="store_true", help="Skip batch IDs already present in the output JSONL.")
    parser.add_argument("--backend", choices=["claude_code", "dry_run"], default="claude_code")
    parser.add_argument("--claude-bin", default="claude", help="Claude Code executable.")
    parser.add_argument("--model", default="haiku", help="Claude Code model alias/name.")
    parser.add_argument("--max-budget-usd", type=float, default=0.15)
    parser.add_argument("--contributor", default="ElegantLin", help="GitHub username.")
    parser.add_argument("--prompt-version", default="v1")
    parser.add_argument("--added-date", default=str(date.today()))
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    if args.overwrite and args.resume:
        raise ValueError("--overwrite and --resume cannot be used together")

    rows = read_jsonl(args.input, limit=args.limit)
    if not rows:
        raise ValueError(f"No rows found in {args.input}")

    prompt_template = args.prompt.read_text(encoding="utf-8")
    output_path = args.output
    if output_path is None:
        output_path = (
            DEFAULT_OUTPUT_DIR / f"{args.dataset}_{args.source_config}_dimension_candidates.jsonl"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.overwrite and output_path.exists():
        output_path.unlink()

    completed_batch_ids: set[str] = set()
    if args.resume:
        completed_batch_ids = read_completed_batch_ids(output_path)
        if completed_batch_ids:
            log(f"Resuming {output_path}; skipping {len(completed_batch_ids)} completed batch(es)")

    batch_count = 0
    with output_path.open("a", encoding="utf-8") as out_fh:
        for batch_index, batch in enumerate(batched(rows, args.batch_size), start=1):
            if args.max_batches is not None and batch_count >= args.max_batches:
                break
            batch_id = f"{args.dataset}_{args.source_config}_batch_{batch_index:04d}"
            if batch_id in completed_batch_ids:
                log(f"Skipping completed {batch_id}")
                continue
            compact_records = [
                compact_row(
                    row,
                    source_config=args.source_config,
                    row_index=(batch_index - 1) * args.batch_size + offset,
                    text_limit=args.text_limit,
                )
                for offset, row in enumerate(batch, start=1)
            ]
            source_row_ids = [str(record["source_row_id"]) for record in compact_records]
            prompt = build_prompt(
                prompt_template=prompt_template,
                dataset_id=args.dataset,
                source_config=args.source_config,
                batch_id=batch_id,
                records=compact_records,
                max_candidates=args.max_candidates,
            )

            if args.backend == "dry_run":
                log(f"Dry run for {batch_id}: {len(compact_records)} records")
                payload = {"dimension_candidates": []}
            else:
                log(f"Running Claude for {batch_id}: {len(compact_records)} records")
                payload = run_claude(
                    prompt=prompt,
                    claude_bin=args.claude_bin,
                    model=args.model,
                    max_budget_usd=args.max_budget_usd,
                )

            candidates = validate_payload(payload)
            record = {
                "dataset_id": args.dataset,
                "source_config": args.source_config,
                "batch_id": batch_id,
                "source_row_ids": source_row_ids,
                "dimension_candidates": candidates,
                "extraction_origin": {
                    "contributor_github": args.contributor,
                    "backend": args.backend,
                    "model": args.model,
                    "prompt_version": args.prompt_version,
                    "added_date": args.added_date,
                },
            }
            out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_fh.flush()
            log(f"Wrote {len(candidates)} candidates for {batch_id}")
            batch_count += 1

    log(f"Completed {batch_count} batch(es): {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
