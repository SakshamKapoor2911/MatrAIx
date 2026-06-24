#!/usr/bin/env python3
"""solver.py — THIS IS THE FILE YOU WORK ON.

`attribute()` takes one profile and a list of persona dimensions and returns a
list of result fields. The harness calls it; everything around it (reading
tasks.jsonl, batching, writing results.jsonl) is provided and you should not
need to touch it.

You are free to rewrite the body of `attribute()` however you like — a different
prompt, a different model or API client, multi-pass extraction, retrieval,
rules, whatever — AS LONG AS the fields you return conform to
schemas/result.output.schema.json. Run `conformance.py` to check.

The contract for one field:
    {"field_id": <one id from `dimensions`>,
     "value": <one of that id's allowed values, verbatim, or null>,
     "confidence": <number 0..1>,
     "evidence": <short quote copied from profile_text; required if value != null>,
     "assignment_type": "direct" | "structured_claim" | "summary_inference" | "unsupported"}

The reference implementation below builds a prompt and calls the repo's backend
adapters (mock / claude-code-acp / codex-acp / *-api). Replace it freely.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Make the repo importable so the reference backend works with no PYTHONPATH.
# (If you replace the backend with your own API call, you can delete this.)
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

Profile = dict[str, Any]
Dimension = dict[str, Any]
Field = dict[str, Any]


def build_prompt(profile: Profile, dimensions: list[Dimension]) -> str:
    """Render the instruction sent to the model. EDIT ME to improve extraction."""
    lines = [
        "Extract persona-attribution fields from a Wikipedia-derived profile.",
        "Return ONLY JSON: {\"fields\": [ ... ]}. One object per dimension below.",
        "Each field: {field_id, value, confidence (0..1), evidence (quote from "
        "profile_text), assignment_type}.",
        "value MUST be one of that dimension's allowed values (verbatim) or null.",
        "Use null + assignment_type 'unsupported' when the text does not support it.",
        "assignment_type: direct | structured_claim | summary_inference | unsupported.",
        "",
        "DIMENSIONS (field_id — label — allowed values):",
    ]
    for d in dimensions:
        allowed = " | ".join(str(v) for v in d.get("values", [])) or "(free value)"
        lines.append(f"- {d['id']} — {d.get('label', d['id'])} — [{allowed}]")
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
    # the pipeline (and the contract) with zero model setup.
    if backend == "mock":
        return [_unsupported(d) for d in dimensions]

    # Reference real implementation: prompt -> backend adapter -> fields.
    from personas.existing_data_curation.worker_kit.backends import create_backend

    prompt = build_prompt(profile, dimensions)
    out = create_backend(backend, model, effort).run(prompt, profile)
    return list(out.fields)
