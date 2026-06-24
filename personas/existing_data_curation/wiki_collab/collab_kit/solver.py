#!/usr/bin/env python3
"""solver.py — THIS IS THE FILE YOU WORK ON.

`attribute()` takes one profile and a list of persona dimensions and returns a
list of result fields. The harness calls it; everything around it (reading
tasks.jsonl, batching, writing results.jsonl) is provided and you should not
need to touch it.

The DEFAULT extraction method (the prompt in `build_prompt` below) is the same
method the dataset owner uses. You are encouraged to IMPROVE it — a better
prompt, a different model or API client, multi-pass extraction, retrieval,
rules, whatever — AS LONG AS the fields you return conform to
schemas/result.output.schema.json. Run `conformance.py` to check.

Same code for everyone — only your credentials differ:
  --backend mock            zero-setup smoke test (all "unsupported")
  --backend claude-code-acp run the real method on YOUR Claude subscription
                            (just `claude` logged in; nothing to edit)
  --backend codex-acp       run on YOUR Codex subscription (set WIKI_COLLAB_CODEX_CMD)
  --backend anthropic-api   run on YOUR Anthropic API key (set WIKI_COLLAB_ANTHROPIC_CMD)
  --backend openai-api      run on YOUR OpenAI API key (set WIKI_COLLAB_OPENAI_CMD)

The contract for one field:
    {"field_id": <one id from `dimensions`>,
     "value": <one of that id's allowed values, verbatim, or null>,
     "confidence": <number 0..1>,
     "evidence": <short quote copied from profile_text; required if value != null>,
     "assignment_type": "direct" | "structured_claim" | "summary_inference" | "unsupported"}
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

KIT_DIR = Path(__file__).resolve().parent
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))

Profile = dict[str, Any]
Dimension = dict[str, Any]
Field = dict[str, Any]


def build_prompt(profile: Profile, dimensions: list[Dimension]) -> str:
    """The default extraction method. EDIT ME to improve attribution quality."""
    lines = [
        "You are extracting persona-attribution fields from a Wikipedia-derived profile.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim, or null>", '
        '"confidence": 0.0, "evidence": "<short quote copied from profile_text>", '
        '"assignment_type": "direct"}]}',
        "",
        "Allowed assignment_type values:",
        "- direct: explicitly stated in the text.",
        "- structured_claim: derived from structured facts in the input.",
        "- summary_inference: reasonable inference from the profile summary.",
        "- unsupported: not supported by the input.",
        "",
        "Rules:",
        "- Emit exactly one object per dimension listed below.",
        "- value MUST be exactly one of that dimension's allowed values (copy it "
        "verbatim), OR null.",
        "- If the profile does not support a dimension, set value to null and "
        'assignment_type to "unsupported".',
        "- Every non-null value MUST include a short evidence quote copied from "
        "profile_text.",
        "- Do not infer private, sensitive, or psychological traits unless directly "
        "stated; when unsure, prefer null/unsupported.",
        "- Return valid JSON only, with no markdown.",
        "",
        "DIMENSIONS (field_id — label — description — allowed values):",
    ]
    for d in dimensions:
        allowed = " | ".join(str(v) for v in d.get("values", [])) or "(free value)"
        desc = str(d.get("description", "")).strip()
        lines.append(f"- {d['id']} — {d.get('label', d['id'])} — {desc} — [{allowed}]")
    lines += ["", "PROFILE:", profile.get("profile_text", "")]
    return "\n".join(lines)


def _unsupported(dim: Dimension) -> Field:
    return {
        "field_id": str(dim["id"]),
        "value": None,
        "confidence": 0.0,
        "evidence": "",
        "assignment_type": "unsupported",
    }


def _ensure_default_command(backend: str) -> None:
    """Wire the bundled CLI adapter so a collaborator's own auth just works.

    Only fills in a default when the env var is unset, so anyone can override
    with their own wrapper command. `claude-code-acp` uses the bundled
    claude_json_backend.py, which calls the `claude` CLI you logged in with.
    """
    if backend == "claude-code-acp" and not os.environ.get("WIKI_COLLAB_CLAUDE_CMD"):
        adapter = KIT_DIR / "claude_json_backend.py"
        os.environ["WIKI_COLLAB_CLAUDE_CMD"] = f"{sys.executable} {adapter}"


def attribute(
    profile: Profile,
    dimensions: list[Dimension],
    *,
    backend: str = "mock",
    model: str | None = None,
    effort: str = "high",
) -> list[Field]:
    """Return result fields for one profile over the given dimensions."""
    # `mock` produces a conformant all-unsupported answer so you can smoke-test
    # the pipeline (and the contract) with zero model/credential setup.
    if backend == "mock":
        return [_unsupported(d) for d in dimensions]

    # Real run: same prompt for everyone, routed to YOUR chosen backend/auth.
    _ensure_default_command(backend)
    from backends import create_backend  # bundled in this kit; pure stdlib

    prompt = build_prompt(profile, dimensions)
    out = create_backend(backend, model, effort).run(prompt, profile)
    return list(out.fields)
