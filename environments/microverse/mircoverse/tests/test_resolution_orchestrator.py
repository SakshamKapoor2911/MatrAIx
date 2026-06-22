"""Tests for the tick-resolution orchestration layer (mircoverse.resolution).

Two registers, matching the repo convention:
- PURE tests (no DB) cover the translation helpers: action-row → envelope, cell-meta pack/unpack,
  changed-cell detection, and observation assembly over an in-memory WorldState.
- DB-backed tests are marked `requires_db` and SKIP (never fail) when Postgres is down. They
  exercise load_world_state and the full end-to-end resolve_tick, including a scripted 3-agent
  synthetic tick that must resolve DETERMINISTICALLY and write correct next-tick observations.
"""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from mircoverse.config import settings
from mircoverse.contracts import Action, ActionType, SoulFile
from mircoverse.persistence import dal, db
from mircoverse.resolution import build_observation, load_world_state, resolve_tick
from mircoverse.resolution import orchestrator as orch
from mircoverse.tests.conftest import requires_db
from mircoverse.world import Agent, Cell, DeathCache, PendingMessage, WorldState
from mircoverse.world.resolver import ActionResult


def _live_dsn() -> str:
    for dsn in (settings.test_database_url, settings.database_url):
        try:
            if asyncio.run(db.ping(dsn)):
                return dsn
        except Exception:  # pragma: no cover - defensive
            continue
    return settings.database_url


DSN = _live_dsn()


# ── pure helpers (no DB) ─────────────────────────────────────────────────────────────


def test_envelope_from_row():
    """A valid action_log row rebuilds into the frozen ActionEnvelope."""
    row = {"agent_id": "a", "tick_number": 7, "action_type": "move",
           "params": json.dumps({"direction": "N"})}
    env = orch._envelope_from_row(row)
    assert env is not None
    assert env.tick == 7
    assert env.action.type == ActionType.MOVE


def test_envelope_from_row_invalid_returns_none():
    """An unparseable/invalid persisted action returns None (caller defaults it to wait)."""
    bad = {"agent_id": "a", "tick_number": 1, "action_type": "teleport", "params": {}}
    assert orch._envelope_from_row(bad) is None


def test_encode_decode_cell_meta_roundtrip():
    """Death-cache + siphon-units pack into known_name and decode back identically."""
    cell = Cell(x=3, y=4, terrain="ruins", siphon_units=12,
                death_cache=DeathCache(water=9, food=3, goods=1, location_facts=[(1, 2), (5, 6)]))
    encoded = orch._encode_cell_meta(cell)
    cache, units = orch._decode_cell_meta(encoded)
    assert units == 12
    assert cache is not None
    assert cache.water == 9 and cache.food == 3 and cache.goods == 1
    assert cache.location_facts == [(1, 2), (5, 6)]


def test_decode_cell_meta_plain_name_is_empty():
    """A non-JSON known_name (a human name) decodes to no cache and zero siphon units."""
    cache, units = orch._decode_cell_meta("Old Well")
    assert cache is None and units == 0


def test_encode_cell_meta_fits_known_name_column_with_many_facts():
    """A cache that accumulated MANY location_facts (multiple deaths on one ruins cell) must still
    encode to <= 100 chars — the world_cells.known_name width. A cache with 4+ raw facts used to
    overflow VARCHAR(100) and crash the cell upsert (StringDataRightTruncationError; killed the
    survival seed-run dump 2026-06-05). The encoder now caps stored facts at 3."""
    cell = Cell(x=9, y=9, terrain="ruins", siphon_units=2,
                death_cache=DeathCache(water=48, food=12, goods=40,
                                       location_facts=[(i, i + 1) for i in range(10)]))
    encoded = orch._encode_cell_meta(cell)
    assert encoded is not None
    assert len(encoded) <= 100, f"known_name blob is {len(encoded)} chars, overflows VARCHAR(100)"
    # And it still round-trips (the first 3 facts are retained — the engine surfaces at most 3).
    cache, units = orch._decode_cell_meta(encoded)
    assert units == 2
    assert cache is not None
    assert cache.water == 48 and cache.food == 12 and cache.goods == 40
    assert cache.location_facts == [(0, 1), (1, 2), (2, 3)]


def test_cell_changed_detects_resource_delta():
    """_cell_changed is True when water changes and False when nothing changed."""
    before = Cell(x=0, y=0, terrain="oasis", water=10)
    same = Cell(x=0, y=0, terrain="oasis", water=10)
    moved = Cell(x=0, y=0, terrain="oasis", water=3)
    assert orch._cell_changed(before, same) is False
    assert orch._cell_changed(before, moved) is True
    assert orch._cell_changed(None, same) is True  # newly seen cell


