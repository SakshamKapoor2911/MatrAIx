"""Generate sidecar-only docker compose files (no invalid Harbor ``main`` service)."""

from __future__ import annotations

from pathlib import Path

import yaml


def write_standalone_sidecar_compose(
    *,
    compose_dir: Path,
    service_name: str,
    build_context: str,
    host_port: int | None = None,
    container_port: int = 8000,
    port_mapping: str | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Write a compose file containing only the chat API sidecar."""
    target_dir = output_dir or (compose_dir / ".persona_eval_sidecar")
    target_dir.mkdir(parents=True, exist_ok=True)
    compose_path = target_dir / "standalone-compose.yaml"
    if port_mapping is None:
        if host_port is None:
            raise ValueError("host_port is required when port_mapping is not set")
        port_mapping = "127.0.0.1:{}:{}".format(host_port, container_port)
    payload = {
        "services": {
            service_name: {
                "build": {"context": build_context},
                "ports": [port_mapping],
                "healthcheck": {
                    "test": [
                        "CMD",
                        "python",
                        "-c",
                        (
                            "import socket; "
                            "s=socket.create_connection(('localhost', {}), timeout=2); "
                            "s.close()"
                        ).format(container_port),
                    ],
                    "interval": "2s",
                    "timeout": "5s",
                    "retries": 15,
                    "start_period": "5s",
                },
            }
        }
    }
    compose_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return compose_path
