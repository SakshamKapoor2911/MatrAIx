"""FastAPI app implementing the NORMATIVE HTTP contract (Protocol.md §5).

The seed-run engine's agent-facing surface. Six endpoints, exactly as §5.1:

    POST /api/v1/agents/register            locks original_soul, returns a one-time api_key
    GET  /api/v1/world/observe              instant read of the precomputed agent_tick_results row
    POST /api/v1/agents/{id}/action         one-per-tick (DB unique constraint → 429 on a second)
    POST /api/v1/agents/{id}/reflection     agent-initiated identity revision, NEVER gated
    GET  /api/v1/agents/{id}/memory/{file}  pull a full memory file (?ref= one entry, ?q= keyword)
    GET  /api/v1/simulation/status          current tick, window open/closed, tick_ends_at

Plus an admin tick driver (POST /admin/tick) and an optional wall-clock asyncio loop, both of
which simply call ``resolution.resolve_tick`` — the engine internals are NOT part of the contract
(§1), so the driver is deliberately thin.

Auth is a per-agent bearer token (§5.1): the SHA-256 of the token is matched against
``agents.api_key_hash``. The plaintext key is shown once, at registration, and never stored.

Everything DB-touching goes through ``mircoverse.persistence`` (the frozen DAL + db pool) or the
resolution orchestrator. This module adds no business logic to the world — it only enforces the
wire contract (auth, one-action-per-tick, never-gated reflection) and serves precomputed rows.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Path as PathParam, Query, Request
from fastapi.responses import JSONResponse

from mircoverse.config import settings
from mircoverse.contracts import (
    ActionEnvelope,
    MemoryFile,
    RegistrationRequest,
    ReflectionRequest,
)
from mircoverse.contracts.identity import RegistrationResponse
from mircoverse.persistence import dal, db
from mircoverse.resolution import resolve_tick
from mircoverse.server import auth

API_PREFIX = "/api/v1"

# The canonical contract endpoints (used by the no-DB OpenAPI test to assert the surface is
# exactly §5.1 — no accidental extra agent-facing route leaks into the spec).
CONTRACT_ROUTES: set[tuple[str, str]] = {
    ("POST", f"{API_PREFIX}/agents/register"),
    ("GET", f"{API_PREFIX}/world/observe"),
    ("POST", f"{API_PREFIX}/agents/{{agent_id}}/action"),
    ("POST", f"{API_PREFIX}/agents/{{agent_id}}/reflection"),
    ("GET", f"{API_PREFIX}/agents/{{agent_id}}/memory/{{file}}"),
    ("GET", f"{API_PREFIX}/simulation/status"),
}


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── auth dependency ────────────────────────────────────────────────────────────────────


async def authenticated_agent(
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Resolve the bearer token to its agent row, or raise 401.

    Hashes the presented token and matches ``agents.api_key_hash`` (auth.hash_api_key). The
    plaintext key is never stored, so a DB read cannot recover it. Returns the decoded agent
    row dict (including agent_id, current_identity, status)."""
    token = auth.parse_bearer(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="missing or malformed bearer token")
    key_hash = auth.hash_api_key(token)
    async with db.connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM agents WHERE api_key_hash = $1", key_hash
        )
    if row is None:
        raise HTTPException(status_code=401, detail="invalid api key")
    d = dict(row)
    d["agent_id"] = str(d["agent_id"])
    for col in ("original_soul", "current_identity", "resources"):
        if isinstance(d.get(col), str):
            d[col] = json.loads(d[col])
    return d


def _require_self(agent: dict[str, Any], agent_id: str) -> None:
    """A token may only act for its own agent_id (path id must match the authenticated row)."""
    if agent["agent_id"] != agent_id:
        raise HTTPException(status_code=403, detail="token does not own this agent_id")


