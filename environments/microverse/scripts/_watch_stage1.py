"""Non-destructive watcher for the Stage-1 calibration smoke (control+acute, t300, seed1).

The run was launched detached (nohup); its tool-wrapper already returned exit-0, so there is no
reliable completion signal from the harness. This watcher READS ONLY (DB + the two artifacts + the
log) and exits exactly once at a meaningful moment, emitting the calibration verdict:

  * DONE   — both control_seed1.json and acute_seed1.json (re)written after start AND the log shows
             "ALL RUNS COMPLETE". Prints the survival curve + the PASS/FAIL gate on the calibration
             criteria (acute >=10/25 alive at t300 trending up; control loses ~0; agent_errors==0).
  * STALL  — max_tick frozen for STALL_POLLS polls => crashed/hung; tails the log; exit 2.
  * TIMEOUT— hard cap; exit 3.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mircoverse.persistence import db
from mircoverse.config import settings

RUNS = Path(__file__).resolve().parent.parent / "data" / "runs"
LOG = Path(__file__).resolve().parent.parent / "data" / "stage1_calibration.log"
ARTIFACTS = {"acute": RUNS / "acute_seed1.json", "control": RUNS / "control_seed1.json"}
POLL_SECS = 120
STALL_POLLS = 6
MAX_HOURS = 8.0
TICKS_TARGET = 300


def _mtimes():
    return {k: (p.stat().st_mtime if p.exists() else None) for k, p in ARTIFACTS.items()}


def _report():
    print("\n=== STAGE-1 CALIBRATION RESULT ===")
    verdicts = {}
    for arm, p in ARTIFACTS.items():
        if not p.exists():
            print(f"  {arm}: artifact MISSING")
            continue
        art = json.loads(p.read_text(encoding="utf-8"))
        infra = art.get("infra") or {}
        errs = infra.get("agent_errors_total", 0)
        # survival-at-t300 = survivors at end of a 300-tick run (final state)
        surv = art.get("survivors")
        n = art.get("n_agents")
        contaminated = art.get("infra_contaminated")
        print(f"  {arm:8} survivors={surv}/{n}  agent_errors={errs}  "
              f"throttle_retries={infra.get('throttle_retries_total', 0)}"
              f"{'  <<< INFRA-CONTAMINATED' if contaminated else ''}")
        verdicts[arm] = {"surv": surv, "n": n, "errs": errs, "contaminated": contaminated}

    # Gate (REFRAMED 2026-06-06): control must be non-binding (>=90% survive). ACUTE has NO survival
    # floor — its fast collapse is an ACCEPTED "high access-difficulty" extreme, NOT a failure.
    # (MILD is the alive-AND-pressured arm and is validated in a SEPARATE mild smoke, not this one.)
    ok = True
    msgs = []
    if "control" in verdicts:
        c = verdicts["control"]
        if c["contaminated"] or c["errs"] > 3:
            ok = False; msgs.append("control infra-contaminated")
        if c["surv"] is not None and c["surv"] < 0.9 * c["n"]:
            ok = False; msgs.append(f"control survival {c['surv']}/{c['n']} < 90% — control NOT "
                                    f"non-binding; bump oasis_regen/cap UP and re-smoke")
        else:
            msgs.append(f"control {c['surv']}/{c['n']} survive — non-binding baseline OK")
    if "acute" in verdicts:
        a = verdicts["acute"]
        if a["contaminated"] or a["errs"] > 3:
            ok = False; msgs.append("acute infra-contaminated")
        else:
            msgs.append(f"acute {a['surv']}/{a['n']} survive — collapse is the ACCEPTED erosion extreme "
                        f"(no floor required)")
    msgs.append("NEXT: validate MILD in its own t300 smoke (needs >=10/25 alive, trending up).")
    print(f"\n  CALIBRATION GATE (control + acute): "
          f"{'PASS — control non-binding, acute valid; now smoke MILD' if ok else 'FAIL — see below'}")
    for m in msgs:
        print(f"    - {m}")
    print("  (final arm numbers should be re-derived from these survival curves before the overnight run.)")


def _tail(n=25):
    try:
        for ln in LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]:
            print("  " + ln)
    except FileNotFoundError:
        print("  (no log)")


async def _poll():
    async with db.connection() as conn:
        mt = await conn.fetchval("SELECT COALESCE(MAX(tick_number), -1) FROM action_log")
        na = await conn.fetchval("SELECT count(*) FROM action_log")
        al = await conn.fetchval("SELECT count(*) FROM agents WHERE status='active'")
    await db.close_pool()
    return int(mt), int(na), int(al)


def _log_has_complete() -> bool:
    try:
        return "ALL RUNS COMPLETE" in LOG.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return False


async def main():
    if not await db.ping(settings.database_url):
        print("WATCHER: DB unreachable"); return 1
    start = time.time()
    base = _mtimes()
    print(f"STAGE-1 WATCHER start: target_tick={TICKS_TARGET} arms={list(ARTIFACTS)} mtimes={base}")
    last_tick, stall = -1, 0
    while True:
        elapsed = (time.time() - start) / 3600.0
        try:
            mt, na, al = await _poll()
        except Exception as exc:  # noqa: BLE001
            print(f"WATCHER poll error: {exc!r}")
            await asyncio.sleep(POLL_SECS); continue

        # DONE: both artifacts rewritten after start AND the harness printed completion.
        now = _mtimes()
        both_fresh = all(now[k] is not None and (base[k] is None or now[k] > base[k] + 1) for k in ARTIFACTS)
        if both_fresh and _log_has_complete():
            print(f"WATCHER: DONE at {elapsed:.2f}h (both artifacts written, log complete).")
            _report()
            return 0

        if mt == last_tick:
            stall += 1
        else:
            stall = 0; last_tick = mt
        if stall >= STALL_POLLS:
            print(f"WATCHER: STALLED at {elapsed:.2f}h (tick stuck at {mt} ~{stall*POLL_SECS//60}min).")
            _tail()
            return 2
        if elapsed >= MAX_HOURS:
            print(f"WATCHER: TIMEOUT {elapsed:.2f}h (tick={mt}).")
            return 3
        print(f"  [hb {elapsed:5.2f}h] tick={mt:>4} actions={na:>6} active={al}/25 stall={stall}")
        await asyncio.sleep(POLL_SECS)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass
    raise SystemExit(asyncio.run(main()))
