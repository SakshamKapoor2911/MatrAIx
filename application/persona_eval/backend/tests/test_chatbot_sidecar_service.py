"""Tests for chatbot sidecar health + start helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.service import chatbot_sidecar_service as svc


def test_resolve_health_url_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHATBOT_API_URL", raising=False)
    assert svc.resolve_health_url("recai") == "http://127.0.0.1:8000"
    assert svc.resolve_health_url("finance_openbb") == "http://127.0.0.1:8901"
    assert svc.resolve_health_url("medical_assistant") == "http://127.0.0.1:8902"


def test_sidecar_status_unknown_application() -> None:
    with pytest.raises(ValueError, match="unknown chatbot application"):
        svc.sidecar_status("not_real")


def test_list_sidecar_statuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(svc, "sidecar_reachable", lambda _url, timeout=1.5: True)
    statuses = svc.list_sidecar_statuses()
    assert {item["applicationId"] for item in statuses} == {
        "recai",
        "finance_openbb",
        "medical_assistant",
    }
    assert all(item["ok"] for item in statuses)


def test_start_sidecar_runs_compose_for_sidecar_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    compose_dir = tmp_path / "compose"
    compose_dir.mkdir()
    (compose_dir / "docker-compose.yaml").write_text(
        "services:\n  main:\n    depends_on: [rec-agent-api]\n  rec-agent-api:\n    build: .\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        svc,
        "_SIDECAR_SPECS",
        {
            "recai": svc.SidecarSpec(
                application_id="recai",
                compose_dir=str(compose_dir.relative_to(tmp_path)),
                service_name="rec-agent-api",
                build_context="recommender-api",
                host_port=8000,
                primary_env="CHATBOT_API_URL",
            )
        },
    )
    monkeypatch.setattr(svc, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(svc, "sidecar_reachable", lambda _url, timeout=1.5: True)

    captured: dict[str, list[str]] = {}

    def fake_run(command, **kwargs):  # noqa: ANN001
        captured["command"] = list(command)
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(svc.subprocess, "run", fake_run)
    result = svc.start_sidecar("recai", repo_root=tmp_path)
    assert result["ok"] is True
    assert captured["command"][-1] == "rec-agent-api"
    assert "main" not in captured["command"]