def test_build_observation_assembles_packet():
    """build_observation produces the §5.2 packet with self/fov/global/inbox/last_action_result."""
    world = WorldState(
        tick=5,
        width=50,
        height=50,
        cells={(10, 10): Cell(x=10, y=10, terrain="settlement", water=37, siphon=True,
                              siphon_units=37),
               (11, 10): Cell(x=11, y=10, terrain="desert")},
        agents={
            "a1": Agent(agent_id="a1", pos=(10, 10), water=30, food=5, goods=2, stance="neutral",
                        intention="Stock water, then trade with a2."),
            "a2": Agent(agent_id="a2", pos=(11, 10), water=12, stance="aggressive"),
        },
        inbox={"a1": [PendingMessage(from_agent="a2", to_agent="a1", tick=4,
                                     message="hello", location_claim=(12, 40))]},
    )
    obs = build_observation(
        world, "a1", next_tick=6, tick_ends_at="2026-06-01T00:00:30Z",
        memory_index=[], last_action_result=ActionResult("a1", "move", "ok", "moved to (10,10)"),
        siphon_units=37,
    )
    assert obs.tick == 6
    assert obs.self.agent_id == "a1"
    assert obs.self.on_terrain == "settlement"
    assert obs.global_.alive_count == 2
    assert obs.global_.siphon_units_this_tick == 37
    # a2 is within Chebyshev radius 2, so it appears in the FOV agents.
    assert any(fa.agent_id == "a2" for fa in obs.fov.agents)
    # The inbox message delivered last tick is present and carries the location claim.
    assert obs.inbox[0].from_agent == "a2"
    assert obs.inbox[0].location_claim == (12, 40)
    assert obs.last_action_result is not None
    assert obs.last_action_result.tick == 5
    # The carried-forward intention (Protocol §4.2 / §5.2) is surfaced in self.
    assert obs.self.intention == "Stock water, then trade with a2."


def test_envelope_from_row_carries_intention():
    """A persisted action_log row's intention rebuilds onto the frozen envelope."""
    row = {"agent_id": "a", "tick_number": 3, "action_type": "wait",
           "params": json.dumps({}), "intention": "Wait out the storm here."}
    env = orch._envelope_from_row(row)
    assert env is not None
    assert env.intention == "Wait out the storm here."


# ── DB-backed (skip when Postgres down) ───────────────────────────────────────────────


def _soul() -> SoulFile:
    return SoulFile(core_values=["survive"], moral_boundaries=["I will not steal"],
                    personality="test", goals=["live"])


async def _seed_world(dsn: str, *, prefix: str, agents: list[dict]) -> dict[str, str]:
    """Register a fresh isolated set of agents + their spawn cells. Returns name→agent_id.

    Each agent dict: {name, pos, water, food?, goods?, stance?, status?}. Cells are written for
    every distinct position plus a settlement siphon at (25,25). Returns mapping of the caller's
    logical name to the generated UUID so scripted actions can reference targets.
    """
    await dal.migrate(dsn)
    # Isolate each scripted scenario: load_world_state reads the WHOLE agents/world tables, so
    # leftover rows from earlier tests would pollute alive_count, cell occupancy, and death-caches.
    # Clear the world tables so every scripted tick resolves against a clean grid (deterministic).
    async with db.connection(dsn) as conn:
        await conn.execute(
            "TRUNCATE agents, world_cells, agent_known_locations, action_log, "
            "agent_tick_results, tick_scratch, tick_state, agent_memory, "
            "identity_snapshots RESTART IDENTITY CASCADE"
        )
    name_to_id: dict[str, str] = {}
    positions: set[tuple[int, int]] = {(25, 25)}
    for spec in agents:
        resources = {
            "water": spec["water"],
            "food": spec.get("food", 10),
            "goods": spec.get("goods", 0),
            "stance": spec.get("stance", "neutral"),
        }
        aid = await dal.register_agent(
            soul=_soul(),
            display_name=f"{prefix}-{spec['name']}",
            api_key_hash="h_" + uuid.uuid4().hex,
            position=tuple(spec["pos"]),
            resources=resources,
            # A spec MAY pin a fixed agent_id so a scenario can be replayed with IDENTICAL agent
            # identities — contention is hashed over agent_id, so stable IDs are required to assert
            # seed-determinism across two runs.
            agent_id=spec.get("id"),
            status=spec.get("status", "active"),
            dsn=dsn,
        )
        name_to_id[spec["name"]] = aid
        positions.add(tuple(spec["pos"]))
    for (x, y) in positions:
        terrain = "settlement" if (x, y) == (25, 25) else "desert"
        await dal.upsert_cell(x=x, y=y, terrain=terrain,
                              water=37 if terrain == "settlement" else 0,
                              food=0, goods=0, dsn=dsn)
    return name_to_id


