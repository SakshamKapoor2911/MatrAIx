#!/usr/bin/env python3
"""Reusable crosswalk engine for the rule-based (exact / "observed") layer of
mapping an existing persona dataset onto MatrAIx's 1290-dimension schema.

Each dataset provides only a small declarative **crosswalk**; this shared engine does
the schema loading, value validation, provenance, and unmapped-value tracking — so a
new dataset's exact-mapping layer is "write a crosswalk", not "write a pipeline".
The inferred layer (free-text -> the remaining dims) is a separate LLM pass; this
module only covers the fields a source states directly.

Faithfulness guarantees (enforced here):
  * A mapped value MUST be in that dimension's allowed set, else a hard ``ValueError``
    (no off-schema values are ever emitted).
  * A source value with no faithful target -> left unobserved and recorded as
    ``unmapped`` for review (never forced to a "reasonable-looking" value).
  * Unobserved dimensions are simply absent from the returned ``observed`` dict
    (the caller fills the full 1290 with null downstream).

Crosswalk format::

    crosswalk = {
        "<dim_id>": {"src": "<source_field>",
                     "map": {"<lowercased source value>": "<target>" | None, ...},
                     "prov": "observed"},
        "<dim_id>": {"compute": lambda row: "<target>" | None,   # multi-field / derived
                     "prov": "observed"},
    }

  * ``map`` keys are matched case-insensitively (source value is lower/stripped).
  * ``map`` value ``None`` means "present but deliberately not mapped" -> stays null.
  * a ``map`` miss is recorded in ``unmapped`` (surfaced for crosswalk review), stays null.

Run ``python crosswalk_engine.py --selftest`` to verify the contract.
"""

import argparse
import json
import sys

_MISS = object()


def load_allowed(schema_path):
    """Return {dim_id: set(allowed values)} from a dimensions.json schema."""
    dims = json.load(open(schema_path))["dimensions"]
    return {d["id"]: set(d.get("values") or []) for d in dims}


def _isna(v):
    if v is None:
        return True
    try:
        return v != v  # NaN (works for float NaN without importing pandas/numpy)
    except (TypeError, ValueError):
        return False


def apply_crosswalk(row, crosswalk, allowed):
    """Map one source ``row`` (any object with ``.get``) via ``crosswalk``.

    Returns ``(observed, provenance, unmapped)``:
      * ``observed``   -> {dim_id: value}   validated exact values only
      * ``provenance`` -> {dim_id: "observed"|...}
      * ``unmapped``   -> {dim_id: raw_source_value}  (source had a value we couldn't map)
    Raises ``KeyError`` if the crosswalk targets a dim not in ``allowed`` (schema drift),
    or ``ValueError`` if a mapped value is not in that dim's allowed set.
    """
    observed, provenance, unmapped = {}, {}, {}
    for dim_id, rule in crosswalk.items():
        if dim_id not in allowed:
            raise KeyError(f"crosswalk targets unknown dim {dim_id!r} (schema drift?)")

        if "compute" in rule:
            target = rule["compute"](row)
        else:
            raw = row.get(rule["src"])
            if _isna(raw):
                continue
            mapping = rule["map"]
            key = str(raw).strip().lower()
            target = mapping(key) if callable(mapping) else mapping.get(key, _MISS)
            if target is _MISS:
                unmapped[dim_id] = raw
                continue

        if target is None:
            continue  # deliberately unobserved
        if allowed[dim_id] and target not in allowed[dim_id]:
            raise ValueError(
                f"{dim_id}: mapped value {target!r} is not in the schema's allowed set"
            )
        observed[dim_id] = target
        provenance[dim_id] = rule.get("prov", "observed")
    return observed, provenance, unmapped


def _selftest():
    allowed = {
        "gender_identity": {"Man", "Woman", "Non-binary"},
        "age_bracket": {"25-34", "35-44"},
        "demo_marital_status": {"Single", "Married"},
        "region": {"North America"},
    }
    crosswalk = {
        "gender_identity": {
            "src": "sex",
            "map": {"male": "Man", "female": "Woman"},
            "prov": "observed",
        },
        "age_bracket": {
            "compute": lambda r: "25-34" if 25 <= int(r.get("age", 0)) <= 34 else None,
            "prov": "observed",
        },
        # 'divorced' is present in the source but intentionally not mapped -> stays null
        "demo_marital_status": {
            "src": "marital",
            "map": {"single": "Single", "divorced": None},
            "prov": "observed",
        },
    }

    row = {"sex": "Male", "age": 30, "marital": "Divorced", "country": None}
    observed, prov, unmapped = apply_crosswalk(row, crosswalk, allowed)
    assert observed == {"gender_identity": "Man", "age_bracket": "25-34"}, observed
    assert prov["gender_identity"] == "observed"
    assert unmapped == {}, (
        unmapped
    )  # 'divorced' mapped to None (deliberate), not a miss

    # a source value with no map entry is recorded as unmapped, left null
    _, _, um = apply_crosswalk({"sex": "genderqueer"}, crosswalk, allowed)
    assert um == {"gender_identity": "genderqueer"}, um

    # off-schema mapped value must raise
    bad = {
        "gender_identity": {"src": "sex", "map": {"male": "Dude"}, "prov": "observed"}
    }
    try:
        apply_crosswalk({"sex": "male"}, bad, allowed)
        raise AssertionError("expected ValueError for off-schema value")
    except ValueError:
        pass

    # crosswalk targeting an unknown dim must raise
    try:
        apply_crosswalk(
            {"x": "y"}, {"not_a_dim": {"src": "x", "map": {"y": "z"}}}, allowed
        )
        raise AssertionError("expected KeyError for unknown dim")
    except KeyError:
        pass

    print("crosswalk_engine self-test: all assertions passed ✅")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--selftest", action="store_true", help="run built-in contract tests"
    )
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        ap.print_help()


if __name__ == "__main__":
    sys.exit(main())
