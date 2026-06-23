"""Tests for :mod:`backend.service.session`.

Covers :class:`RecBotSession` (request building, a blocking turn via the fake
backend, in-memory state updates, (de)serialization) and
:class:`SessionManager` (create/get/list, config patching + cache-invalidation
reporting, the async-job turn flow, error surfacing, and persistence).

All turns go through the fake ``recbot.interecagent_bridge.run_turn`` installed
by ``conftest`` — no RecAI / numpy / network involved.
"""

from __future__ import annotations

import time

import pytest

from backend.service.jobs import TERMINAL_STATES
from backend.service.session import ChatTurn, RecBotSession, SessionManager


def _wait_for_job(manager: SessionManager, job_id: str, timeout: float = 10.0):
    """Poll a job until it reaches a terminal state; return its view."""
    deadline = time.monotonic() + timeout
    view = manager.get_job(job_id)
    while time.monotonic() < deadline:
        view = manager.get_job(job_id)
        if view is not None and view["status"] in TERMINAL_STATES:
            return view
        time.sleep(0.01)
    return view


# --------------------------------------------------------------------------- #
# RecBotSession
# --------------------------------------------------------------------------- #
def test_build_request_includes_history_and_new_message(catalog, config_manager):
    session = RecBotSession(
        id="ses_1",
        title="t",
        config=config_manager.normalize(None),
        catalog=catalog,
        config_manager=config_manager,
        messages=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}],
    )
    request = session.build_request("recommend something")
    # The new user turn is appended after the existing history.
    assert request.messages[-1] == {"role": "user", "content": "recommend something"}
    assert len(request.messages) == 3
    assert request.conversation_id == "ses_1"


def test_run_turn_sync_updates_in_memory_state(catalog, config_manager):
    session = RecBotSession(
        id="ses_2",
        title="t",
        config=config_manager.normalize(None),
        catalog=catalog,
        config_manager=config_manager,
    )
    view = session.run_turn_sync("recommend sci-fi")

    # The view is the TraceView shape.
    assert view["userMessage"] == "recommend sci-fi"
    assert view["assistantMessage"] == "Here are a couple of films you might enjoy."
    # The fake recommends cmu:1 (resolvable) + cmu:unknown.
    rec_ids = [it["itemId"] for it in view["recommendedItems"]]
    assert rec_ids == ["cmu:1", "cmu:unknown"]
    assert view["recommendedItems"][0]["title"] == "Blade Runner"
    assert isinstance(view["durationSeconds"], float)

    # In-memory conversation state grew by user + assistant; the turn is stored.
    assert [m["role"] for m in session.messages] == ["user", "assistant"]
    assert session.messages[0]["content"] == "recommend sci-fi"
    assert len(session.turns) == 1
    assert session.turns[0] is view


def test_run_turn_alias(catalog, config_manager):
    session = RecBotSession(
        id="ses_alias",
        title="t",
        config=config_manager.normalize(None),
        catalog=catalog,
        config_manager=config_manager,
    )
    # run_turn is documented as an alias of run_turn_sync.
    view = session.run_turn("hello")
    assert view["userMessage"] == "hello"
    assert len(session.turns) == 1


def test_run_turn_uses_patched_run_turn(catalog, config_manager, set_run_turn):
    from backend.tests.conftest import ChatMessage, RecBotTrace, RecBotTurnResult

    def custom(request):
        return RecBotTurnResult(
            turn_id="custom-turn",
            assistant_message=ChatMessage("assistant", "custom answer"),
            trace=RecBotTrace(recommended_item_ids=[]),
        )

    set_run_turn(custom)
    session = RecBotSession(
        id="ses_custom",
        title="t",
        config=config_manager.normalize(None),
        catalog=catalog,
        config_manager=config_manager,
    )
    view = session.run_turn_sync("anything")
    assert view["turnId"] == "custom-turn"
    assert view["assistantMessage"] == "custom answer"
    assert view["recommendedItems"] == []


