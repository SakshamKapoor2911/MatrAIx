#!/usr/bin/env python3
"""Example crosswalk: PRISM Alignment Corpus → the exact/"observed" layer of the 1290 schema.

This is the **worked example** for `crosswalk_engine.py`. A new dataset's rule-based layer is just
a module like this one: a `CROSSWALK` dict mapping each schema dimension to a source field + a
value map (or a `compute` function). Feed it to `crosswalk_engine.apply_crosswalk(row, CROSSWALK,
allowed)` and you get validated `observed` dims for free — copy this file's shape for the next dataset.

Source: `HannahRoseKirk/prism-alignment` (`survey.jsonl`). PRISM nests a few fields (ethnicity,
religion, location), so flatten the row first — e.g. surface `ethnicity.simplified` as
`ethnicity_simplified`, `religion.simplified` as `religion_simplified`, and
`location.reside_subregion` as `reside_subregion` — then apply this crosswalk.

Notes on faithful mapping choices (map value ``None`` = present-but-deliberately-unmapped → null):
  * ``age_bracket``: PRISM's "65+ years old" is too coarse to place in a single bracket → null.
  * ``demo_ethnicity_broad``: "asian" is too coarse for the schema's regional buckets → null.
  * "prefer not to say" everywhere → null (unobserved), never guessed.

Run ``python crosswalks/prism.py --selftest`` to check it against the engine.
"""

CROSSWALK = {
    "age_bracket": {
        "src": "age",
        "map": {
            "18-24 years old": "18-24",
            "25-34 years old": "25-34",
            "35-44 years old": "35-44",
            "45-54 years old": "45-54",
            "55-64 years old": "55-64",
            "65+ years old": None,  # too coarse to bracket
            "prefer not to say": None,
        },
        "prov": "observed",
    },
    "gender_identity": {
        "src": "gender",
        "map": {
            "male": "Man",
            "female": "Woman",
            "non-binary / third gender": "Non-binary",
            "prefer not to say": "Prefer not to say",
        },
        "prov": "observed",
    },
    "highest_education": {
        "src": "education",
        "map": {
            "university bachelors degree": "Bachelor's",
            "graduate / professional degree": "Master's",
            "some university but no degree": "Some college",
            "completed secondary school": "Secondary",
            "some secondary": "Secondary",
            "vocational": "Vocational / cert",
            "completed primary school": "Primary",
            "some primary": "Primary",
            "prefer not to say": None,
        },
        "prov": "observed",
    },
    "demo_marital_status": {
        "src": "marital_status",
        "map": {
            "never been married": "Single",
            "married": "Married",
            "divorced / separated": "Divorced",
            "widowed": "Widowed",
            "prefer not to say": None,
        },
        "prov": "observed",
    },
    "demo_employment_status": {
        "src": "employment_status",
        "map": {
            "working full-time": "Full-time",
            "working part-time": "Part-time",
            "student": "Student",
            "unemployed, seeking work": "Unemployed",
            "unemployed, not seeking work": "Unemployed",
            "retired": "Retired",
            "homemaker / stay-at-home parent": "Homemaker",
            "prefer not to say": None,
        },
        "prov": "observed",
    },
    "english_proficiency": {
        "src": "english_proficiency",
        "map": {
            "native speaker": "Native",
            "fluent": "Fluent (C1-C2)",
            "advanced": "Fluent (C1-C2)",
            "intermediate": "Intermediate (B1-B2)",
            "basic": "Basic (A1-A2)",
        },
        "prov": "observed",
    },
    "demo_ethnicity_broad": {
        "src": "ethnicity_simplified",
        "map": {
            "white": "White / European",
            "black": "Black / African",
            "hispanic": "Hispanic / Latino",
            "mixed": "Multiracial",
            "asian": None,  # too coarse for the schema's regional buckets
            "other": None,
            "prefer not to say": None,
        },
        "prov": "observed",
    },
    "demo_religion_affiliation": {
        "src": "religion_simplified",
        "map": {
            "no affiliation": "None",
            "christian": "Christian",
            "jewish": "Jewish",
            "muslim": "Muslim",
            "other": None,
            "prefer not to say": None,
        },
        "prov": "observed",
    },
    "region": {
        "src": "reside_subregion",
        "map": {
            "northern america": "North America",
            "northern europe": "Western Europe",
            "western europe": "Western Europe",
            "southern europe": "Western Europe",
            "eastern europe": "Eastern Europe",
            "australia and new zealand": "Oceania",
            "latin america and the caribbean": "Latin America",
            "sub-saharan africa": "Sub-Saharan Africa",
            "western asia": "MENA",
            "eastern asia": "East Asia",
            "prefer not to say": None,
        },
        "prov": "observed",
    },
}


def _selftest():
    import os
    import sys

    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )  # scripts/
    from crosswalk_engine import apply_crosswalk

    # mock allowed sets for the dims this example touches (real runs pass dimensions.json)
    allowed = {
        "age_bracket": {"18-24", "25-34", "35-44", "45-54", "55-64"},
        "gender_identity": {"Man", "Woman", "Non-binary", "Prefer not to say"},
        "demo_marital_status": {"Single", "Married", "Divorced", "Widowed"},
        "english_proficiency": {
            "Native",
            "Fluent (C1-C2)",
            "Intermediate (B1-B2)",
            "Basic (A1-A2)",
        },
        "demo_ethnicity_broad": {
            "White / European",
            "Black / African",
            "Hispanic / Latino",
            "Multiracial",
        },
        "region": {"North America", "Western Europe", "Sub-Saharan Africa"},
    }
    tested = {k: CROSSWALK[k] for k in allowed}

    row = {
        "age": "35-44 years old",
        "gender": "Female",
        "marital_status": "Never been married",
        "english_proficiency": "Fluent",
        "ethnicity_simplified": "asian",  # deliberately unmapped -> null
        "reside_subregion": "Northern America",
    }
    observed, prov, unmapped = apply_crosswalk(row, tested, allowed)
    assert observed == {
        "age_bracket": "35-44",
        "gender_identity": "Woman",
        "demo_marital_status": "Single",
        "english_proficiency": "Fluent (C1-C2)",
        "region": "North America",
    }, observed
    assert (
        "demo_ethnicity_broad" not in observed
    )  # 'asian' mapped to None -> unobserved
    assert unmapped == {}, unmapped
    assert all(p == "observed" for p in prov.values())
    print(
        f"prism crosswalk self-test: {len(CROSSWALK)} dims, mapping verified against engine ✅"
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="PRISM example crosswalk for crosswalk_engine."
    )
    ap.add_argument(
        "--selftest",
        action="store_true",
        help="verify the crosswalk against the engine",
    )
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        print(
            f"PRISM crosswalk: {len(CROSSWALK)} dimensions. Import CROSSWALK, or run --selftest."
        )
