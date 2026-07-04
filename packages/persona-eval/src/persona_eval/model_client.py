from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from persona_eval.openai_client import OpenAIChatClient, coerce_json


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
    if value.startswith("openai/"):
        return OpenAIChatClient(
            model=value.split("/", 1)[1],
            temperature=temperature,
        )
    if value.startswith("gpt-"):
        return OpenAIChatClient(model=value, temperature=temperature)
    return AnthropicJSONClient(value, temperature=temperature)
