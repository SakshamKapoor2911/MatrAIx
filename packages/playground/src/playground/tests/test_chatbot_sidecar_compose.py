"""Tests for chatbot sidecar standalone compose generation."""

from __future__ import annotations

from pathlib import Path

import yaml

from playground.inprocess.chatbot_sidecar_compose import write_standalone_sidecar_compose


def test_write_standalone_includes_companion_services_from_source(tmp_path: Path) -> None:
    compose_dir = tmp_path / "sidecar"
    compose_dir.mkdir()
    (compose_dir / "docker-compose.yaml").write_text(
        "\n".join(
            [
                "services:",
                "  main:",
                "    depends_on:",
                "      multi-agent-medical-assistant-api:",
                "        condition: service_healthy",
                "  multi-agent-medical-assistant-api:",
                "    build:",
                "      context: ./multi-agent-medical-assistant-api",
                "    depends_on:",
                "      multi-agent-medical-assistant:",
                "        condition: service_healthy",
                "  multi-agent-medical-assistant:",
                "    build:",
                "      context: ./multi-agent-medical-assistant",
                "volumes:",
                "  multi-agent-medical-assistant-cache:",
            ]
        ),
        encoding="utf-8",
    )

    path = write_standalone_sidecar_compose(
        compose_dir=compose_dir,
        service_name="multi-agent-medical-assistant-api",
        build_context="multi-agent-medical-assistant-api",
        host_port=8902,
    )
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "main" not in payload["services"]
    assert "multi-agent-medical-assistant-api" in payload["services"]
    assert "multi-agent-medical-assistant" in payload["services"]
    assert payload["services"]["multi-agent-medical-assistant-api"]["ports"] == [
        "127.0.0.1:8902:8000"
    ]
    assert "volumes" in payload
