"""Host-native chat agent for the ``user_sim_chat`` Harbor trial profile."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.agent.name import AgentName

from environment.integrations.persona_eval.harbor.chat_artifacts import (
    harbor_artifacts_from_result,
)
from environment.integrations.persona_eval.harbor.chat_eval import (
    run_harbor_chat_eval_for_persona,
)
from environment.integrations.persona_eval.harbor.trial_events import TrialEventWriter
from personabench.agents.persona.mixin import PersonaMixin


class PersonaUserSim(PersonaMixin, BaseAgent):
    """Drive a multi-turn chat via UserSimulator + task sidecar (no Claude Code)."""

    SUPPORTS_WINDOWS = True

    @staticmethod
    def name() -> str:
        return AgentName.PERSONA_USER_SIM.value

    def version(self) -> str:
        return "1.0.0"

    def __init__(
        self,
        logs_dir: Path,
        persona_path: str | None = None,
        persona_template_path: str | None = None,
        **kwargs,
    ) -> None:
        self._init_persona(
            persona_path,
            AgentName.PERSONA_USER_SIM.value,
            persona_template_path=persona_template_path,
        )
        super().__init__(logs_dir=logs_dir, **kwargs)

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        del instruction, context
        await self._prepare_persona_trial(environment)
        event_writer = TrialEventWriter.for_trial_dir(self.logs_dir.parent)

        def on_event(event: dict) -> None:
            event_writer.append(event)

        result, session_id = await run_harbor_chat_eval_for_persona(
            environment,
            self._persona,
            on_event=on_event,
        )
        artifacts = harbor_artifacts_from_result(
            result,
            session_id=session_id or "harbor-chat",
            domain=result.config.domain,
        )
        for filename, payload in artifacts.items():
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", suffix=".json", delete=False
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                temp_path = Path(handle.name)
            try:
                await environment.upload_file(temp_path, "/app/output/{}".format(filename))
            finally:
                temp_path.unlink(missing_ok=True)
