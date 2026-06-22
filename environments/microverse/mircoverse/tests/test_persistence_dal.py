"""Tests for the persistence layer (schema.sql + DAL).

The single pure test (load_schema_sql) always runs. Every DB-backed test is marked
`requires_db` and SKIPS cleanly when Postgres is unreachable (Docker down) — it never
fails for lack of a database. Each test isolates its own data behind a unique agent_id
so the suite is order-independent and leaves the DB usable.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest

from mircoverse.config import settings
from mircoverse.contracts import MemoryFile, MemoryOp, MemoryUpdate, SoulFile
from mircoverse.persistence import dal, db
from mircoverse.tests.conftest import requires_db


# Pick whichever DSN actually answers (mirrors conftest's test-then-dev order), so DB tests
# run against the test DB when present and fall back to dev otherwise.
def _live_dsn() -> str:
    for dsn in (settings.test_database_url, settings.database_url):
        try:
            if asyncio.run(db.ping(dsn)):
                return dsn
        except Exception:  # pragma: no cover - defensive
            continue
    return settings.database_url


DSN = _live_dsn()


def _soul(value: str = "alpha") -> SoulFile:
    return SoulFile(
        core_values=[f"value-{value}"],
        moral_boundaries=["I will not steal"],
        personality=value,
        goals=["survive"],
    )


async def _fresh_agent(soul: SoulFile | None = None, **kw) -> str:
    """Register a uniquely-keyed agent and return its id (helper for DB tests)."""
    return await dal.register_agent(
        soul=soul or _soul(),
        display_name=kw.get("display_name", "tester"),
        api_key_hash=kw.get("api_key_hash", "hash_" + uuid.uuid4().hex),
        position=kw.get("position", (1, 2)),
        resources=kw.get("resources", {"water": 50, "food": 10, "goods": 0}),
        status=kw.get("status", "active"),
        dsn=DSN,
    )


# ── pure (no DB) ──────────────────────────────────────────────────────────────────

def test_load_schema_sql():
    """schema.sql loads and contains the required DDL objects (pure — no DB)."""
    sql = dal.load_schema_sql()
    for needle in (
        "CREATE TABLE IF NOT EXISTS agents",
        "protect_original_soul",
        "BEFORE UPDATE ON agents",
        "CREATE TABLE IF NOT EXISTS world_cells",
        "PARTITION BY RANGE (tick_number)",
        "action_log_default PARTITION OF action_log DEFAULT",
        "one_action_per_tick",
        "CREATE TABLE IF NOT EXISTS agent_memory",
        "CREATE TABLE IF NOT EXISTS identity_snapshots",
        "CREATE TABLE IF NOT EXISTS tick_state",
        "CREATE TABLE IF NOT EXISTS tick_scratch",
        "CREATE TABLE IF NOT EXISTS simulation_state",
    ):
        assert needle in sql, f"missing DDL: {needle}"


# ── DB-backed (skip when Postgres down) ─────────────────────────────────────────────

@requires_db
def test_migrate_idempotent():
    """migrate() applies the schema and is safe to run twice."""
    async def go():
        await dal.migrate(DSN)
        await dal.migrate(DSN)  # second run must not raise
        async with db.connection(DSN) as conn:
            exists = await conn.fetchval("SELECT to_regclass('public.agents')")
        assert exists is not None
    asyncio.run(go())


@requires_db
def test_register_agent():
    """register_agent inserts a row; current_identity starts equal to original_soul."""
    async def go():
        await dal.migrate(DSN)
        soul = _soul("reg")
        aid = await _fresh_agent(soul)
        row = await dal.get_agent(aid, dsn=DSN)
        assert row is not None
        assert row["original_soul"] == soul.model_dump()
        assert row["current_identity"] == soul.model_dump()
        assert row["status"] == "active"
    asyncio.run(go())


@requires_db
def test_get_agent_missing_returns_none():
    """get_agent returns None for an unknown agent_id."""
    async def go():
        await dal.migrate(DSN)
        assert await dal.get_agent(str(uuid.uuid4()), dsn=DSN) is None
    asyncio.run(go())


@requires_db
def test_update_current_identity():
    """update_current_identity changes current_identity but leaves original_soul intact."""
    async def go():
        await dal.migrate(DSN)
        original = _soul("orig")
        aid = await _fresh_agent(original)
        revised = _soul("revised")
        await dal.update_current_identity(aid, revised, dsn=DSN)
        row = await dal.get_agent(aid, dsn=DSN)
        assert row["current_identity"] == revised.model_dump()
        assert row["original_soul"] == original.model_dump()
    asyncio.run(go())


@requires_db
def test_original_soul_trigger_raises_on_update():
    """The protect_original_soul BEFORE UPDATE trigger RAISES when original_soul changes.

    This is the identity-integrity guarantee (Architecture.md): immutability fails LOUDLY,
    it is not a silently-dropped row update."""
    async def go():
        await dal.migrate(DSN)
        aid = await _fresh_agent(_soul("immutable"))
        with pytest.raises(asyncpg.PostgresError) as exc:
            async with db.connection(DSN) as conn:
                await conn.execute(
                    "UPDATE agents SET original_soul = $2::jsonb WHERE agent_id = $1",
                    uuid.UUID(aid),
                    '{"core_values": ["TAMPERED"]}',
                )
        assert "original_soul is immutable" in str(exc.value)
        # And the row's original_soul is unchanged.
        row = await dal.get_agent(aid, dsn=DSN)
        assert row["original_soul"] == _soul("immutable").model_dump()
    asyncio.run(go())


@requires_db
def test_insert_action_on_conflict_do_nothing():
    """insert_action returns 1 on first insert, 0 on a duplicate (agent_id, tick_number)."""
    async def go():
        await dal.migrate(DSN)
        aid = await _fresh_agent()
        tick = 1000 + int(uuid.uuid4().int % 100000)
        first = await dal.insert_action(
            agent_id=aid, tick_number=tick, action_type="wait", params={}, dsn=DSN
        )
        second = await dal.insert_action(
            agent_id=aid, tick_number=tick, action_type="move",
            params={"direction": "N"}, dsn=DSN,
        )
        assert first == 1
        assert second == 0  # one-action-per-tick: second is a no-op
    asyncio.run(go())


@requires_db
def test_get_actions_for_tick():
    """get_actions_for_tick returns the accepted actions with decoded params."""
    async def go():
        await dal.migrate(DSN)
        aid = await _fresh_agent()
        tick = 2000 + int(uuid.uuid4().int % 100000)
        await dal.insert_action(
            agent_id=aid, tick_number=tick, action_type="move",
            params={"direction": "NE"}, dsn=DSN,
        )
        rows = await dal.get_actions_for_tick(tick, dsn=DSN)
        mine = [r for r in rows if r["agent_id"] == aid]
        assert len(mine) == 1
        assert mine[0]["action_type"] == "move"
        assert mine[0]["params"] == {"direction": "NE"}
    asyncio.run(go())


@requires_db
def test_write_action_result():
    """write_action_result fills result + resolved_at for a recorded action."""
    async def go():
        await dal.migrate(DSN)
        aid = await _fresh_agent()
        tick = 3000 + int(uuid.uuid4().int % 100000)
        await dal.insert_action(
            agent_id=aid, tick_number=tick, action_type="wait", params={}, dsn=DSN
        )
        affected = await dal.write_action_result(
            agent_id=aid, tick_number=tick,
            result={"status": "ok", "note": "passed"}, status="accepted", dsn=DSN,
        )
        assert affected == 1
        rows = await dal.get_actions_for_tick(tick, dsn=DSN)
        mine = [r for r in rows if r["agent_id"] == aid][0]
        async with db.connection(DSN) as conn:
            res = await conn.fetchval(
                "SELECT result FROM action_log WHERE agent_id=$1 AND tick_number=$2",
                uuid.UUID(aid), tick,
            )
        assert mine["log_id"]
        assert "ok" in str(res)
    asyncio.run(go())


@requires_db
def test_write_memory_delta_and_get_memory_file():
    """write_memory_delta stores one typed entry; get_memory_file reads it back."""
    async def go():
        await dal.migrate(DSN)
        aid = await _fresh_agent()
        tick = 40
        update = MemoryUpdate(
            file=MemoryFile.EVENTS, op=MemoryOp.APPEND, importance=9,
            content="Watched agent_18 die of thirst nearby.",
        )
        mid = await dal.write_memory_delta(
            agent_id=aid, tick_number=tick, update=update, dsn=DSN
        )
        entries = await dal.get_memory_file(aid, MemoryFile.EVENTS, dsn=DSN)
        assert any(e["memory_id"] == mid for e in entries)
        target = [e for e in entries if e["memory_id"] == mid][0]
        assert target["memory_type"] == "event"
        assert target["importance"] == 9
    asyncio.run(go())


@requires_db
def test_get_memory_index():
    """get_memory_index returns refs ranked by importance, summaries truncated."""
    async def go():
        await dal.migrate(DSN)
        aid = await _fresh_agent()
        low = MemoryUpdate(file=MemoryFile.EVENTS, importance=2, content="minor note")
        high = MemoryUpdate(
            file=MemoryFile.RELATIONSHIPS, importance=8,
            subject_agent_id=str(uuid.uuid4()), content="agent shared a real oasis",
        )
        await dal.write_memory_delta(agent_id=aid, tick_number=10, update=low, dsn=DSN)
        await dal.write_memory_delta(agent_id=aid, tick_number=11, update=high, dsn=DSN)
        index = await dal.get_memory_index(aid, dsn=DSN)
        assert len(index) == 2
        assert index[0]["importance"] == 8  # highest importance first
        assert index[0]["ref"].startswith("relationships#")
        assert all(len(e["summary"]) <= 120 for e in index)
    asyncio.run(go())


@requires_db
def test_snapshot_identity_and_get_drift_history():
    """snapshot_identity appends rows; get_drift_history returns them oldest-first."""
    async def go():
        await dal.migrate(DSN)
        aid = await _fresh_agent(_soul("snap"))
        await dal.snapshot_identity(
            agent_id=aid, tick_number=0, identity=_soul("snap"),
            trigger="engine_measurement", drift_score=0.0, dsn=DSN,
        )
        await dal.snapshot_identity(
            agent_id=aid, tick_number=10, identity=_soul("drifted"),
            trigger="agent_revision", drift_score=0.42, dsn=DSN,
        )
        hist = await dal.get_drift_history(aid, dsn=DSN)
        assert [h["tick_number"] for h in hist] == [0, 10]
        assert hist[1]["trigger"] == "agent_revision"
        assert hist[1]["drift_score"] == pytest.approx(0.42)
        assert hist[1]["identity_json"] == _soul("drifted").model_dump()
    asyncio.run(go())


@requires_db
def test_open_tick_and_get_tick_state():
    """open_tick inserts a window-open tick_state row (idempotent on re-open)."""
    async def go():
        await dal.migrate(DSN)
        tick = 5000 + int(uuid.uuid4().int % 100000)
        ends = datetime.now(timezone.utc) + timedelta(seconds=30)
        await dal.open_tick(tick_number=tick, active_agent_count=3, tick_ends_at=ends, dsn=DSN)
        await dal.open_tick(tick_number=tick, active_agent_count=5, tick_ends_at=ends, dsn=DSN)
        state = await dal.get_tick_state(tick, dsn=DSN)
        assert state["window_open"] is True
        assert state["active_agent_count"] == 5
        assert state["submitted_count"] == 0
    asyncio.run(go())


@requires_db
def test_bump_submitted_count_closes_window_on_last_submitter():
    """The atomic early-close: only the last expected submitter closes the window."""
    async def go():
        await dal.migrate(DSN)
        tick = 6000 + int(uuid.uuid4().int % 100000)
        ends = datetime.now(timezone.utc) + timedelta(seconds=30)
        await dal.open_tick(tick_number=tick, active_agent_count=2, tick_ends_at=ends, dsn=DSN)
        first = await dal.bump_submitted_count(tick, dsn=DSN)   # 1 of 2
        second = await dal.bump_submitted_count(tick, dsn=DSN)  # 2 of 2 → closes
        third = await dal.bump_submitted_count(tick, dsn=DSN)   # window already closed
        assert first is False
        assert second is True
        assert third is None
        state = await dal.get_tick_state(tick, dsn=DSN)
        assert state["window_open"] is False
    asyncio.run(go())


@requires_db
def test_write_and_read_scratch():
    """tick_scratch round-trips a JSON value and upserts on conflict."""
    async def go():
        await dal.migrate(DSN)
        tick = 7000 + int(uuid.uuid4().int % 100000)
        await dal.write_scratch(tick_number=tick, key="positions", value={"a": [1, 2]}, dsn=DSN)
        await dal.write_scratch(tick_number=tick, key="positions", value={"a": [3, 4]}, dsn=DSN)
        got = await dal.read_scratch(tick, "positions", dsn=DSN)
        assert got == {"a": [3, 4]}
        assert await dal.read_scratch(tick, "missing", dsn=DSN) is None
    asyncio.run(go())


@requires_db
def test_upsert_and_get_cell():
    """world_cells writes and reads one cell in place."""
    async def go():
        await dal.migrate(DSN)
        x = 25 + int(uuid.uuid4().int % 25)
        y = 25 + int(uuid.uuid4().int % 25)
        await dal.upsert_cell(x=x, y=y, terrain="settlement", water=37, food=0, goods=0, dsn=DSN)
        await dal.upsert_cell(x=x, y=y, terrain="settlement", water=10, food=0, goods=0, dsn=DSN)
        cell = await dal.get_cell(x, y, dsn=DSN)
        assert cell["terrain"] == "settlement"
        assert cell["water"] == 10  # updated in place
    asyncio.run(go())


@requires_db
def test_simulation_state_singleton():
    """simulation_state upserts the singleton row (id = 1)."""
    async def go():
        await dal.migrate(DSN)
        await dal.set_simulation_state(status="running", current_tick=7, dsn=DSN)
        state = await dal.get_simulation_state(dsn=DSN)
        assert state["id"] == 1
        assert state["status"] == "running"
        assert state["current_tick"] == 7
    asyncio.run(go())