async def _conn(dsn: str):
    return await db.connection(dsn).__aenter__()


@requires_db
def test_load_world_state_reads_agents_and_cells():
    """load_world_state materialises agents (alive=active), positions, resources, and cells."""
    async def go():
        prefix = "lws-" + uuid.uuid4().hex[:6]
        ids = await _seed_world(DSN, prefix=prefix, agents=[
            {"name": "alpha", "pos": (10, 10), "water": 40, "stance": "friendly"},
        ])
        async with db.connection(DSN) as conn:
            world = await load_world_state(conn, tick_n=0)
        a = world.agents[ids["alpha"]]
        assert a.pos == (10, 10)
        assert a.water == 40
        assert a.stance == "friendly"
        assert a.alive is True
        assert (10, 10) in world.cells
        assert world.cells[(25, 25)].siphon is True
    asyncio.run(go())


@requires_db
def test_resolve_tick_consume_persists_and_opens_next_tick():
    """A scripted consume resolves, the agent's water rises, and tick N+1 opens with an obs row."""
    async def go():
        prefix = "rtc-" + uuid.uuid4().hex[:6]
        ids = await _seed_world(DSN, prefix=prefix, agents=[
            {"name": "drinker", "pos": (25, 25), "water": 20},
        ])
        drinker = ids["drinker"]
        tick = 100000 + int(uuid.uuid4().int % 100000)
        await dal.insert_action(
            agent_id=drinker, tick_number=tick, action_type="consume",
            params={"resource": "water", "amount": 10}, dsn=DSN,
        )
        rng = random.Random(1234)
        async with db.connection(DSN) as conn:
            results = await resolve_tick(conn, tick, rng)
        assert results[drinker].status == "ok"
        # Drank 10 from the settlement cell (0 terrain water cost, base_drain=1) → 20+10-1=29.
        row = await dal.get_agent(drinker, dsn=DSN)
        assert row["resources"]["water"] == 29
        # tick N+1 is open with the live agent counted, and a precomputed observation exists.
        state = await dal.get_tick_state(tick + 1, dsn=DSN)
        assert state["window_open"] is True
        assert state["active_agent_count"] == 1
        async with db.connection(DSN) as conn:
            fov = await conn.fetchval(
                "SELECT world_fov FROM agent_tick_results WHERE agent_id=$1 AND tick_number=$2",
                uuid.UUID(drinker), tick + 1,
            )
        obs = json.loads(fov) if isinstance(fov, str) else fov
        assert obs["tick"] == tick + 1
        assert obs["self"]["water"] == 29
    asyncio.run(go())


@requires_db
def test_intention_is_set_carried_forward_and_overwritten():
    """The stated `intention` (Protocol §4.2 / §7.4) is persisted, surfaced in the next-tick
    observation, CARRIED FORWARD when omitted, and OVERWRITTEN when a new one is set."""
    async def go():
        prefix = "intent-" + uuid.uuid4().hex[:6]
        ids = await _seed_world(DSN, prefix=prefix, agents=[
            {"name": "planner", "pos": (25, 25), "water": 40},
        ])
        planner = ids["planner"]
        base = 200000 + int(uuid.uuid4().int % 100000)

        async def read_intention(at_tick: int):
            async with db.connection(DSN) as conn:
                fov = await conn.fetchval(
                    "SELECT world_fov FROM agent_tick_results WHERE agent_id=$1 AND tick_number=$2",
                    uuid.UUID(planner), at_tick,
                )
            obs = json.loads(fov) if isinstance(fov, str) else fov
            return obs["self"]["intention"]

        # Tick 1: set an intention.
        await dal.insert_action(
            agent_id=planner, tick_number=base, action_type="wait", params={},
            intention="Camp the Siphon until my water is topped off.", dsn=DSN,
        )
        async with db.connection(DSN) as conn:
            await resolve_tick(conn, base, random.Random(1))
        # The action_log row recorded the stated intention (the §9.5 research channel).
        async with db.connection(DSN) as conn:
            logged = await conn.fetchval(
                "SELECT intention FROM action_log WHERE agent_id=$1 AND tick_number=$2",
                uuid.UUID(planner), base,
            )
        assert logged == "Camp the Siphon until my water is topped off."
        assert await read_intention(base + 1) == "Camp the Siphon until my water is topped off."

        # Tick 2: omit intention → it must CARRY FORWARD unchanged.
        await dal.insert_action(
            agent_id=planner, tick_number=base + 1, action_type="wait", params={}, dsn=DSN,
        )
        async with db.connection(DSN) as conn:
            await resolve_tick(conn, base + 1, random.Random(2))
        assert await read_intention(base + 2) == "Camp the Siphon until my water is topped off."

        # Tick 3: set a new intention → it must OVERWRITE.
        await dal.insert_action(
            agent_id=planner, tick_number=base + 2, action_type="wait", params={},
            intention="Leave for the eastern ruins to find goods.", dsn=DSN,
        )
        async with db.connection(DSN) as conn:
            await resolve_tick(conn, base + 2, random.Random(3))
        assert await read_intention(base + 3) == "Leave for the eastern ruins to find goods."
    asyncio.run(go())


