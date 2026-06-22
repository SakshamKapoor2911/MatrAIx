"""Tests for the FastAPI server (mircoverse.server.app).

Two registers, matching the repo convention:
- PURE / no-DB tests: the app builds and its OpenAPI lists EXACTLY the §5.1 contract endpoints;
  unauthenticated requests are rejected before any DB touch; the pure memory helpers
  (ref-select, keyword scan, entry serialization) behave correctly.
- DB-backed tests are marked ``requires_db`` and SKIP (never fail) when Postgres is down. They
  drive the full agent lifecycle through the live wire surface: register -> drive a tick ->
  observe the precomputed row -> action (and the 429 on a second) -> reflection -> memory pull
  (?ref / ?q) -> simulation/status.
"""

from __future__ import annotations

import asyncio
import uuid

from mircoverse.config import settings
from mircoverse.contracts import RegistrationRequest, SoulFile
from mircoverse.persistence import dal, db
from mircoverse.server import API_PREFIX, CONTRACT_ROUTES, app as live_app, create_app
from mircoverse.server.app import (
    _keyword_filter,
    _select_by_ref,
    _serialize_entry,
)
from mircoverse.tests.conftest import requires_db

from fastapi.testclient import TestClient


def _live_dsn() -> str:
    for dsn in (settings.test_database_url, settings.database_url):
        try:
            if asyncio.run(db.ping(dsn)):
                return dsn
        except Exception:  # pragma: no cover - defensive
            continue
    return settings.database_url


DSN = _live_dsn()


# ── pure / no-DB ───────────────────────────────────────────────────────────────────────


def test_app_builds_and_openapi_lists_exactly_the_contract_endpoints():
    """The app constructs with no DB and its OpenAPI paths × methods are EXACTLY §5.1
    (no missing contract route, no leaked extra agent-facing route)."""
    app = create_app()
    spec = app.openapi()
    got: set[tuple[str, str]] = set()
    for path, ops in spec["paths"].items():
        if not path.startswith(API_PREFIX):
            continue
        for method in ops:
            got.add((method.upper(), path))
    assert got == CONTRACT_ROUTES


def test_unauthenticated_requests_are_rejected_without_db():
    """A request with no bearer token is 401'd by the auth dependency before any DB access,
    so this passes even with Postgres down."""
    client = TestClient(create_app())
    assert client.get(f"{API_PREFIX}/world/observe").status_code == 401
    assert (
        client.post(f"{API_PREFIX}/agents/{uuid.uuid4()}/action",
                    json={"tick": 0, "action": {"type": "wait", "params": {}}}).status_code
        == 401
    )
    # Malformed scheme is also rejected.
    assert client.get(
        f"{API_PREFIX}/world/observe", headers={"Authorization": "Basic xyz"}
    ).status_code == 401


def test_select_by_ref_picks_exact_and_latest_relationship():
    """_select_by_ref matches an exact memory_id, and for a relationship ref returns the
    latest belief about that subject."""
    mid = str(uuid.uuid4())
    subj = str(uuid.uuid4())
    entries = [
        {"memory_id": mid, "memory_type": "event", "tick_number": 3, "content": "x"},
        {"memory_id": str(uuid.uuid4()), "memory_type": "relationship",
         "subject_agent_id": subj, "tick_number": 5, "content": "early belief"},
        {"memory_id": str(uuid.uuid4()), "memory_type": "relationship",
         "subject_agent_id": subj, "tick_number": 9, "content": "latest belief"},
    ]
    assert _select_by_ref(entries, f"events#{mid}")["content"] == "x"
    assert _select_by_ref(entries, f"relationships#{subj}")["content"] == "latest belief"
    assert _select_by_ref(entries, "events#" + str(uuid.uuid4())) is None


def test_keyword_filter_is_lexical_case_insensitive():
    """_keyword_filter does a substring scan (no embeddings), case-insensitive, with a regex
    fallback when no substring matches."""
    entries = [
        {"content": "Found an OASIS at (12,40)"},
        {"content": "Traded goods with a stranger"},
        {"content": "Nothing of note"},
    ]
    hits = _keyword_filter(entries, "oasis")
    assert len(hits) == 1 and "OASIS" in hits[0]["content"]
    # regex fallback: digits pattern matches the coordinate entry when no substring hit.
    rx = _keyword_filter(entries, r"\(\d+,\d+\)")
    assert len(rx) == 1
    assert _keyword_filter(entries, "nonexistent") == []


