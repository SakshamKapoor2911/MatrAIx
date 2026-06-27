#!/usr/bin/env python3
"""Normalize Claude Code CLI output for the wiki collaboration runner.

The range runner expects an external command that reads the full prompt from
stdin and writes a compact JSON object with a ``fields`` list to stdout. Claude
Code's ``--output-format json`` wraps the model result in CLI metadata, so this
adapter keeps the runner backend simple while still using the user's Claude
subscription.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
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
                    "value": {},
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
}

JSON_SYSTEM_PROMPT = (
    "You are a strict JSON extraction endpoint. Return exactly one JSON object "
    "matching the provided schema. Do not use markdown, prose, tables, bullets, "
    "or code fences."
)

VALID_ASSIGNMENT_TYPES = {
    "direct",
    "structured_claim",
    "summary_inference",
    "unsupported",
}


def _cli_model_name(requested_model: str) -> str:
    override = os.environ.get("WIKI_COLLAB_CLAUDE_CLI_MODEL")
    if override:
        return override
    if requested_model in {"claude-opus-4-8", "claude-opus-4.8"}:
        return "opus"
    return requested_model or "opus"


def _parse_markdown_table(text: str) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or "|" not in line[1:]:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        field_id, value, assignment_type, confidence = cells[:4]
        if field_id.lower() == "field" or set(field_id) <= {"-", ":"}:
            continue
        if assignment_type not in VALID_ASSIGNMENT_TYPES:
            continue
        parsed_value: Any = None if value.lower() in {"null", "none", ""} else value
        try:
            parsed_confidence = float(confidence)
        except ValueError:
            parsed_confidence = 0.0 if assignment_type == "unsupported" else 0.5
        fields.append(
            {
                "field_id": field_id,
                "value": parsed_value,
                "confidence": max(0.0, min(1.0, parsed_confidence)),
                "evidence": value if parsed_value is not None else "unsupported by profile",
                "assignment_type": assignment_type,
            }
        )
    if not fields:
        raise ValueError("no persona fields found in markdown table fallback")
    return {
        "fields": fields,
        "reported_model": None,
        "model_source": "claude_code_cli_markdown_fallback",
        "model_confidence": "fallback",
    }


def _extract_payload(stdout: str) -> dict[str, Any]:
    payload = json.loads(stdout)
    if isinstance(payload, dict) and isinstance(payload.get("fields"), list):
        return payload
    structured_output = payload.get("structured_output") if isinstance(payload, dict) else None
    if isinstance(structured_output, dict) and isinstance(structured_output.get("fields"), list):
        return structured_output

    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, str):
        result = result.strip()
        if result.startswith("```"):
            result = result.strip("`")
            if result.startswith("json"):
                result = result[4:].strip()
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = _parse_markdown_table(result)
        if isinstance(parsed, dict):
            return parsed

    if isinstance(result, dict):
        return result

    raise ValueError("Claude CLI JSON did not contain a parseable result object")


def main() -> int:
    prompt = sys.stdin.read()
    requested_model = os.environ.get("WIKI_COLLAB_REQUESTED_MODEL", "claude-opus-4-8")
    effort = os.environ.get("WIKI_COLLAB_EFFORT", "high")
    claude_bin = os.environ.get("WIKI_COLLAB_CLAUDE_BIN", "claude")
    timeout = int(os.environ.get("WIKI_COLLAB_COMMAND_TIMEOUT", "900"))
    cmd = [
        claude_bin,
        "-p",
        "--model",
        _cli_model_name(requested_model),
        "--effort",
        effort,
        "--system-prompt",
        JSON_SYSTEM_PROMPT,
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(OUTPUT_SCHEMA, separators=(",", ":")),
    ]
    prompt = (
        prompt
        + "\n\nCRITICAL OUTPUT CONTRACT: Return only one JSON object with a fields array. "
        "No markdown table, no prose, no explanation."
    )
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
        # Claude Code with --output-format json usually reports the real failure
        # (auth, model access, unsupported flag, usage limit) as a JSON object on
        # STDOUT with an empty stderr. Surface both so the error isn't blank.
        detail = (proc.stderr or "").strip()
        if proc.stdout.strip():
            detail = (detail + "\n[claude stdout]\n" + proc.stdout.strip()).strip()
        sys.stderr.write((detail or f"claude exited {proc.returncode} with no output")[-4000:])
        return proc.returncode

    try:
        normalized = _extract_payload(proc.stdout)
    except Exception as exc:
        sys.stderr.write(f"Could not parse Claude CLI output: {exc}\n{proc.stdout[:2000]}")
        return 2

    out = {
        "fields": normalized.get("fields", []),
        "reported_model": normalized.get("reported_model") or requested_model,
        "model_source": normalized.get("model_source") or "claude_code_cli",
        "model_confidence": normalized.get("model_confidence") or "declared_or_cli",
    }
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
