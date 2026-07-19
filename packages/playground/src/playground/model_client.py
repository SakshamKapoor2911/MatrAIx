from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from playground.openai_client import OpenAIChatClient, coerce_json

DASHSCOPE_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def dashscope_model_id(model: str) -> str:
    """Return the bare DashScope model id from a Harbor persona model string."""
    value = (model or "").strip()
    if value.startswith("dashscope/"):
        return value.split("/", 1)[1]
    return value


def dashscope_openai_client_kwargs(model: str) -> Dict[str, str]:
    """OpenAI SDK kwargs for Alibaba DashScope compatible-mode chat."""
    api_key = (os.environ.get("DASHSCOPE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is required for persona model {!r}".format(model)
        )
    base_url = (
        os.environ.get("DASHSCOPE_API_BASE")
        or os.environ.get("LLM_BASE_URL")
        or DASHSCOPE_DEFAULT_BASE_URL
    ).strip()
    return {
        "model": dashscope_model_id(model),
        "api_key": api_key,
        "base_url": base_url,
    }


class AnthropicJSONClient:
    """Minimal Anthropic Messages client that returns a JSON object."""

    def __init__(
        self,
        model: str,
        *,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.model = model
        self.api_key = (
            api_key
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("CLAUDE_API_KEY")
            or ""
        ).strip()
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY or CLAUDE_API_KEY is required for persona model {}".format(
                    model
                )
            )

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        body = {
            "model": self.model,
            "max_tokens": 1200,
            "temperature": self.temperature,
            "system": system,
            "messages": [
                {
                    "role": "user",
                    "content": user
                    + "\n\nReturn only a valid JSON object. Do not include markdown.",
                }
            ],
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
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                "Anthropic persona model request failed: HTTP {} {}".format(
                    exc.code, detail[:500]
                )
            ) from exc
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Anthropic persona model request failed: {}".format(exc)
            ) from exc

        text_parts = []
        for block in payload.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text") or ""))
        return coerce_json("\n".join(text_parts))


def build_json_client(model: str, *, temperature: float = 0.7) -> Any:
    """Return a JSON-mode client for a configured persona model string."""
    value = (model or "openai/gpt-4o-mini").strip()
    if value.startswith("anthropic/"):
        return AnthropicJSONClient(value.split("/", 1)[1], temperature=temperature)
    if value.startswith("dashscope/"):
        kwargs = dashscope_openai_client_kwargs(value)
        return OpenAIChatClient(
            model=kwargs["model"],
            api_key=kwargs["api_key"],
            base_url=kwargs["base_url"],
            temperature=temperature,
        )
    if value.startswith("openai/"):
        return OpenAIChatClient(
            model=value.split("/", 1)[1],
            temperature=temperature,
        )
    if value.startswith("gpt-"):
        return OpenAIChatClient(model=value, temperature=temperature)
    return AnthropicJSONClient(value, temperature=temperature)