# ── app factory ───────────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Build the FastAPI app. No DB connection is opened at import/build time, so the app
    constructs (and its OpenAPI is inspectable) even with Postgres down — the no-DB test relies
    on this."""
    app = FastAPI(title="MircoVerse Engine", version="1.0.0")

    # ── POST /agents/register ──────────────────────────────────────────────────────────
    @app.post(f"{API_PREFIX}/agents/register", status_code=201)
    async def register(req: RegistrationRequest) -> RegistrationResponse:
        """Submit a persona/soul at T=0. Locks ``original_soul`` (the DB trigger makes it
        immutable thereafter) and ``current_identity`` starts as a copy of it (Protocol.md §7.1).
        Returns the one-time bearer ``api_key`` — only its SHA-256 hash is persisted."""
        api_key = auth.generate_api_key()
        key_hash = auth.hash_api_key(api_key)
        agent_id = str(uuid.uuid4())
        # Spawn at the siphon-adjacent default until the world generator places the agent;
        # the seed-run rollout seeds positions out-of-band. Resources start empty and are set
        # by world generation; register only locks identity + key.
        try:
            await dal.register_agent(
                soul=req.original_soul,
                display_name=req.name,
                api_key_hash=key_hash,
                position=(0, 0),
                resources={"water": 0, "food": 0, "goods": 0, "stance": "neutral"},
                agent_id=agent_id,
                status="active",
            )
        except Exception as exc:  # pragma: no cover - surfaced as 500 with a clean message
            raise HTTPException(status_code=500, detail=f"registration failed: {exc}")
        return RegistrationResponse(agent_id=agent_id, api_key=api_key)

    # ── GET /world/observe ────────────────────────────────────────────────────────────
    @app.get(f"{API_PREFIX}/world/observe")
    async def observe(agent: dict[str, Any] = Depends(authenticated_agent)) -> JSONResponse:
        """Instant read of the agent's precomputed observation for the open tick (§5.2).

        The resolution layer precomputes each live agent's next-tick observation into
        ``agent_tick_results`` (Step 8). This endpoint reads the newest such row for the agent
        and returns the stored ``world_fov`` packet verbatim — never gated, never recomputed.
        Marks ``fetched_at`` so the engine can see who has pulled. 204 if no open observation
        (e.g. a dead agent, or before tick 0 resolved)."""
        agent_id = agent["agent_id"]
        async with db.connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT tick_number, world_fov
                FROM agent_tick_results
                WHERE agent_id = $1
                ORDER BY tick_number DESC
                LIMIT 1
                """,
                uuid.UUID(agent_id),
            )
            if row is None:
                return JSONResponse(status_code=204, content=None)
            await conn.execute(
                """
                UPDATE agent_tick_results SET fetched_at = $3
                WHERE agent_id = $1 AND tick_number = $2
                """,
                uuid.UUID(agent_id),
                row["tick_number"],
                _now_naive(),
            )
        packet = row["world_fov"]
        if isinstance(packet, str):
            packet = json.loads(packet)
        return JSONResponse(content=packet)

    # ── POST /agents/{id}/action ────────────────────────────────────────────────────────
    @app.post(f"{API_PREFIX}/agents/{{agent_id}}/action")
    async def submit_action(
        envelope: ActionEnvelope,
        agent_id: str = PathParam(...),
        agent: dict[str, Any] = Depends(authenticated_agent),
    ) -> JSONResponse:
        """Submit the tick's one action (+ optional memory delta, §4.2).

        One-action-per-tick is the DB unique constraint on ``(agent_id, tick_number)``: the first
        accepted insert wins; a second for the same tick is rejected with **429** (Protocol.md
        §5.3). The optional ``memory_update`` is persisted only when the action is accepted, so a
        rejected duplicate never writes memory. Bumps ``tick_state.submitted_count`` for the
        early-close discipline."""
        _require_self(agent, agent_id)
        action = envelope.action
        params = action.params.model_dump(mode="json") if action.params is not None else {}
        rows = await dal.insert_action(
            agent_id=agent_id,
            tick_number=envelope.tick,
            action_type=action.type.value,
            params=params,
            status="accepted",
            intention=envelope.intention,
        )
        if rows == 0:
            raise HTTPException(
                status_code=429, detail="action already submitted for this tick"
            )
        if envelope.memory_update is not None:
            await dal.write_memory_delta(
                agent_id=agent_id,
                tick_number=envelope.tick,
                update=envelope.memory_update,
            )
        # Best-effort early-close bookkeeping (no-op if the window row is absent).
        try:
            await dal.bump_submitted_count(envelope.tick)
        except Exception:  # pragma: no cover - bookkeeping must never fail the accepted action
            pass
        return JSONResponse(
            status_code=202,
            content={"status": "accepted", "tick": envelope.tick, "action": action.type.value},
        )

    # ── POST /agents/{id}/reflection ─────────────────────────────────────────────────────
    @app.post(f"{API_PREFIX}/agents/{{agent_id}}/reflection")
    async def submit_reflection(
        req: ReflectionRequest,
        agent_id: str = PathParam(...),
        agent: dict[str, Any] = Depends(authenticated_agent),
    ) -> JSONResponse:
        """Agent-initiated identity revision. NEVER gated/forced/scheduled and never blocks
        actions (Protocol.md §5.4). Writes the new ``current_identity`` (the trigger keeps
        ``original_soul`` immutable) and appends an ``identity_snapshots`` row with
        ``trigger='agent_revision'`` — the agent-driven half of the change-vs-measurement split.
        The optional ``reflection_note`` is recorded as a reflections-file memory entry for the
        research log."""
        _require_self(agent, agent_id)
        await dal.update_current_identity(agent_id, req.current_identity)
        await dal.snapshot_identity(
            agent_id=agent_id,
            tick_number=req.tick,
            identity=req.current_identity,
            trigger="agent_revision",
        )
        if req.reflection_note:
            from mircoverse.contracts import MemoryUpdate, MemoryOp

            note = MemoryUpdate(
                file=MemoryFile.REFLECTIONS,
                op=MemoryOp.APPEND,
                importance=8,
                content=req.reflection_note,
            )
            await dal.write_memory_delta(
                agent_id=agent_id, tick_number=req.tick, update=note
            )
        return JSONResponse(
            status_code=200, content={"status": "reflected", "tick": req.tick}
        )

    # ── GET /agents/{id}/memory/{file} ───────────────────────────────────────────────────
    @app.get(f"{API_PREFIX}/agents/{{agent_id}}/memory/{{file}}")
    async def get_memory(
        agent_id: str = PathParam(...),
        file: str = PathParam(...),
        ref: Optional[str] = Query(default=None),
        q: Optional[str] = Query(default=None),
        agent: dict[str, Any] = Depends(authenticated_agent),
    ) -> JSONResponse:
        """Pull a full memory file (events/relationships/reflections), §5.1 / §7.2.

        - bare: return every entry of the file, chronological.
        - ``?ref=events#88``: return only the one entry that ref names (``read_memory``).
        - ``?q=oasis``: keyword/regex substring scan over the file's content (``search_memory`` —
          lexical, NO embeddings, consistent with §6.2).
        An agent may only read its own memory."""
        _require_self(agent, agent_id)
        try:
            file_enum = MemoryFile(file)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"unknown memory file '{file}'")
        entries = await dal.get_memory_file(agent_id, file_enum)

        if ref is not None:
            entry = _select_by_ref(entries, ref)
            if entry is None:
                raise HTTPException(status_code=404, detail=f"no entry for ref '{ref}'")
            return JSONResponse(content=_serialize_entry(entry))

        if q is not None:
            entries = _keyword_filter(entries, q)

        return JSONResponse(
            content={
                "file": file_enum.value,
                "entries": [_serialize_entry(e) for e in entries],
            }
        )

    # ── GET /simulation/status ────────────────────────────────────────────────────────
    @app.get(f"{API_PREFIX}/simulation/status")
    async def simulation_status() -> JSONResponse:
        """Current tick, window open/closed, and ``tick_ends_at`` (§5.1). Never gated, no auth —
        a public read so observers and agents can sync to the server clock (§5.3)."""
        async with db.connection() as conn:
            sim = await conn.fetchrow("SELECT * FROM simulation_state WHERE id = 1")
            current_tick = int(sim["current_tick"]) if sim and sim["current_tick"] is not None else 0
            status = sim["status"] if sim else "registration"
            tick_row = await conn.fetchrow(
                "SELECT * FROM tick_state WHERE tick_number = $1", current_tick
            )
        body: dict[str, Any] = {
            "status": status,
            "current_tick": current_tick,
            "window_open": bool(tick_row["window_open"]) if tick_row else False,
            "tick_ends_at": _iso(tick_row["tick_ends_at"]) if tick_row else None,
        }
        return JSONResponse(content=body)

    # ── admin lifecycle (Architecture.md §Experiment Lifecycle; engine-internal, not §5) ──
    # REGISTRATION → RUNNING → PAUSED → ENDED. The seed run drives ticks via the wall-clock loop
    # (run_tick_loop) or POST /admin/tick; these endpoints set the lifecycle status that the loop
    # and the tick driver respect. NOTE: admin auth is out of scope for the local seed run — on the
    # AWS platform these are IAM/SigV4-gated (Architecture.md §API Authentication).
    @app.post("/admin/simulation/start")
    async def admin_start(seed: int = Query(default=0), scale: int = Query(default=25)) -> JSONResponse:
        """Generate a world (25-agent seed world by default, or an N-agent scale world), bootstrap
        it into the DB (cells + registered agents + tick-0 observations), and open tick 0 with the
        simulation marked RUNNING. Returns the registered roster (agent_id + one-time api_key)."""
        from mircoverse.manifest import gen_seed_world, gen_scale_world
        from mircoverse.resolution import initialize_simulation

        world = gen_seed_world(seed=seed) if scale == 25 else gen_scale_world(n=scale, seed=seed)
        async with db.connection() as conn:
            roster = await initialize_simulation(
                conn, world, tick_interval_seconds=settings.tick_interval_seconds
            )
        return JSONResponse(
            status_code=201,
            content={
                "status": "running",
                "agents": [
                    {"agent_id": r.agent_id, "api_key": r.api_key, "pos": list(r.pos)}
                    for r in roster
                ],
            },
        )

    @app.post("/admin/simulation/pause")
    async def admin_pause() -> JSONResponse:
        """Halt tick advancement after the current tick (the wall-clock loop checks status)."""
        async with db.connection() as conn:
            sim = await conn.fetchrow("SELECT current_tick FROM simulation_state WHERE id = 1")
            tick = int(sim["current_tick"]) if sim and sim["current_tick"] is not None else 0
        await dal.set_simulation_state(status="paused", current_tick=tick)
        return JSONResponse(content={"status": "paused", "current_tick": tick})

    @app.post("/admin/simulation/resume")
    async def admin_resume() -> JSONResponse:
        """Re-enable tick advancement."""
        async with db.connection() as conn:
            sim = await conn.fetchrow("SELECT current_tick FROM simulation_state WHERE id = 1")
            tick = int(sim["current_tick"]) if sim and sim["current_tick"] is not None else 0
        await dal.set_simulation_state(status="running", current_tick=tick)
        return JSONResponse(content={"status": "running", "current_tick": tick})

    @app.post("/admin/simulation/end")
    async def admin_end() -> JSONResponse:
        """End the experiment: take a final forced_end identity snapshot for every active agent
        (the primary research artifact — Architecture.md §Experiment Lifecycle) and mark ENDED."""
        async with db.connection() as conn:
            sim = await conn.fetchrow("SELECT current_tick FROM simulation_state WHERE id = 1")
            tick = int(sim["current_tick"]) if sim and sim["current_tick"] is not None else 0
            rows = await conn.fetch(
                "SELECT agent_id, current_identity FROM agents WHERE status = 'active'"
            )
            for r in rows:
                ident = r["current_identity"]
                if isinstance(ident, str):
                    ident = json.loads(ident)
                await dal.snapshot_identity(
                    agent_id=str(r["agent_id"]),
                    tick_number=tick,
                    identity=ident,
                    trigger="forced_end",
                )
        await dal.set_simulation_state(status="ended", current_tick=tick)
        return JSONResponse(content={"status": "ended", "current_tick": tick, "final_snapshots": len(rows)})

    # ── admin tick driver (engine-internal, NOT part of the §5 contract) ──────────────────
    @app.post("/admin/tick")
    async def admin_tick(
        request: Request,
        tick: Optional[int] = Query(default=None),
        seed: int = Query(default=0),
    ) -> JSONResponse:
        """Drive one tick: resolve ``tick`` (defaults to ``simulation_state.current_tick``) and
        open the next. Thin wrapper over ``resolution.resolve_tick`` so the engine internals stay
        off the contract (§1). Returns the per-agent result statuses."""
        async with db.connection() as conn:
            if tick is None:
                sim = await conn.fetchrow("SELECT current_tick FROM simulation_state WHERE id = 1")
                tick = int(sim["current_tick"]) if sim and sim["current_tick"] is not None else 0
            rng = random.Random(seed + tick)
            results = await resolve_tick(
                conn, tick, rng, tick_interval_seconds=settings.tick_interval_seconds
            )
        return JSONResponse(
            content={
                "resolved_tick": tick,
                "next_tick": tick + 1,
                "results": {aid: r.status for aid, r in results.items()},
            }
        )

    return app


