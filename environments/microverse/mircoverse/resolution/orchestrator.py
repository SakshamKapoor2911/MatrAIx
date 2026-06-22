"""Local tick-resolution orchestration over an asyncpg connection.

All functions take a live ``asyncpg.Connection`` (``conn``) — the orchestrator owns its own SQL
so it can run the whole tick inside ONE transaction without depending on the frozen DAL's
per-call connection helpers. Reads of the world and writes of the resolved state therefore commit
or roll back atomically (Architecture.md Step 7a's "small atomic transaction" intent, collapsed to
the local single-process engine).

The PURE world core does all physics; this module only translates persisted rows ⇄ the world-core
dataclasses ⇄ the frozen wire contracts, and persists the result. It never makes a stochastic
choice — determinism lives entirely in the pure core + the seeded RNG passed through.
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import asyncpg

from mircoverse.contracts import (
    Action,
    ActionEnvelope,
    ActionType,
    Fov,
    GlobalView,
    InboxMessage,
    LastActionResult,
    MemoryIndexEntry,
    Observation,
    SelfView,
)
from mircoverse.world import (
    Agent,
    Cell,
    DeathCache,
    PendingMessage,
    WorldState,
    apply_environment,
    compute_fov,
)
from mircoverse.world import resolve_tick as pure_resolve_tick
from mircoverse.world.resolver import ActionResult

# Scratch key under which a tick's outbound messages are parked for delivery NEXT tick
# (the world core's inbox/outbound is in-memory; persistence rides on tick_scratch).
_INBOX_SCRATCH_KEY = "inbox"

# Seed-run world geometry (Protocol.md §2.1). Used only to size the WorldState when the DB has
# no explicit width/height row; cells themselves come from world_cells.
_DEFAULT_WIDTH = 50
_DEFAULT_HEIGHT = 50
_SIPHON_POS = (25, 25)


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _jsonb(value: Any) -> str:
    return json.dumps(value)


def _decode_json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


# ── action-row → frozen wire envelope ───────────────────────────────────────────────


def _envelope_from_row(row: dict[str, Any]) -> Optional[ActionEnvelope]:
    """Rebuild the frozen ``ActionEnvelope`` from a persisted action_log row.

    Returns ``None`` for an unparseable/invalid action so the caller defaults it to ``wait``
    (the engine never trusts a malformed persisted action over physics — Protocol.md §5.3).
    Carries ``intention`` through (Protocol §4.2 / §7.4) so the resolver can stamp it on the
    agent and carry it forward.
    """
    params = _decode_json(row.get("params")) or {}
    try:
        action = Action(type=ActionType(row["action_type"]), params=params)
        return ActionEnvelope(
            tick=int(row["tick_number"]), action=action, intention=row.get("intention")
        )
    except Exception:
        return None


async def _read_actions(conn: asyncpg.Connection, tick_n: int) -> dict[str, ActionEnvelope]:
    """Accepted actions for tick N, keyed by agent_id (deterministic order by agent_id)."""
    rows = await conn.fetch(
        """
        SELECT agent_id, tick_number, action_type, params, intention
        FROM action_log
        WHERE tick_number = $1 AND status = 'accepted'
        ORDER BY agent_id
        """,
        tick_n,
    )
    out: dict[str, ActionEnvelope] = {}
    for r in rows:
        aid = str(r["agent_id"])
        env = _envelope_from_row(dict(r))
        if env is not None:
            out[aid] = env
    return out


# ── DB → WorldState ───────────────────────────────────────────────────────────────────


async def _read_inbox(
    conn: asyncpg.Connection, tick_n: int
) -> dict[str, list[PendingMessage]]:
    """The inbox delivered to agents THIS tick = messages tick N-1's resolution parked under
    ``tick_scratch[(N, "inbox")]`` (conversation latency, Protocol.md §4.4)."""
    raw = await conn.fetchval(
        "SELECT value FROM tick_scratch WHERE tick_number = $1 AND key = $2",
        tick_n,
        _INBOX_SCRATCH_KEY,
    )
    data = _decode_json(raw)
    if not data:
        return {}
    inbox: dict[str, list[PendingMessage]] = {}
    for aid, msgs in data.items():
        inbox[aid] = [
            PendingMessage(
                from_agent=m["from_agent"],
                to_agent=m.get("to_agent"),
                tick=m["tick"],
                message=m["message"],
                location_claim=tuple(m["location_claim"]) if m.get("location_claim") else None,
                broadcast=m.get("broadcast", False),
                sender_pos=tuple(m.get("sender_pos", (0, 0))),
            )
            for m in msgs
        ]
    return inbox


async def load_world_state(conn: asyncpg.Connection, tick_n: int,
                            base_drain: int = 1) -> WorldState:
    """Materialise the pure ``WorldState`` for tick N from persisted rows.

    Agents: every row (alive = status == 'active'); resources from the ``resources`` JSONB,
    ``stance`` rides inside that blob (the schema has no stance column, so it is carried in the
    resources JSON which round-trips). Known locations from ``agent_known_locations``. Cells from
    ``world_cells`` (a death-cache, if any, is carried in ``known_name`` as a JSON tag prefixed
    ``cache:`` so the frozen schema needs no new column).
    """
    cell_rows = await conn.fetch("SELECT * FROM world_cells")
    cells: dict[tuple[int, int], Cell] = {}
    max_x = _DEFAULT_WIDTH - 1
    max_y = _DEFAULT_HEIGHT - 1
    for r in cell_rows:
        x, y = r["x"], r["y"]
        max_x = max(max_x, x)
        max_y = max(max_y, y)
        siphon = (x, y) == _SIPHON_POS or r["terrain"] == "settlement"
        death_cache, siphon_units = _decode_cell_meta(r["known_name"])
        cells[(x, y)] = Cell(
            x=x,
            y=y,
            terrain=r["terrain"],
            water=r["water"] or 0,
            food=r["food"] or 0,
            goods=r["goods"] or 0,
            siphon=siphon,
            siphon_units=siphon_units,
            death_cache=death_cache,
        )

    known_rows = await conn.fetch(
        "SELECT agent_id, x, y FROM agent_known_locations"
    )
    known_by_agent: dict[str, set[tuple[int, int]]] = {}
    for r in known_rows:
        known_by_agent.setdefault(str(r["agent_id"]), set()).add((r["x"], r["y"]))

    agent_rows = await conn.fetch("SELECT * FROM agents")
    agents: dict[str, Agent] = {}
    for r in agent_rows:
        aid = str(r["agent_id"])
        res = _decode_json(r["resources"]) or {}
        pos = (r["position_x"] or 0, r["position_y"] or 0)
        agents[aid] = Agent(
            agent_id=aid,
            pos=pos,
            water=int(res.get("water", 0)),
            food=int(res.get("food", 0)),
            goods=int(res.get("goods", 0)),
            stance=res.get("stance", "neutral"),
            alive=(r["status"] == "active"),
            death_tick=res.get("death_tick"),
            known_locations=known_by_agent.get(aid, set()) | {pos},
            # Persisted (like stance) in the resources JSONB so it survives across ticks/process
            # restarts; carried forward each tick until the agent overwrites it (§4.2 / §7.4).
            intention=res.get("intention"),
        )

    inbox = await _read_inbox(conn, tick_n)
    return WorldState(
        tick=tick_n,
        width=max_x + 1,
        height=max_y + 1,
        cells=cells,
        agents=agents,
        # base_drain is the per-tick water cost of merely existing — the SCARCITY lever (2026-06-06).
        # It is NOT persisted in any table (the frozen schema has no column), so the per-tick reload
        # MUST receive it from the caller, or it silently resets to 1 and the manipulation is ignored
        # (the same class of bug as the tick-0 siphon coupling). resolve_tick threads the arm's value.
        base_drain=base_drain,
        inbox=inbox,
    )


def _decode_cell_meta(known_name: Optional[str]) -> tuple[Optional[DeathCache], int]:
    """Decode the death-cache + siphon-units packed into ``world_cells.known_name``.

    The frozen schema has no death_cache/siphon_units columns, so the orchestrator packs them as
    a small JSON object in ``known_name`` (``{"cache": {...}, "siphon_units": N}``). A plain
    human name (or NULL) decodes to "no cache, no siphon units". This keeps the shared schema
    untouched while round-tripping the engine's per-cell physics state.
    """
    if not known_name:
        return None, 0
    try:
        meta = json.loads(known_name)
    except (ValueError, TypeError):
        return None, 0
    if not isinstance(meta, dict):
        return None, 0
    su = int(meta.get("siphon_units", 0))
    c = meta.get("cache")
    if not c:
        return None, su
    return (
        DeathCache(
            water=int(c.get("water", 0)),
            food=int(c.get("food", 0)),
            goods=int(c.get("goods", 0)),
            location_facts=[tuple(p) for p in c.get("location_facts", [])],
        ),
        su,
    )


def _encode_cell_meta(cell: Cell) -> Optional[str]:
    """Pack a cell's death-cache + siphon-units into ``known_name`` JSON, or None when empty."""
    meta: dict[str, Any] = {}
    if cell.siphon_units:
        meta["siphon_units"] = cell.siphon_units
    if cell.death_cache is not None:
        dc = cell.death_cache
        # Cap stored location_facts so the packed JSON cannot overflow world_cells.known_name
        # (VARCHAR(100)). A cache ACCUMULATES facts across multiple deaths on one cell
        # (resolver.py ~632), so the per-death [:3] slice doesn't bound the total — 4+ facts push
        # the blob past 100 chars and the cell upsert raises StringDataRightTruncationError (this
        # killed the survival seed-run dump, 2026-06-05). The scavenge resolver only ever surfaces
        # up to 3 location hints from a looted cache anyway, so keeping 3 loses nothing observable.
        meta["cache"] = {
            "water": dc.water,
            "food": dc.food,
            "goods": dc.goods,
            "location_facts": [list(p) for p in dc.location_facts[:3]],
        }
    # Compact separators (no spaces) so the packed blob stays within VARCHAR(100): even capped at
    # 3 facts, the default ", "/": " spacing pushes a cache+siphon blob to ~112 chars; compact
    # encoding brings it to ~97. `_decode_cell_meta` uses json.loads, which reads this fine.
    return json.dumps(meta, separators=(",", ":")) if meta else None


