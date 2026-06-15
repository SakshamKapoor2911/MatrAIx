"""Persona-backed computer-1 agent."""

from __future__ import annotations

from pathlib import Path

from harbor.agents.computer_1 import Computer1
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.agent.name import AgentName

from matraix.agents.persona.mixin import PersonaMixin


class PersonaComputer1(PersonaMixin, Computer1):
    @staticmethod
    def name() -> str:
        return AgentName.PERSONA_COMPUTER_1.value

    def __init__(
        self,
        logs_dir: Path,
        persona_path: str | None = None,
        persona_template_path: str | None = None,
        **kwargs,
    ) -> None:
        self._init_persona(
            persona_path,
            AgentName.PERSONA_COMPUTER_1.value,
            persona_template_path=persona_template_path,
        )
        super().__init__(logs_dir=logs_dir, **kwargs)

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        self._write_persona_meta()
        rendered = self._render_persona_instruction(instruction)
        await super().run(rendered, environment, context)
