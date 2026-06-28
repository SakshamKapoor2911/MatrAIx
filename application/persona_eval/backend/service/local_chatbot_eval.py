from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException

from backend.service.catalog_index import CatalogIndex
from backend.service.config import ConfigManager
from persona_eval.model_client import build_json_client
from persona_eval.runner import run_persona_eval
from persona_eval.session_factory import build_session
from persona_eval.types import PersonaEvalConfig
from persona_eval.user_simulator import UserSimulator


class LocalChatbotEvalRunner:
    """Run persona/chatbot simulations through the direct local runtime."""

    def __call__(
        self,
        session: Any,
        persona: Any,
        sut_description: str,
        config: PersonaEvalConfig,
        simulator: Any,
        *,
        created_at: str,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Any:
        return run_persona_eval(
            session,
            persona,
            sut_description,
            config,
            simulator,
            created_at=created_at,
            on_event=on_event,
        )


class DirectApplicationSession:
    """Session wrapper for non-RecAI chatbot application adapters."""

    def __init__(self, config: PersonaEvalConfig) -> None:
        self.config = config
        self.turns = []
        self._session_id: Optional[str] = None
        self._application = _application_for(config.application_id)

    def run_turn_sync(self, message: str) -> Dict[str, Any]:
        response = self._application.send_message(
            session_id=self._session_id,
            message=message,
            title="persona-eval",
            context=config_context(self.config),
            engine=self.config.engine,
            bot_type="chat",
        )
        self._session_id = str(response["sessionId"])
        turn = dict(response.get("turn") or {})
        if "recommendedItems" not in turn:
            turn["recommendedItems"] = list(response.get("recommendedItems") or [])
        if "groundedItems" not in turn:
            turn["groundedItems"] = list(response.get("groundedItems") or [])
        self.turns.append(turn)
        return turn


def config_context(config: PersonaEvalConfig) -> str:
    return config.application_context or config.domain


def _application_for(application_id: str) -> Any:
    if application_id == "finance_openbb":
        return HTTPChatbotApplication(
            application_id="finance_openbb",
            default_context="financial_research",
            base_url=_sidecar_base_url(
                "CHATBOT_UPSTREAM_FINANCE",
                "FINANCE_CHATBOT_URL",
                "http://127.0.0.1:8901",
            ),
        )
    if application_id == "medical_assistant":
        return HTTPChatbotApplication(
            application_id="medical_assistant",
            default_context="medical_consultation",
            base_url=_sidecar_base_url(
                "CHATBOT_UPSTREAM_MEDICAL",
                "MEDICAL_CHATBOT_URL",
                "http://127.0.0.1:8902",
            ),
        )
    raise ValueError("unsupported direct application: {}".format(application_id))


def _sidecar_base_url(primary_env: str, legacy_env: str, default: str) -> str:
    return (
        os.environ.get(primary_env)
        or os.environ.get(legacy_env)
        or os.environ.get("CHATBOT_API_URL")
        or default
    )


class HTTPChatbotApplication:
    """HTTP client for task-owned chatbot application sidecars."""

    def __init__(self, *, application_id: str, default_context: str, base_url: str) -> None:
        self.application_id = application_id
        self.default_context = default_context
        self.base_url = base_url.rstrip("/")

    def send_message(
        self,
        *,
        session_id: Optional[str],
        message: str,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        body = {
            "sessionId": session_id,
            "message": message,
            "title": title,
            "applicationId": self.application_id,
            "applicationContext": context or self.default_context,
            "engine": engine,
            "botType": bot_type,
        }
        return self._request_json("POST", "/v1/messages", body=body)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        timeout: float = 180.0,
    ) -> Dict[str, Any]:
        url = "{}{}".format(self.base_url, path)
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(
                {key: value for key, value in body.items() if value is not None}
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HTTPException(status_code=exc.code, detail=detail) from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "{} sidecar unavailable at {}. Start the chatbot sidecar "
                    "or set CHATBOT_UPSTREAM_{}."
                ).format(
                    self.application_id,
                    self.base_url,
                    "FINANCE" if self.application_id == "finance_openbb" else "MEDICAL",
                ),
            ) from exc
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail="{} sidecar returned invalid JSON".format(self.application_id),
            ) from exc
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=502,
                detail="{} sidecar returned non-object JSON".format(self.application_id),
            )
        return payload


def build_local_chat_session(
    config: PersonaEvalConfig,
    *,
    catalog_provider: Callable[[str], CatalogIndex],
    config_manager: ConfigManager,
) -> Any:
    """Return the application-under-test session for one local eval run."""
    if config.application_id == "recai":
        return build_session(
            config,
            catalog=catalog_provider(config.domain),
            config_manager=config_manager,
        )
    return DirectApplicationSession(config)


def build_local_user_simulator(engine: str, goal_context_id: str, domain: str) -> UserSimulator:
    from persona_eval.goal_contexts import get_goal_context

    del engine
    return UserSimulator(
        build_json_client("openai/gpt-4o-mini"),
        get_goal_context(goal_context_id),
        domain,
    )


def build_local_user_simulator_for_model(
    persona_model: str,
    goal_context_id: str,
    domain: str,
) -> UserSimulator:
    from persona_eval.goal_contexts import get_goal_context

    return UserSimulator(
        build_json_client(persona_model),
        get_goal_context(goal_context_id),
        domain,
    )