# ── memory helpers (pure, unit-testable) ──────────────────────────────────────────────


def _serialize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Render one agent_memory row into the wire shape returned by GET /memory/{file}."""
    file_of = {"event": "events", "relationship": "relationships", "reflection": "reflections"}
    mtype = entry.get("memory_type", "event")
    file = file_of.get(mtype, "events")
    mid = entry.get("memory_id")
    subj = entry.get("subject_agent_id")
    if mtype == "relationship" and subj is not None:
        ref = f"{file}#{subj}"
    else:
        ref = f"{file}#{mid}"
    return {
        "ref": ref,
        "memory_id": str(mid) if mid is not None else None,
        "tick": entry.get("tick_number"),
        "memory_type": mtype,
        "subject_agent_id": str(subj) if subj is not None else None,
        "importance": entry.get("importance"),
        "content": entry.get("content", ""),
    }


def _select_by_ref(entries: list[dict[str, Any]], ref: str) -> Optional[dict[str, Any]]:
    """Return the single entry a ``ref`` (``<file>#<id-or-subject>``) names, or None.

    For ``relationships#<subject>`` the latest belief about that subject wins; for
    ``<file>#<memory_id>`` it is an exact memory_id match. Pure."""
    key = ref.split("#", 1)[1] if "#" in ref else ref
    is_relationship = ref.startswith("relationships#")
    matches: list[dict[str, Any]] = []
    for e in entries:
        if is_relationship:
            if e.get("subject_agent_id") is not None and str(e["subject_agent_id"]) == key:
                matches.append(e)
        elif e.get("memory_id") is not None and str(e["memory_id"]) == key:
            matches.append(e)
    if not matches:
        return None
    # Latest by tick for a relationship subject; exact id otherwise (single match).
    return max(matches, key=lambda e: e.get("tick_number") or 0)


def _keyword_filter(entries: list[dict[str, Any]], q: str) -> list[dict[str, Any]]:
    """Regex (RE2-style via Python ``re``), case-insensitive, lexical — NO embeddings
    (Protocol.md §7.2). The ``search_memory`` tool's "grep your own notes" scan over each
    entry's content. Falls back to case-insensitive substring containment if ``q`` is not a
    valid regex (so a stray ``(`` from the model never 500s). Pure."""
    try:
        pattern = re.compile(q, re.IGNORECASE)
    except re.error:
        needle = q.lower()
        return [e for e in entries if needle in (e.get("content", "") or "").lower()]
    return [e for e in entries if pattern.search(e.get("content", "") or "")]


def _iso(value: Any) -> Optional[str]:
    """Render a TIMESTAMP column as an ISO8601 string with a trailing Z (agents read this as
    the authoritative ``tick_ends_at``, §5.3)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        s = value.replace(microsecond=0).isoformat()
        return s if (s.endswith("Z") or "+" in s) else s + "Z"
    return str(value)


# ── wall-clock tick driver (optional asyncio loop) ──────────────────────────────────────


async def run_tick_loop(
    *,
    start_tick: int = 0,
    max_ticks: Optional[int] = None,
    seed: int = 0,
    interval_seconds: Optional[float] = None,
) -> None:
    """Drive ticks on the wall clock (Protocol.md §1: a single-process engine + Postgres on a
    wall-clock tick). Each iteration resolves the current tick via ``resolve_tick`` then sleeps
    ``interval_seconds`` (defaults to the configured tick interval). The seeded RNG is derived
    per-tick from ``seed + tick`` so a replay with the same seed is identical (World.md §11).

    This is the local seed-run runtime; the §5 contract is engine-agnostic, so a future platform
    swaps this loop for Step Functions without any agent noticing (§1)."""
    interval = interval_seconds if interval_seconds is not None else settings.tick_interval_seconds
    tick = start_tick
    resolved = 0
    while max_ticks is None or resolved < max_ticks:
        # Respect the lifecycle status (Architecture.md §Experiment Lifecycle): only advance while
        # RUNNING. PAUSED → idle-wait (current tick already completed); ENDED → stop the loop.
        async with db.connection() as conn:
            sim = await conn.fetchrow("SELECT status, current_tick FROM simulation_state WHERE id = 1")
        status = sim["status"] if sim else "running"
        if status == "ended":
            break
        if status == "paused":
            await asyncio.sleep(interval)
            continue
        # Drive the authoritative current tick (so the loop and /admin/tick agree on position).
        tick = int(sim["current_tick"]) if sim and sim["current_tick"] is not None else tick
        async with db.connection() as conn:
            rng = random.Random(seed + tick)
            await resolve_tick(conn, tick, rng, tick_interval_seconds=interval)
        resolved += 1
        await asyncio.sleep(interval)


app = create_app()
