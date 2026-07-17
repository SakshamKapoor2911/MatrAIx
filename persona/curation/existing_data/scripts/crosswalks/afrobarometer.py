#!/usr/bin/env python3
"""Afrobarometer Round 9 persona table -> exact MatrAIx schema fields.

Only lossless mappings belong here. The source's ``name`` is synthetic and its
``domain``/``seniority_level`` can be inferred, so none of those are overlaid as
observed facts.  Values that are too coarse for the target schema (notably 65+)
remain unobserved and are left for the normalizer to represent as null.
"""

import json


def _region(row):
    country = str(row.get("country") or "").strip().lower()
    return "MENA" if country in {"morocco", "sudan", "tunisia"} else (
        "Sub-Saharan Africa" if country else None
    )


def _religion(row):
    try:
        values = json.loads(row.get("values") or "[]")
    except (TypeError, json.JSONDecodeError):
        return None
    stated = {str(v).lower().removeprefix("identifies as ") for v in values}
    christian = {
        "anglican", "baptist", "calvinist", "christian mission in many lands",
        "christian only", "church of christ", "coptic", "dutch reformed",
        "eglise du christianisme céleste", "evangelical", "jehovah’s witness",
        "lutheran", "mennonite", "methodist", "mormon", "morovian",
        "new apostolic church", "orthodox", "pentecostal", "presbyterian",
        "quaker / friends", "roman catholic", "salvation army",
        "seventh day adventist", "united church of zambia or ucz",
        "zionist christian church",
    }
    muslim = {"ismaeli", "mouridiya brotherhood", "muslim only",
              "qadiriya brotherhood", "shia", "sunni only", "tijaniya brotherhood"}
    if stated & christian:
        return "Christian"
    if stated & muslim:
        return "Muslim"
    exact = {"hindu": "Hindu", "jewish": "Jewish",
             "traditional / ethnic religion": "Folk / traditional",
             "atheist": "Atheist / agnostic", "agnostic": "Atheist / agnostic"}
    return next((target for source, target in exact.items() if source in stated), None)


CROSSWALK = {
    "age_bracket": {
        "src": "age_bracket",
        "map": {
            "18-24": "18-24", "25-34": "25-34", "35-44": "35-44",
            "45-54": "45-54", "55-64": "55-64", "65+": None,
        },
        "prov": "observed",
    },
    "gender_identity": {
        "src": "gender",
        "map": {"female": "Woman", "male": "Man"},
        "prov": "observed",
    },
    "highest_education": {
        "src": "education_level",
        "map": {
            "no formal schooling": "No formal",
            "informal schooling": None,
            "primary": "Primary",
            "secondary": "Secondary",
            "post-secondary (non-university)": "Vocational / cert",
            # "Tertiary" does not say whether a degree was completed.
            "tertiary (university)": None,
            "postgraduate": None,
        },
        "prov": "observed",
    },
    "region": {"compute": _region, "prov": "observed"},
    "primary_language": {
        "src": "primary_language",
        "map": {
            "english": "English", "arabic": "Arabic", "french": "French",
            "portuguese": "Portuguese", "swahili": "Swahili",
        },
        "prov": "observed",
    },
    "demo_employment_status": {
        "src": "professional_background",
        "map": {"student": "Student", "retired": "Retired",
                "housewife / homemaker": "Homemaker"},
        "prov": "observed",
    },
    "demo_religion_affiliation": {"compute": _religion, "prov": "observed"},
}


def _selftest():
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from crosswalk_engine import apply_crosswalk

    allowed = {
        "age_bracket": {"18-24", "25-34", "35-44", "45-54", "55-64", "65-74"},
        "gender_identity": {"Woman", "Man"},
        "highest_education": {"No formal", "Primary", "Secondary", "Vocational / cert", "Some college", "Master's"},
        "region": {"Sub-Saharan Africa", "MENA"},
        "primary_language": {"English", "Arabic", "French", "Portuguese", "Swahili"},
        "demo_employment_status": {"Student", "Retired", "Homemaker"},
        "demo_religion_affiliation": {"Christian", "Muslim", "Hindu", "Jewish", "Folk / traditional", "Atheist / agnostic"},
    }
    row = {"age_bracket": "35-44", "gender": "Female", "education_level": "Secondary",
           "country": "Angola", "location": "Luanda, urban", "primary_language": "Portuguese",
           "professional_background": "Housewife / homemaker",
           "values": '["identifies as baptist"]'}
    observed, provenance, unmapped = apply_crosswalk(row, CROSSWALK, allowed)
    assert observed == {"age_bracket": "35-44", "gender_identity": "Woman",
                        "highest_education": "Secondary", "region": "Sub-Saharan Africa",
                        "primary_language": "Portuguese", "demo_employment_status": "Homemaker",
                        "demo_religion_affiliation": "Christian"}
    assert not unmapped and set(provenance.values()) == {"observed"}


if __name__ == "__main__":
    _selftest()
    print("afrobarometer crosswalk self-test passed")
