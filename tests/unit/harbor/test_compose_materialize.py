from __future__ import annotations

from pathlib import Path

from harbor.environments.compose_materialize import (
    materialize_persona_with_local_compose,
)


def test_materialize_persona_with_local_compose(tmp_path: Path) -> None:
    persona = tmp_path / "persona"
    persona.mkdir()
    (persona / "Dockerfile").write_text("FROM ubuntu:24.04\n", encoding="utf-8")
    (persona / "install-claude-code.sh").write_text("#!/bin/bash\n", encoding="utf-8")

    sidecar = tmp_path / "sidecar"
    api = sidecar / "recommender-api"
    api.mkdir(parents=True)
    (sidecar / "docker-compose.yaml").write_text(
        "services:\n  rec-agent-api:\n    build: ./recommender-api\n",
        encoding="utf-8",
    )
    (api / "server.py").write_text("print('ok')\n", encoding="utf-8")

    dest = tmp_path / "composed"
    result = materialize_persona_with_local_compose(
        persona_dir=persona,
        local_compose_dir=sidecar,
        dest_dir=dest,
    )
    assert result == dest.resolve()
    assert (dest / "Dockerfile").is_file()
    assert (dest / "install-claude-code.sh").is_file()
    assert (dest / "docker-compose.yaml").is_file()
    assert (dest / "recommender-api" / "server.py").is_file()
