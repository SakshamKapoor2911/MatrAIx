"""Concrete LLM provider backends + the selection factory (Protocol.md §7).

Each provider is a thin translator at the edge of the reference agent's tool-use
loop: it consumes the neutral `complete(system, messages, tools)` surface
(mircoverse/agents/llm_types.py) and speaks one vendor's native wire dialect. The
engine never imports any of this on the hot path (§7.3) — only the participant-side
reference agent does.

Importing this package pulls in the provider *classes* (which lazy-import their
vendor SDKs only when no client is injected) and the `make_provider` factory, which
maps human-friendly names/aliases to a provider without importing any SDK itself.
"""

from __future__ import annotations

from mircoverse.agents.providers.anthropic_provider import AnthropicProvider
from mircoverse.agents.providers.bedrock_provider import BedrockProvider
from mircoverse.agents.providers.factory import make_provider
from mircoverse.agents.providers.openai_provider import (
    OpenAICompatibleProvider,
    OpenAIProvider,
)

__all__ = [
    "AnthropicProvider",
    "OpenAIProvider",
    "OpenAICompatibleProvider",
    "BedrockProvider",
    "make_provider",
]
