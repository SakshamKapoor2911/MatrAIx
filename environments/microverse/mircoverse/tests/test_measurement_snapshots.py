"""Tests for engine measurement (mircoverse/measurement/snapshots.py).

Pure tests (cosine helper, text flattening, the tripwire's degrade-to-None / stub paths)
always run with NO model and NO database. DB-backed tests are marked `requires_db` and
SKIP cleanly when Postgres is unreachable — they never fail for lack of a database.

The cosine helper is exercised with hand-supplied vectors only (no embedding model), per
the build brief: the tripwire is optional and must never be a hard dependency.
"""

from __future__ import annotations

import asyncio
import math
import uuid

import pytest

from mircoverse.contracts import SoulFile
from mircoverse.measurement import snapshots
from mircoverse.persistence import dal, db
from mircoverse.tests.conftest import requires_db

from mircoverse.config import settings


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


# ── pure: cosine_distance (hand-supplied vectors, no model) ───────────────────────────

def test_cosine_distance():
    """Identical vectors → 0; orthogonal → 1; opposite → 2; zero-vector → 0; mismatch raises."""
    assert snapshots.cosine_distance([1.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)
    assert snapshots.cosine_distance([2.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)  # scale-invariant
    assert snapshots.cosine_distance([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0)
    assert snapshots.cosine_distance([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(2.0)
    # 45° between them → similarity cos(45°)=√2/2 → distance 1 − √2/2.
    assert snapshots.cosine_distance([1.0, 0.0], [1.0, 1.0]) == pytest.approx(
        1.0 - math.sqrt(2) / 2
    )
    assert snapshots.cosine_distance([0.0, 0.0], [1.0, 1.0]) == 0.0  # degenerate zero vector
    with pytest.raises(ValueError):
        snapshots.cosine_distance([1.0, 0.0], [1.0])


# ── pure: soul_to_text ────────────────────────────────────────────────────────────────

def test_soul_to_text():
    """Flattens dict/JSON-string identities to a stable ordered blob; non-dict passthrough."""
    text = snapshots.soul_to_text(_soul("x").model_dump())
    assert "core_values: value-x" in text
    assert "moral_boundaries: I will not steal" in text
    assert "personality: x" in text
    # JSON string input decodes to the same text as the dict.
    assert snapshots.soul_to_text(_soul("x").model_dump_json()) == text
    # Plain string that is not JSON passes through unchanged.
    assert snapshots.soul_to_text("not json") == "not json"


# ── pure: compute_drift_tripwire (optional embedding — stub & degrade) ────────────────

def test_compute_drift_tripwire():
    """No backend → None (degrade, never fail); a hand-supplied stub embed_fn → a distance.

    Confirms the tripwire is OPTIONAL: with the default backend absent it returns None, and
    with a deterministic stub the orthogonal souls produce a non-trivial cosine distance.
    """
    # No backend available and none injected → degrade to None.
    assert snapshots.compute_drift_tripwire(_soul("a").model_dump(),
                                            _soul("b").model_dump(),
                                            embed_fn=None) is None

    # Deterministic stub: map each soul text to an orthogonal basis vector.
    def stub(text: str) -> list[float]:
        return [1.0, 0.0] if "value-a" in text else [0.0, 1.0]

    same = snapshots.compute_drift_tripwire(
        _soul("a").model_dump(), _soul("a").model_dump(), embed_fn=stub
    )
    assert same == pytest.approx(0.0)
    drifted = snapshots.compute_drift_tripwire(
        _soul("a").model_dump(), _soul("b").model_dump(), embed_fn=stub
    )
    assert drifted == pytest.approx(1.0)

    # A stub that raises must degrade to None, never propagate.
    def boom(text: str) -> list[float]:
        raise RuntimeError("embedding backend down")

    assert snapshots.compute_drift_tripwire(
        _soul("a").model_dump(), _soul("b").model_dump(), embed_fn=boom
    ) is None


# ── DB-backed: cadence + forced_end (skip when Postgres down) ─────────────────────────

@requires_db
def test_take_measurement_snapshot_cadence():
    """Snapshots active agents only when tick_n % N == 0, with trigger=engine_measurement.

    Off-cadence ticks write nothing; on-cadence writes one engine_measurement snapshot per
    active agent holding the current current_identity. drift_score is NULL with no backend.
    """
    async def go():
        await dal.migrate(DSN)
        aid = await dal.register_agent(
            soul=_soul("cad"),
            display_name="cad",
            api_key_hash="hash_" + uuid.uuid4().hex,
            position=(1, 1),
            resources={"water": 50, "food": 5, "goods": 0},
            dsn=DSN,
        )
        async with db.connection(DSN) as conn:
            # Off-cadence: 7 % 10 != 0 → no write.
            assert await snapshots.take_measurement_snapshot(conn, 7, 10) == []
            before = await dal.get_drift_history(aid, dsn=DSN)
            assert all(s["trigger"] != "engine_measurement" for s in before)

            # On-cadence: 10 % 10 == 0 → exactly one engine_measurement snapshot for our agent.
            written = await snapshots.take_measurement_snapshot(conn, 10, 10)
            assert len(written) >= 1

        history = await dal.get_drift_history(aid, dsn=DSN)
        mine = [s for s in history if s["trigger"] == "engine_measurement"
                and s["tick_number"] == 10]
        assert len(mine) == 1
        assert mine[0]["identity_json"] == _soul("cad").model_dump()
        assert mine[0]["drift_score"] is None  # no embedding backend → NULL tripwire

    asyncio.run(go())


@requires_db
def test_take_forced_end_snapshot_includes_dead():
    """forced_end snapshots EVERY agent regardless of status (survivor-bias mitigation §10.3)."""
    async def go():
        await dal.migrate(DSN)
        dead_id = await dal.register_agent(
            soul=_soul("dead"),
            display_name="dead",
            api_key_hash="hash_" + uuid.uuid4().hex,
            position=(2, 2),
            resources={"water": 0, "food": 0, "goods": 0},
            status="dead",
            dsn=DSN,
        )
        active_id = await dal.register_agent(
            soul=_soul("alive"),
            display_name="alive",
            api_key_hash="hash_" + uuid.uuid4().hex,
            position=(3, 3),
            resources={"water": 40, "food": 5, "goods": 0},
            status="active",
            dsn=DSN,
        )
        async with db.connection(DSN) as conn:
            written = await snapshots.take_forced_end_snapshot(conn, 999)
            assert len(written) >= 2  # at least our dead + active agent

        for aid in (dead_id, active_id):
            history = await dal.get_drift_history(aid, dsn=DSN)
            forced = [s for s in history
                      if s["trigger"] == "forced_end" and s["tick_number"] == 999]
            assert len(forced) == 1, f"agent {aid} missing forced_end snapshot"

    asyncio.run(go())
