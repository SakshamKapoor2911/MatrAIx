#!/usr/bin/env python3
"""harness.py — the provided runner (resumable, with progress + status).

Reads the owner's tasks.jsonl + dimensions.json, calls solver.attribute() for
each (profile, category) unit, and writes results.jsonl in the contract format.
It is SAFE TO STOP AND RE-RUN: every finished unit is checkpointed to
`<out>.progress.jsonl`, so if your model quota runs out (or you Ctrl-C), just
run the SAME command again later and it resumes where it left off — finished
units are skipped, only the remaining ones are attempted.

  # run (and resume — same command both times):
  python3 harness.py --tasks tasks.jsonl --dimensions dimensions.json \
      --out results.jsonl --backend claude-code-acp \
      --model claude-opus-4-8 --effort high --jobs 6

  # how far along am I? (reads the checkpoint, runs nothing)
  python3 harness.py --tasks tasks.jsonl --dimensions dimensions.json \
      --out results.jsonl --status

  # start over, discarding the checkpoint:
  python3 harness.py ... --restart

When everything is done it runs the conformance check; a green run means
results.jsonl is ready to send back.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any

KIT_DIR = Path(__file__).resolve().parent
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))

import conformance  # noqa: E402
import solver  # noqa: E402

Unit = tuple[int, str]  # (global_idx, category)


def group_by_category(
    dimensions: list[dict[str, Any]]
) -> "OrderedDict[str, list[dict[str, Any]]]":
    """category name -> its dimensions (order preserved; missing category = '_')."""
    batches: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for d in dimensions:
        batches.setdefault(str(d.get("category", "_")), []).append(d)
    return batches


def progress_path(out: Path) -> Path:
    return out.with_name(out.name + ".progress.jsonl")


def load_checkpoint(path: Path) -> dict[Unit, list[dict[str, Any]]]:
    """Read finished units from a prior run. Tolerates a truncated last line."""
    done: dict[Unit, list[dict[str, Any]]] = {}
    if not path.exists():
        return done
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # ignore a half-written final line from a hard kill
            gi, cat = rec.get("global_idx"), rec.get("category")
            if isinstance(gi, int) and isinstance(cat, str):
                done[(gi, cat)] = rec.get("fields", [])
    return done


def assemble_results(
    tasks: list[dict[str, Any]],
    done: dict[Unit, list[dict[str, Any]]],
    model: str | None,
) -> list[dict[str, Any]]:
    """Union all finished category-units back into one record per profile."""
    per_profile: dict[int, dict[str, dict[str, Any]]] = {}
    for (gi, _cat), fields in done.items():
        bucket = per_profile.setdefault(gi, {})
        for f in fields:
            fid = f.get("field_id")
            if fid:
                bucket[str(fid)] = f
    results = []
    for task in tasks:
        gi = task.get("global_idx")
        results.append(
            {
                "global_idx": gi,
                "task_id": task.get("task_id"),
                "qid": task.get("qid"),
                "model": model,
                "fields": list(per_profile.get(gi, {}).values()),
            }
        )
    return results


def run_resumable(
    tasks: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
    *,
    out: Path,
    backend: str,
    model: str | None,
    effort: str,
    jobs: int,
) -> tuple[dict[Unit, list[dict[str, Any]]], int]:
    """Attempt all not-yet-done (profile, category) units. Returns (done, failed)."""
    batches = group_by_category(dimensions)
    units: list[tuple[Unit, dict[str, Any], list[dict[str, Any]]]] = []
    for task in tasks:
        gi = task.get("global_idx")
        for cat, batch in batches.items():
            units.append(((gi, cat), task, batch))

    ckpt = progress_path(out)
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    done = load_checkpoint(ckpt)
    pending = [u for u in units if u[0] not in done]

    total = len(units)
    completed = total - len(pending)
    print(f"Units: {total} total ({len(tasks)} profiles x {len(batches)} categories) | "
          f"done {completed} | to do {len(pending)} | backend={backend}"
          f"{' model=' + model if model else ''} effort={effort}")
    if not pending:
        return done, 0

    lock = threading.Lock()
    step = max(1, total // 100)
    failed = 0
    fh = open(ckpt, "a", encoding="utf-8")

    def _one(unit: tuple[Unit, dict[str, Any], list[dict[str, Any]]]):
        key, task, batch = unit
        fields = solver.attribute(task, batch, backend=backend, model=model, effort=effort)
        return key, fields

    def _record(key: Unit, fields: list[dict[str, Any]]) -> None:
        nonlocal completed
        with lock:
            fh.write(json.dumps(
                {"global_idx": key[0], "category": key[1], "fields": fields},
                ensure_ascii=False) + "\n")
            fh.flush()
            done[key] = fields
            completed += 1
            if completed % step == 0 or completed == total:
                pct = 100 * completed // total
                print(f"  [{completed}/{total}] {pct}%", flush=True)

    try:
        if jobs <= 1:
            for unit in pending:
                try:
                    key, fields = _one(unit)
                    _record(key, fields)
                except Exception as exc:  # quota/network/parse — keep progress, resume later
                    failed += 1
                    print(f"  WARN unit gidx={unit[0][0]} cat={unit[0][1]} failed: {exc}",
                          file=sys.stderr)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
                futs = {ex.submit(_one, u): u for u in pending}
                for fut in concurrent.futures.as_completed(futs):
                    unit = futs[fut]
                    try:
                        key, fields = fut.result()
                        _record(key, fields)
                    except Exception as exc:
                        failed += 1
                        print(f"  WARN unit gidx={unit[0][0]} cat={unit[0][1]} failed: {exc}",
                              file=sys.stderr)
    finally:
        fh.close()
    return done, failed


def write_results(out: Path, results: list[dict[str, Any]]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        for rec in results:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--dimensions", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results.jsonl"))
    ap.add_argument("--backend", default="mock",
                    help="mock | claude-code-acp | codex-acp | anthropic-api | openai-api")
    ap.add_argument("--model", default=None, help="model id (defaults per backend)")
    ap.add_argument("--effort", default="high", help="reasoning effort: low|medium|high|max")
    ap.add_argument("--jobs", type=int, default=4, help="parallel (profile, category) calls")
    ap.add_argument("--status", action="store_true",
                    help="show how far along you are (reads checkpoint), then exit")
    ap.add_argument("--restart", action="store_true",
                    help="discard the checkpoint and start over")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tasks = conformance.load_jsonl(args.tasks)
    dimensions = json.loads(args.dimensions.read_text(encoding="utf-8"))
    batches = group_by_category(dimensions)
    total = len(tasks) * len(batches)
    ckpt = progress_path(args.out)

    if args.status:
        done = load_checkpoint(ckpt)
        n = sum(1 for t in tasks for cat in batches if (t.get("global_idx"), cat) in done)
        profiles_done = sum(
            1 for t in tasks
            if all((t.get("global_idx"), cat) in done for cat in batches)
        )
        pct = (100 * n // total) if total else 100
        print(f"Progress: {n}/{total} units ({pct}%) | "
              f"{profiles_done}/{len(tasks)} profiles fully done | checkpoint: {ckpt}")
        if n < total:
            print("Not finished. Re-run the same command (without --status) to continue.")
        else:
            print("All units done. Re-run without --status to write & validate results.jsonl.")
        return 0

    if args.restart and ckpt.exists():
        ckpt.unlink()
        print(f"Discarded checkpoint {ckpt}; starting over.")

    done, failed = run_resumable(
        tasks, dimensions, out=args.out, backend=args.backend,
        model=args.model, effort=args.effort, jobs=args.jobs,
    )

    results = assemble_results(tasks, done, args.model)
    write_results(args.out, results)
    attributed = sum(
        1 for r in results for f in r["fields"]
        if f.get("value") is not None and f.get("assignment_type") != "unsupported"
    )
    units_done = len(done)
    print(f"\nWrote {len(results)} records ({attributed} attributed fields) -> {args.out}")
    print(f"Units done: {units_done}/{total}" + (f"  (failed this run: {failed})" if failed else ""))

    if units_done < total:
        print(f"\nNOT COMPLETE — {total - units_done} unit(s) still pending "
              f"(quota/errors?). Re-run the SAME command to finish; finished units are skipped.")
        # still validate what we have so the format is known-good
        errors, _ = conformance.check_results(results, dimensions, tasks)
        if errors:
            print(f"(partial results have {len(errors)} conformance error(s) — see solver output.)")
        return 1

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