# ── WorldState → DB (changed cells only, agents, results) ─────────────────────────────


def _cell_changed(before: Optional[Cell], after: Cell) -> bool:
    if before is None:
        return True
    return (
        before.terrain != after.terrain
        or before.water != after.water
        or before.food != after.food
        or before.goods != after.goods
        or before.siphon_units != after.siphon_units
        or (before.death_cache is None) != (after.death_cache is None)
        or _encode_cell_meta(before) != _encode_cell_meta(after)
    )


async def _persist_cells(
    conn: asyncpg.Connection, before: WorldState, after: WorldState
) -> int:
    """Upsert only the cells that changed this tick (Architecture.md Step 7a / World Repr:
    write ~50-200 rows, never the full grid). Returns the count written."""
    written = 0
    for pos, cell in after.cells.items():
        if not _cell_changed(before.cells.get(pos), cell):
            continue
        await conn.execute(
            """
            INSERT INTO world_cells (x, y, terrain, water, food, goods, passable, known_name)
            VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7)
            ON CONFLICT (x, y) DO UPDATE
            SET terrain = EXCLUDED.terrain,
                water = EXCLUDED.water,
                food = EXCLUDED.food,
                goods = EXCLUDED.goods,
                passable = EXCLUDED.passable,
                known_name = EXCLUDED.known_name
            """,
            cell.x,
            cell.y,
            cell.terrain,
            cell.water,
            cell.food,
            cell.goods,
            _encode_cell_meta(cell),
        )
        written += 1
    return written


