#!/usr/bin/env python3
"""Run one assigned index range against a selected backend."""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import json
from pathlib import Path
import sqlite3
import tarfile
import time
from typing import Any

from personas.existing_data_curation.wiki_collab.core import (
    build_result_archive_name,
    load_protocol_manifest,
    parse_range,
    profile_input_payload,
)
from personas.existing_data_curation.worker_kit.backends import (
    RUNNER_VERSION,
    DEFAULT_EFFORT,
    create_backend,
)


def load_profiles(db_path: Path, range_start: int, range_end: int) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in conn.execute(
            """
            select global_idx, task_id, qid, title, source_url, profile_text, input_sha256
            from profiles
            where global_idx >= ? and global_idx < ?
            order by global_idx
            """,
            (range_start, range_end),
        )
    ]
    conn.close()
    return rows


def render_prompt(prompt_template: str, input_record: dict[str, Any]) -> str:
    input_json = json.dumps(input_record, ensure_ascii=False, sort_keys=True, indent=2)
    if "{{input_json}}" in prompt_template:
        return prompt_template.replace("{{input_json}}", input_json)
    return prompt_template.rstrip() + "\n\nINPUT_JSON:\n" + input_json + "\n"


def _run_one(
    *,
    backend_name: str,
    model: str | None,
    effort: str,
    worker_id: str,
    prompt_template: str,
    prompt_sha256: str,
    protocol_sha256: str,
    row: dict[str, Any],
    max_attempts: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    input_record = profile_input_payload(row)
    prompt = render_prompt(prompt_template, input_record)
    for attempt in range(1, max_attempts + 1):
        backend = create_backend(backend_name, model, effort)
        started = time.time()
        try:
            output = backend.run(prompt, input_record)
            result = {
                "global_idx": row["global_idx"],
                "task_id": row["task_id"],
                "qid": row["qid"],
                "status": "succeeded",
                "input_sha256": row["input_sha256"],
                "provenance": {
                    "worker_id": worker_id,
                    "backend": backend.name,
                    "provider": backend.provider,
                    "requested_model": backend.model,
                    "reported_model": output.reported_model,
                    "model_source": output.model_source,
                    "model_confidence": output.model_confidence,
                    "prompt_sha256": prompt_sha256,
                    "protocol_sha256": protocol_sha256,
                    "runner_version": RUNNER_VERSION,
                    "effort": backend.effort,
                    "attempt": attempt,
                    "elapsed_seconds": round(time.time() - started, 3),
                },
                "fields": output.fields,
            }
            return result, None
        except Exception as exc:
            if attempt >= max_attempts:
                failure = {
                    "global_idx": row["global_idx"],
                    "task_id": row["task_id"],
                    "qid": row["qid"],
                    "status": "failed",
                    "input_sha256": row["input_sha256"],
                    "worker_id": worker_id,
                    "backend": backend_name,
                    "requested_model": create_backend(backend_name, model, effort).model,
                    "effort": effort,
                    "attempt_count": attempt,
                    "error": str(exc),
                }
                return None, failure
            time.sleep(min(2**attempt, 30))
    raise AssertionError("unreachable")


def write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_archive(work_dir: Path, archive_path: Path) -> None:
    if archive_path.exists():
        archive_path.unlink()
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(work_dir / "results.jsonl.gz", arcname="results.jsonl.gz")
        tar.add(work_dir / "failures.jsonl.gz", arcname="failures.jsonl.gz")
        tar.add(work_dir / "run_manifest.json", arcname="run_manifest.json")


def run_range(
    *,
    db_path: Path,
    protocol_dir: Path,
    range_start: int,
    range_end: int,
    backend_name: str,
    model: str | None,
    concurrency: int,
    effort: str = DEFAULT_EFFORT,
    worker_id: str,
    out_dir: Path,
    dataset_id: str,
    dataset_sha256: str,
    max_attempts: int = 3,
) -> Path:
    if concurrency <= 0:
        raise ValueError("concurrency must be positive")
    manifest = load_protocol_manifest(protocol_dir)
    prompt_template = (protocol_dir / manifest.prompt_file).read_text(encoding="utf-8")
    rows = load_profiles(db_path, range_start, range_end)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_name = build_result_archive_name(worker_id, manifest.protocol_id, range_start, range_end)
    work_dir = out_dir / archive_name.removesuffix(".tar.gz")
    work_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                _run_one,
                backend_name=backend_name,
                model=model,
                effort=effort,
                worker_id=worker_id,
                prompt_template=prompt_template,
                prompt_sha256=manifest.prompt_sha256,
                protocol_sha256=manifest.protocol_sha256,
                row=row,
                max_attempts=max_attempts,
            )
            for row in rows
        ]
        for future in concurrent.futures.as_completed(futures):
            result, failure = future.result()
            if result is not None:
                results.append(result)
            if failure is not None:
                failures.append(failure)
    results.sort(key=lambda row: row["global_idx"])
    failures.sort(key=lambda row: row["global_idx"])
    write_jsonl_gz(work_dir / "results.jsonl.gz", results)
    write_jsonl_gz(work_dir / "failures.jsonl.gz", failures)
    reported_models: dict[str, int] = {}
    for row in results:
        model_name = row["provenance"].get("reported_model") or "unknown"
        reported_models[model_name] = reported_models.get(model_name, 0) + 1
    backend = create_backend(backend_name, model, effort)
    run_manifest = {
        "worker_id": worker_id,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256,
        "protocol_id": manifest.protocol_id,
        "protocol_sha256": manifest.protocol_sha256,
        "range_start": range_start,
        "range_end": range_end,
        "backend": backend.name,
        "provider": backend.provider,
        "requested_model": backend.model,
        "reported_models": reported_models,
        "auth_mode": backend.auth_mode,
        "concurrency": concurrency,
        "effort": backend.effort,
        "runner_version": RUNNER_VERSION,
        "succeeded": len(results),
        "failed": len(failures),
    }
    (work_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    archive_path = out_dir / archive_name
    build_archive(work_dir, archive_path)
    return archive_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--range", required=True, dest="range_spec")
    parser.add_argument("--backend", required=True)
    parser.add_argument("--model", help="Defaults by backend: codex/openai -> gpt-5.5, claude/anthropic -> claude-opus-4-8.")
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("wiki_collab_runs"))
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--max-attempts", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    range_start, range_end = parse_range(args.range_spec)
    archive = run_range(
        db_path=args.db,
        protocol_dir=args.protocol,
        range_start=range_start,
        range_end=range_end,
        backend_name=args.backend,
        model=args.model,
        concurrency=args.concurrency,
        effort=args.effort,
        worker_id=args.worker_id,
        out_dir=args.out_dir,
        dataset_id=args.dataset_id,
        dataset_sha256=args.dataset_sha256,
        max_attempts=args.max_attempts,
    )
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

