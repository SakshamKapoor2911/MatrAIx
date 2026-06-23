#!/usr/bin/env python3
"""Normalize Codex CLI output for the wiki collaboration runner.

The range runner's command-adapter contract is intentionally simple: read the
rendered extraction prompt from stdin and write one JSON object containing a
``fields`` list to stdout. This wrapper lets collaborators use a Codex CLI
subscription while preserving that contract.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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

JSON_CONTRACT = (
    "Return exactly one JSON object matching the provided output schema. "
    "Do not use markdown, prose, bullets, tables, or code fences."
)

VALID_ASSIGNMENT_TYPES = {
    "direct",
    "structured_claim",
    "summary_inference",
    "unsupported",
}


def _cli_effort(effort: str) -> str:
    normalized = (effort or "xhigh").lower()
    if normalized == "max":
        return "xhigh"
    if normalized in {"low", "medium", "high", "xhigh"}:
        return normalized
    return "xhigh"


def build_codex_command(
    *,
    codex_bin: str,
    requested_model: str,
    effort: str,
    schema_path: Path,
    last_message_path: Path,
) -> list[str]:
    return [
        codex_bin,
        "exec",
        "-",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-rules",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(last_message_path),
        "-m",
        requested_model,
        "-c",
        f'model_reasoning_effort="{_cli_effort(effort)}"',
    ]


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    stripped = stripped.strip("`").strip()
    if stripped.startswith("json"):
        stripped = stripped[4:].strip()
    return stripped


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
        "model_source": "codex_cli_markdown_fallback",
        "model_confidence": "fallback",
    }


def _extract_payload(text: str) -> dict[str, Any]:
    stripped = _strip_code_fence(text)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = _parse_markdown_table(stripped)
    if not isinstance(payload, dict) or not isinstance(payload.get("fields"), list):
        raise ValueError("Codex CLI output must be a JSON object with a fields list")
    return payload


def main() -> int:
    prompt = sys.stdin.read()
    requested_model = os.environ.get("WIKI_COLLAB_REQUESTED_MODEL", "gpt-5.5")
    effort = os.environ.get("WIKI_COLLAB_EFFORT", "max")
    codex_bin = os.environ.get("WIKI_COLLAB_CODEX_BIN", "codex")
    timeout = int(os.environ.get("WIKI_COLLAB_COMMAND_TIMEOUT", "900"))

    with tempfile.TemporaryDirectory(prefix="wiki-collab-codex-") as tmp:
        tmp_path = Path(tmp)
        schema_path = tmp_path / "output.schema.json"
        last_message_path = tmp_path / "last-message.json"
        schema_path.write_text(
            json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        cmd = build_codex_command(
            codex_bin=codex_bin,
            requested_model=requested_model,
            effort=effort,
            schema_path=schema_path,
            last_message_path=last_message_path,
        )
        prompt = prompt.rstrip() + "\n\n" + JSON_CONTRACT + "\n"
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
            sys.stderr.write(proc.stderr[-4000:] or proc.stdout[-4000:])
            return proc.returncode
        output_text = (
            last_message_path.read_text(encoding="utf-8")
            if last_message_path.exists()
            else proc.stdout
        )

    try:
        normalized = _extract_payload(output_text)
    except Exception as exc:
        sys.stderr.write(f"Could not parse Codex CLI output: {exc}\n{output_text[:2000]}")
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
