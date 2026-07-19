#!/usr/bin/env python3
"""Reusable §8 post-processor — normalize a raw 1290-dim extraction into its faithful,
schema-consistent form, applying `BENCHMARK.md` §8.

The output-side counterpart to `crosswalk_engine.py`: given one persona's raw extraction
`fields`, it returns exactly `len(order)` field objects in schema order, with §8 applied.
No LLM, no network — pure transform, so it's fully unit-testable.

Rules (faithful — demote unreliable inferences, never invent):
  * off-allowed `value` (not in the dim's allowed set)          -> null, `unsupported`
  * null / empty `value`                                        -> null, `unsupported`
  * non-null value whose `evidence` is an argument-from-absence
    ("no mention of…") or — when `profile_text` is given — is
    not a verbatim quote from it                                -> `unsupported`, evidence dropped
  * grounded positive (value in allowed + real quote)           -> kept as-is
  * exact `observed` dims from the rule layer                   -> value set, `direct`, conf 1.0
  * dims the model never emitted                                -> null, `unsupported`

Run `python postprocess_engine.py --selftest`.
"""

import argparse
import json
import re
import sys

SUPPORTED_AT = {"direct", "structured_claim", "summary_inference"}
_ABSENCE = re.compile(
    r"no (mention|indication|reference|evidence|sign|record|major|significant|clear)"
    r"|not (mention|indicat|stat|explicit|specif|discuss)|absence of",
    re.I,
)


def load_schema(schema_path):
    """Return (order, allowed) from a dimensions.json schema."""
    dims = json.load(open(schema_path))["dimensions"]
    order = [d["id"] for d in dims]
    allowed = {d["id"]: set(d.get("values") or []) for d in dims}
    return order, allowed


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _grounded(evidence, profile):
    e = _norm(evidence)
    if not e:
        return False
    if e in profile:
        return True
    return len(e) > 30 and (e[:30] in profile or e[-30:] in profile)


def _null_field(fid):
    return {
        "field_id": fid,
        "value": None,
        "confidence": 0.0,
        "evidence": "",
        "description": "",
        "assignment_type": "unsupported",
    }


def normalize(fields, order, allowed, profile_text=None, observed=None):
    """Apply §8 to one persona's raw `fields`; return `len(order)` field objects in order."""
    profile = _norm(profile_text) if profile_text is not None else None
    by_id = {f.get("field_id"): f for f in fields if f.get("field_id") in allowed}

    out = []
    for fid in order:
        src = by_id.get(fid)
        if src is None:
            out.append(_null_field(fid))
            continue
        value = src.get("value")
        if value in (None, "null", "") or value not in allowed[fid]:
            out.append(_null_field(fid))  # null or off-allowed -> unsupported null
            continue
        evidence = src.get("evidence", "")
        ungrounded = bool(_ABSENCE.search(evidence or ""))
        if profile is not None and not _grounded(evidence, profile):
            ungrounded = True
        at = src.get("assignment_type", "unsupported")
        out.append(
            {
                "field_id": fid,
                "value": value,
                "confidence": src.get("confidence", 0.0),
                "evidence": "" if ungrounded else evidence,
                "description": src.get("description", ""),
                "assignment_type": "unsupported" if ungrounded else at,
            }
        )

    if observed:
        by_order = {f["field_id"]: f for f in out}
        for dim, val in observed.items():
            if dim in by_order and val in allowed.get(dim, set()):
                f = by_order[dim]
                f["value"] = val
                f["assignment_type"] = "direct"
                f["confidence"] = 1.0
    return out


def _selftest():
    order = [
        "age_bracket",
        "gender_identity",
        "demo_veteran_status",
        "trait_openness",
        "urbanicity",
    ]
    allowed = {
        "age_bracket": {"25-34"},
        "gender_identity": {"Man", "Woman"},
        "demo_veteran_status": {"Civilian", "Veteran"},
        "trait_openness": {"High", "Low"},
        "urbanicity": {"Urban", "Rural"},
    }
    profile = "A 25-34-year-old woman. She loves trying new things and travel."
    fields = [
        # grounded positive -> kept
        {
            "field_id": "gender_identity",
            "value": "Woman",
            "confidence": 0.9,
            "evidence": "A 25-34-year-old woman.",
            "description": "",
            "assignment_type": "direct",
        },
        # grounded positive (inference) -> kept
        {
            "field_id": "trait_openness",
            "value": "High",
            "confidence": 0.7,
            "evidence": "loves trying new things",
            "description": "",
            "assignment_type": "summary_inference",
        },
        # argument-from-absence -> demoted to unsupported, evidence dropped
        {
            "field_id": "demo_veteran_status",
            "value": "Civilian",
            "confidence": 1.0,
            "evidence": "No mention of military service",
            "description": "",
            "assignment_type": "direct",
        },
        # off-allowed value -> nulled
        {
            "field_id": "age_bracket",
            "value": "999",
            "confidence": 0.5,
            "evidence": "A 25-34-year-old woman.",
            "description": "",
            "assignment_type": "direct",
        },
        # 'urbanicity' intentionally absent from fields -> null field
    ]
    observed = {"age_bracket": "25-34"}  # exact rule-layer value overrides
    out = normalize(fields, order, allowed, profile_text=profile, observed=observed)

    assert len(out) == len(order), len(out)
    byid = {f["field_id"]: f for f in out}
    assert byid["gender_identity"]["assignment_type"] == "direct"
    assert (
        byid["trait_openness"]["value"] == "High" and byid["trait_openness"]["evidence"]
    )
    assert byid["demo_veteran_status"]["assignment_type"] == "unsupported"
    assert byid["demo_veteran_status"]["evidence"] == ""  # dropped
    assert byid["demo_veteran_status"]["value"] == "Civilian"  # demoted, not deleted
    assert (
        byid["age_bracket"]["value"] == "25-34"
    )  # observed overlay beat the off-allowed junk
    assert byid["age_bracket"]["assignment_type"] == "direct"
    assert byid["urbanicity"]["value"] is None  # never emitted -> null
    # every record has all dims, valid assignment_types, and no off-allowed values
    for f in out:
        assert f["value"] is None or f["value"] in allowed[f["field_id"]]
        assert f["assignment_type"] in SUPPORTED_AT | {"unsupported"}
    print(
        f"postprocess_engine self-test: §8 normalization verified ({len(order)} dims) ✅"
    )


def main():
    ap = argparse.ArgumentParser(
        description="Reusable §8 post-processor for 1290-dim extractions."
    )
    ap.add_argument(
        "--selftest", action="store_true", help="run built-in §8 contract tests"
    )
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        ap.print_help()


if __name__ == "__main__":
    sys.exit(main())
