"""Shared persona injection helpers for PersonaBench agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from personabench.agents.persona.loader import Persona, load_persona
from personabench.persona_job import SMOKE_PERSONA_PATH
from personabench.agents.persona.templating import (
    PERSONA_INSTRUCTION_TEMPLATE,
    PERSONA_SYSTEM_TEMPLATE,
    render_persona_template,
    resolve_persona_template,
)

if TYPE_CHECKING:
    from harbor.environments.base import BaseEnvironment


class PersonaMixin:
    """Load persona YAML and write trial-level persona_meta.json."""

    _persona: Persona
    _persona_agent_name: str
    _persona_template_path: Path | None

    def _init_persona(
        self,
        persona_path: str | None,
        agent_name: str,
        *,
        persona_template_path: str | None = None,
    ) -> None:
        if not persona_path:
            raise ValueError(
                f"{agent_name} requires persona_path "
                f"(pass --ak persona_path={SMOKE_PERSONA_PATH})"
            )
        self._persona = load_persona(persona_path)
        self._persona_agent_name = agent_name
        self._persona_template_path = (
            Path(persona_template_path).expanduser().resolve()
            if persona_template_path
            else None
        )

    def _render_persona_system(self) -> str:
        template = resolve_persona_template(
            self._persona,
            self._persona_template_path,
            PERSONA_SYSTEM_TEMPLATE,
        )
        return render_persona_template(template, self._persona)

    def _render_persona_instruction(self, instruction: str) -> str:
        template = resolve_persona_template(
            self._persona,
            self._persona_template_path,
            PERSONA_INSTRUCTION_TEMPLATE,
        )
        return render_persona_template(template, self._persona, instruction=instruction)

    def _write_persona_meta(self) -> None:
        logs_dir: Path = self.logs_dir  # type: ignore[attr-defined]
        meta_path = logs_dir.parent / "persona_meta.json"
        meta = self._persona.to_meta(self._persona_agent_name)
        if self._persona_template_path is not None:
            meta["persona_template_path"] = str(self._persona_template_path)
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    async def _prepare_persona_trial(self, environment: BaseEnvironment) -> None:
        """Write trial meta and upload persona YAML for in-container verifiers."""
        self._write_persona_meta()
        await environment.upload_file(
            self._persona.persona_path,
            "/app/input/persona.yaml",
        )