async def _persist_agents(conn: asyncpg.Connection, after: WorldState) -> None:
    """Write each agent's position / resources / status. ``stance`` and ``death_tick`` ride in
    the resources JSONB (no dedicated columns in the frozen schema). ``original_soul`` is never
    touched here, so the protect_original_soul trigger never fires."""
    for aid, agent in after.agents.items():
        resources = {
            "water": agent.water,
            "food": agent.food,
            "goods": agent.goods,
            "stance": agent.stance,
        }
        if agent.death_tick is not None:
            resources["death_tick"] = agent.death_tick
        if agent.intention is not None:
            resources["intention"] = agent.intention
        await conn.execute(
            """
            UPDATE agents
            SET position_x = $2, position_y = $3, resources = $4::jsonb, status = $5
            WHERE agent_id = $1
            """,
            uuid.UUID(aid),
            agent.pos[0],
            agent.pos[1],
            _jsonb(resources),
            "active" if agent.alive else "dead",
        )


async def _persist_known_locations(
    conn: asyncpg.Connection, before: WorldState, after: WorldState, tick_n: int
) -> None:
    """Persist newly-learned cells (visited or told via talk) into agent_known_locations.

    Only INSERTs the delta (ON CONFLICT DO NOTHING) so existing discovery ticks are preserved."""
    for aid, agent in after.agents.items():
        prev = before.agents.get(aid)
        prev_known = prev.known_locations if prev else set()
        for pos in agent.known_locations - prev_known:
            await conn.execute(
                """
                INSERT INTO agent_known_locations (agent_id, x, y, location_type, discovered_tick)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (agent_id, x, y) DO NOTHING
                """,
                uuid.UUID(aid),
                pos[0],
                pos[1],
                after.cells[pos].terrain if pos in after.cells else "unknown",
                tick_n,
            )


