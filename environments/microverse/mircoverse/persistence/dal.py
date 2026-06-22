"""Async data-access layer over the Architecture.md schema.

Thin, typed functions on top of `mircoverse.persistence.db` (the asyncpg pool). No business
logic lives here — these are the persistence primitives the resolution/server layers call.
All JSON columns are passed as JSON-encoded text and cast to JSONB in SQL, so asyncpg never
needs a custom codec. Soul files / identities arrive as the frozen `SoulFile` contract or as
plain dicts; both are accepted.

The schema (schema.sql) and `migrate()` are applied idempotently; every function here assumes
the schema already exists. DB-backed tests SKIP (never fail) when Postgres is unreachable.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import asyncpg

from mircoverse.contracts import MemoryFile, MemoryUpdate, SoulFile
from mircoverse.persistence import db

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# memory_type column values (Architecture.md agent_memory) ↔ the wire MemoryFile enum,
# which is plural (events/relationships/reflections). The DB stores the singular noun.
_MEMORY_FILE_TO_TYPE: dict[MemoryFile, str] = {
    MemoryFile.EVENTS: "event",
    MemoryFile.RELATIONSHIPS: "relationship",
    MemoryFile.REFLECTIONS: "reflection",
}
_MEMORY_TYPE_TO_FILE: dict[str, str] = {v: k.value for k, v in _MEMORY_FILE_TO_TYPE.items()}


def _now() -> datetime:
    """A timezone-naive UTC timestamp matching the schema's TIMESTAMP (no tz) columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_jsonb(value: Any) -> str:
    """JSON-encode a value for a JSONB column. Pydantic models are dumped to plain dicts."""
    if isinstance(value, SoulFile):
        value = value.model_dump()
    return json.dumps(value)


# ── schema management ─────────────────────────────────────────────────────────────

def load_schema_sql() -> str:
    """Return the DDL text. Pure — no DB needed (so it is unit-testable without Postgres)."""
    return _SCHEMA_PATH.read_text(encoding="utf-8")


async def migrate(dsn: Optional[str] = None) -> None:
    """Apply schema.sql idempotently. Safe to call repeatedly (every statement is IF NOT
    EXISTS / OR REPLACE / DROP-then-CREATE), so it doubles as create-if-absent on boot."""
    sql = load_schema_sql()
    async with db.connection(dsn) as conn:
        await conn.execute(sql)


# ── agents ──────────────────────────────────────────────────────────────────────────

async def register_agent(
    *,
    soul: Union[SoulFile, dict[str, Any]],
    display_name: str,
    api_key_hash: str,
    position: tuple[int, int],
    resources: dict[str, int],
    agent_id: Optional[str] = None,
    status: str = "active",
    dsn: Optional[str] = None,
) -> str:
    """Insert a new agent. `current_identity` starts as a copy of `original_soul`
    (Protocol.md §7.1). Returns the agent_id (generated if not supplied)."""
    aid = agent_id or str(uuid.uuid4())
    soul_json = _as_jsonb(soul)
    async with db.connection(dsn) as conn:
        await conn.execute(
            """
            INSERT INTO agents (
                agent_id, display_name, registered_at, original_soul, current_identity,
                position_x, position_y, resources, status, api_key_hash
            )
            VALUES ($1, $2, $3, $4::jsonb, $4::jsonb, $5, $6, $7::jsonb, $8, $9)
            """,
            uuid.UUID(aid),
            display_name,
            _now(),
            soul_json,
            position[0],
            position[1],
            _as_jsonb(resources),
            status,
            api_key_hash,
        )
    return aid


