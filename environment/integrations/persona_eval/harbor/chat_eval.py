"""Host-native chat eval for the ``user_sim_chat`` Harbor trial profile."""

from __future__ import annotations

import base64
import json
import shlex
import textwrap
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from harbor.environments.base import BaseEnvironment

from environment.integrations.persona_eval.harbor.chat_sidecar_io import parse_json_stdout
from environment.integrations.persona_eval.harbor.chat_artifacts import (
    chat_api_url_from_env,
    harbor_chat_config_from_env,
)
from environment.integrations.persona_eval.local.chatbot_eval import config_context
from persona_eval.goal_contexts import get_goal_context
from persona_eval.model_client import build_json_client
from persona_eval.runner import _items_id_title
from persona_eval.sut_descriptions import sut_description_for
from persona_eval.types import (
    Persona,
    PersonaEvalConfig,
    PersonaEvalResult,
    PersonaEvalTurn,
    Questionnaire,
)
from persona_eval.user_simulator import UserSimulator


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval_persona(persona: object) -> Persona:
    data = getattr(persona, "data", {}) or {}
    return Persona(
        id=str(getattr(persona, "persona_id", None) or data.get("persona_id") or "persona"),
        name=str(getattr(persona, "display_name", None) or data.get("name") or "Persona"),
        summary=str(getattr(persona, "summary", None) or data.get("summary") or ""),
        context=str(
            getattr(persona, "system_prompt", None)
            or data.get("context")
            or getattr(persona, "summary", "")
            or ""
        ),
        source=str(data.get("source") or ""),
    )


def _normalize_turn_view(response: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    turn = dict(response.get("turn") or {})
    recommended = list(response.get("recommendedItems") or turn.get("recommendedItems") or [])
    grounded = list(turn.get("groundedItems") or recommended)
    assistant = str(
        turn.get("assistantMessage")
        or turn.get("assistantReply")
        or response.get("reply")
        or ""
    )
    return {
        "assistantMessage": assistant,
        "recommendedItems": recommended,
        "groundedItems": grounded,
        "userMessage": user_message,
    }


class HarborSidecarChatSession:
    """Drive a chat sidecar from the Harbor main container via ``environment.exec``."""

    def __init__(
        self,
        environment: BaseEnvironment,
        config: PersonaEvalConfig,
        *,
        api_url: str,
    ) -> None:
        self._environment = environment
        self.config = config
        self._api_url = api_url.rstrip("/")
        self._session_id: Optional[str] = None
        self.turns: List[Dict[str, Any]] = []

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        timeout_sec: int = 200,
    ) -> Dict[str, Any]:
        url = "{}{}".format(self._api_url, path)
        payload = json.dumps(body or {}, ensure_ascii=False, separators=(",", ":"))
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        script = textwrap.dedent(
            """
            import base64, json, urllib.error, urllib.request
            body = base64.b64decode({encoded!r})
            req = urllib.request.Request(
                {url!r},
                data=body if {method!r} != "GET" else None,
                headers={{"Content-Type": "application/json", "Accept": "application/json"}},
                method={method!r},
            )
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    print(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise SystemExit("HTTP {{}}: {{}}".format(exc.code, detail)) from exc
            """
        ).format(encoded=encoded, url=url, method=method)
        command = "python3 -c {}".format(shlex.quote(script.strip()))
        result = await self._environment.exec(command, timeout_sec=timeout_sec)
        if result.return_code != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                "chat sidecar request failed ({} {}): {}".format(method, path, detail)
            )
        parsed = parse_json_stdout((result.stdout or "").strip())
        return parsed

    async def run_turn_sync(self, message: str) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "sessionId": self._session_id,
            "message": message,
            "title": "persona-eval",
            "botType": "chat",
        }
        if self.config.application_id == "recai":
            body["domain"] = self.config.domain
        else:
            body["applicationId"] = self.config.application_id
            body["applicationContext"] = config_context(self.config)
            body["engine"] = self.config.engine
        response = await self._request_json("POST", "/v1/messages", body=body)
        session_id = response.get("sessionId")
        if session_id:
            self._session_id = str(session_id)
        view = _normalize_turn_view(response, message)
        self.turns.append(view)
        return view

    @property
    def session_id(self) -> str:
        return self._session_id or ""