async def _persist_results(
    conn: asyncpg.Connection,
    tick_n: int,
    results: dict[str, ActionResult],
) -> None:
    """Step 7b audit write: fill action_log.result + resolved_at for every resolved agent.

    Agents whose action was defaulted to ``wait`` (no submitted row) get a freshly-inserted
    log row so the objective record is complete and replayable (Architecture.md: missing
    submission → defaulted wait)."""
    for aid, res in results.items():
        result_json = {
            "tick": tick_n,
            "action": res.action,
            "status": res.status,
            "note": res.note,
            "detail": res.detail,
        }
        tag = await conn.execute(
            """
            UPDATE action_log
            SET result = $3::jsonb, resolved_at = $4
            WHERE agent_id = $1 AND tick_number = $2
            """,
            uuid.UUID(aid),
            tick_n,
            _jsonb(result_json),
            _now_naive(),
        )
        if tag.split()[-1] == "0":
            # No submitted action this tick → record the defaulted wait as a log row.
            await conn.execute(
                """
                INSERT INTO action_log
                    (log_id, agent_id, tick_number, action_type, params,
                     result, submitted_at, resolved_at, status)
                VALUES ($1, $2, $3, $4, '{}'::jsonb, $5::jsonb, $6, $6, 'defaulted')
                ON CONFLICT (agent_id, tick_number) DO NOTHING
                """,
                uuid.uuid4(),
                uuid.UUID(aid),
                tick_n,
                res.action,
                _jsonb(result_json),
                _now_naive(),
            )


# ── inbox parking (next tick's delivery) ─────────────────────────────────────────────


async def _park_inbox(
    conn: asyncpg.Connection, next_tick: int, world: WorldState
) -> None:
    """Park the post-tick inbox under ``tick_scratch[(next_tick, "inbox")]`` so tick N+1's load
    delivers it (conversation latency, Protocol.md §4.4)."""
    serialized: dict[str, list[dict[str, Any]]] = {}
    for aid, msgs in world.inbox.items():
        serialized[aid] = [
            {
                "from_agent": m.from_agent,
                "to_agent": m.to_agent,
                "tick": m.tick,
                "message": m.message,
                "location_claim": list(m.location_claim) if m.location_claim else None,
                "broadcast": m.broadcast,
                "sender_pos": list(m.sender_pos),
            }
            for m in msgs
        ]
    await conn.execute(
        """
        INSERT INTO tick_scratch (tick_number, key, value)
        VALUES ($1, $2, $3::jsonb)
        ON CONFLICT (tick_number, key) DO UPDATE SET value = EXCLUDED.value
        """,
        next_tick,
        _INBOX_SCRATCH_KEY,
        _jsonb(serialized),
    )


# ── observation precompute (§5.2) ─────────────────────────────────────────────────────


async def _memory_index(
    conn: asyncpg.Connection, agent_id: str, limit: int = 50
) -> list[MemoryIndexEntry]:
    """Compact table-of-contents over the agent's long-term store, ranked importance then
    recency (Protocol.md §5.2 / §6.2 — index-driven retrieval, no embeddings)."""
    rows = await conn.fetch(
        """
        SELECT memory_id, tick_number, memory_type, subject_agent_id, content, importance
        FROM agent_memory
        WHERE agent_id = $1
        ORDER BY importance DESC, tick_number DESC
        LIMIT $2
        """,
        uuid.UUID(agent_id),
        limit,
    )
    file_of = {"event": "events", "relationship": "relationships", "reflection": "reflections"}
    index: list[MemoryIndexEntry] = []
    for r in rows:
        file = file_of.get(r["memory_type"], "events")
        if r["memory_type"] == "relationship" and r["subject_agent_id"] is not None:
            ref = f"{file}#{r['subject_agent_id']}"
        else:
            ref = f"{file}#{r['memory_id']}"
        index.append(
            MemoryIndexEntry(
                ref=ref,
                tick=r["tick_number"],
                importance=r["importance"],
                summary=(r["content"] or "")[:120],
            )
        )
    return index