def test_keyword_filter_is_true_regex_with_substring_fallback():
    """_keyword_filter is a regex-first grep (case-insensitive, NO embeddings): alternation and
    cross-string patterns match; an invalid regex falls back to substring and does not raise."""
    entries = [
        {"content": "Refilled at the spring before dawn"},
        {"content": "Hid the water in a hidden cache nearby"},
        {"content": "Nothing of note"},
    ]
    # alternation regex matches the 'spring' entry.
    alt = _keyword_filter(entries, "oasis|spring")
    assert len(alt) == 1 and "spring" in alt[0]["content"]
    # cross-string '.*' regex matches 'water ... cache' within one content string.
    span = _keyword_filter(entries, "water.*cache")
    assert len(span) == 1 and "cache" in span[0]["content"]
    # an invalid regex ('(' is unbalanced) must NOT raise: fall back to substring containment.
    safe = _keyword_filter(entries, "(")
    assert safe == []  # no content contains a literal '(' — substring fallback, no re.error


def test_serialize_entry_builds_ref_for_event_and_relationship():
    """_serialize_entry renders the wire shape and builds the right ref form per type."""
    mid = uuid.uuid4()
    subj = uuid.uuid4()
    ev = _serialize_entry(
        {"memory_id": mid, "memory_type": "event", "tick_number": 2,
         "subject_agent_id": None, "importance": 7, "content": "did a thing"}
    )
    assert ev["ref"] == f"events#{mid}"
    assert ev["content"] == "did a thing"
    rel = _serialize_entry(
        {"memory_id": uuid.uuid4(), "memory_type": "relationship", "tick_number": 4,
         "subject_agent_id": subj, "importance": 6, "content": "trusts me"}
    )
    assert rel["ref"] == f"relationships#{subj}"


# ── DB-backed (skip when Postgres down) ──────────────────────────────────────────────────


def _client() -> TestClient:
    # The app uses the default db pool (settings.database_url). The DB tests below run against
    # whichever DSN is live; the pool picks it up via db.get_pool() with no dsn override.
    return TestClient(live_app)


def _soul() -> dict:
    return SoulFile(
        core_values=["survive"], moral_boundaries=["I will not steal"],
        personality="test", goals=["live"],
    ).model_dump()


@requires_db
def test_register_returns_key_and_locks_soul():
    """POST /register creates the agent, returns a one-time api_key, and the stored
    api_key_hash matches the SHA-256 of that key (plaintext never persisted)."""
    asyncio.run(dal.migrate(DSN))
    client = _client()
    body = RegistrationRequest(name="reg-" + uuid.uuid4().hex[:6], original_soul=SoulFile(**_soul()))
    resp = client.post(f"{API_PREFIX}/agents/register", json=body.model_dump())
    assert resp.status_code == 201
    data = resp.json()
    assert data["api_key"] and data["agent_id"]
    row = asyncio.run(dal.get_agent(data["agent_id"], dsn=DSN))
    assert row is not None
    assert row["original_soul"]["moral_boundaries"] == ["I will not steal"]
    # current_identity starts as a copy of original_soul (Protocol §7.1).
    assert row["current_identity"] == row["original_soul"]


@requires_db
def test_observe_returns_precomputed_row():
    """After a tick resolves, GET /observe returns the precomputed observation packet verbatim
    and marks fetched_at."""
    async def go():
        await dal.migrate(DSN)
        # register via the wire, then seed the agent's spawn cell + an action and resolve tick 0.
        client = _client()
        body = RegistrationRequest(name="obs-" + uuid.uuid4().hex[:6], original_soul=SoulFile(**_soul()))
        r = client.post(f"{API_PREFIX}/agents/register", json=body.model_dump())
        data = r.json()
        aid, key = data["agent_id"], data["api_key"]
        # place the agent somewhere with a cell + give it water so it survives the tick.
        await dal.upsert_cell(x=5, y=5, terrain="oasis", water=20, food=0, goods=0, dsn=DSN)
        async with db.connection(DSN) as conn:
            await conn.execute(
                "UPDATE agents SET position_x=5, position_y=5, resources=$2::jsonb WHERE agent_id=$1",
                uuid.UUID(aid),
                '{"water": 30, "food": 5, "goods": 0, "stance": "neutral"}',
            )
        tick = 500000 + int(uuid.uuid4().int % 100000)
        await dal.insert_action(agent_id=aid, tick_number=tick, action_type="wait", params={}, dsn=DSN)
        import random
        async with db.connection(DSN) as conn:
            await __import__("mircoverse.resolution", fromlist=["resolve_tick"]).resolve_tick(
                conn, tick, random.Random(1)
            )
        # The observation for tick+1 is now precomputed; pull it.
        resp = client.get(f"{API_PREFIX}/world/observe", headers={"Authorization": f"Bearer {key}"})
        assert resp.status_code == 200
        obs = resp.json()
        assert obs["tick"] == tick + 1
        assert obs["self"]["agent_id"] == aid
        # fetched_at was stamped.
        async with db.connection(DSN) as conn:
            fetched = await conn.fetchval(
                "SELECT fetched_at FROM agent_tick_results WHERE agent_id=$1 AND tick_number=$2",
                uuid.UUID(aid), tick + 1,
            )
        assert fetched is not None
    asyncio.run(go())


