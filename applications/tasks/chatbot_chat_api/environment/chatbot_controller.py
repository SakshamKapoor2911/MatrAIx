from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

try:
    from chatbot_client import item_count, request_json, write_json
except ImportError:  # pragma: no cover - supports direct test imports from repo.
    import importlib.util

    _CLIENT_PATH = Path(__file__).with_name("chatbot_client.py")
    _SPEC = importlib.util.spec_from_file_location("chatbot_client", _CLIENT_PATH)
    if _SPEC is None or _SPEC.loader is None:
        raise
    _CLIENT = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_CLIENT)
    item_count = _CLIENT.item_count
    request_json = _CLIENT.request_json
    write_json = _CLIENT.write_json


@dataclass
class ControllerConfig:
    application_id: str
    application_context: str
    domain: str
    max_turns: int
    min_turns: int
    output_dir: Path
    task_prompt: str
    persona_prompt: str
    api_url: str = "http://chatbot-api:8000"
    retries: int = 6
    retry_delay: float = 2.0


class PersonaModel(Protocol):
    def next_turn(self, request: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def self_report(self, request: Dict[str, Any]) -> Dict[str, Any]:
        ...


class ChatbotClient(Protocol):
    def ready(self) -> Dict[str, Any]:
        ...

    def send_message(self, message: str) -> Dict[str, Any]:
        ...

    def conversation(self, session_id: str) -> Dict[str, Any]:
        ...

    def application_result(self, session_id: str) -> Dict[str, Any]:
        ...


class HttpChatbotClient:
    def __init__(self, config: ControllerConfig) -> None:
        self.config = config
        self.session_id: Optional[str] = None

    @property
    def _request_kwargs(self) -> Dict[str, Any]:
        return {
            "api_url": self.config.api_url,
            "retries": self.config.retries,
            "retry_delay": self.config.retry_delay,
        }

    def ready(self) -> Dict[str, Any]:
        return request_json(
            method="GET",
            path="/ready",
            query={
                "applicationId": self.config.application_id,
                "applicationContext": self.config.application_context,
                "domain": self.config.domain,
            },
            **self._request_kwargs,
        )

    def send_message(self, message: str) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "applicationId": self.config.application_id,
            "applicationContext": self.config.application_context,
            "domain": self.config.domain,
            "message": message,
        }
        if self.session_id:
            body["sessionId"] = self.session_id
        payload = request_json(
            method="POST",
            path="/v1/messages",
            body=body,
            **self._request_kwargs,
        )
        self.session_id = str(payload.get("sessionId") or self.session_id or "")
        if not self.session_id:
            raise RuntimeError("chatbot response did not include sessionId")
        return payload

    def conversation(self, session_id: str) -> Dict[str, Any]:
        return request_json(
            method="GET",
            path="/v1/conversation",
            query={"sessionId": session_id, "applicationId": self.config.application_id},
            **self._request_kwargs,
        )

    def application_result(self, session_id: str) -> Dict[str, Any]:
        return request_json(
            method="GET",
            path="/v1/application-result",
            query={"sessionId": session_id, "applicationId": self.config.application_id},
            **self._request_kwargs,
        )