async def get_agent(agent_id: str, dsn: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Fetch one agent row as a dict (JSONB columns decoded), or None if absent."""
    async with db.connection(dsn) as conn:
        row = await conn.fetchrow(
            "SELECT * FROM agents WHERE agent_id = $1", uuid.UUID(agent_id)
        )
    return _decode_agent_row(row) if row is not None else None


def _decode_agent_row(row: asyncpg.Record) -> dict[str, Any]:
    d = dict(row)
    d["agent_id"] = str(d["agent_id"])
    for col in ("original_soul", "current_identity", "resources"):
        if isinstance(d.get(col), str):
            d[col] = json.loads(d[col])
    return d


async def update_current_identity(
    agent_id: str,
    identity: Union[SoulFile, dict[str, Any]],
    dsn: Optional[str] = None,
) -> None:
    """Update only `current_identity`. Touching `original_soul` is impossible — the
    protect_original_soul trigger raises — so this write is always identity-safe."""
    async with db.connection(dsn) as conn:
        await conn.execute(
            "UPDATE agents SET current_identity = $2::jsonb WHERE agent_id = $1",
            uuid.UUID(agent_id),
            _as_jsonb(identity),
        )


# ── action_log ────────────────────────────────────────────────────────────────────

async def insert_action(
    *,
    agent_id: str,
    tick_number: int,
    action_type: str,
    params: dict[str, Any],
    status: str = "accepted",
    intention: Optional[str] = None,
    log_id: Optional[str] = None,
    dsn: Optional[str] = None,
) -> int:
    """Record one action with INSERT ... ON CONFLICT (agent_id, tick_number) DO NOTHING.

    Returns rows-affected: 1 on a real insert, 0 if the agent already submitted this tick
    (the one-action-per-tick guarantee — Architecture.md / Protocol.md §5.3). The caller
    maps 0 → HTTP 429. `intention` (Protocol §4.2 / §7.4) is the agent's stated "what I'm
    trying to do" this tick; None leaves the column NULL (= unchanged). No mechanical effect."""
    lid = log_id or str(uuid.uuid4())
    async with db.connection(dsn) as conn:
        tag = await conn.execute(
            """
            INSERT INTO action_log
                (log_id, agent_id, tick_number, action_type, params, intention, submitted_at, status)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8)
            ON CONFLICT (agent_id, tick_number) DO NOTHING
            """,
            uuid.UUID(lid),
            uuid.UUID(agent_id),
            tick_number,
            action_type,
            _as_jsonb(params),
            intention,
            _now(),
            status,
        )
    return _rows_affected(tag)


def _rows_affected(command_tag: str) -> int:
    """asyncpg returns a command tag like 'INSERT 0 1'; the last token is the row count."""
    try:
        return int(command_tag.split()[-1])
    except (ValueError, IndexError):
        return 0


async def get_actions_for_tick(
    tick_number: int, dsn: Optional[str] = None
) -> list[dict[str, Any]]:
    """All accepted actions for a tick, ordered by agent_id for deterministic iteration."""
    async with db.connection(dsn) as conn:
        rows = await conn.fetch(
            """
            SELECT log_id, agent_id, tick_number, action_type, params, status
            FROM action_log
            WHERE tick_number = $1
            ORDER BY agent_id
            """,
            tick_number,
        )
    out: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["log_id"] = str(d["log_id"])
        d["agent_id"] = str(d["agent_id"])
        if isinstance(d.get("params"), str):
            d["params"] = json.loads(d["params"])
        out.append(d)
    return out


async def write_action_result(
    *,
    agent_id: str,
    tick_number: int,
    result: dict[str, Any],
    status: Optional[str] = None,
    dsn: Optional[str] = None,
) -> int:
    """Step 7b audit write: fill action_log.result + resolved_at (and optionally status)."""
    async with db.connection(dsn) as conn:
        tag = await conn.execute(
            """
            UPDATE action_log
            SET result = $3::jsonb,
                resolved_at = $4,
                status = COALESCE($5, status)
            WHERE agent_id = $1 AND tick_number = $2
            """,
            uuid.UUID(agent_id),
            tick_number,
            _as_jsonb(result),
            _now(),
            status,
        )
    return _rows_affected(tag)


# ── agent_memory (subjective long-term layer) ─────────────────────────────────────────

async def write_memory_delta(
    *,
    agent_id: str,
    tick_number: int,
    update: MemoryUpdate,
    memory_id: Optional[str] = None,
    dsn: Optional[str] = None,
) -> str:
    """Persist one subjective-memory delta (Protocol.md §4.2). The engine only STORES what
    the agent chose to remember — it never authors memory. Returns the new memory_id."""
    mid = memory_id or str(uuid.uuid4())
    subject = (
        uuid.UUID(update.subject_agent_id) if update.subject_agent_id is not None else None
    )
    async with db.connection(dsn) as conn:
        await conn.execute(
            """
            INSERT INTO agent_memory
                (memory_id, agent_id, tick_number, memory_type, subject_agent_id,
                 content, importance, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            uuid.UUID(mid),
            uuid.UUID(agent_id),
            tick_number,
            _MEMORY_FILE_TO_TYPE[update.file],
            subject,
            update.content,
            update.importance,
            _now(),
        )
    return mid


async def get_memory_index(
    agent_id: str, limit: int = 100, dsn: Optional[str] = None
) -> list[dict[str, Any]]:
    """The compact table-of-contents that drives index-driven agentic retrieval (no
    embeddings — Protocol.md §6.2). Ranked by importance then recency; `ref` is built as
    `<file>#<memory_id>` (or `relationships#<subject>` for relationship rows) so the agent
    can pull a full entry via GET /memory/{file}."""
    async with db.connection(dsn) as conn:
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
    index: list[dict[str, Any]] = []
    for row in rows:
        file = _MEMORY_TYPE_TO_FILE[row["memory_type"]]
        if row["memory_type"] == "relationship" and row["subject_agent_id"] is not None:
            ref = f"{file}#{row['subject_agent_id']}"
        else:
            ref = f"{file}#{row['memory_id']}"
        summary = row["content"] or ""
        index.append(
            {
                "ref": ref,
                "tick": row["tick_number"],
                "importance": row["importance"],
                "summary": summary[:120],
            }
        )
    return index


async def get_memory_file(
    agent_id: str, file: Union[MemoryFile, str], dsn: Optional[str] = None
) -> list[dict[str, Any]]:
    """Full entries of one typed file (events/relationships/reflections), chronological —
    backs GET /agents/{id}/memory/{file}."""
    file_enum = MemoryFile(file) if not isinstance(file, MemoryFile) else file
    mtype = _MEMORY_FILE_TO_TYPE[file_enum]
    async with db.connection(dsn) as conn:
        rows = await conn.fetch(
            """
            SELECT memory_id, tick_number, memory_type, subject_agent_id, content, importance
            FROM agent_memory
            WHERE agent_id = $1 AND memory_type = $2
            ORDER BY tick_number ASC
            """,
            uuid.UUID(agent_id),
            mtype,
        )
    out: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["memory_id"] = str(d["memory_id"])
        if d["subject_agent_id"] is not None:
            d["subject_agent_id"] = str(d["subject_agent_id"])
        out.append(d)
    return out


# ── identity_snapshots ────────────────────────────────────────────────────────────────

async def snapshot_identity(
    *,
    agent_id: str,
    tick_number: int,
    identity: Union[SoulFile, dict[str, Any]],
    trigger: str,
    drift_score: Optional[float] = None,
    snapshot_id: Optional[str] = None,
    dsn: Optional[str] = None,
) -> str:
    """Append an identity_snapshots row. `trigger` ∈
    {agent_revision, engine_measurement, forced_end} (Architecture.md). Append-only —
    the drift audit log. Returns the snapshot_id."""
    sid = snapshot_id or str(uuid.uuid4())
    async with db.connection(dsn) as conn:
        await conn.execute(
            """
            INSERT INTO identity_snapshots
                (snapshot_id, agent_id, tick_number, snapshot_at, identity_json,
                 drift_score, trigger)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
            """,
            uuid.UUID(sid),
            uuid.UUID(agent_id),
            tick_number,
            _now(),
            _as_jsonb(identity),
            drift_score,
            trigger,
        )
    return sid


async def get_drift_history(
    agent_id: str, dsn: Optional[str] = None
) -> list[dict[str, Any]]:
    """All snapshots for one agent, oldest first — the per-agent drift trajectory
    (GET /admin/agents/{id}/drift)."""
    async with db.connection(dsn) as conn:
        rows = await conn.fetch(
            """
            SELECT snapshot_id, tick_number, snapshot_at, identity_json, drift_score, trigger
            FROM identity_snapshots
            WHERE agent_id = $1
            ORDER BY tick_number ASC, snapshot_at ASC
            """,
            uuid.UUID(agent_id),
        )
    out: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["snapshot_id"] = str(d["snapshot_id"])
        if isinstance(d.get("identity_json"), str):
            d["identity_json"] = json.loads(d["identity_json"])
        out.append(d)
    return out


# ── tick_state (window discipline / early close) ───────────────────────────────────────

async def open_tick(
    *,
    tick_number: int,
    active_agent_count: int,
    tick_ends_at: datetime,
    dsn: Optional[str] = None,
) -> None:
    """Step 9: insert the tick_state row for the next tick (window_open = TRUE,
    submitted_count = 0). Idempotent on the PK so a re-run does not error."""
    async with db.connection(dsn) as conn:
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
            tick_number,
            active_agent_count,
            _now(),
            tick_ends_at.replace(tzinfo=None) if tick_ends_at.tzinfo else tick_ends_at,
        )


async def bump_submitted_count(
    tick_number: int, dsn: Optional[str] = None
) -> Optional[bool]:
    """The Architecture.md atomic early-close statement: increment submitted_count and flip
    window_open to FALSE iff this caller is the last expected submitter, all in one
    row-locked UPDATE. RETURNS whether THIS caller closed the window
    (True/False), or None if the window was already closed (0 rows)."""
    async with db.connection(dsn) as conn:
        val = await conn.fetchval(
            """
            UPDATE tick_state
            SET    submitted_count = submitted_count + 1,
                   window_open  = CASE WHEN submitted_count + 1 >= active_agent_count
                                       THEN FALSE ELSE window_open END,
                   tick_ends_at = CASE WHEN submitted_count + 1 >= active_agent_count
                                       THEN NOW()  ELSE tick_ends_at END,
                   closed_at    = CASE WHEN submitted_count + 1 >= active_agent_count
                                       THEN NOW()  ELSE closed_at    END
            WHERE  tick_number = $1 AND window_open = TRUE
            RETURNING (NOT window_open) AS i_closed_the_window
            """,
            tick_number,
        )
    return val


async def get_tick_state(
    tick_number: int, dsn: Optional[str] = None
) -> Optional[dict[str, Any]]:
    """Fetch one tick_state row as a dict, or None."""
    async with db.connection(dsn) as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tick_state WHERE tick_number = $1", tick_number
        )
    return dict(row) if row is not None else None


# ── tick_scratch (inter-step data) ──────────────────────────────────────────────────────

async def write_scratch(
    *, tick_number: int, key: str, value: Any, dsn: Optional[str] = None
) -> None:
    """Upsert one inter-step scratch value (Step Functions context is only {"tick": N})."""
    async with db.connection(dsn) as conn:
        await conn.execute(
            """
            INSERT INTO tick_scratch (tick_number, key, value)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT (tick_number, key) DO UPDATE SET value = EXCLUDED.value
            """,
            tick_number,
            key,
            _as_jsonb(value),
        )


async def read_scratch(
    tick_number: int, key: str, dsn: Optional[str] = None
) -> Optional[Any]:
    """Read one scratch value back (JSONB-decoded), or None if absent."""
    async with db.connection(dsn) as conn:
        raw = await conn.fetchval(
            "SELECT value FROM tick_scratch WHERE tick_number = $1 AND key = $2",
            tick_number,
            key,
        )
    return json.loads(raw) if isinstance(raw, str) else raw


# ── world_cells ───────────────────────────────────────────────────────────────────────

async def upsert_cell(
    *,
    x: int,
    y: int,
    terrain: str,
    water: int,
    food: int,
    goods: int,
    passable: bool = True,
    known_name: Optional[str] = None,
    dsn: Optional[str] = None,
) -> None:
    """Write one cell in place (Step 7a writes only changed cells — never the full grid)."""
    async with db.connection(dsn) as conn:
        await conn.execute(
            """
            INSERT INTO world_cells (x, y, terrain, water, food, goods, passable, known_name)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (x, y) DO UPDATE
            SET terrain = EXCLUDED.terrain,
                water = EXCLUDED.water,
                food = EXCLUDED.food,
                goods = EXCLUDED.goods,
                passable = EXCLUDED.passable,
                known_name = EXCLUDED.known_name
            """,
            x, y, terrain, water, food, goods, passable, known_name,
        )


async def get_cell(x: int, y: int, dsn: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Fetch one cell, or None."""
    async with db.connection(dsn) as conn:
        row = await conn.fetchrow(
            "SELECT * FROM world_cells WHERE x = $1 AND y = $2", x, y
        )
    return dict(row) if row is not None else None


# ── simulation_state (singleton) ──────────────────────────────────────────────────────

async def set_simulation_state(
    *,
    status: str,
    current_tick: int,
    dsn: Optional[str] = None,
) -> None:
    """Upsert the singleton simulation_state row (id = 1)."""
    async with db.connection(dsn) as conn:
        await conn.execute(
            """
            INSERT INTO simulation_state (id, status, current_tick, started_at)
            VALUES (1, $1, $2, $3)
            ON CONFLICT (id) DO UPDATE
            SET status = EXCLUDED.status,
                current_tick = EXCLUDED.current_tick
            """,
            status,
            current_tick,
            _now(),
        )


async def get_simulation_state(dsn: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Read the singleton simulation_state row, or None if uninitialized."""
    async with db.connection(dsn) as conn:
        row = await conn.fetchrow("SELECT * FROM simulation_state WHERE id = 1")
    return dict(row) if row is not None else None
