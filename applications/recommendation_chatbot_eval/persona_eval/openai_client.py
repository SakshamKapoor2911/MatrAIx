from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Protocol

_FENCE = re.compile(r"```(?:json)?\s*(?P<body>\{.*\})\s*```", re.DOTALL)


def coerce_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = _FENCE.search(text)
    if match:
        return json.loads(match.group("body"))
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        return json.loads(text[start:end + 1])
    raise ValueError("could not parse JSON from model output: {!r}".format(text[:200]))


class ChatClient(Protocol):
    def complete_json(self, system: str, user: str) -> Dict[str, Any]: ...


class OpenAIChatClient:
    """OpenAI v1 client (`from openai import OpenAI`) using JSON response mode."""

    def __init__(self, model: str = "gpt-4o-mini", client: Optional[Any] = None,
                 temperature: float = 0.7) -> None:
        self.model = model
        self.temperature = temperature
        if client is None:
            from openai import OpenAI  # lazy: tests inject a fake
            client = OpenAI()
        self._client = client

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        completion = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return coerce_json(completion.choices[0].message.content)
