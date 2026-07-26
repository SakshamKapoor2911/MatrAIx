#!/usr/bin/env python3
"""Deterministic ConvAI2/PersonaChat -> MatrAIx observed-field crosswalk.

Rules operate only on the original crowdsourced persona sentences. Upstream
``domain`` and ``seniority_level`` columns are inferred and intentionally ignored.
Each match retains the source sentence as verbatim evidence.
"""

import re
from functools import lru_cache


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text or "")) if s.strip()]


def _first(text, patterns):
    for sentence in _sentences(text):
        for pattern, value in patterns:
            if re.search(pattern, sentence, re.I):
                return value, sentence
    return None, ""


SIMPLE_RULES = {
    "urbanicity": [
        (r"\b(?:from|live in|grew up in) (?:a )?small town\b", "Small town")
    ],
    "demo_marital_status": [
        (
            r"\b(?:i am|i'm) widowed\b|\bmy (?:wife|husband|spouse) (?:died|passed away)\b",
            "Widowed",
        ),
        (
            r"\b(?:i am|i'm|got|recently) married\b|\bmy (?:wife|husband|spouse)\b",
            "Married",
        ),
        (r"\b(?:i am|i'm) engaged\b|\bmy fianc(?:e|é|ée)\b", "Engaged"),
        (r"\b(?:i am|i'm) divorced\b|\bmy ex-(?:wife|husband|spouse)\b", "Divorced"),
        (r"\b(?:i am|i'm) single\b", "Single"),
        (
            r"\b(?:my boyfriend|my girlfriend|i am dating|i'm dating)\b",
            "In a relationship",
        ),
    ],
    "demo_employment_status": [
        (
            r"\b(?:i am|i'm) (?:a )?(?:college|university|high school )?student\b|\bi (?:attend|go to) (?:a )?(?:local )?(?:college|university)\b|\bi'm in college\b",
            "Student",
        ),
        (r"\b(?:i am|i'm) retired\b", "Retired"),
        (r"\b(?:i am|i'm) unemployed\b|\bi do not have a job\b", "Unemployed"),
        (r"\b(?:i work|working) part[ -]time\b|\bpart[ -]time job\b", "Part-time"),
        (
            r"\b(?:i am|i'm) (?:a )?(?:stay[ -]at[ -]home (?:mom|mother|dad|father|parent)|homemaker)\b",
            "Homemaker",
        ),
        (r"\b(?:i am|i'm) self[ -]employed\b", "Self-employed"),
    ],
    "demo_sexual_orientation": [
        (r"\b(?:i am|i'm) (?:a )?(?:gay|lesbian)\b|\bi am gay\b", "Gay / lesbian"),
        (r"\b(?:i am|i'm) bisexual\b", "Bisexual"),
        (r"\b(?:i am|i'm) pansexual\b", "Pansexual"),
        (r"\b(?:i am|i'm) asexual\b", "Asexual"),
        (r"\b(?:i am|i'm) queer\b", "Queer"),
    ],
    "lstyle_diet_type": [
        (r"\b(?:i am|i'm) (?:a )?vegan\b", "Vegan"),
        (r"\b(?:i am|i'm) (?:a )?vegetarian\b", "Vegetarian"),
        (r"\b(?:i am|i'm) (?:a )?pescatarian\b", "Pescatarian"),
        (
            r"\b(?:i am|i'm|i follow) (?:a )?(?:keto|low[ -]carb)(?: diet)?\b",
            "Keto/low-carb",
        ),
    ],
}

SPORTS = {
    "soccer": "sport_soccer",
    "basketball": "sport_basketball",
    "american football": "sport_american_football",
    "baseball": "sport_baseball",
    "tennis": "sport_tennis",
    "golf": "sport_golf",
    "cricket": "sport_cricket",
    "rugby": "sport_rugby",
    "hockey": "sport_hockey",
    "volleyball": "sport_volleyball",
    "swimming": "sport_swimming",
    "running": "sport_running",
    "cycling": "sport_cycling",
    "boxing": "sport_boxing",
    "wrestling": "sport_wrestling",
    "skiing": "sport_skiing",
    "snowboarding": "sport_snowboarding",
    "surfing": "sport_surfing",
    "skateboarding": "sport_skateboarding",
    "gymnastics": "sport_gymnastics",
    "badminton": "sport_badminton",
    "bowling": "sport_bowling",
    "archery": "sport_archery",
    "yoga": "sport_yoga",
    "weightlifting": "sport_weightlifting",
}

