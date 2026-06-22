"""Tests for the provider selection factory (mircoverse/agents/providers/factory.py).

These cover Protocol.md §7's launcher entry point: aliases map case-insensitively to
the right concrete provider, the OpenAI-compatible backend insists on a `base_url`,
and an unknown name fails loudly. Every constructed provider is given an injected
fake `client`, so no vendor SDK is imported and no network/API key is touched —
keeping the suite runnable with none of anthropic/openai/boto3 installed.
"""

from __future__ import annotations

import pytest

from mircoverse.agents.providers import (
    BedrockProvider,
    OpenAIProvider,
    make_provider,
)


class _FakeClient:
    """Stand-in for a vendor SDK client; its presence suppresses any lazy SDK import."""


def test_oai_alias_returns_openai_provider() -> None:
    """`make_provider("oai", ...)` builds an OpenAIProvider from an injected client."""
    provider = make_provider("oai", "gpt-4o", client=_FakeClient())
    assert isinstance(provider, OpenAIProvider)


def test_gpt_alias_is_case_insensitive() -> None:
    """Aliases match case-insensitively (e.g. 'GPT' -> OpenAIProvider)."""
    provider = make_provider("GPT", "gpt-4o", client=_FakeClient())
    assert isinstance(provider, OpenAIProvider)


def test_aws_alias_returns_bedrock_provider() -> None:
    """`make_provider("aws", ...)` builds a BedrockProvider from an injected client."""
    provider = make_provider(
        "aws", "anthropic.claude-3-5-sonnet-20240620-v1:0", client=_FakeClient()
    )
    assert isinstance(provider, BedrockProvider)


def test_compat_without_base_url_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """The OpenAI-compatible backend requires a base_url; omitting it is a ValueError."""
    monkeypatch.delenv("MIRCOVERSE_LLM_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="base_url"):
        make_provider("other", "x")


def test_unknown_name_raises_value_error_listing_supported() -> None:
    """An unknown provider name raises a ValueError that enumerates supported names."""
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        make_provider("definitely-not-a-provider", "x")
