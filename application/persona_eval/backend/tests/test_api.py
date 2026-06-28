"""End-to-end tests for the FastAPI app (:mod:`backend.api.app`).

Drives the real ``create_app`` via a ``TestClient`` with the fake ``recbot``
backend (installed by ``conftest``) and an isolated catalog + session store.
Covers health, preflight, config options, the full session lifecycle, the async
turn/job flow (POST -> poll ``GET /api/jobs/{id}``), export, and catalog search /
item lookup. No RecAI / OpenAI / numpy / network is touched.
"""

from __future__ import annotations

import time
from typing import Any, Dict

import pytest

# Skip the whole module cleanly if FastAPI/pydantic are unavailable in the env
# (the rest of the suite is stdlib-only and still runs).
pytest.importorskip("fastapi")
pytest.importorskip("pydantic")


def _poll_job(client, job_id: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Poll ``GET /api/jobs/{id}`` until the job is terminal; return its body."""
    deadline = time.monotonic() + timeout
    body: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        resp = client.get("/api/jobs/{}".format(job_id))
        assert resp.status_code == 200
        body = resp.json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.02)
    return body


def _create_session(client, **body) -> Dict[str, Any]:
    resp = client.post("/api/sessions", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --------------------------------------------------------------------------- #
# Health / preflight / config
# --------------------------------------------------------------------------- #
def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_preflight_shape(client):
    resp = client.get("/api/preflight")
    assert resp.status_code == 200
    body = resp.json()
    assert "ready" in body and isinstance(body["ready"], bool)
    assert isinstance(body["checks"], list) and body["checks"]
    names = {c["name"] for c in body["checks"]}
    # User-facing check names — readable, never raw env-var names.
    assert "OpenAI credentials" in names
    assert "Catalog" in names
    # Overall, interface-aware coverage — not just the RecAI recommender.
    assert {"OpenBB (finance)", "Medical assistant", "Survey forms", "Web tasks"} <= names
    for check in body["checks"]:
        assert set(check.keys()) >= {"name", "ok", "detail", "group"}


def test_preflight_does_not_leak_env_var_names(client):
    """Checks must read as plain language, not echo raw config/env-var names."""
    body = client.get("/api/preflight").json()
    leaked = ("OPENAI_API_KEY", "INTERECAGENT_ROOT", "INTERECAGENT_CATALOG_PATH")
    for check in body["checks"]:
        for token in leaked:
            assert token not in check["name"]
            assert token not in check["detail"]


def test_interecagent_root_falls_back_to_task_app_path(monkeypatch):
    from backend.api.app import _interecagent_root

    monkeypatch.delenv("INTERECAGENT_ROOT", raising=False)
    root = _interecagent_root().replace("\\", "/")
    expected_suffix = (
        "/application/tasks/recommender-agent_chat_api/environment/recommender-api/recai/InteRecAgent"
    )
    assert expected_suffix in root
    assert "/applications/tasks/" not in root


def test_preflight_catalog_check_ok(client):
    # The app is built over the temp catalog, so that check should pass.
    body = client.get("/api/preflight").json()
    catalog_check = next(c for c in body["checks"] if c["name"] == "Catalog")
    assert catalog_check["ok"] is True
    assert "items" in catalog_check["detail"]


class _FakeOkResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def getcode(self):
        return 200


def test_sidecar_reachable_true_on_2xx(monkeypatch):
    from backend.api import app as appmod

    monkeypatch.setattr(appmod.urllib.request, "urlopen", lambda req, timeout=0: _FakeOkResponse())
    assert appmod._sidecar_reachable("http://sidecar.test:8902") is True


def test_sidecar_reachable_false_when_unreachable(monkeypatch):
    from backend.api import app as appmod

    def _boom(req, timeout=0):
        raise OSError("connection refused")

    monkeypatch.setattr(appmod.urllib.request, "urlopen", _boom)
    assert appmod._sidecar_reachable("http://sidecar.test:8902") is False


def test_preflight_marks_down_sidecars_optional(client, monkeypatch):
    from backend.api import app as appmod

    monkeypatch.setattr(appmod, "_sidecar_reachable", lambda url, timeout=1.5: False)
    body = client.get("/api/preflight").json()
    by_name = {c["name"]: c for c in body["checks"]}
    for name in ("OpenBB (finance)", "Medical assistant"):
        assert by_name[name]["ok"] is False
        assert by_name[name]["optional"] is True
        assert "not running" in by_name[name]["detail"]
    # Optional sidecars never gate overall readiness.
    assert body["ready"] == all(c["ok"] for c in body["checks"] if not c.get("optional"))


def test_preflight_reachable_sidecar_shows_ok(client, monkeypatch):
    from backend.api import app as appmod

    monkeypatch.setattr(appmod, "_sidecar_reachable", lambda url, timeout=1.5: True)
    body = client.get("/api/preflight").json()
    medical = next(c for c in body["checks"] if c["name"] == "Medical assistant")
    assert medical["ok"] is True
    assert "reachable" in medical["detail"]


def test_preflight_validates_real_resource_bundle(client):
    """The RecAI resources check validates the real native bundle across domains."""
    body = client.get("/api/preflight").json()
    res = next(c for c in body["checks"] if c["name"] == "RecAI resources")
    assert res["group"] == "Chatbot"
    # Collapsed across every supported domain, named in FRIENDLY form in the
    # plain-language detail (no raw tokens like "beauty_product").
    for label in ("Movies", "Beauty products", "Games"):
        assert label in res["detail"]
    assert "beauty_product" not in res["detail"]


def test_config_options(client):
    resp = client.get("/api/config/options")
    assert resp.status_code == 200
    body = resp.json()
    # Enriched shape: editable knobs + full defaults + read-only environment.
    assert set(body.keys()) >= {"knobs", "defaults", "environment"}

    knobs = {k["key"]: k for k in body["knobs"]}
    assert set(knobs.keys()) == {
        "applicationId",
        "engine",
        "personaModel",
        "domain",
        "botType",
    }
    # Each knob carries display metadata + per-value options + rebuild flag.
    engine = knobs["engine"]
    assert engine["label"]
    assert engine["rebuildsAgent"] is True
    engine_values = {o["value"] for o in engine["options"]}
    assert engine_values == {"gpt-4o-mini", "gpt-4o"}
    assert all(o["label"] for o in engine["options"])
    persona_model = knobs["personaModel"]
    assert persona_model["label"]
    assert persona_model["rebuildsAgent"] is False
    persona_model_values = {o["value"] for o in persona_model["options"]}
    assert persona_model_values == {
        "anthropic/claude-haiku-4-5",
        "anthropic/claude-sonnet-4-6",
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
    }

    # defaults remain the full canonical config.
    assert body["defaults"]["engine"] == "gpt-4o-mini"
    assert body["defaults"]["rankerMode"] == "native"

    # environment reports the fixed stack facts.
    assert body["environment"]["resources"] == "adapter-specific resources"
    assert body["environment"]["agent"] == "chatbot application adapter"
    assert body["environment"]["personaModel"] == "anthropic/claude-haiku-4-5"
    assert body["environment"]["scorer"] == "PersonaEval self-report scorer"
    assert "application-specific" in body["environment"]["ranker"]
    assert body["environment"]["promptOwnership"] == {
        "personaSystemPrompt": "Persona prompt from PersonaEval",
        "taskPrompt": "Application-provided chatbot simulation prompt",
    }


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #
def test_create_session_defaults(client):
    session = _create_session(client)
    assert session["id"].startswith("ses_")
    assert session["title"] == "New session"
    assert session["config"]["engine"] == "gpt-4o-mini"
    assert session["config"]["domain"] == "movie"
    assert session["messages"] == []
    assert session["turns"] == []


def test_create_session_with_config(client):
    session = _create_session(client, title="Custom", config={"engine": "gpt-4o"})
    assert session["title"] == "Custom"
    assert session["config"]["engine"] == "gpt-4o"


def test_create_session_invalid_config_422(client):
    resp = client.post("/api/sessions", json={"config": {"engine": "bogus"}})
    assert resp.status_code == 422


def test_list_sessions(client):
    a = _create_session(client, title="A")
    b = _create_session(client, title="B")
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    ids = {s["id"] for s in resp.json()}
    assert {a["id"], b["id"]} <= ids


def test_get_session(client):
    created = _create_session(client, title="Fetch me")
    resp = client.get("/api/sessions/{}".format(created["id"]))
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
    assert resp.json()["title"] == "Fetch me"


def test_get_session_404(client):
    resp = client.get("/api/sessions/ses_missing")
    assert resp.status_code == 404


def test_get_session_legacy_shape_opens_without_500(client, store):
    """Regression: a legacy-shaped persisted session must open, not 500.

    Older artifacts persisted ``turnId`` as an int (the native backend's 0-based
    turn index) and carried removed config keys (``semanticProfile`` /
    ``matraixCatalog``). The response model used to reject the int ``turnId`` with
    a ``string_type`` error, surfacing as a 500. The read path now coerces the
    legacy shape so the session opens with ``turnId`` as a string.
    """
    legacy = {
        "id": "ses_legacy",
        "title": "Legacy session",
        # Old config: removed/renamed keys must not break opening.
        "config": {
            "engine": "gpt-4o-mini",
            "rankerMode": "native",
            "resourceMode": "semantic_profile",
            "domain": "movie",
            "botType": "chat",
            "semanticProfile": "on",
            "matraixCatalog": "cmu",
        },
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ],
        "turns": [
            {
                # turnId persisted as an int (the legacy bug).
                "turnId": 0,
                "userMessage": "hi",
                "assistantMessage": "hello",
                # Plan/recommendedItems omitted (legacy gap) -> must default.
            }
        ],
        "createdAt": "2026-01-01T00:00:00Z",
    }
    store.save(legacy)

    resp = client.get("/api/sessions/ses_legacy")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == "ses_legacy"
    # turnId coerced int -> str.
    assert body["turns"][0]["turnId"] == "0"
    assert body["turns"][0]["plan"] == []
    assert body["turns"][0]["recommendedItems"] == []
    # Old config keys are preserved (config is an open dict), not rejected.
    assert body["config"]["matraixCatalog"] == "cmu"


def test_patch_config_invalidates_cache(client):
    session = _create_session(client, config={"engine": "gpt-4o-mini"})
    resp = client.patch(
        "/api/sessions/{}/config".format(session["id"]),
        json={"config": {"engine": "gpt-4o"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cacheInvalidated"] is True
    assert body["session"]["config"]["engine"] == "gpt-4o"


def test_patch_config_no_cache_invalidation(client):
    # A patch that does not actually change any cache-invalidating key (here a
    # same-value botType write) must not report a rebuild. Every editable knob
    # (engine/domain/botType) now feeds the agent cache key, so the no-op path
    # is what exercises cacheInvalidated == False.
    session = _create_session(client, config={"botType": "chat"})
    resp = client.patch(
        "/api/sessions/{}/config".format(session["id"]),
        json={"config": {"botType": "chat"}},
    )
    assert resp.status_code == 200
    assert resp.json()["cacheInvalidated"] is False


def test_patch_config_bottype_invalidates_cache(client):
    # botType is part of the bridge's agent cache key, so changing it forces a
    # rebuild (cold start) on the next turn.
    session = _create_session(client, config={"botType": "chat"})
    resp = client.patch(
        "/api/sessions/{}/config".format(session["id"]),
        json={"config": {"botType": "completion"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cacheInvalidated"] is True
    assert body["session"]["config"]["botType"] == "completion"


def test_patch_config_404(client):
    resp = client.patch(
        "/api/sessions/ses_missing/config", json={"config": {"engine": "gpt-4o"}}
    )
    assert resp.status_code == 404


def test_patch_config_invalid_value_422(client):
    session = _create_session(client)
    resp = client.patch(
        "/api/sessions/{}/config".format(session["id"]),
        json={"config": {"engine": "nope"}},
    )
    assert resp.status_code == 422


def test_export_session_download_headers(client):
    session = _create_session(client, title="Exportable")
    resp = client.get("/api/sessions/{}/export".format(session["id"]))
    assert resp.status_code == 200
    disposition = resp.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert session["id"] in disposition
    assert resp.json()["id"] == session["id"]


def test_export_session_404(client):
    resp = client.get("/api/sessions/ses_missing/export")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Turns & jobs (async)
# --------------------------------------------------------------------------- #
def test_turn_job_flow_done(client):
    session = _create_session(client)
    resp = client.post(
        "/api/sessions/{}/turns".format(session["id"]),
        json={"message": "recommend a sci-fi film"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["jobId"]
    assert job_id.startswith("job_")

    body = _poll_job(client, job_id)
    assert body["status"] == "done"
    assert body["error"] is None
    turn = body["turn"]
    assert turn["userMessage"] == "recommend a sci-fi film"
    assert turn["assistantMessage"] == "Here are a couple of films you might enjoy."
    rec_ids = [it["itemId"] for it in turn["recommendedItems"]]
    assert rec_ids == ["cmu:1", "cmu:unknown"]
    assert turn["recommendedItems"][0]["title"] == "Blade Runner"

    # The session now reflects the completed turn.
    fetched = client.get("/api/sessions/{}".format(session["id"])).json()
    assert len(fetched["turns"]) == 1
    assert [m["role"] for m in fetched["messages"]] == ["user", "assistant"]


def test_turn_job_flow_error(client, set_run_turn):
    def boom(request):
        raise RuntimeError("kaboom from backend")

    set_run_turn(boom)
    session = _create_session(client)
    resp = client.post(
        "/api/sessions/{}/turns".format(session["id"]),
        json={"message": "cause an error"},
    )
    assert resp.status_code == 200
    body = _poll_job(client, resp.json()["jobId"])
    assert body["status"] == "error"
    assert body["turn"] is None
    assert "kaboom from backend" in body["error"]


def test_submit_turn_404_for_unknown_session(client):
    resp = client.post("/api/sessions/ses_missing/turns", json={"message": "hi"})
    assert resp.status_code == 404


def test_submit_turn_empty_message_422(client):
    session = _create_session(client)
    resp = client.post(
        "/api/sessions/{}/turns".format(session["id"]), json={"message": "   "}
    )
    assert resp.status_code == 422


def test_get_job_404(client):
    resp = client.get("/api/jobs/job_missing")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Catalog
# --------------------------------------------------------------------------- #
def test_catalog_search_default_browse(client):
    resp = client.get("/api/catalog/search")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4
    first = body["items"][0]
    assert first["itemId"] == "cmu:1"
    assert first["title"] == "Blade Runner"
    assert "Sci-Fi" in first["categories"]


def test_catalog_search_query(client):
    body = client.get("/api/catalog/search", params={"q": "noir"}).json()
    ids = {it["itemId"] for it in body["items"]}
    assert ids == {"cmu:1", "cmu:3"}
    assert body["total"] == 2


def test_catalog_search_genre_filter(client):
    body = client.get("/api/catalog/search", params={"genre": "horror"}).json()
    ids = {it["itemId"] for it in body["items"]}
    assert ids == {"cmu:4"}


def test_catalog_search_limit(client):
    body = client.get("/api/catalog/search", params={"limit": 2}).json()
    assert len(body["items"]) == 2
    # total ignores the limit.
    assert body["total"] == 4


def test_catalog_item_lookup(client):
    resp = client.get("/api/catalog/items/cmu:2")
    assert resp.status_code == 200
    item = resp.json()
    assert item["itemId"] == "cmu:2"
    assert item["title"] == "Casablanca"
    assert item["displayText"] == "Casablanca (1942)"
    assert item["metadata"]["release_year"] == 1942


def test_catalog_item_404(client):
    resp = client.get("/api/catalog/items/cmu:nope")
    assert resp.status_code == 404