HOBBIES = {
    "knit(?:ting)?": "hob_knitting",
    "crochet(?:ing)?": "hob_crocheting",
    "pottery": "hob_pottery",
    "woodwork(?:ing)?": "hob_woodworking",
    "origami": "hob_origami",
    "calligraphy": "hob_calligraphy",
    "quilting": "hob_quilting",
    "embroidery": "hob_embroidery",
    "birdwatch(?:ing)?": "hob_birdwatching",
    "stargaz(?:e|ing)": "hob_stargazing",
    "rock climb(?:ing)?": "hob_rock_climbing",
    "kayak(?:ing)?": "hob_kayaking",
    "scuba div(?:e|ing)": "hob_scuba_diving",
    "snorkel(?:ing)?": "hob_snorkeling",
    "skydiv(?:e|ing)": "hob_skydiving",
    "horseback rid(?:e|ing)": "hob_horseback_riding",
    "karaoke": "hob_karaoke",
    "juggling": "hob_juggling",
    "cosplay": "hob_cosplay",
}


@lru_cache(maxsize=20000)
def extract_assignments(text):
    """Return ``{dim_id: (allowed_value, verbatim_sentence)}``."""
    out = {}
    for dim, rules in SIMPLE_RULES.items():
        value, evidence = _first(text, rules)
        if value:
            out[dim] = (value, evidence)

    sentences = _sentences(text)
    current = [
        s
        for s in sentences
        if not re.search(
            r"\b(?:died|passed away|used to|no longer|had a|had an)\b", s, re.I
        )
    ]
    current_text = " ".join(current)
    dog = _first(
        current_text, [(r"\b(?:i have|i own) (?:an? )?[^.]*\bdog\b|\bmy dog\b", "Dog")]
    )
    cat = _first(
        current_text, [(r"\b(?:i have|i own) (?:an? )?[^.]*\bcat\b|\bmy cat\b", "Cat")]
    )
    if dog[0] and cat[0]:
        out["lstyle_pet_ownership"] = (
            "Multiple pets",
            f"{dog[1]} {cat[1]}" if dog[1] != cat[1] else dog[1],
        )
    elif dog[0] or cat[0]:
        out["lstyle_pet_ownership"] = dog if dog[0] else cat

    for term, dim in SPORTS.items():
        play = rf"\b(?:i |we )?(?:(?:like|love|enjoy)\s+to\s+)?(?:play|practice|do|go)\s+(?:\w+\s+)?{term}\b"
        follow = rf"\b(?:i |we )?(?:(?:like|love|enjoy)\s+to\s+)?(?:watch|follow)\s+(?:\w+\s+)?{term}\b|\b(?:i |we )?(?:like|love|enjoy)\s+watching\s+(?:\w+\s+)?{term}\b"
        casual = rf"\b(?:i |we )?(?:like|love|enjoy)\s+{term}\b"
        value, evidence = _first(
            text, [(play, "Play"), (follow, "Follow"), (casual, "Casual")]
        )
        if value and not re.search(
            r"\b(?:used to|hop(?:e|ing) to|would like to|one day|taught me to)\b",
            evidence,
            re.I,
        ):
            out[dim] = (value, evidence)

    for term, dim in HOBBIES.items():
        active = rf"\b(?:i |we )(?:do|practice)\s+{term}\b|\bi {term}(?:\s|[.!?])"
        interested = rf"\b(?:i |we )?(?:like|love|enjoy)\s+(?:to )?{term}\b"
        value, evidence = _first(text, [(active, "Active"), (interested, "Curious")])
        if value and not re.search(
            r"\b(?:used to|hop(?:e|ing) to|would like to|one day)\b", evidence, re.I
        ):
            out[dim] = (value, evidence)
    return out


def _value(dim):
    return lambda row: extract_assignments(row.get("persona_description", "")).get(
        dim, (None, "")
    )[0]


_DIMS = (
    set(SIMPLE_RULES)
    | set(SPORTS.values())
    | set(HOBBIES.values())
    | {"lstyle_pet_ownership"}
)
CROSSWALK = {dim: {"compute": _value(dim), "prov": "observed"} for dim in sorted(_DIMS)}


if __name__ == "__main__":
    sample = "I'm in college. I have a dog. I love to crochet. I watch basketball. I am vegetarian."
    found = extract_assignments(sample)
    assert found["demo_employment_status"][0] == "Student"
    assert found["lstyle_pet_ownership"][0] == "Dog"
    assert found["hob_crocheting"][0] == "Curious"
    assert found["sport_basketball"][0] == "Follow"
    assert found["lstyle_diet_type"][0] == "Vegetarian"
    print(f"convai2 crosswalk self-test passed ({len(CROSSWALK)} target dimensions)")
