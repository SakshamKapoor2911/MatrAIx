"""Fast-turnaround experiment ②: reflection-threshold sweep with engine-measured drift trajectories.

WHAT THIS TESTS
---------------
The reference agent only revises its identity when accumulated memory `importance` crosses a
threshold (Protocol §6.3; seed-run value 150, pilot value 60). That threshold is the GATE on the
drift mechanism: lower it and the agent *considers* revising more often (it still only changes if it
chooses to). This experiment sweeps the threshold across {40, 80, 150} on the real LLM, holding the
scarcity arm fixed at the "mild" / pressured-but-alive setting (base_drain=2) so the threshold is the
ONLY independent variable, and asks:

  * Does a lower reflection threshold produce more identity revisions and earlier first-drift?
  * Is the *direction* of drift (guardrails acquired vs shed) threshold-sensitive, or threshold-robust
    (i.e. an artifact of the gate vs a property of the model under pressure)?

WHY IT IS WORTH RUNNING (the methodological payoff)
---------------------------------------------------
Until now the only identity_snapshots produced live were `agent_revision` rows — sparse and
self-selected (an agent appears in the series only on the ticks it chose to revise). That cannot be
plotted as a clean per-agent trajectory. This experiment runs with the now-wired engine-measurement
snapshot (run_real_inproc --snapshot-cadence): every N ticks the engine records EVERY active agent's
current_identity uniformly, regardless of whether it revised. The result is the uniform longitudinal
series the drift figures in the paper need (World.md §9). It also exercises the forced-end snapshot
(survivor-bias guard, §10.3).

DESIGN NOTES / HONESTY
----------------------
  * One seed, one model (Haiku), n=25, short horizon — DIRECTIONAL, not significant. The output is
    explicitly labelled preliminary; it is hypothesis-shaping scaffolding for the workshop demo, not a
    confirmatory result. Run multiple --seeds for a noise floor before claiming anything.
  * initialize_simulation WIPES the DB at every bootstrap, so (as in run_three_settings) each arm's
    drift artifact is written to disk BEFORE the next arm starts, while the data is still live.
  * The scarcity arm is held at mild/base_drain=2 across all thresholds so threshold is the only IV.

USAGE (token in env only, never on the CLI; Postgres up)
--------------------------------------------------------
    docker compose up -d
    AWS_BEARER_TOKEN_BEDROCK=... .venv/Scripts/python.exe scripts/exp_threshold_sweep.py \\
        --agents 25 --ticks 80 --seed 1 --snapshot-cadence 10 \\
        --model global.anthropic.claude-haiku-4-5-20251001-v1:0 --region us-east-1

    # quick free smoke of the harness wiring (no real spend) — uses a tiny horizon:
    AWS_BEARER_TOKEN_BEDROCK=... .venv/Scripts/python.exe scripts/exp_threshold_sweep.py \\
        --agents 6 --ticks 8 --thresholds 40 --snapshot-cadence 2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Running this file directly puts scripts/ on sys.path[0], not the project root, so the
# `scripts.*` imports below would fail. Put the project root on the path first.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mircoverse.config import settings
from mircoverse.persistence import db

import scripts.run_real_inproc as driver
from scripts.run_three_settings import _dump_drift

# Artifacts land in data/results/ (the experiment's own namespace, distinct from the pilot's
# data/runs/). _dump_drift writes its per-arm file into data/runs/; we additionally write the
# consolidated, trajectory-focused sweep file here.
_RESULTS_DIR = Path(__file__).resolve().parent.parent / "data" / "results"

# The scarcity arm is FIXED at "mild" (base_drain=2 — pressured but survivable) so reflection
# threshold is the only thing that varies across the sweep. These mirror run_three_settings' mild arm.
_FIXED_ARM = {
    "oasis_regen": 12, "oasis_cap": 50,
    "siphon_base": 37, "siphon_decay": 0.0, "siphon_floor": 0,
    "base_drain": 2,  # mild: survival is skill-gated → a pressured-but-alive cohort to observe
}

# Tables to wipe between arms, in FK-safe order (children before parents). initialize_simulation
# wipes inside ONE transaction, but back-to-back arms can hit a between-bootstrap race where the
# prior arm's in-flight memory writes re-populate agent_memory between the bootstrap's agent_memory
# and agents deletes, tripping agent_memory_agent_id_fkey. Doing an explicit, COMMITTED full wipe on
# a fresh connection (pool drained) before each arm guarantees a known-clean start regardless of what
# the previous arm left behind — the empirically-verified fix.
_WIPE_ORDER = [
    "agent_tick_results", "agent_known_locations", "action_log", "agent_memory",
    "identity_snapshots", "tick_scratch", "tick_state", "agents", "world_cells", "simulation_state",
]


async def _wipe_clean() -> None:
    """Explicitly clear all run tables on a fresh pooled connection, then close the pool so the next
    arm's driver opens a clean pool with no lingering in-flight transactions."""
    async with db.connection() as conn:
        for table in _WIPE_ORDER:
            await conn.execute(f"DELETE FROM {table}")
    await db.close_pool()


