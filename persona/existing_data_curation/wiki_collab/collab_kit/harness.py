#!/usr/bin/env python3
"""harness.py — the provided runner (resumable, with progress + status).

Reads the owner's tasks.jsonl + dimensions.json, calls solver.attribute() for
each (profile, category) unit, and writes results.jsonl in the contract format.
It is SAFE TO STOP AND RE-RUN: every finished unit is checkpointed to
`<out>.progress.jsonl`, with its own run provenance. If your model quota runs
out (or you Ctrl-C), rerun later and it resumes where it left off — finished
units are skipped, only the remaining ones are attempted. When invoked through
run_assignment.sh, you can switch backend/model/effort before resuming; mixed
results preserve per-unit provenance.

  # run (and resume):
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
import datetime
import json
import os
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

KIT_DIR = Path(__file__).resolve().parent
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))

import conformance  # noqa: E402
import solver  # noqa: E402

HARNESS_VERSION = "1.0.0"
BACKEND_CHOICES = ("mock", "claude-code-acp", "codex-acp")
EFFORT_CHOICES_BY_BACKEND = {
    "mock": ("high",),
    "codex-acp": ("high", "medium", "xhigh"),
    "claude-code-acp": ("high", "medium", "xhigh", "max"),
}
DEFAULT_MAX_FAILURES = 8

Unit = tuple[int, str]  # (global_idx, category)
UnitResult = dict[str, Any]  # {"fields": [...], "run": {...}}


def run_provenance(backend: str, model: str | None, effort: str) -> dict[str, Any]:
    """What produced these results — stamped on every record so the returned
    log always says which model/version/effort was used."""
    resolved = model
    if resolved is None:
        try:
            from backends import DEFAULT_MODELS  # bundled in this kit
            resolved = DEFAULT_MODELS.get(backend)
        except Exception:
            resolved = None
    run = {
        "backend": backend,
        "model": resolved,
        "effort": effort,
        "runner_version": HARNESS_VERSION,
    }
    assignment_raw = os.environ.get("WIKI_COLLAB_ASSIGNMENT_PROVENANCE")
    if assignment_raw:
        try:
            assignment = json.loads(assignment_raw)
        except json.JSONDecodeError:
            assignment = None
        if isinstance(assignment, dict):
            run["assignment"] = assignment
    return run


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


def failures_path(out: Path) -> Path:
    """Durable per-unit failure log. The worker sends this back to the owner so a
    blank `exited 1:` in the terminal isn't the only record of what went wrong."""
    return out.with_name(out.name + ".failures.jsonl")


