"""Engine-driven identity measurement (World.md §9, §9.3; Architecture.md Step 9b).

This module is the *reflective-layer snapshotter*: independently of any agent, every
``N`` ticks the engine records whatever each agent's ``current_identity`` currently is
into ``identity_snapshots`` with ``trigger='engine_measurement'`` (World.md §9 "uniform,
unbiased longitudinal series"). At experiment end it forces one final snapshot of *every*
agent — alive **and** dead — so terminal analysis is not censored by survivor bias
(World.md §10.3).

It never authors identity and never asks the agent for anything; it only copies the
agent-owned ``current_identity`` verbatim. The engine writes the reflective layer's
*snapshot*, never its *content* (World.md §7).

Cosine distance is computed here as an **online tripwire ONLY** (World.md §9.3): it flags
*that* something shifted and roughly when, and is stored in ``identity_snapshots.drift_score``
— it is never the reported magnitude of moral change (that comes from the offline,
human-validated instrument in §9.1-9.2). The embedding model is therefore an **optional,
operator-borne** dependency: the import is guarded and the tripwire degrades to ``None``
(snapshots still happen) when no embedding backend is installed. There is NEVER a hard
embedding dependency.

These functions operate on a caller-supplied asyncpg ``conn`` (the resolution layer already
holds one inside the tick transaction), so they compose into Step 9b without opening their
own pool.
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

# ── optional embedding backend (tripwire only — never a hard dependency) ───────────────
# Guarded so the whole measurement module imports and runs even with no embedding model
# installed. If you later wire in Bedrock Titan/Cohere (Architecture.md §Drift Measurement),
# expose it as a module-level `embed_text(text) -> list[float]` and the tripwire turns on
# automatically. Until then `_EMBED_FN is None` and `drift_score` is stored as NULL.
try:  # pragma: no cover - exercised only when an embedding backend is present
    from mircoverse.measurement.embedding import embed_text as _EMBED_FN  # type: ignore
except Exception:  # ImportError, or a backend that fails to initialise — degrade silently.
    _EMBED_FN = None


TRIGGER_ENGINE_MEASUREMENT = "engine_measurement"
TRIGGER_FORCED_END = "forced_end"


# ── pure helpers (no DB, no model) ──────────────────────────────────────────────────────

def cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine *distance* (1 − cosine similarity) between two equal-length vectors.

    Pure and deterministic — the unit of the online tripwire (World.md §9.3). Range is
    [0, 2]: 0 == identical direction, 1 == orthogonal, 2 == opposite. A zero-magnitude
    vector has no defined direction, so distance from it is defined as 0.0 (no signal),
    matching "absence of drift evidence" rather than spuriously flagging a tripwire.

    Raises ValueError on a length mismatch — comparing differently-sized embeddings is a
    programming error, not a degrade-to-None condition.
    """
    if len(a) != len(b):
        raise ValueError(f"vector length mismatch: {len(a)} != {len(b)}")
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for av, bv in zip(a, b):
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    similarity = dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
    # Guard against tiny floating-point overshoot outside [-1, 1].
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


def soul_to_text(identity: Any) -> str:
    """Flatten a soul/identity (dict or JSON string) into a single stable text blob for
    embedding. Pure. Field order is fixed so the same identity always embeds identically.
    """
    if isinstance(identity, str):
        try:
            identity = json.loads(identity)
        except (ValueError, TypeError):
            return identity
    if not isinstance(identity, dict):
        return str(identity)
    parts: list[str] = []
    for key in ("core_values", "moral_boundaries", "personality", "goals"):
        value = identity.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            parts.append(f"{key}: " + "; ".join(str(v) for v in value))
        else:
            parts.append(f"{key}: {value}")
    return "\n".join(parts)


def compute_drift_tripwire(
    original_soul: Any,
    current_identity: Any,
    embed_fn: Optional[Any] = None,
) -> Optional[float]:
    """The online cosine tripwire (World.md §9.3) — returns cosine distance between the
    original-soul embedding and the current-identity embedding, or ``None`` when no
    embedding backend is available (degrade, never fail).

    ``embed_fn`` defaults to the module's optional backend; tests pass a stub. This is a
    TRIPWIRE, not the drift metric — it only flags that something moved.
    """
    fn = embed_fn if embed_fn is not None else _EMBED_FN
    if fn is None:
        return None
    try:
        original_vec = fn(soul_to_text(original_soul))
        current_vec = fn(soul_to_text(current_identity))
    except Exception:  # pragma: no cover - any backend failure degrades to no-tripwire.
        return None
    if not original_vec or not current_vec:
        return None
    return cosine_distance(original_vec, current_vec)