def _trajectories_from_artifact(artifact: dict) -> list[dict]:
    """Extract per-agent engine-measurement drift trajectories from a _dump_drift artifact.

    Each agent's `snapshots` list holds every identity_snapshots row (both engine_measurement and
    agent_revision). For the paper's drift-over-time figures we want the UNIFORM series, so we surface
    the engine_measurement trail explicitly (tick → number of moral_boundaries / core_values, plus the
    raw identity), alongside the sparse agent_revision ticks. Boundary/value COUNTS are a cheap,
    model-free proxy for "how much the stated self has moved" that a plotting script can chart directly;
    the semantic magnitude is left to the offline judge (World.md §9.1)."""
    out: list[dict] = []
    for a in artifact.get("agents", []):
        snaps = a.get("snapshots") or []
        series = []
        for s in snaps:
            ident = s.get("identity") or {}
            series.append({
                "tick": s.get("tick"),
                "trigger": s.get("trigger"),
                "drift_score": s.get("drift_score"),
                "n_boundaries": len(ident.get("moral_boundaries") or []),
                "n_values": len(ident.get("core_values") or []),
            })
        series.sort(key=lambda r: (r["tick"] if r["tick"] is not None else -1))
        n_orig_b = len((a.get("original_soul") or {}).get("moral_boundaries") or [])
        n_orig_v = len((a.get("original_soul") or {}).get("core_values") or [])
        revisions = [r for r in series if r["trigger"] == "agent_revision"]
        out.append({
            "name": a.get("name"),
            "status": a.get("status"),
            "identity_changed": a.get("identity_changed"),
            "n_boundaries_t0": n_orig_b,
            "n_values_t0": n_orig_v,
            "n_revisions": len(revisions),
            "first_revision_tick": revisions[0]["tick"] if revisions else None,
            "series": series,
        })
    return out


async def main_async(agents: int, ticks: int, model: str, region: str, seed: int,
                     thresholds: list[int], snapshot_cadence: int) -> None:
    if not await db.ping(settings.database_url):
        raise SystemExit("Postgres unreachable. Start it with `docker compose up -d` and retry.")
    await db.close_pool()  # the driver manages its own pool lifecycle per run

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    sweep = {
        "experiment": "reflection_threshold_sweep",
        "iv": "reflection_threshold",
        "fixed_arm": _FIXED_ARM,
        "seed": seed, "ticks": ticks, "agents": agents, "model": model,
        "snapshot_cadence": snapshot_cadence,
        "caveat": "1 seed, 1 model (Haiku), n=25, short horizon — DIRECTIONAL, not significant.",
        "arms": [],
    }

    for i, threshold in enumerate(sorted(set(thresholds)), 1):
        label = f"thresh{threshold}"
        print("\n" + "=" * 72)
        print(f"ARM {i}/{len(set(thresholds))}: reflection_threshold={threshold}  "
              f"(base_drain={_FIXED_ARM['base_drain']} fixed)  agents={agents} ticks={ticks} "
              f"seed={seed} cadence={snapshot_cadence}")
        print("=" * 72)
        try:
            # Guarantee a clean DB before this arm's bootstrap (between-arm race guard).
            await _wipe_clean()
            infra = await driver.run(
                agents, ticks, seed, model, region,
                reflection_threshold=threshold,
                snapshot_cadence=snapshot_cadence,
                **_FIXED_ARM,
            )
            # run() closed the pool; _dump_drift reopens lazily, reads the live DB, writes the
            # per-arm artifact (data/runs/thresh<N>_seed<seed>.json) before the next bootstrap wipes it.
            arm_bundle = {"label": label, "reflection_threshold": threshold,
                          "iv_label": "reflection_threshold", **_FIXED_ARM,
                          "seed": seed, "ticks": ticks}
            artifact = await _dump_drift(label, seed, ticks, arm=arm_bundle, infra=infra)
            sweep["arms"].append({
                "reflection_threshold": threshold,
                "survivors": artifact["survivors"],
                "n_agents": artifact["n_agents"],
                "agents_with_changed_identity": artifact["agents_with_changed_identity"],
                "total_snapshots": artifact["total_snapshots"],
                "engine_measurement_snapshots": infra.get("engine_measurement_snapshots"),
                "forced_end_snapshots": infra.get("forced_end_snapshots"),
                "infra_contaminated": artifact.get("infra_contaminated"),
                "trajectories": _trajectories_from_artifact(artifact),
            })
        except Exception as exc:
            print(f"\n  !! ARM {i} (threshold={threshold}) FAILED: {exc!r} — continuing.")
        finally:
            await db.close_pool()

    out = _RESULTS_DIR / f"threshold_sweep_seed{seed}.json"
    out.write_text(json.dumps(sweep, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + "=" * 72)
    print(f"SWEEP COMPLETE — consolidated results: {out}")
    print("=" * 72)
    print("  threshold  survivors  changed  total-snaps  engine-meas  forced-end  infra")
    for arm in sweep["arms"]:
        print(f"  {arm['reflection_threshold']:>9}  {arm['survivors']:>9}  "
              f"{arm['agents_with_changed_identity']:>7}  {arm['total_snapshots']:>11}  "
              f"{str(arm['engine_measurement_snapshots']):>11}  "
              f"{str(arm['forced_end_snapshots']):>10}  "
              f"{'CONTAM' if arm['infra_contaminated'] else 'ok'}")
    print(f"\n  per-arm drift artifacts: data/runs/thresh<N>_seed{seed}.json")
    print(f"  evaluate: .venv/Scripts/python.exe scripts/evaluate_runs.py data/runs/thresh*_seed{seed}.json")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Reflection-threshold sweep with engine-measured drift trajectories")
    ap.add_argument("--agents", type=int, default=25)
    ap.add_argument("--ticks", type=int, default=80)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--model", default="global.anthropic.claude-haiku-4-5-20251001-v1:0")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--thresholds", type=int, nargs="+", default=[40, 80, 150],
                    help="reflection-threshold values to sweep (the IV); default 40 80 150")
    ap.add_argument("--snapshot-cadence", type=int, default=10,
                    help="engine_measurement snapshot every N ticks (Protocol §2.6 default 10)")
    args = ap.parse_args()
    asyncio.run(main_async(args.agents, args.ticks, args.model, args.region, args.seed,
                           thresholds=args.thresholds, snapshot_cadence=args.snapshot_cadence))


if __name__ == "__main__":
    main()