@requires_db
def test_action_one_per_tick_then_429():
    """The first POST /action for (agent, tick) is accepted; a second is rejected 429
    (Protocol §5.3). The optional memory_update is persisted on the accepted write."""
    async def go():
        await dal.migrate(DSN)
        client = _client()
        body = RegistrationRequest(name="act-" + uuid.uuid4().hex[:6], original_soul=SoulFile(**_soul()))
        data = client.post(f"{API_PREFIX}/agents/register", json=body.model_dump()).json()
        aid, key = data["agent_id"], data["api_key"]
        h = {"Authorization": f"Bearer {key}"}
        tick = 600000 + int(uuid.uuid4().int % 100000)
        envelope = {
            "tick": tick,
            "action": {"type": "scavenge", "params": {}},
            "memory_update": {"file": "events", "op": "append", "importance": 8,
                              "content": "Looted a cache."},
            "intention": "Grab the cache, then retreat to the oasis.",
            "rationale": "water low",
        }
        first = client.post(f"{API_PREFIX}/agents/{aid}/action", json=envelope, headers=h)
        assert first.status_code == 202
        second = client.post(f"{API_PREFIX}/agents/{aid}/action", json=envelope, headers=h)
        assert second.status_code == 429
        # The memory delta from the accepted action is persisted exactly once.
        rows = await dal.get_memory_file(aid, "events", dsn=DSN)
        assert len([e for e in rows if e["content"] == "Looted a cache."]) == 1
        # The optional intention rides the envelope into action_log (Protocol §4.2 / §9.5).
        async with db.connection(DSN) as conn:
            logged = await conn.fetchval(
                "SELECT intention FROM action_log WHERE agent_id=$1 AND tick_number=$2",
                uuid.UUID(aid), tick,
            )
        assert logged == "Grab the cache, then retreat to the oasis."
    asyncio.run(go())


