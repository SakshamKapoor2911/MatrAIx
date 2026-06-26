from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.service.harbor_persona_eval import harbor_persona_system_prompt
from backend.service.harbor_web_eval import (
    HarborWebEvalConfig,
    WebEvalResultArtifact,
    build_web_task_prompt,
)
from backend.service.web_tasks import get_web_eval_task
from persona_eval.experiments.applications import ApplicationSpec
from persona_eval.experiments.chatbot import JsonlEventWriter
from persona_eval.experiments.json_client import JsonCompletionClient
from persona_eval.experiments.models import ExperimentRunResult, ExperimentRunSpec
from persona_eval.types import Persona


class WebPersonaModel:
    def __init__(self, model: str) -> None:
        self.client = JsonCompletionClient(model)

    def complete_web_task(self, request: Dict[str, Any]) -> Dict[str, Any]:
        prompt = """Use the website catalog as a text representation of the hosted web app.
State a realistic website task, select a product shown in the catalog, and rate
the website experience as the assigned persona. Return only JSON.

Task prompt:
{task_prompt}

Request:
{request}
""".format(
            task_prompt=request["taskPrompt"],
            request=json.dumps(request, ensure_ascii=False, indent=2),
        )
        return self.client.complete_json(request["personaPrompt"], prompt)


class WebExperimentRunner:
    """Run one ecommerce web experiment without Harbor."""

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
            task = get_web_eval_task(application.task_id)
            task_prompt = build_web_task_prompt(task)
            catalog = _load_catalog(task.task_path)
            request = {
                "personaPrompt": harbor_persona_system_prompt(persona),
                "taskPrompt": task_prompt,
                "task": task.to_dict(),
                "catalog": catalog,
                "applicationId": spec.application_id,
                "applicationContext": spec.application_context,
            }
            emit(
                {
                    "type": "web.request",
                    "taskId": task.id,
                    "productCount": len(catalog.get("products") or []),
                }
            )
            payload = self._build_persona_model(spec, persona).complete_web_task(request)
            emit(
                {
                    "type": "web.response",
                    "selectedProductId": payload.get("selected_product_id")
                    or payload.get("selectedProductId"),
                }
            )
            web_payload = _web_payload(payload)
            WebEvalResultArtifact.from_dict(web_payload, created_at=started_at)
            (output_dir / task.output_artifact).write_text(
                json.dumps(web_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            trace = {
                "events": _trace_events(payload),
                "raw": payload.get("trace") if isinstance(payload.get("trace"), dict) else payload,
            }
            (output_dir / "web_trace.json").write_text(
                json.dumps(trace, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            metadata = {
                "selectedProductId": web_payload["selected_product_id"],
                "overallExperienceRating": web_payload["overall_experience_rating"],
                "traceEvents": len(trace["events"]),
            }
            finished_at = self.now()
            artifacts = _artifact_names(output_dir, task.output_artifact)
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
            artifacts = _artifact_names(output_dir, task.output_artifact)
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
                artifacts=_artifact_names(output_dir, "ecommerce_interaction.json"),
                error=error,
            )

    def _build_persona_model(self, spec: ExperimentRunSpec, persona: Persona) -> Any:
        if self.persona_model_factory is not None:
            return self.persona_model_factory(spec, persona)
        return WebPersonaModel(spec.persona_model)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_catalog(task_path: Path) -> Dict[str, Any]:
    path = task_path
    if not path.is_absolute():
        path = _repo_root() / path
    catalog_path = path / "environment" / "ecommerce-web" / "site" / "catalog.json"
    with catalog_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("web catalog must be a JSON object")
    return data


def _web_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "selected_product_id": payload.get("selected_product_id", payload.get("selectedProductId")),
        "selected_product_name": payload.get("selected_product_name", payload.get("selectedProductName")),
        "need_satisfaction": payload.get("need_satisfaction", payload.get("needSatisfaction")),
        "ease_of_use": payload.get("ease_of_use", payload.get("easeOfUse")),
        "overall_experience_rating": payload.get(
            "overall_experience_rating",
            payload.get("overallExperienceRating"),
        ),
        "reason": payload.get("reason"),
    }


def _trace_events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = payload.get("trace")
    if isinstance(raw, list):
        return [dict(event) for event in raw if isinstance(event, dict)]
    if isinstance(raw, dict):
        events = raw.get("events")
        if isinstance(events, list):
            return [dict(event) for event in events if isinstance(event, dict)]
    return [
        {
            "step": 1,
            "action": "state_task",
            "observation": str(payload.get("task_statement") or "Persona selected a web task."),
        },
        {
            "step": 2,
            "action": "select_product",
            "observation": str(
                payload.get("selected_product_id", payload.get("selectedProductId", ""))
            ),
        },
    ]


def _artifact_names(output_dir: Path, output_artifact: str) -> list:
    names = [
        "events.ndjson",
        output_artifact,
        "web_trace.json",
        "experiment_run.json",
        "error.json",
    ]
    return [name for name in names if (output_dir / name).is_file()]
