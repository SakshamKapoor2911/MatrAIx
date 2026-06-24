#!/usr/bin/env python3
"""Run every per-category persona-attribution protocol over one profile range.

Covering all 1339 dimensions for a range of profiles == running the 39
per-category protocols (from generate_category_protocols.py) over that same
range. This loops worker_kit.run_range.run_range, producing one results archive
per category. Union them per person with merge_persona_records.py.

The backend is your subscription/CLI, identical to a single run_range call:
  - mock         : smoke test (emits a placeholder field)
  - claude-code-acp : Claude Code, via $WIKI_COLLAB_CLAUDE_CMD wrapper
  - codex-acp       : Codex, via $WIKI_COLLAB_CODEX_CMD wrapper
  - anthropic-api / openai-api : direct API

Run from the repo root with the repo on PYTHONPATH, e.g.:
  PYTHONPATH=. python personas/existing_data_curation/scripts/run_all_categories.py \
    --db profiles.sqlite \
    --protocols-dir personas/existing_data_curation/protocols/persona_attribution_by_category \
    --range 0:1 --backend mock --worker-id alice \
    --dataset-id DATASET_ID --dataset-sha256 DATASET_SHA256 \
    --out-dir wiki_collab_runs
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path
from typing import Any

from personas.existing_data_curation.wiki_collab.core import parse_range
from personas.existing_data_curation.worker_kit.run_range import run_range


def discover_categories(
    protocols_dir: Path, only: list[str] | None = None
) -> list[str]:
    """Ordered list of category slugs (protocol subdir names)."""
    index = protocols_dir / "index.json"
    if index.exists():
        data = json.loads(index.read_text(encoding="utf-8"))
        slugs = [c["slug"] for c in data.get("categories", [])]
    else:
        slugs = sorted(
            p.name
            for p in protocols_dir.iterdir()
            if (p / "protocol_manifest.json").exists()
        )
    if only:
        only_set = {s.strip() for s in only if s.strip()}
        slugs = [s for s in slugs if s in only_set]
    return slugs


def run_all_categories(
    *,
    db_path: Path,
    protocols_dir: Path,
    range_start: int,
    range_end: int,
    backend_name: str,
    model: str | None,
    effort: str,
    concurrency: int,
    worker_id: str,
    out_dir: Path,
    dataset_id: str,
    dataset_sha256: str,
    categories: list[str] | None = None,
    max_attempts: int = 3,
    jobs: int = 1,
) -> list[dict[str, Any]]:
    slugs = discover_categories(protocols_dir, categories)
    if not slugs:
        raise ValueError(f"no category protocols found under {protocols_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    def _one(slug: str) -> dict[str, Any]:
        # Each category run is independent (own work dir + archive), so categories
        # parallelize safely; the backend call inside is I/O-bound on the CLI/API.
        try:
            archive = run_range(
                db_path=db_path,
                protocol_dir=protocols_dir / slug,
                range_start=range_start,
                range_end=range_end,
                backend_name=backend_name,
                model=model,
                concurrency=concurrency,
                effort=effort,
                worker_id=worker_id,
                out_dir=out_dir,
                dataset_id=dataset_id,
                dataset_sha256=dataset_sha256,
                max_attempts=max_attempts,
            )
            return {"slug": slug, "archive": str(archive)}
        except Exception as exc:  # one bad category must not kill the batch
            return {"slug": slug, "error": str(exc)}

    produced: list[dict[str, Any]] = []
    done = 0
    total = len(slugs)
    if jobs <= 1:
        for slug in slugs:
            result = _one(slug)
            done += 1
            produced.append(result)
            _log_result(done, total, result)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = {executor.submit(_one, slug): slug for slug in slugs}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                done += 1
                produced.append(result)
                _log_result(done, total, result)
    produced.sort(key=lambda r: r["slug"])
    return produced


def _log_result(done: int, total: int, result: dict[str, Any]) -> None:
    if "error" in result:
        print(f"[{done}/{total}] {result['slug']} -> ERROR: {result['error']}")
    else:
        print(f"[{done}/{total}] {result['slug']} -> {Path(result['archive']).name}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument(
        "--protocols-dir",
        type=Path,
        default=Path(
            "personas/existing_data_curation/protocols/persona_attribution_by_category"
        ),
    )
    ap.add_argument("--range", required=True, dest="range_spec")
    ap.add_argument("--backend", required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default="max")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--worker-id", required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("wiki_collab_runs"))
    ap.add_argument("--dataset-id", required=True)
    ap.add_argument("--dataset-sha256", required=True)
    ap.add_argument(
        "--categories",
        default=None,
        help="comma-separated slugs to run a subset (default: all 39).",
    )
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="run this many category protocols in parallel (each is one backend call).",
    )
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    range_start, range_end = parse_range(args.range_spec)
    categories = args.categories.split(",") if args.categories else None
    produced = run_all_categories(
        db_path=args.db,
        protocols_dir=args.protocols_dir,
        range_start=range_start,
        range_end=range_end,
        backend_name=args.backend,
        model=args.model,
        effort=args.effort,
        concurrency=args.concurrency,
        worker_id=args.worker_id,
        out_dir=args.out_dir,
        dataset_id=args.dataset_id,
        dataset_sha256=args.dataset_sha256,
        categories=categories,
        max_attempts=args.max_attempts,
        jobs=args.jobs,
    )
    ok = [p for p in produced if "archive" in p]
    errors = [p for p in produced if "error" in p]
    print(f"\nDone: {len(ok)} category archives in {args.out_dir}")
    if errors:
        print(f"Failed categories ({len(errors)}): {', '.join(e['slug'] for e in errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
