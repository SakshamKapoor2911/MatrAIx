"""Probe and start local chatbot HTTP sidecars for PersonaEval cockpit."""

from __future__ import annotations

import os
import re
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from environment.integrations.persona_eval.harbor.persona_eval import _repo_root
from environment.integrations.persona_eval.local.chatbot_eval import _sidecar_base_url


@dataclass(frozen=True)
class SidecarSpec:
    application_id: str
    compose_dir: str
    service_name: str
    build_context: str
    host_port: int
    primary_env: str
    legacy_env: str | None = None


_SIDECAR_SPECS: dict[str, SidecarSpec] = {
    "recai": SidecarSpec(
        application_id="recai",
        compose_dir="environment/task-environments/application/recommender-agent_chat_api",
        service_name="rec-agent-api",
        build_context="recommender-api",
        host_port=8000,
        primary_env="CHATBOT_API_URL",
        legacy_env=None,
    ),
    "finance_openbb": SidecarSpec(
        application_id="finance_openbb",
        compose_dir="environment/task-environments/application/example-chat-mcp_support_chatbot",
        service_name="support-bot",
        build_context="support-bot",
        host_port=8901,
        primary_env="CHATBOT_UPSTREAM_FINANCE",
        legacy_env="FINANCE_CHATBOT_URL",
    ),
    "medical_assistant": SidecarSpec(
        application_id="medical_assistant",
        compose_dir="environment/task-environments/application/example-chat-api_support_chatbot",
        service_name="support-api",
        build_context="support-api",
        host_port=8902,
        primary_env="CHATBOT_UPSTREAM_MEDICAL",
        legacy_env="MEDICAL_CHATBOT_URL",
    ),
}


def _default_health_url(spec: SidecarSpec) -> str:
    return "http://127.0.0.1:{}".format(spec.host_port)


def resolve_health_url(application_id: str) -> str:
    spec = _SIDECAR_SPECS.get(application_id)
    if spec is None:
        raise ValueError("unknown chatbot application: {}".format(application_id))
    if spec.application_id == "recai":
        return (
            os.environ.get(spec.primary_env, "").strip() or _default_health_url(spec)
        )
    return _sidecar_base_url(
        spec.primary_env,
        spec.legacy_env or "",
        _default_health_url(spec),
    )


def sidecar_reachable(base_url: str, *, timeout: float = 1.5) -> bool:
    url = "{}/health".format(base_url.rstrip("/"))
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            return 200 <= int(status) < 300
    except Exception:  # noqa: BLE001
        return False


def _compose_project(application_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", application_id.lower()).strip("-")
    return "persona-eval-{}".format(slug or "chatbot")


def _standalone_compose_path(spec: SidecarSpec, compose_dir: Path) -> Path:
    from environment.integrations.persona_eval.local.chatbot_sidecar_compose import (
        write_standalone_sidecar_compose,
    )

    return write_standalone_sidecar_compose(
        compose_dir=compose_dir,
        service_name=spec.service_name,
        build_context=spec.build_context,
        host_port=spec.host_port,
    )


def sidecar_status(application_id: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    spec = _SIDECAR_SPECS.get(application_id)
    if spec is None:
        raise ValueError("unknown chatbot application: {}".format(application_id))
    health_url = resolve_health_url(application_id)
    ok = sidecar_reachable(health_url)
    return {
        "applicationId": application_id,
        "ok": ok,
        "healthUrl": health_url,
        "canStart": True,
        "detail": (
            "Chat API reachable at {}.".format(health_url)
            if ok
            else "Chat API not reachable at {}.".format(health_url)
        ),
    }


def list_sidecar_statuses(*, repo_root: Path | None = None) -> list[dict[str, Any]]:
    return [sidecar_status(application_id, repo_root=repo_root) for application_id in _SIDECAR_SPECS]


def start_sidecar(application_id: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    spec = _SIDECAR_SPECS.get(application_id)
    if spec is None:
        raise ValueError("unknown chatbot application: {}".format(application_id))

    root = repo_root or _repo_root()
    compose_dir = (root / spec.compose_dir).resolve()
    compose_path = _standalone_compose_path(spec, compose_dir)
    command = [
        "docker",
        "compose",
        "--project-name",
        _compose_project(application_id),
        "--project-directory",
        str(compose_dir),
        "-f",
        str(compose_path),
        "up",
        "-d",
        "--build",
        spec.service_name,
    ]
    result = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            detail or "docker compose failed to start {}".format(application_id)
        )

    health_url = resolve_health_url(application_id)
    ok = sidecar_reachable(health_url, timeout=5.0)
    status = sidecar_status(application_id, repo_root=root)
    status["started"] = True
    if not ok:
        status["detail"] = (
            "Sidecar started but /health is not ready yet at {}. "
            "Retry in a few seconds.".format(health_url)
        )
    return status
