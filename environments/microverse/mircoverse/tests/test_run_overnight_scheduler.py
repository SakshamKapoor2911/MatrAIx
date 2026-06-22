"""Scheduler-safety tests for scripts/run_overnight.py.

The thing under test is NOT the simulation — it's the worker-DB allocator. The failure mode it
guards against is silent and catastrophic for an unattended overnight run: if two concurrently
running (arm, seed) jobs are ever handed the SAME worker DB, the second job's bootstrap
(initialize_simulation, bootstrap.py step 1) WIPES the database the first is still writing, and BOTH
artifacts come out corrupt with no error raised. Jobs finish out of order (acute collapses ~t40,
control runs the full length), which is exactly what made the old static `i % n_workers` mapping
unsafe. These tests run the real scheduler with a FAKE spawn so no Bedrock work happens.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import scripts.run_overnight as ov


def _fake_duration(arm, seed) -> float:
    """Coarse, deterministic, NON-MONOTONIC-per-seed job durations.

    Two properties matter. (1) Coarse (tens to hundreds of ms, >> the Windows event-loop timer
    granularity of ~15ms) so the sleeps actually reorder — sub-ms sleeps all wake in FIFO insertion
    order and would make the race untestable. (2) Within an arm, seed=3 finishes BEFORE seed=1, so
    the first batch of jobs completes out of admission order — the exact condition under which the old
    static `i % n_workers` + counting-semaphore scheduler hands a freed slot a DB that an
    earlier-admitted, still-running job is holding."""
    base = {"acute": 0.30, "mild": 0.60, "control": 0.90}.get(arm, 0.45)
    seed_offset = {1: 0.0, 2: 0.15, 3: -0.25}.get(seed, 0.05 * seed)
    return max(0.05, base + seed_offset)


def _args(arms, seeds, max_parallel, workers=0):
    return SimpleNamespace(
        arms=arms, seeds=seeds, agents=25, ticks=300,
        model="m", region="r", reflection_threshold=60,
        max_parallel_jobs=max_parallel, workers=workers,
    )


class _OccupancyTracker:
    """A fake spawn that asserts no worker index is ever occupied by two jobs at once, while
    forcing out-of-order completion (the condition that broke the old scheduler)."""

    def __init__(self):
        self.live: dict[int, tuple] = {}      # worker_idx -> (arm, seed) currently running on it
        self.max_concurrent = 0
        self.collisions: list = []
        self.completed: list = []

    async def spawn(self, arm, seed, worker_idx, args):
        if worker_idx in self.live:
            self.collisions.append((worker_idx, self.live[worker_idx], (arm, seed)))
        self.live[worker_idx] = (arm, seed)
        self.max_concurrent = max(self.max_concurrent, len(self.live))
        await asyncio.sleep(_fake_duration(arm, seed))
        # Guarded release: under the OLD (buggy) scheduler a collision could have overwritten this
        # entry; only delete it if it's still ours, so the FIX's invariant check stays the signal
        # (not an incidental KeyError).
        if self.live.get(worker_idx) == (arm, seed):
            del self.live[worker_idx]
        self.completed.append((arm, seed))
        return 0


async def _drive(args, spawn):
    """Mirror main_async's pool construction + fan-out, but with an injected spawn (no real run)."""
    jobs = [(arm, seed) for arm in args.arms for seed in args.seeds]
    n_workers = args.workers if args.workers else min(args.max_parallel_jobs, len(jobs))
    effective_parallel = min(args.max_parallel_jobs, n_workers)
    pool: asyncio.Queue = asyncio.Queue()
    for idx in range(effective_parallel):
        pool.put_nowait(idx)
    tasks = [ov._run_job(arm, seed, args, pool, spawn=spawn) for arm, seed in jobs]
    return await asyncio.gather(*tasks), effective_parallel


