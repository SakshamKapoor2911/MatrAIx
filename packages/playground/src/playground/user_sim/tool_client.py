"""LLM clients with tool-calling support for the user simulator."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Protocol

from playground.user_sim.tools import ToolCall, normalize_sim_message, tool_definitions


class ToolStepClient(Protocol):
    def complete_with_tools(self, messages: List[Dict[str, Any]]) -> List[ToolCall]: ...


class FakeToolStepClient:
    """Test double returning a scripted sequence of tool calls."""

    def __init__(self, steps: List[List[ToolCall]]) -> None:
        self._steps = list(steps)
        self.calls: List[List[Dict[str, Any]]] = []

    def complete_with_tools(self, messages: List[Dict[str, Any]]) -> List[ToolCall]:
        self.calls.append(list(messages))
        if not self._steps:
            return [ToolCall("end_conversation", {"reason": "give_up"})]
        return self._steps.pop(0)


class OpenAIToolStepClient:
    def __init__(
        self,
        model: str,
        *,
        client: Optional[Any] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
    ) -> None:
        self.model = model
        self.temperature = temperature
        if client is None:
            from openai import OpenAI

            client_kwargs: Dict[str, Any] = {}
            if api_key is not None:
                client_kwargs["api_key"] = api_key
            if base_url is not None:
                client_kwargs["base_url"] = base_url
            client = OpenAI(**client_kwargs)
        self._client = client

    def complete_with_tools(self, messages: List[Dict[str, Any]]) -> List[ToolCall]:
        completion = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=messages,
            tools=tool_definitions(),
            tool_choice="auto",
        )
        message = completion.choices[0].message
        calls: List[ToolCall] = []
        for tool_call in message.tool_calls or []:
            fn = tool_call.function
            calls.append(ToolCall(fn.name, _coerce_args(fn.arguments)))
        if not calls:
            text = normalize_sim_message(str(message.content or ""))
            if text:
                calls.append(ToolCall("send_message", {"message": text}))
        return calls


class AnthropicToolStepClient:
    def __init__(
        self,
        model: str,
        *,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.api_key = (
            api_key
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("CLAUDE_API_KEY")
            or ""
        ).strip()
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY or CLAUDE_API_KEY is required for persona model {}".format(
                    model
                )
            )

    def complete_with_tools(self, messages: List[Dict[str, Any]]) -> List[ToolCall]:
        from playground.user_sim.tools import anthropic_tool_definitions

        system_parts: List[str] = []
        convo: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get("role")
            content = str(message.get("content") or "")
            if role == "system":
                system_parts.append(content)
            elif role in {"user", "assistant"}:
                convo.append({"role": role, "content": content})
        body = {
            "model": self.model,
            "max_tokens": 1200,
            "temperature": self.temperature,
            "system": "\n\n".join(system_parts),
            "messages": convo,
            "tools": anthropic_tool_definitions(),
        }
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                "Anthropic tool request failed: HTTP {} {}".format(exc.code, detail[:500])
            ) from exc
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("Anthropic tool request failed: {}".format(exc)) from exc

        calls: List[ToolCall] = []
        text_parts: List[str] = []
        for block in payload.get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                calls.append(ToolCall(str(block.get("name") or ""), dict(block.get("input") or {})))
            elif block.get("type") == "text":
                text_parts.append(str(block.get("text") or ""))
        if not calls and text_parts:
            text = normalize_sim_message("\n".join(text_parts))
            if text:
                calls.append(ToolCall("send_message", {"message": text}))
        return calls


def _coerce_args(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def build_tool_step_client(model: str, *, temperature: float = 0.7) -> ToolStepClient:
    from playground.model_client import dashscope_openai_client_kwargs

    value = (model or "openai/gpt-4o-mini").strip()
    if value.startswith("anthropic/"):
        return AnthropicToolStepClient(value.split("/", 1)[1], temperature=temperature)
    if value.startswith("dashscope/"):
        kwargs = dashscope_openai_client_kwargs(value)
        return OpenAIToolStepClient(
            kwargs["model"],
            api_key=kwargs["api_key"],
            base_url=kwargs["base_url"],
            temperature=temperature,
        )
    if value.startswith("openai/"):
        return OpenAIToolStepClient(value.split("/", 1)[1], temperature=temperature)
    if value.startswith("gpt-"):
        return OpenAIToolStepClient(value, temperature=temperature)
    return AnthropicToolStepClient(value, temperature=temperature)