def build_observation(
    world: WorldState,
    agent_id: str,
    *,
    next_tick: int,
    tick_ends_at: str,
    memory_index: list[MemoryIndexEntry],
    last_action_result: Optional[ActionResult],
    siphon_units: int,
    storm_active: bool = False,
    heat_zone_center: Optional[tuple[int, int]] = None,
) -> Observation:
    """Assemble the full §5.2 observation packet for one agent for the upcoming tick.

    Pure: given the post-resolution ``world`` it builds the frozen ``Observation`` contract. The
    spatial FOV comes from the pure ``compute_fov``; this wraps it with self/global/inbox/index.
    """
    agent = world.agents[agent_id]
    cell = world.cell(agent.pos)
    self_view = SelfView(
        agent_id=agent_id,
        pos=agent.pos,
        water=agent.water,
        food=agent.food,
        goods=agent.goods,
        on_terrain=cell.terrain if cell else "desert",
        stance=agent.stance,
        intention=agent.intention,  # carried forward each tick (Protocol §4.2 / §5.2)
    )
    fov: Fov = compute_fov(world, agent_id, noisy=storm_active)
    inbox_msgs = [
        InboxMessage(
            **{"from": m.from_agent},
            tick=m.tick,
            message=m.message,
            location_claim=m.location_claim,
        )
        for m in world.inbox.get(agent_id, [])
    ]
    lar = None
    if last_action_result is not None:
        status = last_action_result.status
        wire_status = status if status in ("ok", "rejected", "failed", "defaulted") else "failed"
        lar = LastActionResult(
            tick=next_tick - 1,
            action=last_action_result.action,
            status=wire_status,  # type: ignore[arg-type]
            note=last_action_result.note,
        )
    global_view = GlobalView(
        alive_count=world.alive_count(),
        storm_active=storm_active,
        heat_zone_center=heat_zone_center,
        siphon_units_this_tick=siphon_units,
    )
    return Observation(
        tick=next_tick,
        tick_ends_at=tick_ends_at,
        self=self_view,
        fov=fov,
        **{"global": global_view},
        inbox=inbox_msgs,
        last_action_result=lar,
        memory_index=memory_index,
    )


async def _persist_observations(
    conn: asyncpg.Connection,
    world: WorldState,
    *,
    next_tick: int,
    tick_ends_at: datetime,
    results: dict[str, ActionResult],
    siphon_units: int,
) -> None:
    """Precompute and write each LIVE agent's next-tick observation into agent_tick_results
    (Architecture.md Step 8 — the precomputed serving row that GET /world/observe reads)."""
    ends_iso = tick_ends_at.replace(microsecond=0).isoformat()
    if not ends_iso.endswith("Z") and "+" not in ends_iso:
        ends_iso = ends_iso + "Z"
    for aid, agent in world.live_agents().items():
        mem_index = await _memory_index(conn, aid)
        obs = build_observation(
            world,
            aid,
            next_tick=next_tick,
            tick_ends_at=ends_iso,
            memory_index=mem_index,
            last_action_result=results.get(aid),
            siphon_units=siphon_units,
        )
        obs_json = obs.model_dump(by_alias=True)
        action_result_json = obs_json.get("last_action_result")
        events_json = [m.model_dump(by_alias=True) for m in obs.inbox]
        await conn.execute(
            """
            INSERT INTO agent_tick_results
                (agent_id, tick_number, world_fov, action_result, events, fetched_at)
            VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, NULL)
            ON CONFLICT (agent_id, tick_number) DO UPDATE
            SET world_fov = EXCLUDED.world_fov,
                action_result = EXCLUDED.action_result,
                events = EXCLUDED.events,
                fetched_at = NULL
            """,
            uuid.UUID(aid),
            next_tick,
            _jsonb(obs_json),
            _jsonb(action_result_json),
            _jsonb(events_json),
        )


async def _cleanup_old_serving_rows(conn: asyncpg.Connection, tick_n: int) -> None:
    """Step 0 cleanup: drop the ephemeral serving rows and scratch for tick N-2 and older
    (agent_tick_results is replayable from action_log, so this is safe)."""
    await conn.execute(
        "DELETE FROM agent_tick_results WHERE tick_number <= $1", tick_n - 2
    )
    await conn.execute(
        "DELETE FROM tick_scratch WHERE tick_number <= $1 AND key = $2",
        tick_n - 1,
        _INBOX_SCRATCH_KEY,
    )