def test_run_turn_sync_uses_in_process_bridge(catalog, config_manager, set_run_turn):
    """The turn runs in-process via the bridge's ``run_turn`` (no demo or
    external-subprocess mode exists anymore)."""
    calls = []

    def spy(request):
        calls.append(request)
        from backend.tests.conftest import ChatMessage, RecBotTrace, RecBotTurnResult

        return RecBotTurnResult(
            turn_id="in-proc",
            assistant_message=ChatMessage("assistant", "in-process answer"),
            trace=RecBotTrace(recommended_item_ids=[]),
        )

    set_run_turn(spy)
    session = RecBotSession(
        id="ses_inproc",
        title="t",
        config=config_manager.normalize(None),
        catalog=catalog,
        config_manager=config_manager,
    )
    view = session.run_turn_sync("recommend something")

    # The in-process bridge callable was invoked exactly once with the request.
    assert len(calls) == 1
    assert view["turnId"] == "in-proc"
    assert view["assistantMessage"] == "in-process answer"


def test_session_to_dict_and_from_dict_roundtrip(catalog, config_manager):
    session = RecBotSession(
        id="ses_rt",
        title="Round Trip",
        config=config_manager.normalize({"engine": "gpt-4o"}),
        catalog=catalog,
        config_manager=config_manager,
    )
    session.run_turn_sync("hi")
    data = session.to_dict()
    assert set(data.keys()) >= {"id", "title", "config", "messages", "turns", "createdAt"}

    restored = RecBotSession.from_dict(data, catalog=catalog, config_manager=config_manager)
    assert restored.id == "ses_rt"
    assert restored.title == "Round Trip"
    assert restored.config["engine"] == "gpt-4o"
    assert len(restored.turns) == 1
    assert len(restored.messages) == 2


def test_from_dict_coerces_legacy_turn_shape(catalog, config_manager):
    """Legacy persisted turns (int ``turnId``, missing collections) are coerced.

    Mirrors the ``GET /api/sessions/{id}`` regression at the service layer: a
    session restored from a legacy artifact must carry a string ``turnId`` and
    default ``plan`` / ``recommendedItems`` lists so it re-serializes clean.
    """
    legacy = {
        "id": "ses_legacy_unit",
        "title": "Legacy",
        "config": {"engine": "gpt-4o-mini", "matraixCatalog": "cmu"},
        "messages": [{"role": "user", "content": "hi"}],
        "turns": [{"turnId": 3, "userMessage": "hi", "assistantMessage": "yo"}],
        "createdAt": "2026-01-01T00:00:00Z",
    }
    restored = RecBotSession.from_dict(
        legacy, catalog=catalog, config_manager=config_manager
    )
    turn = restored.turns[0]
    assert turn["turnId"] == "3"
    assert turn["plan"] == []
    assert turn["recommendedItems"] == []
    # Old config keys survive (config is an open dict).
    assert restored.config["matraixCatalog"] == "cmu"


def test_session_summary_counts(catalog, config_manager):
    session = RecBotSession(
        id="ses_sum",
        title="Sum",
        config=config_manager.normalize(None),
        catalog=catalog,
        config_manager=config_manager,
    )
    session.run_turn_sync("a")
    summary = session.summary()
    assert summary["id"] == "ses_sum"
    assert summary["turnCount"] == 1
    assert summary["messageCount"] == 2


def test_chatturn_from_view_roundtrip():
    view = {
        "userMessage": "q",
        "assistantMessage": "a",
        "turnId": "t9",
        "durationSeconds": 1.5,
    }
    turn = ChatTurn.from_view(view)
    assert turn.user_message == "q"
    assert turn.assistant_message == "a"
    assert turn.turn_id == "t9"
    assert turn.duration_seconds == 1.5
    # to_dict returns the view dict.
    assert turn.to_dict() == view