class AnthropicPersonaModel:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.anthropic.com",
        timeout_sec: int = 180,
    ) -> None:
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for persona self-play")
        self.api_key = api_key
        self.model = _normalize_anthropic_model(model)
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def next_turn(self, request: Dict[str, Any]) -> Dict[str, Any]:
        prompt = """Return only JSON for the next simulated user turn.

Schema:
{{"message": string|null, "done": boolean, "doneReason": string|null}}

Rules:
- Stay in character as the persona.
- Use the task prompt to decide the user's realistic need.
- Reveal preferences gradually and answer naturally.
- Set done=true only when the conversation already satisfies the user's need.
- If done=false, message must be a short natural user message.

Request:
{}""".format(
            json.dumps(request, ensure_ascii=False, indent=2)
        )
        return self._json_completion(system=request["personaPrompt"], prompt=prompt)

    def self_report(self, request: Dict[str, Any]) -> Dict[str, Any]:
        prompt = """You have now FINISHED using the application chatbot. Here is the full conversation (you = user, agent = application chatbot):
{transcript}

Final grounded items (id — title): {final_items}

Reflecting honestly from your own point of view as this persona, fill out this post-use questionnaire as strict JSON (no prose outside the JSON):
{{
  "constraintSatisfaction": <1-5 how well your product-need/constraints were met>,
  "constraintRationale": "<short reason>",
  "preferenceSatisfaction": <1-5 how well your personal preferences were met>,
  "preferenceRationale": "<short reason>",
  "overallRating": <1-10 overall experience, in your own voice>,
  "ratingReason": "<short reason for the rating, your voice>",
  "askedUsefulClarifyingQuestions": <true|false: did the agent ask useful clarifying questions?>,
  "clarifyingNotes": "<which questions, or why not>"
}}

Task prompt:
{task_prompt}

Application context:
- applicationId: {application_id}
- applicationContext: {application_context}
- domain: {domain}
- stopReason: {stop_reason}
- turns: {turns}
""".format(
            transcript=_format_feedback_transcript(request.get("transcript")),
            final_items=_format_feedback_items(request.get("applicationResult")),
            task_prompt=str(request.get("taskPrompt") or ""),
            application_id=str(request.get("applicationId") or ""),
            application_context=str(request.get("applicationContext") or ""),
            domain=str(request.get("domain") or ""),
            stop_reason=str(request.get("stopReason") or ""),
            turns=str(request.get("turns") or ""),
        )
        return self._json_completion(system=request["personaPrompt"], prompt=prompt)

    def _json_completion(self, *, system: str, prompt: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "max_tokens": 1200,
            "temperature": 0.2,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        request = urllib.request.Request(
            "{}/v1/messages".format(self.base_url),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        last_error: Optional[BaseException] = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return _extract_json_object(_anthropic_text(data))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    "Anthropic API HTTP {}: {}".format(exc.code, detail)
                ) from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError("persona model call failed: {}".format(last_error))


def run_controller(
    *,
    config: ControllerConfig,
    persona_model: PersonaModel,
    chatbot: ChatbotClient,
) -> Dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ready = chatbot.ready()
    history: List[Dict[str, Any]] = []
    session_id: Optional[str] = None
    stop_reason = "max_turns"

    for turn_index in range(config.max_turns):
        persona_request = {
            "personaPrompt": config.persona_prompt,
            "taskPrompt": config.task_prompt,
            "applicationId": config.application_id,
            "applicationContext": config.application_context,
            "domain": config.domain,
            "turnIndex": turn_index + 1,
            "maxTurns": config.max_turns,
            "minTurns": config.min_turns,
            "conversationHistory": history,
        }
        persona_turn = persona_model.next_turn(persona_request)
        if _as_bool(persona_turn.get("done")) and len(history) >= config.min_turns:
            stop_reason = "persona_done"
            break

        message = str(persona_turn.get("message") or "").strip()
        if not message:
            if _as_bool(persona_turn.get("done")):
                raise RuntimeError("persona ended before min_turns")
            raise RuntimeError("persona turn did not include a user message")

        payload = chatbot.send_message(message)
        session_id = str(payload.get("sessionId") or session_id or "")
        if not session_id:
            raise RuntimeError("chatbot response did not include sessionId")
        assistant_message = str(payload.get("reply") or "")
        history.append(
            {
                "user": message,
                "assistant": assistant_message,
                "groundedItems": payload.get("groundedItems", []),
            }
        )
        print(
            "TURN {} {}".format(
                len(history),
                json.dumps(
                    {
                        "sessionId": session_id,
                        "groundedItems": item_count(payload),
                        "stopReason": stop_reason,
                    },
                    ensure_ascii=False,
                ),
            ),
            flush=True,
        )

        if _as_bool(payload.get("terminal")) and len(history) >= config.min_turns:
            stop_reason = "chatbot_terminal"
            break
        if len(history) >= config.max_turns:
            stop_reason = "max_turns"
            break

    if not session_id:
        raise RuntimeError("conversation ended before any chatbot message was sent")

    transcript = chatbot.conversation(session_id)
    application_result = chatbot.application_result(session_id)

    feedback_request = {
        "personaPrompt": config.persona_prompt,
        "taskPrompt": config.task_prompt,
        "applicationId": config.application_id,
        "applicationContext": config.application_context,
        "domain": config.domain,
        "stopReason": stop_reason,
        "turns": len(history),
        "transcript": transcript,
        "applicationResult": application_result,
    }
    self_report = _normalize_self_report(persona_model.self_report(feedback_request))
    evaluation_result = {
        "source": "persona_self_report",
        "scores": {
            "constraintSatisfaction": self_report["constraintSatisfaction"],
            "preferenceSatisfaction": self_report["preferenceSatisfaction"],
            "overallRating": self_report["overallRating"],
            "askedUsefulClarifyingQuestions": self_report[
                "askedUsefulClarifyingQuestions"
            ],
        },
        "reason": self_report["ratingReason"],
        "turnsToResult": application_result.get("turnsToResult", len(history)),
        "stopReason": stop_reason,
    }
    run_metadata = {
        "applicationId": config.application_id,
        "applicationContext": config.application_context,
        "domain": config.domain,
        "maxTurns": config.max_turns,
        "minTurns": config.min_turns,
        "turns": len(history),
        "stopReason": stop_reason,
        "ready": ready,
    }

    write_json(output_dir / "transcript.json", transcript)
    write_json(output_dir / "application_result.json", application_result)
    write_json(output_dir / "persona_self_report.json", self_report)
    write_json(output_dir / "evaluation_result.json", evaluation_result)
    write_json(output_dir / "user_feedback.json", self_report)
    write_json(output_dir / "run_metadata.json", run_metadata)
    print(
        "SAVED {}".format(
            json.dumps(
                {
                    "sessionId": session_id,
                    "turns": len(history),
                    "groundedItems": item_count(application_result),
                    "stopReason": stop_reason,
                    "outputDir": str(output_dir),
                },
                ensure_ascii=False,
            )
        ),
        flush=True,
    )
    return run_metadata


def config_from_env() -> ControllerConfig:
    application_id = os.environ.get("MATRIX_CHATBOT_APPLICATION_ID", "recai").strip()
    application_context = os.environ.get(
        "MATRIX_CHATBOT_APPLICATION_CONTEXT", os.environ.get("RECBOT_READY_DOMAIN", "movie")
    ).strip()
    domain = os.environ.get("MATRIX_CHATBOT_DOMAIN", application_context).strip()
    task_prompt_path = Path(
        os.environ.get("MATRIX_CHATBOT_TASK_PROMPT_PATH", "/app/input/task_prompt.md")
    )
    persona_path = Path(os.environ.get("MATRIX_CHATBOT_PERSONA_PATH", "/app/input/persona.yaml"))
    return ControllerConfig(
        application_id=application_id,
        application_context=application_context,
        domain=domain,
        max_turns=_env_int("MATRIX_CHATBOT_MAX_TURNS", 8),
        min_turns=_env_int("MATRIX_CHATBOT_MIN_TURNS", 3),
        output_dir=Path(os.environ.get("MATRIX_CHATBOT_OUTPUT_DIR", "/app/output")),
        task_prompt=_read_text_or_default(task_prompt_path, ""),
        persona_prompt=_read_persona_prompt(persona_path),
        api_url=os.environ.get("MATRIX_CHATBOT_API_URL", "http://chatbot-api:8000"),
        retries=_env_int("MATRIX_CHATBOT_RETRIES", 6),
        retry_delay=float(os.environ.get("MATRIX_CHATBOT_RETRY_DELAY", "2.0")),
    )


def build_persona_model_from_env() -> AnthropicPersonaModel:
    model = (
        os.environ.get("MATRIX_CHATBOT_PERSONA_MODEL")
        or os.environ.get("ANTHROPIC_MODEL")
        or "claude-haiku-4-5"
    )
    return AnthropicPersonaModel(
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        model=model,
        base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
    )


def main() -> int:
    config = config_from_env()
    run_controller(
        config=config,
        persona_model=build_persona_model_from_env(),
        chatbot=HttpChatbotClient(config),
    )
    return 0


def _normalize_self_report(raw: Dict[str, Any]) -> Dict[str, Any]:
    reason = str(raw.get("ratingReason", raw.get("reason", "")) or "").strip()
    constraint_reason = str(
        raw.get("constraintRationale", raw.get("reason", "")) or ""
    ).strip()
    preference_reason = str(
        raw.get("preferenceRationale", raw.get("reason", "")) or ""
    ).strip()
    return {
        "constraintSatisfaction": _score(
            raw.get(
                "constraintSatisfaction",
                raw.get(
                    "productNeedSatisfaction",
                    raw.get("productNeedConstraintSatisfaction"),
                ),
            ),
            3,
            1,
            5,
        ),
        "constraintRationale": constraint_reason
        or reason
        or "Persona did not provide a constraint rationale.",
        "preferenceSatisfaction": _score(
            raw.get(
                "preferenceSatisfaction",
                raw.get("personalPreferenceSatisfaction"),
            ),
            3,
            1,
            5,
        ),
        "preferenceRationale": preference_reason
        or reason
        or "Persona did not provide a preference rationale.",
        "overallRating": _score(
            raw.get("overallRating", raw.get("overallExperienceRating")), 5, 1, 10
        ),
        "ratingReason": reason or "Persona did not provide a reason.",
        "askedUsefulClarifyingQuestions": _as_bool(
            raw.get(
                "askedUsefulClarifyingQuestions",
                raw.get("askedUsefulClarificationQuestions"),
            )
        ),
        "clarifyingNotes": str(
            raw.get("clarifyingNotes", raw.get("reason", "")) or ""
        ).strip()
        or "Persona did not provide clarification notes.",
    }


def _format_feedback_transcript(transcript: Any) -> str:
    if isinstance(transcript, dict):
        turns = transcript.get("turns")
        if isinstance(turns, list) and turns:
            lines: List[str] = []
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                user = str(turn.get("userMessage", turn.get("user", "")) or "").strip()
                assistant = str(
                    turn.get("assistantMessage", turn.get("assistant", "")) or ""
                ).strip()
                if user:
                    lines.append("you: {}".format(user))
                if assistant:
                    lines.append("agent: {}".format(assistant))
                items = turn.get("groundedItems", turn.get("recommendedItems", []))
                formatted_items = _format_feedback_item_list(items)
                if formatted_items != "(none)":
                    lines.append("  [grounded: {}]".format(formatted_items))
            if lines:
                return "\n".join(lines)

        messages = transcript.get("messages")
        if isinstance(messages, list) and messages:
            lines = []
            role_names = {"user": "you", "assistant": "agent"}
            for message in messages:
                if not isinstance(message, dict):
                    continue
                role = role_names.get(str(message.get("role") or ""))
                content = str(message.get("content") or "").strip()
                if role and content:
                    lines.append("{}: {}".format(role, content))
            if lines:
                return "\n".join(lines)
    return "(empty)"


def _format_feedback_items(application_result: Any) -> str:
    if not isinstance(application_result, dict):
        return "(none)"
    items = application_result.get(
        "groundedItems", application_result.get("recommendedItems", [])
    )
    return _format_feedback_item_list(items)


def _format_feedback_item_list(items: Any) -> str:
    if not isinstance(items, list) or not items:
        return "(none)"
    parts: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("itemId", item.get("id", "")) or "").strip()
        title = str(item.get("title") or "?").strip() or "?"
        if item_id:
            parts.append("{} — {}".format(item_id, title))
    return "; ".join(parts) if parts else "(none)"


