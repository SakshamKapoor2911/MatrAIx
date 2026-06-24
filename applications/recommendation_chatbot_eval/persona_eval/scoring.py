from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from persona_eval.goal_contexts import get_goal_context
from persona_eval.openai_client import OpenAIChatClient, coerce_json
from persona_eval.types import Persona, PersonaEvalConfig, PersonaEvalTurn
from persona_eval.user_simulator import UserSimulator


def _rec_item(item: Dict[str, Any]) -> Dict[str, Any]:
    item_id = item.get("itemId", item.get("id"))
    return {"id": str(item_id), "title": item.get("title")}


def _turn_from_view(index: int, turn: Dict[str, Any]) -> PersonaEvalTurn:
    return PersonaEvalTurn(
        turn_index=index,
        user_message=str(turn.get("userMessage") or ""),
        assistant_message=str(turn.get("assistantMessage") or ""),
        recommended_items=[
            _rec_item(item)
            for item in (turn.get("recommendedItems") or [])
            if isinstance(item, dict)
            and (item.get("itemId") or item.get("id")) is not None
        ],
        decision=str(turn.get("decision") or "continue"),
        duration_seconds=turn.get("durationSeconds"),
    )


def _read_json_object(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError("{} must contain a JSON object".format(path))
    return value


def _turn_views_from_transcript(transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
    turns = transcript.get("turns")
    if isinstance(turns, list) and all(isinstance(turn, dict) for turn in turns):
        return [dict(turn) for turn in turns]

    messages = transcript.get("messages") or []
    if not isinstance(messages, list):
        return []
    views: List[Dict[str, Any]] = []
    pending_user: Optional[str] = None
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = str(message.get("content") or "")
        if role == "user":
            pending_user = content
        elif role == "assistant" and pending_user is not None:
            views.append(
                {
                    "turnId": str(len(views)),
                    "userMessage": pending_user,
                    "assistantMessage": content,
                    "recommendedItems": [],
                }
            )
            pending_user = None
    return views


def _config_from_dict(value: Dict[str, Any]) -> PersonaEvalConfig:
    return PersonaEvalConfig(
        domain=str(value.get("domain") or "movie"),
        application_id=str(
            value.get("applicationId", value.get("application_id", "recai"))
        ),
        application_context=str(
            value.get(
                "applicationContext",
                value.get("application_context", value.get("domain") or "movie"),
            )
        ),
        engine=str(value.get("engine") or "gpt-4o-mini"),
        persona_model=str(
            value.get(
                "personaModel", value.get("persona_model", "anthropic/claude-haiku-4-5")
            )
        ),
        ranker_mode=str(value.get("rankerMode", value.get("ranker_mode", "native"))),
        resource_mode=str(
            value.get("resourceMode", value.get("resource_mode", "recai_resources"))
        ),
        max_turns=int(value.get("maxTurns", value.get("max_turns", 8))),
        goal_context_id=str(
            value.get("goalContextId", value.get("goal_context_id", "scenario_default"))
        ),
    )


class StdlibOpenAIChatClient:
    """Small OpenAI JSON-mode client for Harbor verifier containers."""

    def __init__(
        self,
        model: str,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        timeout_seconds: float = 90.0,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (
            base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for application scoring")
        body = json.dumps(
            {
                "model": self.model,
                "temperature": self.temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "{}/chat/completions".format(self.base_url),
            data=body,
            headers={
                "Authorization": "Bearer {}".format(self.api_key),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                "OpenAI scoring request failed: {}".format(detail[:500])
            ) from exc
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI scoring response did not include choices")
        message = choices[0].get("message") or {}
        return coerce_json(str(message.get("content") or ""))


class OriginalPromptFeedbackScorer:
    """Score Harbor recommender runs with the original persona-eval prompt."""

    def __init__(
        self,
        *,
        client_factory: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.client_factory = client_factory or (
            lambda model: OpenAIChatClient(model=model)
        )

    def __call__(
        self,
        *,
        persona: Persona,
        sut_description: str,
        config: PersonaEvalConfig,
        turn_views: List[Dict[str, Any]],
        recommended_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        goal_context = get_goal_context(config.goal_context_id)
        simulator = UserSimulator(
            self.client_factory(config.engine),
            goal_context,
            config.domain,
        )
        transcript = [
            _turn_from_view(index, turn) for index, turn in enumerate(turn_views)
        ]
        final_items = [
            _rec_item(item)
            for item in recommended_items
            if isinstance(item, dict)
            and (item.get("itemId") or item.get("id")) is not None
        ]
        return simulator.final_feedback(
            persona,
            sut_description,
            transcript,
            final_items,
        ).to_dict()


def score_harbor_artifacts(
    *,
    transcript_path: Path,
    application_path: Optional[Path] = None,
    recommendation_path: Optional[Path] = None,
    output_path: Path,
    persona: Persona,
    sut_description: str,
    config: PersonaEvalConfig,
    client_factory: Optional[Callable[[str], Any]] = None,
) -> Dict[str, Any]:
    """Score Harbor chatbot artifacts and write the questionnaire artifact."""
    transcript = _read_json_object(Path(transcript_path))
    result_path = application_path or recommendation_path
    if result_path is None:
        raise ValueError("application_path is required")
    recommendation = _read_json_object(Path(result_path))
    turn_views = _turn_views_from_transcript(transcript)
    recommended_items = recommendation.get(
        "groundedItems", recommendation.get("recommendedItems")
    ) or []
    if not isinstance(recommended_items, list):
        raise ValueError("application_result.groundedItems must be a list")
    scorer = OriginalPromptFeedbackScorer(
        client_factory=client_factory
        or (lambda model: StdlibOpenAIChatClient(model=model))
    )
    questionnaire = scorer(
        persona=persona,
        sut_description=sut_description,
        config=config,
        turn_views=turn_views,
        recommended_items=[
            item for item in recommended_items if isinstance(item, dict)
        ],
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(questionnaire, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return questionnaire


def score_harbor_artifacts_from_env(
    *,
    transcript_path: Path,
    application_path: Optional[Path] = None,
    recommendation_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    client_factory: Optional[Callable[[str], Any]] = None,
) -> Dict[str, Any]:
    """Environment-driven entry point used by the Harbor verifier."""
    persona_payload = os.environ.get("MATRIX_SCORER_PERSONA_JSON")
    config_payload = os.environ.get("MATRIX_SCORER_CONFIG_JSON")
    if not persona_payload:
        raise ValueError("MATRIX_SCORER_PERSONA_JSON is required")
    if not config_payload:
        raise ValueError("MATRIX_SCORER_CONFIG_JSON is required")
    persona = Persona.from_dict(json.loads(persona_payload))
    config = _config_from_dict(json.loads(config_payload))
    sut_description = os.environ.get("MATRIX_SCORER_SUT_DESCRIPTION", "")
    target = Path(
        os.environ.get("MATRIX_SCORER_OUTPUT_PATH")
        or str(output_path or Path(transcript_path).with_name("user_feedback.json"))
    )
    return score_harbor_artifacts(
        transcript_path=Path(transcript_path),
        application_path=Path(application_path)
        if application_path is not None
        else None,
        recommendation_path=Path(recommendation_path)
        if recommendation_path is not None
        else None,
        output_path=target,
        persona=persona,
        sut_description=sut_description,
        config=config,
        client_factory=client_factory,
    )
