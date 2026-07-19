#!/usr/bin/env python3
"""Crosswalk: raw NORC GSS (`gss7224_r3.dta`) → the exact/"observed" layer of the 1290 schema.

The rule layer behind the merged GSS extraction (75,699 respondents). GSS is a fully coded survey,
so this observed layer alone is the whole rule-based extraction — feed it to
`run_pipeline.py --observed-only` (no LLM). Same declarative shape as `crosswalks/prism.py`; the only
extras are a few `compute` functions where a schema value needs two source columns.

Source: the raw `.dta` read with `convert_categoricals=True` (decoded string labels; lowercased here).
Richer than the thinned HF/submission GSS: exact integer `age` (65+ split resolved), `educ`
distinguishing Primary…Doctorate, a clean 7-point `polviews`, and the `fefam` attitude item →
`att_traditional_gender_roles`. All values are direct survey responses → provenance `observed`.

Faithful (map value ``None`` = present-but-deliberately-unmapped → null): coarse / withheld /
ambiguous codes resolve to null, never guessed — e.g. `race` "other", `class` "no class",
`born` "no" (foreign-born says nothing about the schema's citizenship bucket).

Run ``python crosswalks/gss.py --selftest``.
"""

import re


def _s(row, key):
    """Lowercased source string, or None for missing/NaN — no pandas dependency."""
    v = row.get(key)
    if v is None:
        return None
    try:
        if v != v:  # NaN
            return None
    except (TypeError, ValueError):
        pass
    return str(v).strip().lower()


def _age_bracket(row):
    a = row.get("age")
    if a is None or (a != a):  # None / NaN
        return None
    if "older" in str(a).lower():  # GSS top-code "89 or older"
        return "85+"
    try:
        a = float(a)
    except (TypeError, ValueError):
        return None
    for lo, hi, lab in (
        (18, 24, "18-24"),
        (25, 34, "25-34"),
        (35, 44, "35-44"),
        (45, 54, "45-54"),
        (55, 64, "55-64"),
        (65, 74, "65-74"),
        (75, 84, "75-84"),
    ):
        if lo <= a <= hi:
            return lab
    return "85+" if a >= 85 else None


def _ethnicity(row):
    h, r = _s(row, "hispanic"), _s(row, "race")
    if h and h != "not hispanic":
        return "Hispanic / Latino"
    if r == "white":
        return "White / European"
    if r == "black":
        return "Black / African"
    return None  # "other" race is unresolvable → null


def _education(row):
    d, e = _s(row, "degree"), _s(row, "educ")
    if (
        d == "graduate"
    ):  # GSS lumps master's+doctorate; split on years of school when available
        return (
            "Doctorate"
            if (e and ("7 years" in e or "8 or more years" in e))
            else "Master's"
        )
    if d == "bachelor's":
        return "Bachelor's"
    if d == "associate/junior college":
        return "Associate's"
    if d == "high school":
        return "Secondary"
    if d == "less than high school":  # grades 1-8 → Primary, 9-11 → Secondary
        m = re.match(r"(\d+)", e) if e else None
        return "Primary" if (m and int(m.group(1)) <= 8) else "Secondary"
    return None


def _religiosity(row):
    rl, rt = _s(row, "relig"), _s(row, "reliten")
    if rl == "none" or rt == "no religion":
        return "Secular"
    if rt == "strong":
        return "Devout"
    if rt == "somewhat strong (vol.)":
        return "Observant"
    if rt == "not very strong":
        return "Spiritual"
    return None


def _region(row):
    return "North America" if _s(row, "region") else None  # GSS is US-only


def _seniority(row):
    return {"retired": "Retired", "in school": "Student / intern"}.get(
        _s(row, "wrkstat")
    )


def _life_stage(row):
    return {"in school": "Student", "retired": "Retirement"}.get(_s(row, "wrkstat"))