async def test_no_two_live_jobs_share_a_worker_db():
    """The core invariant: with 3 arms × 3 seeds at parallelism 3, no worker DB is ever double-booked,
    even though jobs finish out of order."""
    tracker = _OccupancyTracker()
    args = _args(["acute", "mild", "control"], [1, 2, 3], max_parallel=3)
    results, _ = await _drive(args, tracker.spawn)

    assert tracker.collisions == [], f"worker DB double-booked: {tracker.collisions}"
    assert len(results) == 9
    assert all(r["ok"] for r in results)
    assert len(tracker.completed) == 9


async def test_concurrency_never_exceeds_pool_size():
    """The pool — not a separate semaphore — is the concurrency cap; it must never be exceeded."""
    tracker = _OccupancyTracker()
    args = _args(["acute", "mild", "control"], [1, 2, 3], max_parallel=3)
    await _drive(args, tracker.spawn)
    assert tracker.max_concurrent <= 3
    # And it should actually USE the parallelism (otherwise the test proves nothing).
    assert tracker.max_concurrent == 3


async def test_parallelism_capped_at_worker_db_count():
    """Asking for more parallel jobs than worker DBs must cap at the DB count, not over-subscribe
    (over-subscription is precisely the corruption path)."""
    tracker = _OccupancyTracker()
    args = _args(["acute", "mild", "control"], [1, 2, 3], max_parallel=8, workers=2)
    _, effective = await _drive(args, tracker.spawn)
    assert effective == 2
    assert tracker.max_concurrent <= 2
    assert tracker.collisions == []


async def test_every_worker_index_is_within_bounds():
    """Returned worker indices must all be < effective parallelism (valid, existing DBs)."""
    tracker = _OccupancyTracker()
    args = _args(["acute", "mild", "control"], [1, 2], max_parallel=3)
    results, effective = await _drive(args, tracker.spawn)
    assert all(0 <= r["worker"] < effective for r in results)


async def _drive_OLD_buggy(args, spawn):
    """The pre-fix scheduler, kept ONLY in this test: static worker = i % n_workers, admission gated
    by a counting Semaphore. Reproduced here so we can assert the new tests are non-vacuous — i.e.
    that the timing in this file genuinely exercises the race the fix removed."""
    jobs = [(arm, seed) for arm in args.arms for seed in args.seeds]
    n_workers = min(args.max_parallel_jobs, len(jobs))
    sem = asyncio.Semaphore(args.max_parallel_jobs)

    async def run(i, arm, seed):
        async with sem:
            await spawn(arm, seed, i % n_workers, args)

    await asyncio.gather(*(run(i, a, s) for i, (a, s) in enumerate(jobs)))


async def test_old_scheduler_WOULD_collide_proving_tests_are_not_vacuous():
    """Guard against a vacuous suite: the OLD static-index scheduler MUST collide under this file's
    timing. If this ever stops colliding, the other tests no longer prove the fix does anything."""
    tracker = _OccupancyTracker()
    args = _args(["acute", "mild", "control"], [1, 2, 3], max_parallel=3)
    await _drive_OLD_buggy(args, tracker.spawn)
    assert tracker.collisions, ("the old scheduler did not collide under this timing — the "
                                "no-collision tests would be vacuous; make _fake_duration more "
                                "out-of-order")


async def test_failed_job_still_releases_its_db():
    """A crashing job must return its DB to the pool (finally), or the pool starves and the run hangs.
    Here every job 'fails' (rc=1); all must still complete and free their DB."""
    class _Failing(_OccupancyTracker):
        async def spawn(self, arm, seed, worker_idx, args):
            if worker_idx in self.live:
                self.collisions.append((worker_idx, self.live[worker_idx], (arm, seed)))
            self.live[worker_idx] = (arm, seed)
            self.max_concurrent = max(self.max_concurrent, len(self.live))
            await asyncio.sleep(_fake_duration(arm, seed))
            if self.live.get(worker_idx) == (arm, seed):
                del self.live[worker_idx]
            self.completed.append((arm, seed))
            return 1  # non-zero exit

    tracker = _Failing()
    args = _args(["acute", "mild", "control"], [1, 2, 3], max_parallel=3)
    results, _ = await asyncio.wait_for(_drive(args, tracker.spawn), timeout=10.0)
    assert len(results) == 9
    assert all(not r["ok"] for r in results)
    assert tracker.collisions == []
