"""End-to-end tests for the FastAPI app (:mod:`backend.api.app`).

Covers health, preflight, and config options. No RecAI / OpenAI / numpy /
network is touched.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from backend.service.config import PERSONA_MODEL_OPTIONS


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
    assert "OpenAI credentials" in names
    assert "Anthropic credentials" in names
    assert "DashScope (Qwen / DeepSeek)" in names
    assert {"OpenBB (finance)", "Medical assistant", "Survey forms", "Web tasks", "Docker", "use.computer API"} <= names
    for check in body["checks"]:
        assert set(check.keys()) >= {"name", "ok", "detail", "group"}


def test_preflight_does_not_leak_env_var_names(client):
    body = client.get("/api/preflight").json()
    leaked = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CLAUDE_API_KEY",
        "DASHSCOPE_API_KEY",
        "USE_COMPUTER_API_KEY",
        "INTERECAGENT_ROOT",
        "INTERECAGENT_CATALOG_PATH",
    )
    for check in body["checks"]:
        for token in leaked:
            assert token not in check["name"]
            assert token not in check["detail"]


def test_interecagent_root_falls_back_to_task_app_path(monkeypatch):
    from backend.api.app import _interecagent_root

    monkeypatch.delenv("INTERECAGENT_ROOT", raising=False)
    root = _interecagent_root().replace("\\", "/")
    expected_suffix = (
        "/environment/task-environments/application/shared-chat-api-recommender/recommender-api/recai/InteRecAgent"
    )
    assert expected_suffix in root
    assert "/applications/tasks/" not in root


def test_preflight_dashscope_check_optional(client, monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    body = client.get("/api/preflight").json()
    dashscope = next(c for c in body["checks"] if c["name"] == "DashScope (Qwen / DeepSeek)")
    assert dashscope["ok"] is False
    assert dashscope.get("optional") is True

    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    body = client.get("/api/preflight").json()
    dashscope = next(c for c in body["checks"] if c["name"] == "DashScope (Qwen / DeepSeek)")
    assert dashscope["ok"] is True


def test_preflight_anthropic_check(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    body = client.get("/api/preflight").json()
    anthropic = next(c for c in body["checks"] if c["name"] == "Anthropic credentials")
    assert anthropic["ok"] is False

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    body = client.get("/api/preflight").json()
    anthropic = next(c for c in body["checks"] if c["name"] == "Anthropic credentials")
    assert anthropic["ok"] is True


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
    assert body["ready"] == all(c["ok"] for c in body["checks"] if not c.get("optional"))


def test_preflight_reachable_sidecar_shows_ok(client, monkeypatch):
    from backend.api import app as appmod

    monkeypatch.setattr(appmod, "_sidecar_reachable", lambda url, timeout=1.5: True)
    body = client.get("/api/preflight").json()
    medical = next(c for c in body["checks"] if c["name"] == "Medical assistant")
    assert medical["ok"] is True
    assert "reachable" in medical["detail"]


def test_preflight_recai_resources_optional(client):
    body = client.get("/api/preflight").json()
    res = next(c for c in body["checks"] if c["name"] == "RecAI resources")
    assert res.get("optional") is True


def test_preflight_os_app_checks_optional(client, monkeypatch):
    monkeypatch.delenv("USE_COMPUTER_API_KEY", raising=False)
    body = client.get("/api/preflight").json()
    by_name = {c["name"]: c for c in body["checks"]}
    for name in ("Docker", "use.computer API"):
        assert by_name[name]["optional"] is True
    assert by_name["use.computer API"]["group"] == "OS app"


def test_preflight_validates_real_resource_bundle(client):
    body = client.get("/api/preflight").json()
    res = next(c for c in body["checks"] if c["name"] == "RecAI resources")
    assert res["group"] == "Chatbot"
    for label in ("Movies", "Beauty products", "Games"):
        assert label in res["detail"]
    assert "beauty_product" not in res["detail"]


def test_config_options(client):
    resp = client.get("/api/config/options")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) >= {"knobs", "defaults", "environment"}

    knobs = {k["key"]: k for k in body["knobs"]}
    assert set(knobs.keys()) == {
        "applicationId",
        "engine",
        "personaModel",
        "domain",
        "botType",
    }
    engine = knobs["engine"]
    assert engine["label"]
    assert engine["rebuildsAgent"] is True
    engine_values = {o["value"] for o in engine["options"]}
    assert engine_values == {"gpt-4o-mini", "gpt-4o"}
    persona_model = knobs["personaModel"]
    persona_model_values = {o["value"] for o in persona_model["options"]}
    assert persona_model_values == set(PERSONA_MODEL_OPTIONS)
    assert "dashscope/qwen3.6-plus-2026-04-02" in persona_model_values
    assert "dashscope/deepseek-v4-pro" in persona_model_values

    assert body["defaults"]["engine"] == "gpt-4o-mini"
    assert body["defaults"]["rankerMode"] == "native"
    assert body["environment"]["resources"] == "adapter-specific resources"
    assert body["environment"]["agent"] == "chatbot application adapter"
    assert body["environment"]["personaModel"] == "anthropic/claude-haiku-4-5"
    assert body["environment"]["scorer"] == "Playground self-report scorer"
    assert "application-specific" in body["environment"]["ranker"]
    assert body["environment"]["promptOwnership"] == {
        "personaSystemPrompt": "Persona prompt from Playground",
        "taskPrompt": "Application-provided chatbot simulation prompt",
    }
