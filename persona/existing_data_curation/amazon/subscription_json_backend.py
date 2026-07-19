#!/usr/bin/env python3
"""Subscription-backed JSON transport for Amazon persona workflows.

The downstream Amazon extraction and prediction scripts were imported from an
API-oriented workflow. This module keeps their internal chat-completion
response shape while routing the actual model call through local subscription CLIs.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


GENERIC_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
}

JSON_INSTRUCTIONS = (
    "You are a strict JSON endpoint. Return exactly one JSON object matching "
    "the requested task. Do not use markdown, prose, bullets, or code fences."
)

BACKEND_CHOICES = ("codex", "claude")


def default_model_for_backend(backend: str) -> str:
    if backend == "claude":
        return os.environ.get("AMAZON_PERSONA_CLAUDE_MODEL", "opus")
    return os.environ.get("AMAZON_PERSONA_CODEX_MODEL", "gpt-5.5")


def subscription_chat_completion(
    payload: dict[str, Any],
    *,
    backend: str,
    model: str | None = None,
    effort: str = "high",
    timeout: int = 900,
    retries: int = 3,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a JSON chat-completion style payload through a subscription CLI.

    The return value intentionally mimics the chat-completion JSON shape
    consumed by the imported downstream scripts.
    """
    backend = backend.strip().lower()
    if backend not in BACKEND_CHOICES:
        raise ValueError(f"Unsupported subscription backend: {backend}")

    requested_model = model or default_model_for_backend(backend)
    prompt = _prompt_from_payload(payload)
    schema = schema or GENERIC_JSON_SCHEMA
    last_error: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            if backend == "codex":
                model_output = _run_codex(prompt, requested_model, effort, timeout, schema)
            else:
                model_output = _run_claude(prompt, requested_model, effort, timeout, schema)
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(model_output, ensure_ascii=False, sort_keys=True)
                        }
                    }
                ],
                "model": requested_model,
                "subscription_backend": backend,
            }
        except Exception as exc:  # pragma: no cover - exercised with real CLIs.
            last_error = exc
            if attempt < retries - 1:
                time.sleep(min(60, 2**attempt))
                continue
            break
    raise RuntimeError(
        f"Subscription backend {backend!r} failed after {max(1, retries)} attempt(s): {last_error}"
    ) from last_error


def _prompt_from_payload(payload: dict[str, Any]) -> str:
    messages = payload.get("messages") or []
    system_parts: list[str] = []
    user_parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = _stringify_message_content(message.get("content"))
        if message.get("role") == "system":
            system_parts.append(content)
        else:
            user_parts.append(content)
    model = payload.get("model")
    temperature = payload.get("temperature")
    return (
        JSON_INSTRUCTIONS
        + "\n\nSystem instructions:\n"
        + "\n\n".join(part for part in system_parts if part)
        + "\n\nUser payload:\n"
        + "\n\n".join(part for part in user_parts if part)
        + f"\n\nRequested model: {model or 'backend default'}; temperature: {temperature}."
        + "\nReturn compact JSON only."
    )


def _stringify_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def _run_codex(
    prompt: str,
    model: str,
    effort: str,
    timeout: int,
    schema: dict[str, Any],
) -> dict[str, Any]:
    codex_bin = os.environ.get("AMAZON_PERSONA_CODEX_BIN", "codex")
    sandbox = os.environ.get("AMAZON_PERSONA_CODEX_SANDBOX", "read-only")
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        schema_path = tmpdir / "schema.json"
        output_path = tmpdir / "last_message.json"
        schema_path.write_text(json.dumps(schema, separators=(",", ":")), encoding="utf-8")
        cmd = [
            codex_bin,
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            sandbox,
            "--model",
            model,
            "-c",
            f"model_reasoning_effort={effort}",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            "-",
        ]
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or "").strip()
            if proc.stdout.strip():
                detail = (detail + "\n[codex stdout]\n" + proc.stdout.strip()).strip()
            raise RuntimeError((detail or f"codex exited {proc.returncode} with no output")[-4000:])
        raw = output_path.read_text(encoding="utf-8") if output_path.exists() else proc.stdout
        return _extract_json_object(raw)


def _run_claude(
    prompt: str,
    model: str,
    effort: str,
    timeout: int,
    schema: dict[str, Any],
) -> dict[str, Any]:
    claude_bin = os.environ.get("AMAZON_PERSONA_CLAUDE_BIN", "claude")
    cmd = [
        claude_bin,
        "-p",
        "--model",
        _claude_cli_model_name(model),
        "--effort",
        effort,
        "--system-prompt",
        JSON_INSTRUCTIONS,
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, separators=(",", ":")),
    ]
    proc = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip()
        if proc.stdout.strip():
            detail = (detail + "\n[claude stdout]\n" + proc.stdout.strip()).strip()
        raise RuntimeError((detail or f"claude exited {proc.returncode} with no output")[-4000:])
    return _extract_json_object(proc.stdout)


def _claude_cli_model_name(requested_model: str) -> str:
    override = os.environ.get("AMAZON_PERSONA_CLAUDE_CLI_MODEL")
    if override:
        return override
    if requested_model in {"claude-opus-4-8", "claude-opus-4.8"}:
        return "opus"
    return requested_model or default_model_for_backend("claude")


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("empty subscription backend output")
    direct = _loads_object(text)
    if direct is not None:
        return direct

    for line in reversed(text.splitlines()):
        parsed = _loads_object(line.strip())
        if parsed is not None:
            nested = _unwrap_cli_json(parsed)
            if nested is not None:
                return nested

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        parsed = _loads_object(text[start : end + 1])
        if parsed is not None:
            nested = _unwrap_cli_json(parsed)
            if nested is not None:
                return nested
    raise ValueError(f"Could not parse subscription backend JSON output: {text[:1000]}")


def _loads_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        nested = _unwrap_cli_json(parsed)
        return nested if nested is not None else parsed
    return None


def _unwrap_cli_json(payload: dict[str, Any]) -> dict[str, Any] | None:
    structured = payload.get("structured_output")
    if isinstance(structured, dict):
        return structured
    result = payload.get("result")
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        parsed = _loads_object(result.strip())
        if parsed is not None:
            return parsed
    content = payload.get("content") or payload.get("message") or payload.get("text")
    if isinstance(content, str):
        parsed = _loads_object(content.strip())
        if parsed is not None:
            return parsed
    return payload
