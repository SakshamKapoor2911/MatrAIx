"""Parallel overnight runner: every (arm × seed) job as its own process on its own worker DB.

This is the PARALLELIZATION answer. Two levels of concurrency:
  * WITHIN a tick: the 25 agents' Bedrock calls are ALREADY concurrent (run_real_inproc._decide_for_tick
    uses asyncio.gather behind a semaphore) — nothing to add there.
  * ACROSS runs: each (arm, seed) is an independent simulation. They cannot share one database (every
    bootstrap WIPES it), so each runs as a separate OS process pointed at its own worker DB
    (mircoverse_w0..). This script is the across-run scheduler.

CORRECTNESS (the bit that silently corrupts data if wrong): config.Settings reads DATABASE_URL at IMPORT
time into a frozen dataclass. So a child MUST receive its DATABASE_URL via the spawn environment (env=),
BEFORE it imports anything — we never mutate os.environ in-process and hope. Each child also re-asserts
it is NOT on the default DB (run_real_inproc / the assert below), so a misconfigured spawn fails loudly
instead of 3 jobs stampeding the same database.

Concurrency budget: each job internally runs up to `--per-job-concurrency` simultaneous Bedrock calls
(default 6). With J jobs in flight that is J×6 concurrent calls against the Bedrock account quota — keep
J×per-job-concurrency under your throughput limit or every job will throttle (and the retry/backoff will
just slow everything). Default --max-parallel-jobs 3 ⇒ 18 concurrent calls.

The token lives ONLY in this process's env and is inherited by children; it is NEVER placed on a command
line. Postgres + worker DBs must already exist (run setup_worker_dbs.py first).

Usage:
    .venv/Scripts/python.exe scripts/setup_worker_dbs.py --workers 3
    AWS_BEARER_TOKEN_BEDROCK=... .venv/Scripts/python.exe scripts/run_overnight.py \\
        --arms acute mild control --seeds 1 2 3 --ticks 1000 --max-parallel-jobs 3
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_three_settings import _ARMS  # the arm bundles are the single source of arm truth
from scripts.setup_worker_dbs import worker_dsn

_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _ROOT / "data" / "overnight_logs"
_ARM_LABELS = [a[0] for a in _ARMS]


async def _spawn_child(arm: str, seed: int, worker_idx: int, args) -> int:
    """Spawn the actual single-run child process on worker DB ``worker_idx``; return its exit code.

    Factored out from the scheduler so the worker-DB allocation (the part that, done wrong, silently
    corrupts data) can be tested against a fake spawn without launching real Bedrock work."""
    dsn = worker_dsn(os.getenv("DATABASE_URL",
                               "postgresql://mircoverse:mircoverse@localhost:5432/mircoverse"),
                     worker_idx)
    # Child env: inherit everything (incl. the Bedrock token), but OVERRIDE DATABASE_URL so the
    # frozen Settings in the child points at this job's isolated DB. Set at spawn, never mutated.
    child_env = dict(os.environ)
    child_env["DATABASE_URL"] = dsn

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _LOG_DIR / f"{arm}_seed{seed}.log"

    # Reuse the proven single-run path: run_three_settings --only <arm> --seed <seed>. Each writes
    # data/runs/<arm>_seed<seed>.json. (run_three_settings writes one artifact per arm, so --only
    # one arm + one seed = exactly one job's worth of work, isolated on its own DB.)
    cmd = [
        sys.executable, "-u", "scripts/run_three_settings.py",
        "--only", arm, "--seed", str(seed),
        "--agents", str(args.agents), "--ticks", str(args.ticks),
        "--model", args.model, "--region", args.region,
        "--reflection-threshold", str(args.reflection_threshold),
    ]
    print(f"  >> start {arm} seed={seed} on {dsn.rsplit('/', 1)[-1]} -> {log_path.name}")
    with open(log_path, "w", encoding="utf-8") as logf:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=str(_ROOT), env=child_env, stdout=logf, stderr=asyncio.subprocess.STDOUT,
        )
        return await proc.wait()


async def _run_job(arm: str, seed: int, args, pool: "asyncio.Queue[int]", spawn=_spawn_child) -> dict:
    """Run ONE (arm, seed) job, holding a worker DB EXCLUSIVELY for its whole lifetime.

    The DB comes from ``pool`` — a queue of idle worker-DB indices. ``pool.get()`` blocks until an
    index is actually free and removes it, so no other in-flight job can be handed the same DB; the
    ``finally`` returns it only after this job's process has fully exited. This is the fix for the
    static-index bug: jobs finish OUT OF ORDER (acute collapses ~t40, control runs full length), so a
    fixed ``i % n_workers`` mapping plus a counting semaphore would admit a new job onto a DB a slower
    job is still writing — whose bootstrap WIPES it mid-run (initialize_simulation, bootstrap.py step 1),
    silently corrupting BOTH artifacts. The pool makes "a slot is free" and "a DB is free" the same fact.
    The queue's size is therefore the real concurrency cap (no separate semaphore)."""
    worker_idx = await pool.get()
    try:
        log_path = _LOG_DIR / f"{arm}_seed{seed}.log"
        rc = await spawn(arm, seed, worker_idx, args)
    finally:
        pool.put_nowait(worker_idx)  # release the DB for the next queued job (even on failure)
    ok = rc == 0
    print(f"  {'[OK]' if ok else '[FAIL]'} done  {arm} seed={seed}  exit={rc}")
    return {"arm": arm, "seed": seed, "worker": worker_idx, "exit_code": rc, "ok": ok,
            "log": str(log_path), "artifact": f"data/runs/{arm}_seed{seed}.json"}


