# llm_client.py — LLM backend abstraction for agent function-calling.
# Supports OpenAI-compatible APIs (vLLM, OpenAI, Together, local Ollama).
# Sends messages + tool definitions, parses tool_calls from response.

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass
class LLMConfig:
    base_url: str = "http://localhost:8002/v1"
    api_key: str = ""
    model: str = "Qwen/Qwen3-4B"
    temperature: float = 0.7
    max_tokens: int = 512
    timeout: int = 120

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", "no-key"))


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class LLMClient:
    def __init__(self, config: LLMConfig | None = None):
        self._config = config or LLMConfig()

    @property
    def model(self) -> str:
        return self._config.model

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }

        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = requests.post(
                f"{self._config.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self._config.timeout,
            )
        except requests.exceptions.ConnectionError as e:
            return LLMResponse(error=f"Connection failed: {e}")
        except requests.exceptions.Timeout:
            return LLMResponse(error="Request timed out")

        if resp.status_code != 200:
            return LLMResponse(error=f"HTTP {resp.status_code}: {resp.text[:500]}")

        try:
            data = resp.json()
        except json.JSONDecodeError:
            return LLMResponse(error=f"Invalid JSON response: {resp.text[:200]}")

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content")
        raw_tool_calls = message.get("tool_calls", [])

        tool_calls = []
        for tc in raw_tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            args_str = func.get("arguments", "{}")
            try:
                arguments = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                arguments = {}
            if name:
                tool_calls.append(ToolCall(name=name, arguments=arguments))

        if not tool_calls and content:
            parsed = self._parse_tool_calls_from_text(content)
            if parsed:
                tool_calls = parsed

        return LLMResponse(content=content, tool_calls=tool_calls, raw=data)

    def _parse_tool_calls_from_text(self, text: str) -> list[ToolCall]:
        import re
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        if not cleaned:
            cleaned = text

        calls = []

        array_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if array_match:
            try:
                data = json.loads(array_match.group(0))
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("action") or ""
                            if name:
                                args = item.get("arguments", {})
                                if not args:
                                    args = {}
                                    if "post_id" in item:
                                        args["post_id"] = int(item["post_id"])
                                    elif "target" in item:
                                        try:
                                            args["post_id"] = int(item["target"])
                                        except (ValueError, TypeError):
                                            args["user_id"] = item["target"]
                                    if "content" in item and name in ("create_post", "create_comment"):
                                        args["content"] = item["content"]
                                    if "user_id" in item:
                                        args["user_id"] = int(item["user_id"])
                                calls.append(ToolCall(name=name, arguments=args))
                    if calls:
                        return calls
            except (json.JSONDecodeError, TypeError):
                pass

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and "name" in data:
                calls.append(ToolCall(name=data["name"], arguments=data.get("arguments", {})))
        except (json.JSONDecodeError, TypeError):
            json_match = re.search(r"\{.*\"name\".*\}", cleaned, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    if isinstance(data, dict) and "name" in data:
                        calls.append(ToolCall(name=data["name"], arguments=data.get("arguments", {})))
                except (json.JSONDecodeError, TypeError):
                    pass

        return calls
