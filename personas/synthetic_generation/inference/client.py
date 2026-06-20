"""Minimal multi-provider LLM client (Task 2.2), backed by LiteLLM.

LiteLLM routes by the `model` string (e.g. "gpt-4o", "deepseek/deepseek-chat",
"anthropic/claude-opus-4-8") and reads the standard provider API-key env vars
(OPENAI_API_KEY, DEEPSEEK_API_KEY, ANTHROPIC_API_KEY, ...) automatically — so we do
NOT manage base_url or per-provider SDKs. The only models that still need an endpoint
are OpenAI-compatible / self-hosted ones (set `api_base` in the registry).

Requires: pip install litellm pyyaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
import litellm

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "config.yaml"


class LLMClient:
    """Loads a model registry (YAML) and generates via LiteLLM."""

    def __init__(self, config_path: str | Path | None = None):
        cfg = yaml.safe_load(Path(config_path or DEFAULT_CONFIG).read_text(encoding="utf-8")) or {}
        self.defaults: dict[str, Any] = cfg.get("defaults", {}) or {}
        self.models: dict[str, dict] = cfg.get("models", {}) or {}

    def generate(self, model_name: str, system: str, user: str, **overrides: Any) -> str:
        """Return the model's text completion for (system, user)."""
        if model_name not in self.models:
            raise KeyError(f"Unknown model '{model_name}'. Known: {sorted(self.models)}")
        spec = self.models[model_name]
        params = {**self.defaults, **overrides}
        resp = litellm.completion(
            model=spec["model"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            api_base=spec.get("api_base"),  # None for natively-supported providers
            **params,
        )
        return resp.choices[0].message.content or ""