@requires_db
def test_action_rejects_foreign_agent_id():
    """A token may only act for its own agent_id — a mismatched path id is 403."""
    async def go():
        await dal.migrate(DSN)
        client = _client()
        data = client.post(
            f"{API_PREFIX}/agents/register",
            json=RegistrationRequest(name="fa-" + uuid.uuid4().hex[:6],
                                     original_soul=SoulFile(**_soul())).model_dump(),
        ).json()
        key = data["api_key"]
        other = str(uuid.uuid4())
        resp = client.post(
            f"{API_PREFIX}/agents/{other}/action",
            json={"tick": 1, "action": {"type": "wait", "params": {}}},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert resp.status_code == 403
    asyncio.run(go())


@requires_db
def test_reflection_updates_identity_and_snapshots():
    """POST /reflection is never gated: it writes current_identity and an identity_snapshots
    row with trigger=agent_revision, while original_soul stays immutable."""
    async def go():
        await dal.migrate(DSN)
        client = _client()
        data = client.post(
            f"{API_PREFIX}/agents/register",
            json=RegistrationRequest(name="ref-" + uuid.uuid4().hex[:6],
                                     original_soul=SoulFile(**_soul())).model_dump(),
        ).json()
        aid, key = data["agent_id"], data["api_key"]
        new_identity = SoulFile(
            core_values=["survive at any cost"], moral_boundaries=[],
            personality="hardened", goals=["live"],
        )
        resp = client.post(
            f"{API_PREFIX}/agents/{aid}/reflection",
            json={"tick": 12, "current_identity": new_identity.model_dump(),
                  "reflection_note": "I have changed."},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert resp.status_code == 200
        row = await dal.get_agent(aid, dsn=DSN)
        assert row["current_identity"]["personality"] == "hardened"
        assert row["original_soul"]["personality"] == "test"  # immutable
        hist = await dal.get_drift_history(aid, dsn=DSN)
        assert any(s["trigger"] == "agent_revision" for s in hist)
    asyncio.run(go())


@requires_db
def test_memory_pull_full_ref_and_keyword():
    """GET /memory/{file} returns the full file, ?ref=<entry> returns one entry, and ?q=<kw>
    does a lexical keyword scan."""
    async def go():
        await dal.migrate(DSN)
        client = _client()
        data = client.post(
            f"{API_PREFIX}/agents/register",
            json=RegistrationRequest(name="mem-" + uuid.uuid4().hex[:6],
                                     original_soul=SoulFile(**_soul())).model_dump(),
        ).json()
        aid, key = data["agent_id"], data["api_key"]
        h = {"Authorization": f"Bearer {key}"}
        from mircoverse.contracts import MemoryUpdate, MemoryFile, MemoryOp
        mid_a = await dal.write_memory_delta(
            agent_id=aid, tick_number=1,
            update=MemoryUpdate(file=MemoryFile.EVENTS, op=MemoryOp.APPEND, importance=9,
                                content="Found an oasis at (12,40)."), dsn=DSN)
        await dal.write_memory_delta(
            agent_id=aid, tick_number=2,
            update=MemoryUpdate(file=MemoryFile.EVENTS, op=MemoryOp.APPEND, importance=3,
                                content="Walked across the desert."), dsn=DSN)
        # full file
        full = client.get(f"{API_PREFIX}/agents/{aid}/memory/events", headers=h).json()
        assert len(full["entries"]) == 2
        # by ref
        one = client.get(f"{API_PREFIX}/agents/{aid}/memory/events",
                         params={"ref": f"events#{mid_a}"}, headers=h).json()
        assert one["content"] == "Found an oasis at (12,40)."
        # keyword
        kw = client.get(f"{API_PREFIX}/agents/{aid}/memory/events",
                        params={"q": "oasis"}, headers=h).json()
        assert len(kw["entries"]) == 1 and "oasis" in kw["entries"][0]["content"]
        # unknown file -> 404
        assert client.get(f"{API_PREFIX}/agents/{aid}/memory/bogus", headers=h).status_code == 404
    asyncio.run(go())


@requires_db
def test_simulation_status_reports_tick_and_window():
    """GET /simulation/status reports the current tick and window state (no auth, §5.3)."""
    async def go():
        await dal.migrate(DSN)
        await dal.set_simulation_state(status="running", current_tick=7, dsn=DSN)
        from datetime import datetime, timezone, timedelta
        await dal.open_tick(
            tick_number=7, active_agent_count=3,
            tick_ends_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=30),
            dsn=DSN,
        )
        client = _client()
        resp = client.get(f"{API_PREFIX}/simulation/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_tick"] == 7
        assert body["window_open"] is True
        assert body["tick_ends_at"] is not None
    asyncio.run(go())


@requires_db
def test_admin_tick_driver_resolves_and_advances():
    """The admin tick driver resolves the current tick via resolve_tick and advances the sim,
    standing in for the wall-clock loop in tests."""
    async def go():
        await dal.migrate(DSN)
        client = _client()
        data = client.post(
            f"{API_PREFIX}/agents/register",
            json=RegistrationRequest(name="drv-" + uuid.uuid4().hex[:6],
                                     original_soul=SoulFile(**_soul())).model_dump(),
        ).json()
        aid = data["agent_id"]
        await dal.upsert_cell(x=8, y=8, terrain="oasis", water=20, food=0, goods=0, dsn=DSN)
        async with db.connection(DSN) as conn:
            await conn.execute(
                "UPDATE agents SET position_x=8, position_y=8, resources=$2::jsonb WHERE agent_id=$1",
                uuid.UUID(aid),
                '{"water": 30, "food": 5, "goods": 0, "stance": "neutral"}',
            )
        tick = 700000 + int(uuid.uuid4().int % 100000)
        resp = client.post("/admin/tick", params={"tick": tick, "seed": 3})
        assert resp.status_code == 200
        out = resp.json()
        assert out["resolved_tick"] == tick
        assert out["next_tick"] == tick + 1
        # next tick's window is open after the driver ran.
        state = await dal.get_tick_state(tick + 1, dsn=DSN)
        assert state["window_open"] is True
    asyncio.run(go())