CROSSWALK = {
    "age_bracket": {"compute": _age_bracket, "prov": "observed"},
    "gender_identity": {
        "src": "sex",
        "map": {"female": "Woman", "male": "Man"},
        "prov": "observed",
    },
    "demo_ethnicity_broad": {"compute": _ethnicity, "prov": "observed"},
    "demo_citizenship_status": {
        "src": "born",
        "map": {
            "yes": "Citizen by birth",
            "no": None,
        },  # foreign-born ≠ a known schema bucket
        "prov": "observed",
    },
    "demo_children_count": {
        "src": "childs",
        "map": {
            "0.0": "None",
            "1.0": "1 child",
            "2.0": "2 children",
            "3.0": "3+ children",
            "4.0": "3+ children",
            "5.0": "3+ children",
            "6.0": "3+ children",
            "7.0": "3+ children",
            "8 or more": "3+ children",
        },
        "prov": "observed",
    },
    "demo_marital_status": {
        "src": "marital",
        "map": {
            "married": "Married",
            "never married": "Single",
            "divorced": "Divorced",
            "widowed": "Widowed",
            "separated": "Separated",
        },
        "prov": "observed",
    },
    "highest_education": {"compute": _education, "prov": "observed"},
    "socioeconomic_band": {
        "src": "class",
        "map": {
            "lower class": "Low income",
            "working class": "Lower-middle",
            "middle class": "Middle",
            "upper class": "Upper-middle",
            "no class": None,
        },
        "prov": "observed",
    },
    "demo_employment_status": {
        "src": "wrkstat",
        "map": {
            "working full time": "Full-time",
            "working part time": "Part-time",
            "retired": "Retired",
            "keeping house": "Homemaker",
            "unemployed, laid off, looking for work": "Unemployed",
            "in school": "Student",
            "with a job, but not at work because of temporary illness, vacation, strike": "Full-time",
            "other": None,
        },
        "prov": "observed",
    },
    "seniority": {"compute": _seniority, "prov": "observed"},
    "life_stage": {"compute": _life_stage, "prov": "observed"},
    "political_lean": {
        "src": "polviews",
        "map": {
            "extremely liberal": "Left",
            "liberal": "Left",
            "slightly liberal": "Center-left",
            "moderate, middle of the road": "Center",
            "slightly conservative": "Center-right",
            "conservative": "Right",
            "extremely conservative": "Right",
        },
        "prov": "observed",
    },
    "religiosity": {"compute": _religiosity, "prov": "observed"},
    "demo_religion_affiliation": {
        "src": "relig",
        "map": {
            "protestant": "Christian",
            "catholic": "Christian",
            "christian": "Christian",
            "orthodox-christian": "Christian",
            "jewish": "Jewish",
            "muslim/islam": "Muslim",
            "buddhism": "Buddhist",
            "hinduism": "Hindu",
            "none": "None",
            "native american": "Folk / traditional",
            "other": None,
            "inter-nondenominational": None,
            "other eastern religions": None,
        },
        "prov": "observed",
    },
    "health_general_health": {
        "src": "health",
        "map": {
            "excellent": "Excellent",
            "good": "Good",
            "fair": "Fair",
            "poor": "Poor",
        },
        "prov": "observed",
    },
    "trust_level": {
        "src": "trust",
        "map": {
            "most people can be trusted": "Trusting",
            "can't be too careful": "Skeptical",
            "depends": "Verifying",
        },
        "prov": "observed",
    },
    "region": {"compute": _region, "prov": "observed"},
    "att_traditional_gender_roles": {
        "src": "fefam",
        "map": {
            "strongly agree": "Enthusiast",
            "agree": "Positive",
            "disagree": "Skeptical",
            "strongly disagree": "Opposed",
        },
        "prov": "observed",
    },
}


