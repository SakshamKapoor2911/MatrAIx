from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict

from persona_eval.openai_client import OpenAIChatClient, coerce_json


class JsonCompletionClient:
    """Small JSON completion client for non-Harbor experiment runners."""

    def __init__(self, model: str) -> None:
        self.model = model

    def complete_json(self, system: str, prompt: str) -> Dict[str, Any]:
        model = self.model
        if model.startswith("anthropic/") or model.startswith("claude"):
            return _anthropic_complete_json(system=system, prompt=prompt, model=model)
        return OpenAIChatClient(model=model, temperature=0.2).complete_json(system, prompt)


def _anthropic_complete_json(*, system: str, prompt: str, model: str) -> Dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic persona models")
    normalized_model = model.split("/", 1)[1] if model.startswith("anthropic/") else model
    payload = {
        "model": normalized_model,
        "max_tokens": 2400,
        "temperature": 0.2,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    request = urllib.request.Request(
        "{}/v1/messages".format(base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError("Anthropic API HTTP {}: {}".format(exc.code, detail)) from exc
    text_parts = []
    for block in data.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(str(block.get("text") or ""))
    return coerce_json("\n".join(text_parts))
