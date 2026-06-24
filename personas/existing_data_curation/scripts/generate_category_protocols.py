#!/usr/bin/env python3
"""Generate per-category persona-attribution protocols from the dimension catalog.

The live ``persona_attribution_v1`` protocol only asks the model for 9 ad-hoc
fields, while ``personas/dimensions+new.json`` defines 1339 dimensions across 39
categories. Asking for all 1339 in a single prompt is ~92K tokens and tanks
model quality, so we batch by *category*: one protocol per category, each
injecting only that category's dimensions and their closed-enum allowed values.

Category is simultaneously the UI grouping unit and the dispatch/batching unit,
so the generated protocols line up 1:1 with the frontend's category accordions.

Because every generated protocol lists catalog ``id`` values verbatim, the model
output's ``field_id`` equals the catalog ``dimension.id`` *by construction* — no
post-hoc reconciliation needed for new runs. We still emit a reconciliation map
for the *legacy* 9-field protocol so old results can be interpreted.

Each generated protocol directory is drop-in compatible with
``worker_kit/run_range.py`` and ``scripts/make_wiki_assignments.py``:

    <out>/<slug>/
      prompt.md               # {{input_json}} template, lists the category dims
      input.schema.json       # identical to persona_attribution_v1
      output.schema.json      # same shape; field_id enum-constrained to this category
      protocol_manifest.json  # protocol_id = persona_attribution_<slug>
      category_manifest.json  # machine-readable {id,label,description,values[]} spec

    <out>/index.json          # all categories: slug, protocol_id, dim_count, tokens
    <legacy-out>              # legacy 9-field -> catalog reconciliation map

Usage:
    python personas/existing_data_curation/scripts/generate_category_protocols.py \
        --dimensions personas/dimensions+new.json \
        --out personas/existing_data_curation/protocols/persona_attribution_by_category
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """``"Expertise: Domains"`` -> ``"expertise_domains"`` (safe_name compatible)."""
    slug = SLUG_RE.sub("_", value.strip().lower()).strip("_")
    return slug or "uncategorized"


def estimate_tokens(text: str) -> int:
    """Rough GPT-style token estimate (~4 chars/token). Good enough for budgeting."""
    return len(text) // 4


# The legacy persona_attribution_v1 protocol extracts these 9 fields. Five map
# 1:1 onto catalog ids; the other four do not (verified against the catalog).
LEGACY_FIELDS = [
    "source_entity_type",
    "domain",
    "subject_specialty",
    "role_function",
    "known_for_or_source_work",
    "creator",
    "highest_education",
    "intent",
    "personality_big5_openness",
]

# Catalog Openness facets (IPIP-NEO style). The catalog has no single
# ``big5_openness`` dimension; a domain-level openness score maps to this group.
OPENNESS_FACETS = [
    "big5_imagination",
    "big5_artistic_interest",
    "big5_adventurousness",
    "big5_intellect",
    "big5_liberalism",
]


def load_catalog(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    dims = data.get("dimensions")
    if not isinstance(dims, list) or not dims:
        raise ValueError(f"{path}: expected a non-empty 'dimensions' list")
    return dims


def group_by_category(dims: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Preserve first-seen category order and intra-category dimension order."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for dim in dims:
        groups.setdefault(str(dim.get("category", "Uncategorized")), []).append(dim)
    return groups


def _format_values(values: list[Any]) -> str:
    if not values:
        return "(free value)"
    return " | ".join(str(v) for v in values)


def build_prompt(category: str, dims: list[dict[str, Any]]) -> str:
    lines = [
        "You are extracting persona-attribution fields for ONE category of a "
        "structured persona schema, from a Wikipedia-derived profile.",
        "",
        f"CATEGORY: {category}  ({len(dims)} dimensions)",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        "",
        "{",
        '  "fields": [',
        "    {",
        '      "field_id": "<one id from the DIMENSIONS list below>",',
        '      "value": "<exactly one allowed value for that id, copied verbatim, or null>",',
        '      "confidence": 0.0,',
        '      "evidence": "<short quote copied from profile_text>",',
        '      "assignment_type": "direct"',
        "    }",
        "  ],",
        '  "reported_model": null,',
        '  "model_source": "user_declared",',
        '  "model_confidence": "user_declared"',
        "}",
        "",
        "Allowed assignment_type values:",
        "- direct: explicitly stated in the text.",
        "- structured_claim: derived from structured facts in the input.",
        "- summary_inference: reasonable inference from the profile summary.",
        "- unsupported: not supported by the input.",
        "",
        "Rules:",
        "- Emit exactly one object per dimension listed below, in the same order.",
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
    for dim in dims:
        label = str(dim.get("label", dim["id"]))
        desc = str(dim.get("description", "")).strip()
        allowed = _format_values(list(dim.get("values", [])))
        lines.append(f"- {dim['id']} — {label} — {desc} — [{allowed}]")
    lines += ["", "INPUT:", "", "{{input_json}}", ""]
    return "\n".join(lines)


def build_output_schema(ids: list[str]) -> dict[str, Any]:
    """Same structural shape as persona_attribution_v1, but field_id is enum-locked
    to this category's catalog ids so downstream validation catches drift."""
    return {
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
                        "field_id": {"type": "string", "enum": ids},
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


INPUT_SCHEMA = {
    "type": "object",
    "required": ["global_idx", "task_id", "qid", "title", "source_url", "profile_text"],
    "properties": {
        "global_idx": {"type": "integer"},
        "task_id": {"type": "string"},
        "qid": {"type": "string"},
        "title": {"type": "string"},
        "source_url": {"type": "string"},
        "profile_text": {"type": "string"},
    },
}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_reconciliation(catalog_ids: set[str]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for fid in LEGACY_FIELDS:
        if fid in catalog_ids:
            fields[fid] = {"status": "catalog_direct", "catalog_id": fid}
    fields["source_entity_type"] = {
        "status": "meta",
        "catalog_id": None,
        "note": "Entity typing (person/org/work). Pipeline metadata, not a persona "
        "dimension. Keep on the profile header; exclude from the 1339-dim grid.",
    }
    fields["known_for_or_source_work"] = {
        "status": "unmapped_freeform",
        "catalog_id": None,
        "candidates": ["wiki_field_of_work"],
        "note": "Free-form 'notable work' string with no closed-enum catalog "
        "equivalent. Display as profile metadata, not a dimension cell.",
    }
    fields["creator"] = {
        "status": "meta",
        "catalog_id": None,
        "note": "Provenance of a fictional/derived entity; not a persona dimension.",
    }
    fields["personality_big5_openness"] = {
        "status": "domain_level_split",
        "catalog_id": None,
        "facet_ids": [f for f in OPENNESS_FACETS if f in catalog_ids],
        "note": "The catalog decomposes Big5 Openness into IPIP-NEO facets; there is "
        "no single big5_openness dimension. A domain-level openness score maps to "
        "this facet GROUP, not 1:1.",
    }
    return {
        "description": "Maps the legacy persona_attribution_v1 9-field output onto "
        "the dimensions+new.json catalog. New per-category protocols need no "
        "reconciliation (field_id == catalog id by construction); this only "
        "interprets legacy results.",
        "legacy_protocol": "persona_attribution_v1",
        "fields": fields,
    }


def generate(
    dimensions_path: Path,
    out_dir: Path,
    legacy_out: Path,
    protocol_version: str = "1.0.0",
) -> dict[str, Any]:
    dims = load_catalog(dimensions_path)
    catalog_ids = {str(d["id"]) for d in dims}
    groups = group_by_category(dims)

    index_entries: list[dict[str, Any]] = []
    for category, cat_dims in groups.items():
        slug = slugify(category)
        protocol_id = f"persona_attribution_{slug}"
        proto_dir = out_dir / slug
        ids = [str(d["id"]) for d in cat_dims]

        prompt = build_prompt(category, cat_dims)
        _write_json(proto_dir / "input.schema.json", INPUT_SCHEMA)
        _write_json(proto_dir / "output.schema.json", build_output_schema(ids))
        (proto_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        _write_json(
            proto_dir / "protocol_manifest.json",
            {
                "protocol_id": protocol_id,
                "protocol_version": protocol_version,
                "prompt_file": "prompt.md",
                "input_schema_file": "input.schema.json",
                "output_schema_file": "output.schema.json",
            },
        )
        _write_json(
            proto_dir / "category_manifest.json",
            {
                "category": category,
                "slug": slug,
                "protocol_id": protocol_id,
                "dimension_count": len(cat_dims),
                "dimensions": [
                    {
                        "id": str(d["id"]),
                        "label": str(d.get("label", d["id"])),
                        "description": str(d.get("description", "")),
                        "values": list(d.get("values", [])),
                    }
                    for d in cat_dims
                ],
            },
        )
        index_entries.append(
            {
                "category": category,
                "slug": slug,
                "protocol_id": protocol_id,
                "dimension_count": len(cat_dims),
                "est_prompt_tokens": estimate_tokens(prompt),
            }
        )

    index_entries.sort(key=lambda e: e["dimension_count"], reverse=True)
    _write_json(
        out_dir / "index.json",
        {
            "source_catalog": str(dimensions_path),
            "total_dimensions": len(dims),
            "category_count": len(groups),
            "categories": index_entries,
        },
    )
    _write_json(legacy_out, build_reconciliation(catalog_ids))

    return {
        "total_dimensions": len(dims),
        "category_count": len(groups),
        "max_tokens": max(e["est_prompt_tokens"] for e in index_entries),
        "index": index_entries,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dimensions",
        type=Path,
        default=repo_root / "personas" / "dimensions+new.json",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=repo_root
        / "personas/existing_data_curation/protocols/persona_attribution_by_category",
    )
    ap.add_argument(
        "--legacy-reconciliation",
        type=Path,
        default=repo_root
        / "personas/existing_data_curation/protocols/legacy_field_id_reconciliation.json",
    )
    ap.add_argument("--protocol-version", default="1.0.0")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = generate(
        args.dimensions, args.out, args.legacy_reconciliation, args.protocol_version
    )
    print(
        f"Generated {result['category_count']} category protocols "
        f"covering {result['total_dimensions']} dimensions -> {args.out}"
    )
    print(f"Largest prompt ~{result['max_tokens']:,} tokens. Top categories:")
    for entry in result["index"][:8]:
        print(
            f"  {entry['dimension_count']:>4} dims  "
            f"~{entry['est_prompt_tokens']:>6,} tok  {entry['protocol_id']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
