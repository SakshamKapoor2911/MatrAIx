from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from backend.service.harbor_persona_eval import harbor_persona_system_prompt
from backend.service.harbor_survey_eval import (
    HarborSurveyEvalConfig,
    build_result_from_harbor_survey_artifacts,
    build_survey_task_prompt,
)
from backend.service.survey_instruments import get_survey_instrument
from persona_eval.experiments.applications import ApplicationSpec
from persona_eval.experiments.chatbot import JsonlEventWriter
from persona_eval.experiments.json_client import JsonCompletionClient
from persona_eval.experiments.models import ExperimentRunResult, ExperimentRunSpec
from persona_eval.types import Persona


class SurveyPersonaModel:
    def __init__(self, model: str) -> None:
        self.client = JsonCompletionClient(model)

    def complete_survey(self, request: Dict[str, Any]) -> Dict[str, Any]:
        prompt = """Complete this survey as the assigned persona. Return only JSON.

Task prompt:
{task_prompt}

Request:
{request}
""".format(
            task_prompt=request["taskPrompt"],
            request=json.dumps(request, ensure_ascii=False, indent=2),
        )
        return self.client.complete_json(request["personaPrompt"], prompt)


class SurveyExperimentRunner:
    """Run one structured survey experiment without Harbor."""

    def __init__(
        self,
        *,
        persona_model_factory: Optional[Callable[[ExperimentRunSpec, Persona], Any]] = None,
        now: Callable[[], str],
    ) -> None:
        self.persona_model_factory = persona_model_factory
        self.now = now

    def run(
        self,
        spec: ExperimentRunSpec,
        persona: Persona,
        output_dir: Path,
        application: ApplicationSpec,
    ) -> ExperimentRunResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        started_at = self.now()
        events = JsonlEventWriter(output_dir / "events.ndjson", now=self.now)

        def emit(event: Dict[str, Any]) -> None:
            payload = dict(event)
            payload["runId"] = spec.run_id
            events.emit(payload)

        emit({"type": "run.started", "spec": spec.to_dict(), "persona": persona.to_dict()})
        try:
            instrument = get_survey_instrument(application.task_id)
            task_prompt = build_survey_task_prompt(instrument=instrument)
            request = {
                "personaPrompt": harbor_persona_system_prompt(persona),
                "taskPrompt": task_prompt,
                "instrument": instrument.to_dict(),
                "applicationId": spec.application_id,
                "applicationContext": spec.application_context,
            }
            emit(
                {
                    "type": "survey.request",
                    "instrumentId": instrument.id,
                    "questionCount": len(instrument.questions),
                }
            )
            payload = self._build_persona_model(spec, persona).complete_survey(request)
            emit(
                {
                    "type": "survey.response",
                    "answerCount": len(payload.get("answers") or []),
                }
            )
            (output_dir / "survey_result.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            normalized = build_result_from_harbor_survey_artifacts(
                output_dir=output_dir,
                config=HarborSurveyEvalConfig(persona_model=spec.persona_model),
                persona=persona,
                instrument=instrument,
                created_at=started_at,
                prompts={
                    "harborPrompt": harbor_persona_system_prompt(persona),
                    "taskPrompt": task_prompt,
                },
            )
            metadata = {"metrics": normalized.metrics.to_dict()}
            finished_at = self.now()
            artifacts = _artifact_names(output_dir)
            recorded_artifacts = sorted(set(artifacts + ["experiment_run.json"]))
            (output_dir / "experiment_run.json").write_text(
                json.dumps(
                    {
                        "runId": spec.run_id,
                        "status": "done",
                        "startedAt": started_at,
                        "finishedAt": finished_at,
                        "spec": spec.to_dict(),
                        "persona": persona.to_dict(),
                        "application": application.to_dict(),
                        "metadata": metadata,
                        "artifacts": recorded_artifacts,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            artifacts = _artifact_names(output_dir)
            emit({"type": "run.completed", "status": "done", "artifacts": artifacts})
            return ExperimentRunResult(
                run_id=spec.run_id,
                status="done",
                output_dir=output_dir,
                started_at=started_at,
                finished_at=finished_at,
                artifacts=artifacts,
                metadata=metadata,
            )
        except BaseException as exc:  # noqa: BLE001 - keep batch running.
            finished_at = self.now()
            error = "{}: {}".format(type(exc).__name__, exc)
            (output_dir / "error.json").write_text(
                json.dumps(
                    {
                        "runId": spec.run_id,
                        "status": "error",
                        "startedAt": started_at,
                        "finishedAt": finished_at,
                        "error": error,
                        "spec": spec.to_dict(),
                        "persona": persona.to_dict(),
                        "application": application.to_dict(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            emit({"type": "run.completed", "status": "error", "error": error})
            return ExperimentRunResult(
                run_id=spec.run_id,
                status="error",
                output_dir=output_dir,
                started_at=started_at,
                finished_at=finished_at,
                artifacts=_artifact_names(output_dir),
                error=error,
            )

    def _build_persona_model(self, spec: ExperimentRunSpec, persona: Persona) -> Any:
        if self.persona_model_factory is not None:
            return self.persona_model_factory(spec, persona)
        return SurveyPersonaModel(spec.persona_model)


def _artifact_names(output_dir: Path) -> list:
    names = [
        "events.ndjson",
        "survey_result.json",
        "experiment_run.json",
        "error.json",
    ]
    return [name for name in names if (output_dir / name).is_file()]