@requires_db
def test_full_synthetic_tick_resolves_deterministically():
    """A scripted 3-agent tick resolves identically across two independent runs (same DB seed
    world + same actions + same RNG seed ⇒ identical agent state and observations).

    Scenario: two agents both try to MOVE into the same cell (25,25) (deterministic contention),
    a third CONSUMEs water on its own cell. We resolve the same scenario twice in two isolated
    worlds with the same RNG seed and assert the resolved water/positions match exactly.

    Contention is hashed over agent_id, so the two runs must use IDENTICAL agent_ids for the
    determinism claim to hold — we pin fixed UUIDs (the engine, given the same world + actions +
    seed, is deterministic; random per-run IDs would change the hashed contention winner)."""
    fixed_ids = {
        "mover_a": "11111111-1111-1111-1111-111111111111",
        "mover_b": "22222222-2222-2222-2222-222222222222",
        "drinker": "33333333-3333-3333-3333-333333333333",
    }

    # The tick number seeds movement contention (winner = hash(tick_seed + agent_id)), so it MUST
    # be identical across the two runs for the determinism claim to hold — fix it once here.
    fixed_tick = 200000 + int(uuid.uuid4().int % 100000)

    async def run_once() -> dict:
        prefix = "det-" + uuid.uuid4().hex[:6]
        ids = await _seed_world(DSN, prefix=prefix, agents=[
            {"name": "mover_a", "pos": (24, 25), "water": 30, "id": fixed_ids["mover_a"]},
            {"name": "mover_b", "pos": (26, 25), "water": 30, "id": fixed_ids["mover_b"]},
            {"name": "drinker", "pos": (10, 10), "water": 15, "id": fixed_ids["drinker"]},
        ])
        # Both movers know (25,25) so goal-move is valid; seed cells (24,25),(26,25) already exist.
        for nm in ("mover_a", "mover_b"):
            await dal.upsert_cell(x=25, y=25, terrain="settlement", water=37, food=0, goods=0, dsn=DSN)
            async with db.connection(DSN) as conn:
                await conn.execute(
                    """INSERT INTO agent_known_locations (agent_id,x,y,location_type,discovered_tick)
                       VALUES ($1,25,25,'settlement',0) ON CONFLICT DO NOTHING""",
                    uuid.UUID(ids[nm]),
                )
        # also give the drinker's cell some water to drink
        await dal.upsert_cell(x=10, y=10, terrain="oasis", water=20, food=0, goods=0, dsn=DSN)
        tick = fixed_tick
        await dal.insert_action(agent_id=ids["mover_a"], tick_number=tick, action_type="move",
                                params={"toward": [25, 25]}, dsn=DSN)
        await dal.insert_action(agent_id=ids["mover_b"], tick_number=tick, action_type="move",
                                params={"toward": [25, 25]}, dsn=DSN)
        await dal.insert_action(agent_id=ids["drinker"], tick_number=tick, action_type="consume",
                                params={"resource": "water", "amount": 5}, dsn=DSN)
        rng = random.Random(999)
        async with db.connection(DSN) as conn:
            await resolve_tick(conn, tick, rng)
        out = {}
        for nm, aid in ids.items():
            row = await dal.get_agent(aid, dsn=DSN)
            out[nm] = {"pos": (row["position_x"], row["position_y"]),
                       "water": row["resources"]["water"],
                       "status": row["status"]}
        return out

    async def go():
        first = await run_once()
        second = await run_once()
        # Determinism: two independent worlds, same actions + same RNG seed → identical results.
        assert first == second
        # Exactly one mover won the contested cell (25,25); the other stayed put.
        winners = [nm for nm in ("mover_a", "mover_b") if first[nm]["pos"] == (25, 25)]
        assert len(winners) == 1
        # The drinker drank 5 on an oasis (0 terrain water cost, base_drain=1): 15+5-1 = 19.
        assert first["drinker"]["water"] == 19
    asyncio.run(go())


