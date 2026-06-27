#!/usr/bin/env python3
"""Normalize Codex CLI output for the wiki collaboration runner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["fields"],
    "properties": {
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "field_id",
                    "value",
                    "confidence",
                    "evidence",
                    "assignment_type",
                ],
                "properties": {
                    "field_id": {"type": "string"},
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence": {"type": "string"},
                    "assignment_type": {
                        "type": "string",
                        "enum": [
                            "direct",
                            "structured_claim",
                            "summary_inference",
                            "unsupported",
                        ],
                    },
                },
            },
        },
        "reported_model": {"type": ["string", "null"]},
        "model_source": {"type": "string"},
        "model_confidence": {"type": "string"},
    },
    "additionalProperties": True,
}

JSON_INSTRUCTIONS = (
    "You are a strict JSON extraction endpoint. Return exactly one JSON object "
    "matching the schema. Do not edit files, run commands, use markdown, or add "
    "commentary."
)


def _extract_payload(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("empty Codex output")
    try:
        payload = json.loads(text)
        if isinstance(payload, dict) and isinstance(payload.get("fields"), list):
            return payload
    except json.JSONDecodeError:
        pass

    # Fallback for JSONL event output: keep the last parseable object with fields.
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            if isinstance(payload.get("fields"), list):
                return payload
            message = payload.get("message") or payload.get("content") or payload.get("text")
            if isinstance(message, str):
                try:
                    nested = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if isinstance(nested, dict) and isinstance(nested.get("fields"), list):
                    return nested
    raise ValueError(f"Codex output did not contain a fields object: {text[:500]}")


def main() -> int:
    prompt = sys.stdin.read()
    requested_model = os.environ.get("WIKI_COLLAB_REQUESTED_MODEL", "gpt-5.5")
    effort = os.environ.get("WIKI_COLLAB_EFFORT", "high")
    codex_bin = os.environ.get("WIKI_COLLAB_CODEX_BIN", "codex")
    timeout = int(os.environ.get("WIKI_COLLAB_COMMAND_TIMEOUT", "900"))

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        schema_path = tmpdir / "schema.json"
        output_path = tmpdir / "last_message.json"
        schema_path.write_text(json.dumps(OUTPUT_SCHEMA, separators=(",", ":")), encoding="utf-8")
        full_prompt = (
            JSON_INSTRUCTIONS
            + f"\nRequested reasoning effort: {effort}.\n\n"
            + prompt
            + "\n\nCRITICAL OUTPUT CONTRACT: Return only one JSON object with a fields array."
        )
        cmd = [
            codex_bin,
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--model",
            requested_model,
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
            input=full_prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            # Surface stdout too — Codex often reports the real error (auth,
            # model access, sandbox) there with an empty stderr.
            detail = (proc.stderr or "").strip()
            if proc.stdout.strip():
                detail = (detail + "\n[codex stdout]\n" + proc.stdout.strip()).strip()
            sys.stderr.write((detail or f"codex exited {proc.returncode} with no output")[-4000:])
            return proc.returncode

        raw = output_path.read_text(encoding="utf-8") if output_path.exists() else proc.stdout
        try:
            normalized = _extract_payload(raw)
        except Exception as exc:
            sys.stderr.write(f"Could not parse Codex CLI output: {exc}\n{raw[:2000]}")
            return 2

    out = {
        "fields": normalized.get("fields", []),
        "reported_model": normalized.get("reported_model") or requested_model,
        "model_source": normalized.get("model_source") or "codex_cli",
        "model_confidence": normalized.get("model_confidence") or "declared_or_cli",
    }
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