def _selftest():
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from crosswalk_engine import apply_crosswalk

    allowed = {
        "age_bracket": {
            "18-24",
            "25-34",
            "35-44",
            "45-54",
            "55-64",
            "65-74",
            "75-84",
            "85+",
        },
        "gender_identity": {"Man", "Woman", "Non-binary"},
        "demo_ethnicity_broad": {
            "White / European",
            "Black / African",
            "Hispanic / Latino",
        },
        "demo_citizenship_status": {"Citizen by birth", "Naturalized citizen"},
        "demo_children_count": {"None", "1 child", "2 children", "3+ children"},
        "demo_marital_status": {
            "Single",
            "Married",
            "Divorced",
            "Separated",
            "Widowed",
        },
        "highest_education": {
            "Primary",
            "Secondary",
            "Associate's",
            "Bachelor's",
            "Master's",
            "Doctorate",
        },
        "socioeconomic_band": {"Low income", "Lower-middle", "Middle", "Upper-middle"},
        "demo_employment_status": {
            "Full-time",
            "Part-time",
            "Unemployed",
            "Retired",
            "Student",
            "Homemaker",
        },
        "seniority": {"Retired", "Student / intern"},
        "life_stage": {"Student", "Retirement"},
        "political_lean": {"Left", "Center-left", "Center", "Center-right", "Right"},
        "religiosity": {"Secular", "Spiritual", "Observant", "Devout"},
        "demo_religion_affiliation": {
            "Christian",
            "Jewish",
            "Muslim",
            "Buddhist",
            "Hindu",
            "Folk / traditional",
            "None",
        },
        "health_general_health": {"Excellent", "Good", "Fair", "Poor"},
        "trust_level": {"Trusting", "Skeptical", "Verifying"},
        "region": {"North America"},
        "att_traditional_gender_roles": {
            "Enthusiast",
            "Positive",
            "Skeptical",
            "Opposed",
        },
    }

    # a fully-answered respondent → clean observed values across map + compute dims
    row = {
        "age": 42,
        "sex": "Female",
        "race": "Black",
        "hispanic": "not hispanic",
        "region": "Pacific",
        "born": "Yes",
        "marital": "Never married",
        "childs": "2.0",
        "degree": "Bachelor's",
        "educ": "16 years",
        "wrkstat": "Retired",
        "class": "Middle class",
        "polviews": "Slightly conservative",
        "relig": "Catholic",
        "reliten": "Strong",
        "health": "Good",
        "trust": "Depends",
        "fefam": "Disagree",
    }
    obs, prov, unmapped = apply_crosswalk(row, CROSSWALK, allowed)
    assert obs["age_bracket"] == "35-44", obs
    assert obs["gender_identity"] == "Woman"
    assert obs["demo_ethnicity_broad"] == "Black / African"
    assert obs["demo_marital_status"] == "Single"
    assert obs["highest_education"] == "Bachelor's"
    assert obs["demo_children_count"] == "2 children"
    assert obs["demo_employment_status"] == "Retired"
    assert obs["seniority"] == "Retired" and obs["life_stage"] == "Retirement"
    assert obs["political_lean"] == "Center-right"
    assert (
        obs["demo_religion_affiliation"] == "Christian"
        and obs["religiosity"] == "Devout"
    )
    assert obs["region"] == "North America"
    assert obs["att_traditional_gender_roles"] == "Skeptical"
    assert obs["demo_citizenship_status"] == "Citizen by birth"
    assert all(p == "observed" for p in prov.values())

    # faithfulness: coarse / withheld codes → null, never guessed
    coarse = {
        "race": "Other",
        "class": "No class",
        "born": "No",
        "relig": "Other",
        "age": "89 or older",
        "childs": "8 or more",
    }
    obs2, _p2, _u2 = apply_crosswalk(coarse, CROSSWALK, allowed)
    assert "demo_ethnicity_broad" not in obs2  # "other" race → null
    assert "socioeconomic_band" not in obs2  # "no class" → null
    assert "demo_citizenship_status" not in obs2  # foreign-born → null
    assert "demo_religion_affiliation" not in obs2  # "other" relig → null
    assert obs2["age_bracket"] == "85+" and obs2["demo_children_count"] == "3+ children"

    print(
        f"gss crosswalk self-test: {len(CROSSWALK)} dims, mapping + faithfulness verified ✅"
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Raw NORC GSS crosswalk for crosswalk_engine."
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
        ap.print_help()