# ── DB-backed snapshotters (operate on a caller-supplied asyncpg conn) ────────────────────

def _now() -> datetime:
    """Timezone-naive UTC, matching the schema's bare TIMESTAMP columns (cf. dal._now)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _coerce_jsonb(value: Any) -> Any:
    """asyncpg returns JSONB columns as decoded objects or as JSON text depending on codec
    config; normalise to a Python object so the tripwire and the re-insert both work."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


async def _insert_snapshot(
    conn: Any,
    *,
    agent_id: Any,
    tick_number: int,
    identity_json: Any,
    drift_score: Optional[float],
    trigger: str,
) -> str:
    """Append one identity_snapshots row on the given connection. Returns snapshot_id."""
    sid = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO identity_snapshots
            (snapshot_id, agent_id, tick_number, snapshot_at, identity_json,
             drift_score, trigger)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
        """,
        sid,
        agent_id,
        tick_number,
        _now(),
        json.dumps(identity_json),
        drift_score,
        trigger,
    )
    return str(sid)


async def take_measurement_snapshot(
    conn: Any,
    tick_n: int,
    cadence_N: int,
    *,
    embed_fn: Optional[Any] = None,
) -> list[str]:
    """Step 9b: on cadence, snapshot every ACTIVE agent's ``current_identity``.

    Acts only when ``cadence_N > 0`` and ``tick_n % cadence_N == 0`` (World.md §12: suggest
    every 10 ticks); otherwise returns an empty list without touching the DB. For each
    active agent it copies ``current_identity`` verbatim into ``identity_snapshots`` with
    ``trigger='engine_measurement'`` and stores the optional cosine tripwire as
    ``drift_score`` (NULL when no embedding backend). Returns the list of snapshot_ids
    written (empty on an off-cadence tick).

    The engine is the author of the *snapshot*, never of the *identity* — it only records
    what the agent already is (World.md §7, §9).
    """
    if cadence_N <= 0 or tick_n % cadence_N != 0:
        return []

    rows = await conn.fetch(
        """
        SELECT agent_id, original_soul, current_identity
        FROM agents
        WHERE status = 'active'
        ORDER BY agent_id
        """
    )
    snapshot_ids: list[str] = []
    for row in rows:
        current = _coerce_jsonb(row["current_identity"])
        original = _coerce_jsonb(row["original_soul"])
        drift = compute_drift_tripwire(original, current, embed_fn=embed_fn)
        sid = await _insert_snapshot(
            conn,
            agent_id=row["agent_id"],
            tick_number=tick_n,
            identity_json=current,
            drift_score=drift,
            trigger=TRIGGER_ENGINE_MEASUREMENT,
        )
        snapshot_ids.append(sid)
    return snapshot_ids


async def take_forced_end_snapshot(
    conn: Any,
    tick_n: int,
    *,
    embed_fn: Optional[Any] = None,
) -> list[str]:
    """Experiment-end snapshot of EVERY agent — alive and dead — with ``trigger='forced_end'``.

    Unlike the cadenced measurement, this includes dead/idle agents so the terminal series
    is not conditioned on survival (survivor-bias mitigation, World.md §10.3: "analyze the
    full per-tick trajectory of every agent including the dead"). Runs unconditionally
    (no cadence gate). Returns the list of snapshot_ids written.
    """
    rows = await conn.fetch(
        """
        SELECT agent_id, original_soul, current_identity
        FROM agents
        ORDER BY agent_id
        """
    )
    snapshot_ids: list[str] = []
    for row in rows:
        current = _coerce_jsonb(row["current_identity"])
        original = _coerce_jsonb(row["original_soul"])
        drift = compute_drift_tripwire(original, current, embed_fn=embed_fn)
        sid = await _insert_snapshot(
            conn,
            agent_id=row["agent_id"],
            tick_number=tick_n,
            identity_json=current,
            drift_score=drift,
            trigger=TRIGGER_FORCED_END,
        )
        snapshot_ids.append(sid)
    return snapshot_ids