@requires_db
def test_talk_latency_delivers_next_tick():
    """A talk in tick N is parked and delivered in tick N+1's observation inbox (Protocol §4.4)."""
    async def go():
        prefix = "talk-" + uuid.uuid4().hex[:6]
        ids = await _seed_world(DSN, prefix=prefix, agents=[
            {"name": "speaker", "pos": (30, 30), "water": 30},
            {"name": "listener", "pos": (31, 30), "water": 30},
        ])
        await dal.upsert_cell(x=31, y=30, terrain="desert", water=0, food=0, goods=0, dsn=DSN)
        tick = 300000 + int(uuid.uuid4().int % 100000)
        await dal.insert_action(
            agent_id=ids["speaker"], tick_number=tick, action_type="talk",
            params={"target": ids["listener"], "message": "water at (12,40)",
                    "location_claim": [12, 40]}, dsn=DSN,
        )
        rng = random.Random(7)
        async with db.connection(DSN) as conn:
            results = await resolve_tick(conn, tick, rng)
        assert results[ids["speaker"]].status == "ok"
        # Next tick the listener's observation inbox carries the message + claim.
        async with db.connection(DSN) as conn:
            fov = await conn.fetchval(
                "SELECT world_fov FROM agent_tick_results WHERE agent_id=$1 AND tick_number=$2",
                uuid.UUID(ids["listener"]), tick + 1,
            )
        obs = json.loads(fov) if isinstance(fov, str) else fov
        assert len(obs["inbox"]) == 1
        assert obs["inbox"][0]["from"] == ids["speaker"]
        assert obs["inbox"][0]["location_claim"] == [12, 40]
        # And the listener learned the claimed location (known_locations persisted).
        async with db.connection(DSN) as conn:
            known = await conn.fetchval(
                "SELECT COUNT(*) FROM agent_known_locations WHERE agent_id=$1 AND x=12 AND y=40",
                uuid.UUID(ids["listener"]),
            )
        assert known == 1
    asyncio.run(go())


@requires_db
def test_death_writes_cache_and_marks_dead():
    """An agent that drains to water<=0 dies, its cell becomes ruins + a death-cache, and it is
    excluded from the next tick's active_agent_count (World.md §5, Protocol.md §2.4)."""
    async def go():
        prefix = "death-" + uuid.uuid4().hex[:6]
        ids = await _seed_world(DSN, prefix=prefix, agents=[
            {"name": "doomed", "pos": (40, 40), "water": 1, "food": 5, "goods": 2},
            {"name": "survivor", "pos": (10, 10), "water": 50},
        ])
        await dal.upsert_cell(x=40, y=40, terrain="desert", water=0, food=0, goods=0, dsn=DSN)
        tick = 400000 + int(uuid.uuid4().int % 100000)
        # doomed waits on desert: base_drain 1 + desert water cost 2 = 3 → 1-3 = -2 ⇒ dies.
        await dal.insert_action(agent_id=ids["doomed"], tick_number=tick, action_type="wait",
                                params={}, dsn=DSN)
        rng = random.Random(5)
        async with db.connection(DSN) as conn:
            await resolve_tick(conn, tick, rng)
        doomed = await dal.get_agent(ids["doomed"], dsn=DSN)
        assert doomed["status"] == "dead"
        cell = await dal.get_cell(40, 40, dsn=DSN)
        assert cell["terrain"] == "ruins"
        meta = json.loads(cell["known_name"])
        # Costs are debited before the death pass: on desert the agent loses 1 food this tick
        # (TERRAIN_FOOD_COST['desert'] == 1), so 5 - 1 = 4 carried food enters the cache.
        assert meta["cache"]["food"] == 4
        # Only the survivor remains active for tick N+1.
        state = await dal.get_tick_state(tick + 1, dsn=DSN)
        assert state["active_agent_count"] == 1
    asyncio.run(go())