def _score(value: Any, default: int, lower: int, upper: int) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = default
    return max(lower, min(upper, score))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _read_text_or_default(path: Path, default: str) -> str:
    if not path.is_file():
        return default
    return path.read_text(encoding="utf-8")


def _read_persona_prompt(path: Path) -> str:
    text = _read_text_or_default(path, "")
    if not text.strip():
        return "Act as the assigned persona."
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        if isinstance(data, dict):
            for key in ("system_prompt", "context", "summary", "description", "name"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    except Exception:
        pass
    parsed = _simple_yaml_mapping(text)
    for key in ("system_prompt", "context", "summary", "description", "name"):
        value = parsed.get(key)
        if value:
            return value
    return text.strip()


def _simple_yaml_mapping(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    current_key: Optional[str] = None
    block_lines: List[str] = []
    for raw in text.splitlines():
        if current_key and (raw.startswith(" ") or raw.startswith("\t")):
            block_lines.append(raw.strip())
            continue
        if current_key:
            result[current_key] = "\n".join(block_lines).strip()
            current_key = None
            block_lines = []
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if value in {"|", ">"}:
            current_key = key
            block_lines = []
        elif key:
            result[key] = value
    if current_key:
        result[current_key] = "\n".join(block_lines).strip()
    return result


def _normalize_anthropic_model(model: str) -> str:
    model = str(model or "").strip()
    if "/" in model and not model.startswith("http"):
        return model.split("/")[-1]
    return model or "claude-haiku-4-5"


def _anthropic_text(payload: Dict[str, Any]) -> str:
    parts: List[str] = []
    for block in payload.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
    return "\n".join(parts).strip()


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("model did not return a JSON object")
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("model did not return a JSON object")
    return data


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        raise SystemExit(1)
