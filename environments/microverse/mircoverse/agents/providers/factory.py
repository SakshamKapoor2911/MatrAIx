"""Name/alias -> LLMProvider selection (Protocol.md §7).

`make_provider` is the single entry point a launcher uses to pick a model backend
by a human-friendly name. It maps case-insensitive aliases onto the four concrete
providers and threads configuration through with one rule: explicit keyword
arguments are AUTHORITATIVE; anything absent falls back to environment variables
(MIRCOVERSE_LLM_* and the provider-native key vars). A launcher can therefore say
`make_provider("openai", "gpt-4o")` and let MIRCOVERSE_OPENAI_API_KEY / env supply
the rest, or override any of it explicitly.

The provider classes are imported LAZILY inside `make_provider`, so importing this
factory module never imports a vendor SDK (the classes themselves further defer
their SDK import to first use when no client is injected). The engine never touches
any of this on the hot path (§7.3).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime/SDK import
    from mircoverse.agents.llm_types import LLMProvider

# Case-insensitive alias -> canonical provider key. Kept as a single map so the
# error message for an unknown name can enumerate exactly what is accepted.
_ALIASES: dict[str, str] = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "openai": "openai",
    "oai": "openai",
    "gpt": "openai",
    "bedrock": "bedrock",
    "aws": "bedrock",
    "other": "compat",
    "openai-compatible": "compat",
    "compat": "compat",
    "ollama": "compat",
    "groq": "compat",
    "together": "compat",
    "openrouter": "compat",
}


def make_provider(name: str, model: str, **kw: object) -> "LLMProvider":
    """Build a concrete `LLMProvider` for `name`/`model`, kwargs over env.

    `name` is matched case-insensitively against the accepted aliases:

        anthropic : "claude", "anthropic"
        openai    : "openai", "oai", "gpt"
        bedrock   : "bedrock", "aws"
        compat    : "other", "openai-compatible", "compat",
                    "ollama", "groq", "together", "openrouter"

    The OpenAI-compatible backend requires a `base_url` (passed in `kw` or via
    MIRCOVERSE_LLM_BASE_URL); omitting it raises a clear `ValueError`. An unknown
    `name` raises a `ValueError` listing every supported name. Providers are
    imported lazily here so importing this module pulls in no vendor SDK; any
    injected `client=` is forwarded so a fake client keeps tests SDK-free.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "make_provider(name, model): `name` must be a non-empty provider name; "
            f"supported names are: {_supported()}."
        )

    key = _ALIASES.get(name.strip().lower())
    if key is None:
        raise ValueError(
            f"Unknown LLM provider name {name!r}. Supported names are: {_supported()}."
        )

    if key == "anthropic":
        from mircoverse.agents.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=model, **kw)  # type: ignore[arg-type]

    if key == "openai":
        from mircoverse.agents.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(model=model, **kw)  # type: ignore[arg-type]

    if key == "bedrock":
        from mircoverse.agents.providers.bedrock_provider import BedrockProvider

        return BedrockProvider(model=model, **kw)  # type: ignore[arg-type]

    # key == "compat": OpenAI-compatible backend (Ollama/Groq/Together/OpenRouter/…).
    base_url = kw.pop("base_url", None) or os.getenv("MIRCOVERSE_LLM_BASE_URL")
    if not base_url:
        raise ValueError(
            "The OpenAI-compatible provider requires a `base_url` (pass base_url=... "
            "to make_provider or set MIRCOVERSE_LLM_BASE_URL)."
        )
    from mircoverse.agents.providers.openai_provider import OpenAICompatibleProvider

    return OpenAICompatibleProvider(model=model, base_url=base_url, **kw)  # type: ignore[arg-type]


def _supported() -> str:
    """Sorted, comma-joined list of accepted alias names for error messages."""
    return ", ".join(sorted(_ALIASES))