async def run_harbor_chat_eval(
    session: HarborSidecarChatSession,
    persona: Persona,
    sut_description: str,
    config: PersonaEvalConfig,
    simulator: UserSimulator,
    *,
    created_at: str,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    task_path: Optional[str] = None,
    persona_yaml_path: Optional[str] = None,
    repo_root: Optional[Any] = None,
) -> PersonaEvalResult:
    """Async chat eval loop using a Harbor sidecar session."""
    from persona_eval.user_sim.runner import run_persona_eval_v2_async, user_sim_v2_enabled

    if user_sim_v2_enabled():
        return await run_persona_eval_v2_async(
            session,
            persona,
            sut_description,
            config,
            created_at=created_at,
            on_event=on_event,
            task_path=task_path or "application/tasks/recommender-agent_chat_api",
            persona_yaml_path=persona_yaml_path,
            repo_root=repo_root,
        )

    def emit(event: Dict[str, Any]) -> None:
        if on_event is not None:
            on_event(event)

    transcript: List[PersonaEvalTurn] = []
    pairs: List[Tuple[str, str]] = []
    prompts: Dict[str, str] = {}
    if hasattr(simulator, "prompt_bundle"):
        prompts = simulator.prompt_bundle(persona, sut_description)
        emit({"type": "prompts", "prompts": prompts})

    emit({"type": "phase", "phase": "persona_kickoff"})
    message = simulator.kickoff(persona, sut_description)

    for index in range(1, config.max_turns + 1):
        emit({"type": "phase", "phase": "recommender_thinking", "userMessage": message})
        view = await session.run_turn_sync(message)
        assistant = str(view.get("assistantMessage") or "")
        items = _items_id_title(view)

        emit({"type": "phase", "phase": "persona_thinking"})
        sim_turn = simulator.respond(persona, sut_description, list(pairs), assistant, items)

        turn = PersonaEvalTurn(
            turn_index=index,
            user_message=message,
            assistant_message=assistant,
            recommended_items=items,
            decision=sim_turn.decision,
            duration_seconds=view.get("durationSeconds"),
        )
        transcript.append(turn)
        pairs.append((message, assistant))
        emit({"type": "turn", "turn": turn.to_dict()})

        if sim_turn.decision in {"satisfied", "give_up"}:
            break
        message = sim_turn.message

    final_items = next(
        (turn.recommended_items for turn in reversed(transcript) if turn.recommended_items),
        [],
    )
    turns_to_rec = next((turn.turn_index for turn in transcript if turn.recommended_items), None)

    emit({"type": "phase", "phase": "persona_feedback"})
    questionnaire: Questionnaire = simulator.final_feedback(
        persona, sut_description, transcript, final_items
    )

    from persona_eval.types import MetricScores

    return PersonaEvalResult(
        config=config,
        persona=persona,
        sut_description=sut_description,
        transcript=transcript,
        questionnaire=questionnaire,
        metric_scores=MetricScores(
            turns_to_recommendation=turns_to_rec,
            num_turns=len(transcript),
            recommended_item_count=len(final_items),
        ),
        created_at=created_at,
        prompts=prompts,
    )


async def run_harbor_chat_eval_for_persona(
    environment: BaseEnvironment,
    persona: object,
    *,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> tuple[PersonaEvalResult, str]:
    """End-to-end Harbor chat eval for one loaded Harbor persona object."""
    from environment.integrations.persona_eval.harbor.persona_eval import _repo_root

    config = harbor_chat_config_from_env()
    eval_persona = _eval_persona(persona)
    try:
        sut_description = sut_description_for(config.application_context or config.domain)
    except KeyError:
        sut_description = "You are chatting with an interactive application."
    api_url = chat_api_url_from_env(config.application_id)
    marker = environment.trial_paths.trial_dir / ".sidecar_api_url"
    if marker.is_file():
        api_url = marker.read_text(encoding="utf-8").strip() or api_url
    session = HarborSidecarChatSession(environment, config, api_url=api_url)
    simulator = UserSimulator(
        build_json_client(config.persona_model),
        get_goal_context(config.goal_context_id),
        config.domain,
    )
    persona_path = str(getattr(persona, "persona_path", "") or "") or None
    result = await run_harbor_chat_eval(
        session,
        eval_persona,
        sut_description,
        config,
        simulator,
        created_at=_utc_now(),
        on_event=on_event,
        persona_yaml_path=persona_path,
        repo_root=_repo_root(),
    )
    return result, session.session_id