def _fmt_duration(seconds: float) -> str:
    """Human-readable duration: '45s', '2m13s', '1h04m'."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


class _Progress:
    """A single-line progress bar on a TTY; periodic lines when piped/logged.

    Renders to stderr so it never mixes into the structured stdout output. Used
    only from the main thread (workers just compute), so no locking is needed."""

    def __init__(self, total: int, *, completed: int = 0, tty: bool, stream=None) -> None:
        self.total = total
        self.completed = completed
        self.failed = 0
        self.tty = tty
        self.stream = stream or sys.stderr
        self._step = max(1, total // 100)
        self._last_periodic = completed
        self._start = time.monotonic()
        self._initial = completed  # resume baseline; ETA uses throughput since start

    def _eta(self) -> str:
        """Estimate time left from this run's throughput. Empty until a couple of
        units finish (no rate yet) or once everything has been attempted."""
        attempted = self.completed + self.failed
        done_this_run = attempted - self._initial
        remaining = self.total - attempted
        if done_this_run <= 0 or remaining <= 0:
            return ""
        elapsed = time.monotonic() - self._start
        if elapsed <= 0:
            return ""
        rate = done_this_run / elapsed  # units per second, this run
        return _fmt_duration(remaining / rate)

    def _bar(self) -> str:
        attempted = self.completed + self.failed
        pct = (100 * attempted // self.total) if self.total else 100
        width = 28
        filled = int(width * attempted / self.total) if self.total else width
        bar = (
            f"[{'█' * filled}{'░' * (width - filled)}] {pct:3d}%  "
            f"done {self.completed}/{self.total}"
        )
        if self.failed:
            bar += f" · failed {self.failed}"
        bar += f" · used {_fmt_duration(time.monotonic() - self._start)}"
        eta = self._eta()
        if eta:
            bar += f" · ETA {eta}"
        return bar

    def redraw(self) -> None:
        attempted = self.completed + self.failed
        if self.tty:
            self.stream.write("\r" + self._bar() + "\x1b[K")
            self.stream.flush()
        elif attempted - self._last_periodic >= self._step or attempted == self.total:
            self._last_periodic = attempted
            print("  " + self._bar(), file=self.stream, flush=True)

    def tick_done(self) -> None:
        self.completed += 1
        self.redraw()

    def tick_failed(self) -> None:
        self.failed += 1
        self.redraw()

    def log(self, line: str) -> None:
        """Print a full message without clobbering the in-place bar."""
        if self.tty:
            self.stream.write("\r\x1b[K" + line + "\n")
            self.stream.flush()
            self.redraw()
        else:
            print(line, file=self.stream, flush=True)

    def close(self) -> None:
        if self.tty:
            self.stream.write("\n")
            self.stream.flush()


def _dedupe_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        key = json.dumps(run, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        unique.append(run)
    return unique


def _common_assignment(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    assignments = [
        run.get("assignment")
        for run in runs
        if isinstance(run.get("assignment"), dict)
    ]
    if not assignments:
        return None
    comparable = [
        {
            key: value
            for key, value in assignment.items()
            if key != "settings_hash"
        }
        for assignment in assignments
    ]
    first = comparable[0]
    if all(item == first for item in comparable):
        return assignments[-1]
    return None


def _profile_run(base_run: dict[str, Any], unit_runs: list[dict[str, Any]]) -> dict[str, Any]:
    unique_runs = _dedupe_runs(unit_runs)
    if len(unique_runs) <= 1:
        return dict(unique_runs[0]) if unique_runs else dict(base_run)
    run = {
        "backend": "mixed",
        "model": "mixed",
        "effort": "mixed",
        "runner_version": base_run.get("runner_version", HARNESS_VERSION),
        "mixed_provenance": True,
        "unit_runs": unique_runs,
    }
    assignment = _common_assignment(unique_runs)
    if assignment is not None:
        run["assignment"] = assignment
    return run


def load_checkpoint(
    path: Path,
    *,
    default_run: dict[str, Any] | None = None,
) -> dict[Unit, UnitResult]:
    """Read finished units from a prior run. Tolerates a truncated last line."""
    done: dict[Unit, UnitResult] = {}
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
                fields = rec.get("fields", [])
                if not isinstance(fields, list):
                    fields = []
                run = rec.get("run")
                if not isinstance(run, dict):
                    run = default_run
                done[(gi, cat)] = {"fields": fields, "run": run}
    return done


def assemble_results(
    tasks: list[dict[str, Any]],
    done: dict[Unit, UnitResult] | dict[Unit, list[dict[str, Any]]],
    run: dict[str, Any],
) -> list[dict[str, Any]]:
    """Union all finished category-units back into one record per profile."""
    per_profile: dict[int, dict[str, dict[str, Any]]] = {}
    per_profile_runs: dict[int, list[dict[str, Any]]] = {}
    for (gi, _cat), unit_result in done.items():
        if isinstance(unit_result, dict) and "fields" in unit_result:
            fields = unit_result.get("fields", [])
            unit_run = unit_result.get("run") if isinstance(unit_result.get("run"), dict) else run
        else:
            fields = unit_result
            unit_run = run
        if isinstance(unit_run, dict):
            per_profile_runs.setdefault(gi, []).append(unit_run)
        if not isinstance(fields, list):
            continue
        bucket = per_profile.setdefault(gi, {})
        for f in fields:
            fid = f.get("field_id")
            if fid:
                field = dict(f)
                if isinstance(unit_run, dict):
                    field["run"] = unit_run
                bucket[str(fid)] = field
    results = []
    for task in tasks:
        gi = task.get("global_idx")
        profile_run = _profile_run(run, per_profile_runs.get(gi, []))
        results.append(
            {
                "global_idx": gi,
                "task_id": task.get("task_id"),
                "qid": task.get("qid"),
                "input_sha256": task.get("input_sha256"),
                "model": profile_run.get("model"),  # back-compat mirror of run.model
                "run": profile_run,
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
    run: dict[str, Any],
    jobs: int,
    max_failures: int = DEFAULT_MAX_FAILURES,
) -> tuple[dict[Unit, UnitResult], int]:
    """Attempt all not-yet-done (profile, category) units. Returns (done, failed)."""
    batches = group_by_category(dimensions)
    units: list[tuple[Unit, dict[str, Any], list[dict[str, Any]]]] = []
    for task in tasks:
        gi = task.get("global_idx")
        for cat, batch in batches.items():
            units.append(((gi, cat), task, batch))

    ckpt = progress_path(out)
    fail_log = failures_path(out)
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    done = load_checkpoint(ckpt, default_run=run)
    pending = [u for u in units if u[0] not in done]

    total = len(units)
    completed = total - len(pending)
    print(f"Units: {total} total ({len(tasks)} profiles x {len(batches)} categories) | "
          f"done {completed} | to do {len(pending)} | backend={backend}"
          f"{' model=' + model if model else ''} effort={effort}", flush=True)
    if not pending:
        return done, 0

    lock = threading.Lock()
    failed = 0
    stop_after_failures = max(1, max_failures)
    progress = _Progress(total, completed=completed, tty=sys.stderr.isatty())
    progress.redraw()
    fh = open(ckpt, "a", encoding="utf-8")
    fail_fh = None  # opened lazily on the first failure (no empty file on clean runs)

    def _one(unit: tuple[Unit, dict[str, Any], list[dict[str, Any]]]):
        key, task, batch = unit
        fields = solver.attribute(task, batch, backend=backend, model=model, effort=effort)
        return key, fields

    def _record(key: Unit, fields: list[dict[str, Any]]) -> None:
        with lock:
            fh.write(json.dumps(
                {"global_idx": key[0], "category": key[1], "run": run, "fields": fields},
                ensure_ascii=False) + "\n")
            fh.flush()
            done[key] = {"fields": fields, "run": run}
            progress.tick_done()

    def _record_failure(unit: tuple[Unit, dict[str, Any], list[dict[str, Any]]], exc: Exception) -> None:
        nonlocal failed, fail_fh
        failed += 1
        gi, cat = unit[0]
        if fail_fh is None:
            fail_fh = open(fail_log, "a", encoding="utf-8")
        fail_fh.write(json.dumps({
            "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "global_idx": gi,
            "category": cat,
            "backend": backend,
            "model": model,
            "effort": effort,
            "runner_version": HARNESS_VERSION,
            "error": str(exc)[:4000],  # full backend stderr/stdout, bounded
        }, ensure_ascii=False) + "\n")
        fail_fh.flush()
        msg = str(exc).strip()
        first = msg.splitlines()[0][:200] if msg else "(no error text — see failures log)"
        progress.log(f"WARN gidx={gi} cat={cat}: {first}")

    try:
        if jobs <= 1:
            for unit in pending:
                try:
                    key, fields = _one(unit)
                    _record(key, fields)
                except Exception as exc:  # quota/network/parse — keep progress, resume later
                    _record_failure(unit, exc)
                    progress.tick_failed()
                    if failed >= stop_after_failures:
                        progress.log(
                            f"Stopping after {failed} failed unit(s); fix quota/auth/errors "
                            "and rerun to resume."
                        )
                        break
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
                pending_iter = iter(pending)
                futs: dict[concurrent.futures.Future, tuple[Unit, dict[str, Any], list[dict[str, Any]]]] = {}
                stopping = False

                def _submit_next() -> None:
                    try:
                        unit = next(pending_iter)
                    except StopIteration:
                        return
                    futs[ex.submit(_one, unit)] = unit

                for _ in range(min(jobs, len(pending))):
                    _submit_next()

                while futs:
                    done_futs, _ = concurrent.futures.wait(
                        futs,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    for fut in done_futs:
                        unit = futs.pop(fut)
                        if fut.cancelled():
                            continue
                        try:
                            key, fields = fut.result()
                            _record(key, fields)
                        except Exception as exc:
                            _record_failure(unit, exc)
                            progress.tick_failed()
                            if failed >= stop_after_failures and not stopping:
                                stopping = True
                                progress.log(
                                    f"Stopping after {failed} failed unit(s); fix quota/auth/errors "
                                    "and rerun to resume."
                                )
                                for pending_fut in futs:
                                    pending_fut.cancel()
                        if not stopping:
                            _submit_next()
    finally:
        fh.close()
        if fail_fh is not None:
            fail_fh.close()
        progress.close()
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
    ap.add_argument("--backend", default="mock", choices=BACKEND_CHOICES,
                    help="mock | claude-code-acp | codex-acp")
    ap.add_argument("--model", default=None, help="model id (defaults per backend)")
    ap.add_argument(
        "--effort",
        default="high",
        choices=sorted({effort for efforts in EFFORT_CHOICES_BY_BACKEND.values() for effort in efforts}),
        help="reasoning effort; Codex: high|medium|xhigh; "
             "Claude Code: high|medium|xhigh|max",
    )
    ap.add_argument("--jobs", type=int, default=4, help="parallel (profile, category) calls")
    ap.add_argument(
        "--max-failures",
        type=int,
        default=DEFAULT_MAX_FAILURES,
        help="stop after this many failed units so quota/auth outages do not hammer the backend",
    )
    ap.add_argument("--status", action="store_true",
                    help="show how far along you are (reads checkpoint), then exit")
    ap.add_argument("--restart", action="store_true",
                    help="discard the checkpoint and start over")
    args = ap.parse_args(argv)
    allowed_efforts = EFFORT_CHOICES_BY_BACKEND[args.backend]
    if args.effort not in allowed_efforts:
        ap.error(
            f"--effort {args.effort!r} is not supported for --backend {args.backend}; "
            f"choose one of: {', '.join(allowed_efforts)}"
        )
    if args.max_failures < 1:
        ap.error("--max-failures must be >= 1")
    return args


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
            print("Not finished. Re-run without --status to continue.")
        else:
            print("All units done. Re-run without --status to write & validate results.jsonl.")
        return 0

    if args.restart:
        for stale in (ckpt, failures_path(args.out)):
            if stale.exists():
                stale.unlink()
        print(f"Discarded checkpoint {ckpt}; starting over.")

    run = run_provenance(args.backend, args.model, args.effort)
    done, failed = run_resumable(
        tasks, dimensions, out=args.out, backend=args.backend,
        model=args.model, effort=args.effort, run=run, jobs=args.jobs,
        max_failures=args.max_failures,
    )

    results = assemble_results(tasks, done, run)
    write_results(args.out, results)
    attributed = sum(
        1 for r in results for f in r["fields"]
        if f.get("value") is not None and f.get("assignment_type") != "unsupported"
    )
    units_done = len(done)
    print(f"\nWrote {len(results)} records ({attributed} attributed fields) -> {args.out}")
    print(f"Units done: {units_done}/{total}" + (f"  (failed this run: {failed})" if failed else ""))

    fl = failures_path(args.out)
    if fl.exists() and fl.stat().st_size > 0:
        n = sum(1 for line in fl.read_text(encoding="utf-8").splitlines() if line.strip())
        print(f"\nFailure log: {n} failed unit(s) recorded -> {fl}")
        print("If you can't fix it yourself, send this file to the owner — it has the "
              "exact per-unit error from the model/CLI.")

    if units_done < total:
        print(f"\nNOT COMPLETE — {total - units_done} unit(s) still pending "
              f"(quota/errors?). Re-run to finish; finished units are skipped.")
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