# --------------------------------------------------------------------------- #
# SessionManager
# --------------------------------------------------------------------------- #
def test_manager_create_normalizes_config_and_persists(manager, store):
    session = manager.create(title="My Session", config={"engine": "gpt-4o"})
    assert session.id.startswith("ses_")
    assert session.title == "My Session"
    # normalize fills defaults for unspecified keys.
    assert session.config["engine"] == "gpt-4o"
    assert session.config["domain"] == "movie"
    # Persisted to the (isolated) store.
    assert store.load(session.id) is not None


def test_manager_create_default_title(manager):
    session = manager.create(title="   ", config=None)
    assert session.title == "New session"


def test_manager_get_unknown_returns_none(manager):
    assert manager.get("ses_missing") is None


def test_manager_get_loads_from_disk(manager, store, catalog, config_manager):
    session = manager.create(title="Persisted", config=None)
    sid = session.id

    # A fresh manager (cold) must rehydrate the session from disk.
    fresh = SessionManager(catalog=catalog, store=store, config_manager=config_manager)
    try:
        loaded = fresh.get(sid)
        assert loaded is not None
        assert loaded.id == sid
        assert loaded.title == "Persisted"
    finally:
        fresh.shutdown()


def test_manager_list_includes_disk_and_memory(manager):
    a = manager.create(title="A")
    b = manager.create(title="B")
    ids = {s["id"] for s in manager.list()}
    assert {a.id, b.id} <= ids


def test_patch_config_engine_invalidates_cache(manager):
    session = manager.create(config={"engine": "gpt-4o-mini"})
    result = manager.patch_config(session.id, {"engine": "gpt-4o"})
    assert result is not None
    assert result["cacheInvalidated"] is True
    assert result["session"].config["engine"] == "gpt-4o"


def test_patch_config_bottype_invalidates_cache(manager):
    # botType is part of the bridge's agent cache key, so changing it forces a
    # rebuild (cold start) on the next turn — the API reports cacheInvalidated.
    session = manager.create(config={"botType": "chat"})
    result = manager.patch_config(session.id, {"botType": "completion"})
    assert result["cacheInvalidated"] is True
    assert result["session"].config["botType"] == "completion"


def test_patch_config_unknown_session(manager):
    assert manager.patch_config("ses_missing", {"engine": "gpt-4o"}) is None


def test_patch_config_invalid_value_raises(manager):
    from backend.service.config import ConfigError

    session = manager.create()
    with pytest.raises(ConfigError):
        manager.patch_config(session.id, {"engine": "not-a-model"})


def test_submit_turn_runs_to_done(manager):
    session = manager.create()
    job_id = manager.submit_turn(session.id, "recommend something good")
    assert job_id.startswith("job_")

    view = _wait_for_job(manager, job_id)
    assert view is not None
    assert view["status"] == "done"
    assert view["error"] is None
    turn = view["turn"]
    assert turn["assistantMessage"] == "Here are a couple of films you might enjoy."
    # 'result' is a convenience alias for 'turn' on done.
    assert view["result"] == turn

    # The turn was persisted on the session.
    on_disk = manager.store.load(session.id)
    assert len(on_disk["turns"]) == 1


def test_submit_turn_error_surfaces_as_job_error(manager, set_run_turn):
    def boom(request):
        raise RuntimeError("backend exploded")

    set_run_turn(boom)
    session = manager.create()
    job_id = manager.submit_turn(session.id, "trigger failure")

    view = _wait_for_job(manager, job_id)
    assert view["status"] == "error"
    assert view["turn"] is None
    assert "backend exploded" in view["error"]


def test_submit_turn_unknown_session_raises(manager):
    with pytest.raises(KeyError):
        manager.submit_turn("ses_missing", "hi")


def test_submit_turn_empty_message_raises(manager):
    session = manager.create()
    with pytest.raises(ValueError):
        manager.submit_turn(session.id, "   ")


def test_get_job_unknown_returns_none(manager):
    assert manager.get_job("job_missing") is None
