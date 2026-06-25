#!/usr/bin/env python3
"""Backend adapters used by the offline range runner."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import subprocess
from typing import Any


RUNNER_VERSION = "0.1.0"
DEFAULT_EFFORT = "high"
DEFAULT_MODELS = {
    "mock": "mock-model",
    "claude-code-acp": "claude-opus-4-8",
    "codex-acp": "gpt-5.5",
}


class BackendError(RuntimeError):
    pass


@dataclass
class BackendOutput:
    fields: list[dict[str, Any]]
    raw_response: str
    reported_model: str | None
    model_source: str
    model_confidence: str


class BaseBackend:
    name = "base"
    provider = "unknown"
    auth_mode = "unknown"

    def __init__(self, model: str | None = None, effort: str = DEFAULT_EFFORT):
        self.model = model or DEFAULT_MODELS.get(self.name, "unknown")
        self.effort = effort or DEFAULT_EFFORT

    def run(self, prompt: str, input_record: dict[str, Any]) -> BackendOutput:
        raise NotImplementedError


class MockBackend(BaseBackend):
    name = "mock"
    provider = "mock"
    auth_mode = "none"

    def run(self, prompt: str, input_record: dict[str, Any]) -> BackendOutput:
        title = input_record.get("title", "")
        return BackendOutput(
            fields=[
                {
                    "field_id": "source_entity_type",
                    "value": "wiki_person",
                    "confidence": 1.0,
                    "evidence": str(title),
                    "assignment_type": "direct",
                }
            ],
            raw_response=json.dumps({"mock": True}, sort_keys=True),
            reported_model=self.model,
            model_source="runner",
            model_confidence="exact",
        )


class ExternalCommandBackend(BaseBackend):
    provider = "external"
    auth_mode = "external"
    env_var = "WIKI_COLLAB_COMMAND"

    def run(self, prompt: str, input_record: dict[str, Any]) -> BackendOutput:
        command = os.environ.get(self.env_var, "").strip()
        if not command:
            raise BackendError(
                f"{self.name} requires {self.env_var}; command must read prompt from stdin and emit JSON."
            )
        proc = subprocess.run(
            command,
            input=prompt,
            text=True,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=int(os.environ.get("WIKI_COLLAB_COMMAND_TIMEOUT", "600")),
            check=False,
            env={
                **os.environ,
                "WIKI_COLLAB_REQUESTED_MODEL": self.model,
                "WIKI_COLLAB_EFFORT": self.effort,
            },
        )
        if proc.returncode != 0:
            raise BackendError(f"{self.name} exited {proc.returncode}: {proc.stderr[-2000:]}")
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise BackendError(f"{self.name} returned non-JSON stdout: {proc.stdout[:500]}") from exc
        fields = payload.get("fields")
        if not isinstance(fields, list):
            raise BackendError(f"{self.name} JSON must contain a fields list")
        return BackendOutput(
            fields=fields,
            raw_response=proc.stdout,
            reported_model=payload.get("reported_model") or self.model,
            model_source=payload.get("model_source") or "user_declared",
            model_confidence=payload.get("model_confidence") or "user_declared",
        )


class ClaudeCodeAcpBackend(ExternalCommandBackend):
    name = "claude-code-acp"
    provider = "anthropic"
    auth_mode = "subscription_or_api_key"
    env_var = "WIKI_COLLAB_CLAUDE_CMD"


class CodexAcpBackend(ExternalCommandBackend):
    name = "codex-acp"
    provider = "openai"
    auth_mode = "subscription_or_api_key"
    env_var = "WIKI_COLLAB_CODEX_CMD"


BACKENDS = {
    "mock": MockBackend,
    "claude-code-acp": ClaudeCodeAcpBackend,
    "codex-acp": CodexAcpBackend,
}


def create_backend(
    name: str, model: str | None = None, effort: str = DEFAULT_EFFORT
) -> BaseBackend:
    try:
        backend_cls = BACKENDS[name]
    except KeyError as exc:
        available = ", ".join(sorted(BACKENDS))
        raise ValueError(f"unknown backend {name!r}; available: {available}") from exc
    return backend_cls(model, effort)