# ── top-level orchestration ─────────────────────────────────────────────────────────────


async def resolve_tick(
    conn: asyncpg.Connection,
    tick_n: int,
    seeded_rng: random.Random,
    *,
    tick_interval_seconds: float = 30.0,
    siphon_units: int = 37,
    oasis_regen: Optional[int] = None,
    oasis_cap: Optional[int] = None,
    base_drain: int = 1,
) -> dict[str, ActionResult]:
    """Resolve tick N end-to-end against the DB and open tick N+1 (Architecture.md Steps 0-9).

    Runs inside a single transaction: load → pure-resolve → persist (cells/agents/known/results)
    → precompute N+1 observations → advance tick_state to N+1. Returns the per-agent
    ``ActionResult`` map (the objective record) for the caller / tests.

    ``seeded_rng`` is the ONLY source of stochasticity (World.md §11); the same DB state + same
    accepted actions + same seed ⇒ identical writes.
    """
    async with conn.transaction():
        await _cleanup_old_serving_rows(conn, tick_n)

        before = await load_world_state(conn, tick_n, base_drain=base_drain)
        # ENVIRONMENT (supply side) runs BEFORE the resolver (which only consumes/drains): re-stock
        # the Siphon to its scheduled output and regenerate oases, so the chokepoint actually
        # dispenses water this tick (World.md §2-3). Pure; persisted via the normal changed-cell diff.
        # oasis_regen/oasis_cap are the scarcity knob: throttling oasis renewal forces agents off the
        # distributed periphery supply and onto the contested Siphon (World §3 access bottleneck).
        env_kw: dict[str, int] = {}
        if oasis_regen is not None:
            env_kw["oasis_regen"] = oasis_regen
        if oasis_cap is not None:
            env_kw["oasis_cap"] = oasis_cap
        before = apply_environment(before, tick_n, siphon_units=siphon_units, **env_kw)
        actions = await _read_actions(conn, tick_n)

        after, results = pure_resolve_tick(before, actions, seeded_rng)

        # Stamp this tick's stated intention onto each agent (Protocol §4.2 / §7.4). It has NO
        # mechanical effect (so it lives outside the pure physics core); a set value overwrites,
        # an omitted one leaves the carried-forward intention standing. This is the engine side of
        # the stated-intention-vs-executed-action channel (World §9.5).
        for aid, env in actions.items():
            if env.intention is not None and aid in after.agents:
                after.agents[aid].intention = env.intention

        await _persist_cells(conn, before, after)
        await _persist_agents(conn, after)
        await _persist_known_locations(conn, before, after, tick_n)
        await _persist_results(conn, tick_n, results)

        next_tick = tick_n + 1
        tick_ends_at = _now_naive() + timedelta(seconds=tick_interval_seconds)
        await _park_inbox(conn, next_tick, after)
        await _persist_observations(
            conn,
            after,
            next_tick=next_tick,
            tick_ends_at=tick_ends_at,
            results=results,
            siphon_units=siphon_units,
        )

        active_count = after.alive_count()
        await conn.execute(
            """
            INSERT INTO tick_state
                (tick_number, window_open, active_agent_count, submitted_count,
                 opened_at, tick_ends_at)
            VALUES ($1, TRUE, $2, 0, $3, $4)
            ON CONFLICT (tick_number) DO UPDATE
            SET window_open = TRUE,
                active_agent_count = EXCLUDED.active_agent_count,
                submitted_count = 0,
                opened_at = EXCLUDED.opened_at,
                tick_ends_at = EXCLUDED.tick_ends_at
            """,
            next_tick,
            active_count,
            _now_naive(),
            tick_ends_at,
        )
        # Advance current_tick but PRESERVE the lifecycle status (Architecture.md §Experiment
        # Lifecycle). Forcing 'running' here would clobber a concurrent pause/end — the resolver
        # owns the tick position, the admin lifecycle owns the status. On first ever advance with
        # no row yet, default to 'running'.
        await conn.execute(
            """
            INSERT INTO simulation_state (id, status, current_tick, started_at)
            VALUES (1, 'running', $1, $2)
            ON CONFLICT (id) DO UPDATE
            SET current_tick = EXCLUDED.current_tick
            """,
            next_tick,
            _now_naive(),
        )

    return results
