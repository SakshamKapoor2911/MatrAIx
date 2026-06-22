"""Bootstrap a generated WorldState into the database so a run can start.

This is the seam between ``mircoverse.manifest.generate_world`` (a pure in-memory ``WorldState``)
and the running server/tick-loop, which both read persisted rows. It bulk-loads the world, registers
each agent (creating its bearer key), seeds the **tick-0 observation** for every agent (so
``GET /world/observe`` works *before* any tick resolves — otherwise the serving table is empty), and
opens ``tick_state`` for tick 0.

It deliberately REUSES the orchestrator's own writers/encoders (``_persist_cells``,
``_encode_cell_meta``, ``build_observation``) so the bytes it writes are identical to what
``resolve_tick`` writes and reads — no second encoding to drift out of sync.

Agent identity: a generated ``WorldState`` has synthetic agent ids (``agent_00``…) and no souls.
The bootstrap assigns each a real registration: a fresh UUID + a one-time api_key + an
``original_soul`` (from the supplied roster, or a neutral default). It returns the roster
(``BootstrapAgent`` list) mapping the world position to the live ``agent_id`` + ``api_key`` so a
caller can hand keys to participant agents (or drive them locally).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncpg

from mircoverse.contracts.identity import SoulFile
from mircoverse.resolution.orchestrator import (
    _encode_cell_meta,
    _now_naive,
    _jsonb,
    build_observation,
)
from mircoverse.server import auth
from mircoverse.world.state import WorldState


def _soul_json(soul: SoulFile) -> str:
    return json.dumps(soul.model_dump())

__all__ = ["BootstrapAgent", "initialize_simulation"]


@dataclass
class BootstrapAgent:
    """One registered agent after bootstrap: the world's synthetic id, the persisted UUID, the
    one-time plaintext api_key (shown once — give it to whoever runs the agent), and spawn pos."""

    world_id: str          # the id inside the generated WorldState (e.g. "agent_07")
    agent_id: str          # the persisted UUID
    api_key: str           # one-time bearer token (only the SHA-256 hash is stored)
    pos: tuple[int, int]


def _neutral_soul(name: str) -> SoulFile:
    """A minimal genre-neutral default soul for agents the caller didn't supply one for.
    (The controlled arm should pass a curated roster; this keeps a smoke-run self-contained.)"""
    return SoulFile(
        core_values=["Survive", "Keep my word"],
        moral_boundaries=["I will not steal", "I will not kill"],
        personality="Cautious and observant.",
        goals=["Find a reliable water source"],
    )


async def initialize_simulation(
    conn: asyncpg.Connection,
    world: WorldState,
    *,
    souls: Optional[dict[str, SoulFile]] = None,
    names: Optional[dict[str, str]] = None,
    tick_interval_seconds: float = 30.0,
    siphon_units: int = 37,
    storm_active: bool = False,
    heat_zone_center: Optional[tuple[int, int]] = None,
) -> list[BootstrapAgent]:
    """Load ``world`` into the DB and open tick 0. Returns the registered roster.

    Steps (all in one transaction so a partial bootstrap never leaves a half-loaded world):
      1. reset the world tables (idempotent fresh start);
      2. write every cell (full grid — this is the one place we DO write all cells, at t=0);
      3. register each agent (UUID + api_key + soul), persist position/resources/known-spawn;
      4. seed each live agent's tick-0 observation into ``agent_tick_results`` (so /observe works);
      5. open ``tick_state`` for tick 0 and set ``simulation_state`` = running.

    ``souls`` / ``names`` are keyed by the world's synthetic agent id; missing entries get a
    neutral default. Pure-deterministic given the same world (no RNG here — observation assembly
    is deterministic; tick_ends_at is wall-clock and the only non-deterministic field)."""
    souls = souls or {}
    names = names or {}

    async with conn.transaction():
        # 1. Fresh start — clear prior run state (order respects FKs).
        await conn.execute("DELETE FROM agent_tick_results")
        await conn.execute("DELETE FROM agent_known_locations")
        await conn.execute("DELETE FROM action_log")
        await conn.execute("DELETE FROM agent_memory")
        await conn.execute("DELETE FROM identity_snapshots")
        await conn.execute("DELETE FROM tick_scratch")
        await conn.execute("DELETE FROM tick_state")
        await conn.execute("DELETE FROM agents")
        await conn.execute("DELETE FROM world_cells")

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 2. Write the full grid once (t=0 is the only full-grid write; thereafter changed-only).
        #    ALL writes go through the transactional `conn` (NOT the DAL helpers, which open their
        #    own pool connection and would commit outside this transaction — that non-atomicity is
        #    a bug at any scale and a lock-contention disaster at 1000+ cells). Bulk via executemany.
        cell_rows = [
            (x, y, cell.terrain, cell.water, cell.food, cell.goods, _encode_cell_meta(cell))
            for (x, y), cell in world.cells.items()
        ]
        await conn.executemany(
            """
            INSERT INTO world_cells (x, y, terrain, water, food, goods, passable, known_name)
            VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7)
            """,
            cell_rows,
        )

        # 3. Register agents (UUID + api_key + soul) and persist their world state — all on `conn`.
        roster: list[BootstrapAgent] = []
        world_to_uuid: dict[str, str] = {}
        agent_rows = []
        known_rows = []
        for world_id, agent in sorted(world.agents.items()):
            api_key = auth.generate_api_key()
            key_hash = auth.hash_api_key(api_key)
            agent_uuid = str(uuid.uuid4())
            soul = souls.get(world_id) or _neutral_soul(world_id)
            display = names.get(world_id, world_id)
            resources = {
                "water": agent.water, "food": agent.food,
                "goods": agent.goods, "stance": agent.stance,
            }
            agent_rows.append((
                uuid.UUID(agent_uuid), display, now, _soul_json(soul),
                agent.pos[0], agent.pos[1], json.dumps(resources),
                "active" if agent.alive else "dead", key_hash,
            ))
            for (kx, ky) in (agent.known_locations or {agent.pos}):
                ttype = world.cells[(kx, ky)].terrain if (kx, ky) in world.cells else "unknown"
                known_rows.append((uuid.UUID(agent_uuid), kx, ky, ttype))
            world_to_uuid[world_id] = agent_uuid
            roster.append(BootstrapAgent(world_id, agent_uuid, api_key, agent.pos))

        await conn.executemany(
            """
            INSERT INTO agents (
                agent_id, display_name, registered_at, original_soul, current_identity,
                position_x, position_y, resources, status, api_key_hash
            )
            VALUES ($1, $2, $3, $4::jsonb, $4::jsonb, $5, $6, $7::jsonb, $8, $9)
            """,
            agent_rows,
        )
        await conn.executemany(
            """
            INSERT INTO agent_known_locations (agent_id, x, y, location_type, discovered_tick)
            VALUES ($1, $2, $3, $4, 0)
            ON CONFLICT (agent_id, x, y) DO NOTHING
            """,
            known_rows,
        )

        # 4. Seed tick-0 observations. build_observation indexes the world by agent id, so we
        #    build a uuid-keyed view of the world for the packet (FOV/self/global are positional).
        ends = _now_naive() + timedelta(seconds=tick_interval_seconds)
        ends_iso = ends.replace(microsecond=0).isoformat()
        if not ends_iso.endswith("Z") and "+" not in ends_iso:
            ends_iso += "Z"

        uuid_world = _rekey_world(world, world_to_uuid)
        for ba in roster:
            agent = uuid_world.agents[ba.agent_id]
            if not agent.alive:
                continue
            obs = build_observation(
                uuid_world,
                ba.agent_id,
                next_tick=0,
                tick_ends_at=ends_iso,
                memory_index=[],            # no memory at t=0
                last_action_result=None,    # nothing happened yet
                siphon_units=siphon_units,
                storm_active=storm_active,
                heat_zone_center=heat_zone_center,
            )
            obs_json = obs.model_dump(by_alias=True)
            await conn.execute(
                """
                INSERT INTO agent_tick_results
                    (agent_id, tick_number, world_fov, action_result, events, fetched_at)
                VALUES ($1, 0, $2::jsonb, NULL, '[]'::jsonb, NULL)
                """,
                uuid.UUID(ba.agent_id),
                _jsonb(obs_json),
            )

        # 5. Open tick 0 and mark the simulation running — on `conn` (stay in the transaction).
        alive = uuid_world.alive_count()
        await conn.execute(
            """
            INSERT INTO tick_state
                (tick_number, window_open, active_agent_count, submitted_count, opened_at, tick_ends_at)
            VALUES (0, TRUE, $1, 0, $2, $3)
            ON CONFLICT (tick_number) DO UPDATE
            SET window_open = TRUE, active_agent_count = EXCLUDED.active_agent_count,
                submitted_count = 0, opened_at = EXCLUDED.opened_at, tick_ends_at = EXCLUDED.tick_ends_at
            """,
            alive, now, ends,
        )
        await conn.execute(
            """
            INSERT INTO simulation_state (id, status, current_tick, started_at)
            VALUES (1, 'running', 0, $1)
            ON CONFLICT (id) DO UPDATE SET status = 'running', current_tick = 0
            """,
            now,
        )

    return roster


def _rekey_world(world: WorldState, world_to_uuid: dict[str, str]) -> WorldState:
    """Return a shallow copy of ``world`` whose agents are keyed by their persisted UUID (and whose
    ``agent_id`` fields match), so ``build_observation`` — which looks agents up by id and reports
    neighbour ids — speaks UUIDs, consistent with what /observe will later serve."""
    from dataclasses import replace

    new_agents = {}
    for world_id, agent in world.agents.items():
        new_id = world_to_uuid[world_id]
        new_agents[new_id] = replace(agent, agent_id=new_id)
    return replace(world, agents=new_agents)
