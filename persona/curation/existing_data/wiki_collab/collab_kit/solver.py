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
  --backend codex-acp       run on YOUR Codex subscription

The contract for one field:
    {"field_id": <one id from `dimensions`>,
     "value": <one of that id's allowed values, verbatim, or null>,
     "confidence": <number 0..1>,
     "evidence": <short quote copied from profile_text; required if value != null>,
     "assignment_type": "direct" | "structured_claim" | "summary_inference" | "unsupported"}
"""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path
from typing import Any

KIT_DIR = Path(__file__).resolve().parent
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))

Profile = dict[str, Any]
Dimension = dict[str, Any]
Field = dict[str, Any]
ASSIGNMENT_TYPE_PRIORITY = ("direct", "structured_claim", "summary_inference")


def build_prompt(profile: Profile, dimensions: list[Dimension]) -> str:
    """The default extraction method. EDIT ME to improve attribution quality."""
    is_amazon = profile.get("source") == "amazon_reviews_2023"
    if is_amazon:
        opening = (
            "You are extracting persona-attribution fields from Amazon review "
            "evidence for one reviewer."
        )
    else:
        opening = (
            "You are extracting persona-attribution fields from a "
            "Wikipedia-derived profile."
        )
    lines = [
        opening,
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
    ]
    if is_amazon:
        lines += [
            "- Evidence for non-null values must come from the supplied review "
            "title/text in profile_text, not outside knowledge.",
            "- Private, sensitive, demographic, medical, financial, or psychological "
            "attributes require direct statements in the supplied review title/text; "
            "when unsure, prefer null/unsupported.",
        ]
    else:
        lines += [
            "- Do not infer private, sensitive, or psychological traits unless directly "
            "stated; when unsure, prefer null/unsupported.",
        ]
    lines += [
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


def _fold_profiles(profile: Profile) -> list[Profile]:
    """Return one profile per non-empty Amazon CV fold."""
    folds = profile.get("cv_fold_texts")
    if not isinstance(folds, list):
        return [profile]

    fold_profiles: list[Profile] = []
    for idx, fold in enumerate(folds, start=1):
        if not isinstance(fold, dict):
            continue
        raw_text = fold.get("profile_text")
        text = str(raw_text) if raw_text is not None else ""
        if not text.strip():
            continue
        fold_profile = dict(profile)
        fold_profile["profile_text"] = text
        fold_profile["cv_fold_id"] = fold.get("fold_id", idx)
        fold_profiles.append(fold_profile)
    return fold_profiles or [profile]


def _confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _truncate_evidence(evidence_parts: list[str], limit: int = 1200) -> str:
    evidence = "\n\n".join(part for part in evidence_parts if part.strip())
    if len(evidence) <= limit:
        return evidence
    return evidence[: max(0, limit - 3)].rstrip() + "..."


def _merged_assignment_type(assignment_types: list[str]) -> str:
    seen = set(assignment_types)
    for assignment_type in ASSIGNMENT_TYPE_PRIORITY:
        if assignment_type in seen:
            return assignment_type
    return "summary_inference"


def merge_amazon_fold_fields(
    fold_outputs: list[list[Field]],
    dimensions: list[Dimension],
    min_support_folds: int,
    fold_count: int,
) -> list[Field]:
    """Merge per-fold Amazon attribution outputs by exact field/value votes."""
    safe_fold_count = max(1, int(fold_count or 0))
    required_support = max(1, int(min_support_folds))
    dimension_ids = {str(dim["id"]) for dim in dimensions}
    candidates: dict[tuple[str, str], dict[str, Any]] = {}

    for fold_index, fields in enumerate(fold_outputs):
        if not isinstance(fields, list):
            continue
        seen_keys: set[tuple[str, Any]] = set()
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_id = str(field.get("field_id", ""))
            value = field.get("value")
            if field_id not in dimension_ids or value is None:
                continue
            if not isinstance(value, str):
                continue
            if field.get("assignment_type") == "unsupported":
                continue
            key = (field_id, value)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            candidate = candidates.setdefault(
                key,
                {
                    "fold_indexes": set(),
                    "confidences": [],
                    "evidence": [],
                    "assignment_types": [],
                },
            )
            candidate["fold_indexes"].add(fold_index)
            candidate["confidences"].append(_confidence(field.get("confidence")))
            evidence = str(field.get("evidence") or "").strip()
            if evidence:
                candidate["evidence"].append(evidence)
            assignment_type = str(field.get("assignment_type") or "").strip()
            if assignment_type and assignment_type != "unsupported":
                candidate["assignment_types"].append(assignment_type)

    merged: list[Field] = []
    for dim in dimensions:
        field_id = str(dim["id"])
        dim_candidates = [
            (key, candidate)
            for key, candidate in candidates.items()
            if key[0] == field_id and len(candidate["fold_indexes"]) >= required_support
        ]
        if not dim_candidates:
            merged.append(_unsupported(dim))
            continue
        if len(dim_candidates) > 1:
            merged.append(_unsupported(dim))
            continue

        key, selected = max(
            dim_candidates,
            key=lambda item: (
                len(item[1]["fold_indexes"]),
                sum(item[1]["confidences"]) / len(item[1]["confidences"]),
            ),
        )
        support_count = len(selected["fold_indexes"])
        avg_confidence = sum(selected["confidences"]) / len(selected["confidences"])
        assignment_type = _merged_assignment_type(selected["assignment_types"])
        merged.append(
            {
                "field_id": field_id,
                "value": key[1],
                "confidence": round(avg_confidence * (support_count / safe_fold_count), 3),
                "evidence": _truncate_evidence(selected["evidence"]),
                "assignment_type": assignment_type,
            }
        )
    return merged


def _ensure_default_command(backend: str) -> None:
    """Wire the bundled CLI adapter so a collaborator's own auth just works.

    Only fills in a default when the env var is unset, so anyone can override
    with their own wrapper command. `claude-code-acp` uses the bundled
    claude_json_backend.py, which calls the `claude` CLI you logged in with.
    """
    if backend == "claude-code-acp" and not os.environ.get("WIKI_COLLAB_CLAUDE_CMD"):
        adapter = KIT_DIR / "claude_json_backend.py"
        os.environ["WIKI_COLLAB_CLAUDE_CMD"] = " ".join(
            shlex.quote(part) for part in (sys.executable, str(adapter))
        )
    if backend == "codex-acp" and not os.environ.get("WIKI_COLLAB_CODEX_CMD"):
        adapter = KIT_DIR / "codex_json_backend.py"
        os.environ["WIKI_COLLAB_CODEX_CMD"] = " ".join(
            shlex.quote(part) for part in (sys.executable, str(adapter))
        )


def _attribute_single_pass(
    profile: Profile,
    dimensions: list[Dimension],
    backend: str,
    model: str | None,
    effort: str,
) -> list[Field]:
    """Run one non-mock attribution pass against the selected backend."""
    _ensure_default_command(backend)
    from backends import create_backend  # bundled in this kit; pure stdlib

    prompt = build_prompt(profile, dimensions)
    out = create_backend(backend, model, effort).run(prompt, profile)
    return list(out.fields)


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

    if profile.get("source") == "amazon_reviews_2023":
        fold_profiles = _fold_profiles(profile)
        fold_count = len(fold_profiles)
        default_support = min(2, fold_count)
        try:
            min_support = int(profile.get("min_support_folds") or default_support)
        except (TypeError, ValueError):
            min_support = default_support
        min_support = max(1, min_support)
        fold_outputs = [
            _attribute_single_pass(fold_profile, dimensions, backend, model, effort)
            for fold_profile in fold_profiles
        ]
        return merge_amazon_fold_fields(
            fold_outputs,
            dimensions,
            min_support_folds=min_support,
            fold_count=fold_count,
        )

    return _attribute_single_pass(profile, dimensions, backend, model, effort)