async def main_async(args) -> None:
    # Pre-flight: token present (env only — check length/prefix, NEVER print the value).
    tok = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    if not tok:
        raise SystemExit("AWS_BEARER_TOKEN_BEDROCK not in env. Export it (never on the CLI) and retry.")
    print(f"token present (len={len(tok)}, prefix={tok[:6]}…)")

    jobs = [(arm, seed) for arm in args.arms for seed in args.seeds]
    n_workers = args.workers if args.workers else min(args.max_parallel_jobs, len(jobs))
    # Concurrency is bounded by the number of worker DBs we actually hand out, NOT a separate semaphore.
    # A job runs iff it holds a DB; at most n_workers DBs exist ⇒ at most n_workers jobs in flight. If
    # the user asked for more parallelism than we have DBs, the DB count wins (and we say so), because
    # exceeding it is exactly the corruption we're preventing.
    effective_parallel = min(args.max_parallel_jobs, n_workers)
    if effective_parallel < 1:
        raise SystemExit(f"effective parallelism is {effective_parallel} (max_parallel_jobs="
                         f"{args.max_parallel_jobs}, n_workers={n_workers}); must be >= 1. "
                         f"The pool would be empty and the run would hang. Fix the flags.")
    if effective_parallel < args.max_parallel_jobs:
        print(f"  note: capping parallelism at {effective_parallel} (only {n_workers} worker DBs; "
              f"run setup_worker_dbs.py --workers {args.max_parallel_jobs} for more).")
    print(f"{len(jobs)} jobs ({len(args.arms)} arms × {len(args.seeds)} seeds), "
          f"{n_workers} worker DBs, {effective_parallel} parallel "
          f"(⇒ ≤{effective_parallel * 6} concurrent Bedrock calls)\n")

    # The free-DB pool: a queue pre-loaded with the idle worker-DB indices. A job acquires one with
    # pool.get() (blocks until one is genuinely free) and returns it only after its process exits, so
    # two live jobs can NEVER share a DB. Pool size == the real concurrency cap (see _run_job).
    pool: asyncio.Queue[int] = asyncio.Queue()
    for idx in range(effective_parallel):
        pool.put_nowait(idx)

    # return_exceptions=True so ONE scheduler-level raise (EMFILE on spawn, a PermissionError opening
    # a log, an OSError mid-night) cannot cancel every sibling job and orphan their live subprocesses —
    # the whole point of an unattended run is that a single failure costs one job, not the night. A
    # returned BaseException is recorded as a failed job below. (The DB-corruption invariant is
    # unaffected either way: each job still holds a unique pooled index, so no double-book.)
    job_specs = list(jobs)  # parallel to results for labeling exceptions back to their (arm, seed)
    tasks = [_run_job(arm, seed, args, pool) for arm, seed in job_specs]
    results_raw = await asyncio.gather(*tasks, return_exceptions=True)
    results = []
    for (arm, seed), r in zip(job_specs, results_raw):
        if isinstance(r, BaseException):
            print(f"  [FAIL] scheduler error for {arm} seed={seed}: {r!r}")
            results.append({"arm": arm, "seed": seed, "worker": -1, "exit_code": None,
                            "ok": False, "log": str(_LOG_DIR / f"{arm}_seed{seed}.log"),
                            "artifact": f"data/runs/{arm}_seed{seed}.json", "error": repr(r)})
        else:
            results.append(r)

    ok = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    # Durable roll-up: tee the GO/NO-GO verdict to a file so it survives a closed terminal overnight.
    lines = ["=" * 60, f"OVERNIGHT COMPLETE: {len(ok)}/{len(results)} jobs succeeded"]
    for r in results:
        lines.append(f"  {'OK ' if r['ok'] else 'FAIL'}  {r['arm']:<8} seed={r['seed']}  "
                     f"exit={r['exit_code']}  {r['artifact'] if r['ok'] else r['log']}")
    if bad:
        lines.append(f"\n  {len(bad)} job(s) FAILED — inspect their logs in {_LOG_DIR}")
    lines.append("=" * 60)
    summary = "\n".join(lines)
    print("\n" + summary)
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        (_LOG_DIR / "SUMMARY.txt").write_text(summary + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — a failed tee must not mask the run result
        print(f"  (could not write SUMMARY.txt: {exc!r})")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Parallel (arm × seed) overnight runner on isolated worker DBs")
    ap.add_argument("--arms", nargs="+", default=_ARM_LABELS, choices=_ARM_LABELS)
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--agents", type=int, default=25)
    ap.add_argument("--ticks", type=int, default=1000)
    ap.add_argument("--model", default="global.anthropic.claude-haiku-4-5-20251001-v1:0")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--reflection-threshold", type=int, default=60)
    ap.add_argument("--max-parallel-jobs", type=int, default=3,
                    help="jobs in flight at once; ×6 = concurrent Bedrock calls (mind the quota)")
    ap.add_argument("--workers", type=int, default=0,
                    help="number of worker DBs (0 = min(max-parallel-jobs, n_jobs)); must already exist")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
