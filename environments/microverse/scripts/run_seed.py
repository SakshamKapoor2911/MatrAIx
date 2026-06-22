"""End-to-end seed-run smoke driver -- proves the engine runs, not just that tests pass.

In-process (no HTTP server needed): migrate the schema, bootstrap a generated world into the DB
(cells + registered agents + tick-0 observations), then for N ticks have each live agent submit a
random valid action (via the mock agent's pure ``build_envelope``) and resolve the tick through the
real orchestrator. Reports alive-count and a sample agent's trajectory each tick.

This is the bridge from "160 tests pass" to "I can run the simulation." It exercises the exact
production path: gen_seed_world -> initialize_simulation -> insert_action -> resolve_tick -> observe.

SCOPE: the 25-agent run IS the local science artifact (Protocol.md §1). The --scale flag is a
LOCAL CORRECTNESS SMOKE only -- it proves the pure engine + persistence stay correct and atomic at
volume. It is NOT the 1000-agent scale demonstration. The scale CLAIM (tick latency / throughput /
concurrency-correctness at 1000+) is an AWS load-test artifact run against the deployed Step
Functions + Aurora + RDS Proxy platform with the mock-agent fleet (Architecture.md Scale
Demonstration). Never present a local --scale run as proof of distributed scale.

Usage:
    docker compose up -d                       # Postgres must be running
    .venv/Scripts/python.exe scripts/run_seed.py --ticks 15 --agents 25 --seed 1
    .venv/Scripts/python.exe scripts/run_seed.py --scale 1000 --ticks 3   # LOCAL correctness smoke ONLY
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import uuid

from mircoverse.config import settings
from mircoverse.manifest import gen_scale_world, gen_seed_world
from mircoverse.persistence import dal, db
from mircoverse.resolution import initialize_simulation, resolve_tick
from mircoverse.agents.mock_agent import build_envelope
from mircoverse.contracts import Observation


async def _submit_actions_for_tick(conn, tick: int, seed: int) -> int:
    """Each agent with a precomputed observation this tick submits one random valid action.

    Reads each agent's serving row (the same packet GET /observe returns), builds a contract-valid
    envelope via the mock agent, and inserts it (ON CONFLICT DO NOTHING = one-per-tick). Returns
    the number of actions submitted."""
    rows = await conn.fetch(
        "SELECT agent_id, world_fov FROM agent_tick_results WHERE tick_number = $1", tick
    )
    submitted = 0
    for r in rows:
        aid = str(r["agent_id"])
        packet = r["world_fov"]
        if isinstance(packet, str):
            packet = json.loads(packet)
        obs = Observation.model_validate(packet)
        # One deterministic RNG per (agent, tick) -- no global random, no time seed.
        rng = random.Random(f"{seed}:{aid}:{tick}".__hash__() & 0xFFFFFFFF)
        env = build_envelope(obs, rng)
        action = env.action
        params = action.params.model_dump(mode="json") if action.params is not None else {}
        n = await dal.insert_action(
            agent_id=aid,
            tick_number=tick,
            action_type=action.type.value,
            params=params,
            status="accepted",
        )
        submitted += n
    return submitted


async def run(ticks: int, agents: int, scale: int, seed: int) -> None:
    if not await db.ping(settings.database_url):
        raise SystemExit(
            "Postgres unreachable. Start it with `docker compose up -d` and retry."
        )

    print("migrating schema ...")
    await dal.migrate()

    world = (
        gen_seed_world(seed=seed) if scale == 25 and agents == 25
        else gen_scale_world(n=(scale if scale != 25 else agents), seed=seed)
    )
    pop = len(world.agents)
    print(f"generated world: {world.width}x{world.height}, {pop} agents, seed={seed}")

    async with db.connection() as conn:
        roster = await initialize_simulation(
            conn, world, tick_interval_seconds=settings.tick_interval_seconds
        )
    print(f"bootstrapped {len(roster)} agents into the DB; tick 0 open")
    sample = roster[0]
    print(f"  sample agent {sample.world_id} {sample.agent_id[:8]}... at {sample.pos}")

    for tick in range(ticks):
        async with db.connection() as conn:
            n = await _submit_actions_for_tick(conn, tick, seed)
            rng = random.Random(seed + tick)
            results = await resolve_tick(
                conn, tick, rng, tick_interval_seconds=settings.tick_interval_seconds
            )
            alive = await conn.fetchval("SELECT COUNT(*) FROM agents WHERE status = 'active'")
            srow = await conn.fetchrow(
                "SELECT position_x, position_y, resources FROM agents WHERE agent_id = $1",
                uuid.UUID(sample.agent_id),
            )
        res = srow["resources"]
        if isinstance(res, str):
            res = json.loads(res)
        oks = sum(1 for r in results.values() if r.status == "ok")
        print(
            f"  tick {tick:>3}: submitted={n:>3} resolved={len(results):>3} ok={oks:>3} "
            f"alive={alive:>3}  sample@({srow['position_x']},{srow['position_y']}) "
            f"water={res.get('water')} food={res.get('food')}"
        )

    print(f"done. {ticks} ticks resolved end-to-end against real Postgres.")
    await db.close_pool()


def main() -> None:
    ap = argparse.ArgumentParser(description="MircoVerse end-to-end seed-run smoke driver")
    ap.add_argument("--ticks", type=int, default=15)
    ap.add_argument("--agents", type=int, default=25)
    ap.add_argument("--scale", type=int, default=25, help="25 = seed world; >25 = scale world size")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    asyncio.run(run(args.ticks, args.agents, args.scale, args.seed))


if __name__ == "__main__":
    main()
