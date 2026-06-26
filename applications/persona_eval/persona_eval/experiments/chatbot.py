from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from persona_eval.experiments.applications import (
    ApplicationSpec,
    build_chatbot_task_prompt,
)
from persona_eval.experiments.models import ExperimentRunResult, ExperimentRunSpec
from persona_eval.types import Persona


def _utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def persona_system_prompt(persona: Persona) -> str:
    return persona.context or persona.summary or persona.name


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_chatbot_controller() -> Any:
    path = (
        _repo_root()
        / "applications"
        / "tasks"
        / "chatbot_chat_api"
        / "environment"
        / "chatbot_controller.py"
    )
    spec = importlib.util.spec_from_file_location("persona_eval_chatbot_controller", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load chatbot controller from {}".format(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class JsonlEventWriter:
    def __init__(self, path: Path, *, now: Callable[[], str] = _utc_now) -> None:
        self.path = path
        self.now = now
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: Dict[str, Any]) -> None:
        payload = dict(event)
        payload.setdefault("timestamp", self.now())
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


class RecordingPersonaModel:
    def __init__(
        self,
        inner: Any,
        *,
        emit: Callable[[Dict[str, Any]], None],
    ) -> None:
        self.inner = inner
        self.emit = emit

    def next_turn(self, request: Dict[str, Any]) -> Dict[str, Any]:
        turn_index = request.get("turnIndex")
        self.emit(
            {
                "type": "persona.next_turn.request",
                "turnIndex": turn_index,
                "historyTurns": len(request.get("conversationHistory") or []),
            }
        )
        response = self.inner.next_turn(request)
        self.emit(
            {
                "type": "persona.next_turn.response",
                "turnIndex": turn_index,
                "message": response.get("message"),
                "done": bool(response.get("done")),
                "doneReason": response.get("doneReason"),
            }
        )
        return response

    def self_report(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.emit(
            {
                "type": "persona.self_report.request",
                "turns": request.get("turns"),
                "stopReason": request.get("stopReason"),
            }
        )
        response = self.inner.self_report(request)
        self.emit(
            {
                "type": "persona.self_report.response",
                "overallRating": response.get("overallRating")
                or response.get("overallExperienceRating"),
                "keys": sorted(str(key) for key in response.keys()),
            }
        )
        return response


class RecordingChatbotClient:
    def __init__(
        self,
        inner: Any,
        *,
        emit: Callable[[Dict[str, Any]], None],
    ) -> None:
        self.inner = inner
        self.emit = emit

    def ready(self) -> Dict[str, Any]:
        self.emit({"type": "chatbot.ready.request"})
        payload = self.inner.ready()
        self.emit({"type": "chatbot.ready.response", "status": payload.get("status")})
        return payload

    def send_message(self, message: str) -> Dict[str, Any]:
        self.emit({"type": "chatbot.message.request", "message": message})
        payload = self.inner.send_message(message)
        grounded = payload.get("groundedItems") or payload.get("recommendedItems") or []
        self.emit(
            {
                "type": "chatbot.message.response",
                "sessionId": payload.get("sessionId"),
                "reply": payload.get("reply"),
                "groundedItemCount": len(grounded) if isinstance(grounded, list) else 0,
                "terminal": bool(payload.get("terminal")),
            }
        )
        return payload

    def conversation(self, session_id: str) -> Dict[str, Any]:
        self.emit({"type": "chatbot.conversation.request", "sessionId": session_id})
        payload = self.inner.conversation(session_id)
        self.emit(
            {
                "type": "chatbot.conversation.response",
                "sessionId": session_id,
                "turns": len(payload.get("turns") or []),
            }
        )
        return payload

    def application_result(self, session_id: str) -> Dict[str, Any]:
        self.emit({"type": "chatbot.application_result.request", "sessionId": session_id})
        payload = self.inner.application_result(session_id)
        grounded = payload.get("groundedItems") or payload.get("recommendedItems") or []
        self.emit(
            {
                "type": "chatbot.application_result.response",
                "sessionId": session_id,
                "groundedItemCount": len(grounded) if isinstance(grounded, list) else 0,
            }
        )
        return payload


class ChatbotExperimentRunner:
    """Run one chatbot application experiment without Harbor."""

    def __init__(
        self,
        *,
        controller_module: Optional[Any] = None,
        persona_model_factory: Optional[Callable[[ExperimentRunSpec, Persona], Any]] = None,
        chatbot_client_factory: Optional[Callable[[Any], Any]] = None,
        now: Callable[[], str] = _utc_now,
    ) -> None:
        self.controller = controller_module or _load_chatbot_controller()
        self.persona_model_factory = persona_model_factory
        self.chatbot_client_factory = chatbot_client_factory
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
        event_writer = JsonlEventWriter(output_dir / "events.ndjson", now=self.now)

        def emit(event: Dict[str, Any]) -> None:
            payload = dict(event)
            payload["runId"] = spec.run_id
            event_writer.emit(payload)

        emit({"type": "run.started", "spec": spec.to_dict(), "persona": persona.to_dict()})
        try:
            task_prompt = build_chatbot_task_prompt(
                application,
                goal_context_id=spec.goal_context_id,
            )
            config = self.controller.ControllerConfig(
                application_id=spec.application_id,
                application_context=spec.application_context,
                domain=spec.domain,
                max_turns=spec.max_turns,
                min_turns=spec.min_turns,
                output_dir=output_dir,
                task_prompt=task_prompt,
                persona_prompt=persona_system_prompt(persona),
                api_url=spec.api_url,
                retries=spec.retries,
                retry_delay=spec.retry_delay,
            )
            persona_model = self._build_persona_model(spec, persona)
            chatbot = self._build_chatbot_client(config)
            metadata = self.controller.run_controller(
                config=config,
                persona_model=RecordingPersonaModel(persona_model, emit=emit),
                chatbot=RecordingChatbotClient(chatbot, emit=emit),
            )
            finished_at = self.now()
            artifacts = _artifact_names(output_dir)
            run_payload = {
                "runId": spec.run_id,
                "status": "done",
                "startedAt": started_at,
                "finishedAt": finished_at,
                "spec": spec.to_dict(),
                "persona": persona.to_dict(),
                "application": application.to_dict(),
                "metadata": metadata,
                "artifacts": artifacts,
            }
            (output_dir / "experiment_run.json").write_text(
                json.dumps(run_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
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
        return self.controller.AnthropicPersonaModel(
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            model=spec.persona_model,
            base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        )

    def _build_chatbot_client(self, config: Any) -> Any:
        if self.chatbot_client_factory is not None:
            return self.chatbot_client_factory(config)
        return self.controller.HttpChatbotClient(config)


def _artifact_names(output_dir: Path) -> list[str]:
    names = [
        "events.ndjson",
        "transcript.json",
        "application_result.json",
        "persona_self_report.json",
        "evaluation_result.json",
        "user_feedback.json",
        "run_metadata.json",
        "experiment_run.json",
        "error.json",
    ]
    return [name for name in names if (output_dir / name).is_file()]
