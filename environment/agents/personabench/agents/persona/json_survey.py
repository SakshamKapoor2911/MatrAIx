"""Host-native survey agent for the ``json_survey`` Harbor trial profile."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.agent.name import AgentName

from environment.integrations.persona_eval.harbor.persona_eval import resolve_repo_root
from environment.integrations.persona_eval.survey_task_content import (
    instruction_markdown_for_instrument,
)
from environment.integrations.persona_eval.harbor.trial_events import TrialEventWriter
from environment.integrations.persona_eval.local.survey_eval import LocalSurveyEvalRunner
from personabench.agents.persona.mixin import PersonaMixin
from persona_eval.types import Persona as EvalPersona


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval_persona(persona: object) -> EvalPersona:
    data = getattr(persona, "data", {}) or {}
    return EvalPersona(
        id=str(getattr(persona, "persona_id", None) or data.get("persona_id") or "persona"),
        name=str(getattr(persona, "display_name", None) or data.get("name") or "Persona"),
        summary=str(getattr(persona, "summary", None) or data.get("summary") or ""),
        context=str(data.get("context") or getattr(persona, "summary", "") or ""),
        source=str(data.get("source") or ""),
    )


def _load_instrument(*, instrument_path: str | None, instrument_id: str | None):
    from backend.service.survey_instruments import get_survey_instrument
    from backend.service.survey_types import SurveyInstrument

    if instrument_path:
        path = Path(instrument_path).expanduser()
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return SurveyInstrument.from_dict(payload)
    instrument_key = instrument_id or os.environ.get("MATRIX_SURVEY_INSTRUMENT_ID", "product_attitudes_v1")
    return get_survey_instrument(instrument_key)


def _survey_result_payload(result) -> dict[str, object]:
    return {
        "instrument": {
            "id": result.instrument.id,
            "title": result.instrument.title,
        },
        "answers": [answer.to_dict() for answer in result.answers],
        "trajectory": [event.to_dict() for event in result.trajectory],
    }


def _repo_root() -> Path:
    return resolve_repo_root(Path(__file__))


def _instruction_markdown_for_instrument(instrument) -> str:
    from environment.integrations.persona_eval.harbor.survey_eval import (
        build_survey_instruction_markdown,
    )

    full = instruction_markdown_for_instrument(instrument.id, repo_root=_repo_root())
    if full:
        return full
    return build_survey_instruction_markdown(instrument=instrument)


class PersonaJsonSurvey(PersonaMixin, BaseAgent):
    """Complete a survey via one-shot JSON completion (no Claude Code container)."""

    SUPPORTS_WINDOWS = True

    @staticmethod
    def name() -> str:
        return AgentName.PERSONA_JSON_SURVEY.value

    def version(self) -> str:
        return "1.0.0"

    def __init__(
        self,
        logs_dir: Path,
        persona_path: str | None = None,
        persona_template_path: str | None = None,
        survey_instrument_path: str | None = None,
        survey_instrument_id: str | None = None,
        **kwargs,
    ) -> None:
        self._init_persona(
            persona_path,
            AgentName.PERSONA_JSON_SURVEY.value,
            persona_template_path=persona_template_path,
        )
        self._survey_instrument_path = survey_instrument_path
        self._survey_instrument_id = survey_instrument_id
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
        instrument = _load_instrument(
            instrument_path=self._survey_instrument_path,
            instrument_id=self._survey_instrument_id,
        )
        persona = _eval_persona(self._persona)
        created_at = _utc_now()
        trial_dir = self.logs_dir.parent
        event_writer = TrialEventWriter.for_trial_dir(trial_dir)
        instruction_md = _instruction_markdown_for_instrument(instrument)
        (trial_dir / "instruction.md").write_text(instruction_md, encoding="utf-8")
        event_writer.append({"type": "instruction", "markdown": instruction_md})

        def on_event(event: dict) -> None:
            event_writer.append(event)

        result = LocalSurveyEvalRunner()(
            persona,
            instrument,
            config=None,
            created_at=created_at,
            on_event=on_event,
        )
        payload = _survey_result_payload(result)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            temp_path = Path(handle.name)
        try:
            await environment.upload_file(temp_path, "/app/output/survey_result.json")
        finally:
            temp_path.unlink(missing_ok=True)
