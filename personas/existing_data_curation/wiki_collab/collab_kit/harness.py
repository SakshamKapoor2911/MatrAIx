#!/usr/bin/env python3
"""harness.py — the provided runner. You should not need to edit this.

Reads the owner's tasks.jsonl + dimensions.json, calls solver.attribute() for
each profile (batching the dimensions by category so each model call is a
sensible size), unions the fields per profile, writes results.jsonl in the
contract format, and then runs the conformance check so you know immediately
whether your output is valid before sending it back.

    python3 harness.py --tasks sample/tasks.jsonl --dimensions sample/dimensions.json \
        --out results.jsonl --backend mock

    # real run with your Claude subscription (claude logged in):
    export WIKI_COLLAB_CLAUDE_CMD="python3 \
      personas/existing_data_curation/wiki_collab/claude_json_backend.py"
    python3 harness.py --tasks tasks.jsonl --dimensions dimensions.json \
        --out results.jsonl --backend claude-code-acp --jobs 6
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

KIT_DIR = Path(__file__).resolve().parent
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))

import conformance  # noqa: E402
import solver  # noqa: E402


def group_by_category(dimensions: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """One batch per category (preserving order); dims w/o a category share a batch."""
    batches: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for d in dimensions:
        batches.setdefault(str(d.get("category", "_")), []).append(d)
    return list(batches.values())


def run(
    tasks: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
    *,
    backend: str,
    model: str | None,
    effort: str,
    jobs: int,
) -> list[dict[str, Any]]:
    batches = group_by_category(dimensions)
    # work items: (task_index, batch) so categories parallelize per profile.
    work = [(ti, batch) for ti in range(len(tasks)) for batch in batches]

    def _one(item: tuple[int, list[dict[str, Any]]]) -> tuple[int, list[dict[str, Any]]]:
        ti, batch = item
        fields = solver.attribute(tasks[ti], batch, backend=backend, model=model, effort=effort)
        return ti, fields

    # union fields per profile (field_id keyed, last write wins)
    per_profile: list[dict[str, dict[str, Any]]] = [dict() for _ in tasks]
    if jobs <= 1:
        outputs = [_one(w) for w in work]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
            outputs = list(ex.map(_one, work))
    for ti, fields in outputs:
        for f in fields:
            fid = f.get("field_id")
            if fid:
                per_profile[ti][str(fid)] = f

    results = []
    for ti, task in enumerate(tasks):
        results.append(
            {
                "global_idx": task.get("global_idx"),
                "task_id": task.get("task_id"),
                "qid": task.get("qid"),
                "model": model,
                "fields": list(per_profile[ti].values()),
            }
        )
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--dimensions", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results.jsonl"))
    ap.add_argument("--backend", default="mock",
                    help="mock | claude-code-acp | codex-acp | anthropic-api | openai-api")
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--jobs", type=int, default=4, help="parallel (profile, category) calls")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tasks = conformance.load_jsonl(args.tasks)
    dimensions = json.loads(args.dimensions.read_text(encoding="utf-8"))
    print(f"Attributing {len(tasks)} profile(s) x {len(dimensions)} dimensions "
          f"({len(group_by_category(dimensions))} category batches) via backend={args.backend}...")

    results = run(tasks, dimensions, backend=args.backend, model=args.model,
                  effort=args.effort, jobs=args.jobs)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for rec in results:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    attributed = sum(
        1 for r in results for f in r["fields"]
        if f.get("value") is not None and f.get("assignment_type") != "unsupported"
    )
    print(f"Wrote {len(results)} records ({attributed} attributed fields) -> {args.out}\n")

    errors, warnings = conformance.check_results(results, dimensions, tasks)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors[:20]:
        print(f"ERROR {e}")
    if errors:
        print(f"\nFAIL conformance: {len(errors)} error(s). Fix solver.py output and re-run.")
        return 1
    print("PASS conformance. Send this results.jsonl back to the owner.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
