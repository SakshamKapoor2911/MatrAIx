#!/usr/bin/env python3
"""Render PRISM survey participants -> profile_text + exact observed dims.

Output: prism_profiles.jsonl, one line/participant:
  {"uuid": user_id, "profile_text": "<faithful profile incl. self-description>",
   "observed": {dim_id: value}}      # exact rule-based dims (provenance=observed)

profile_text contains only the participant's own answers (demographics + their
verbatim self_description + AI preferences); the LLM pass infers the rest of 1290.
Runs on CPU, no key. Downloads survey.jsonl from HF (public).
"""

import json
import argparse
from huggingface_hub import hf_hub_download

# dim_id -> (survey field, {lowercased source value: allowed target value | None})
CROSSWALK = {
    "age_bracket": (
        "age",
        {
            "18-24 years old": "18-24",
            "25-34 years old": "25-34",
            "35-44 years old": "35-44",
            "45-54 years old": "45-54",
            "55-64 years old": "55-64",
            "65+ years old": None,
            "prefer not to say": None,
        },
    ),  # 65+ too coarse to split
    "gender_identity": (
        "gender",
        {
            "male": "Man",
            "female": "Woman",
            "non-binary / third gender": "Non-binary",
            "prefer not to say": "Prefer not to say",
        },
    ),
    "highest_education": (
        "education",
        {
            "university bachelors degree": "Bachelor's",
            "graduate / professional degree": "Master's",
            "some university but no degree": "Some college",
            "completed secondary school": "Secondary",
            "vocational": "Vocational / cert",
            "some secondary": "Secondary",
            "completed primary school": "Primary",
            "some primary": "Primary",
            "prefer not to say": None,
        },
    ),
    "demo_marital_status": (
        "marital_status",
        {
            "never been married": "Single",
            "married": "Married",
            "divorced / separated": "Divorced",
            "widowed": "Widowed",
            "prefer not to say": None,
        },
    ),
    "demo_employment_status": (
        "employment_status",
        {
            "working full-time": "Full-time",
            "working part-time": "Part-time",
            "student": "Student",
            "unemployed, seeking work": "Unemployed",
            "unemployed, not seeking work": "Unemployed",
            "retired": "Retired",
            "homemaker / stay-at-home parent": "Homemaker",
            "prefer not to say": None,
        },
    ),
    "english_proficiency": (
        "english_proficiency",
        {
            "native speaker": "Native",
            "fluent": "Fluent (C1-C2)",
            "advanced": "Fluent (C1-C2)",
            "intermediate": "Intermediate (B1-B2)",
            "basic": "Basic (A1-A2)",
        },
    ),
    "demo_ethnicity_broad": (
        "ethnicity_simplified",
        {
            "white": "White / European",
            "black": "Black / African",
            "hispanic": "Hispanic / Latino",
            "mixed": "Multiracial",
            "asian": None,
            "other": None,
            "prefer not to say": None,
        },
    ),  # 'asian' too coarse
    "demo_religion_affiliation": (
        "religion_simplified",
        {
            "no affiliation": "None",
            "christian": "Christian",
            "jewish": "Jewish",
            "muslim": "Muslim",
            "other": None,
            "prefer not to say": None,
        },
    ),
    "region": (
        "reside_subregion",
        {
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
    ),
}


def flatten(p):
    loc = p.get("location") or {}
    return {
        **p,
        "ethnicity_simplified": (p.get("ethnicity") or {}).get("simplified"),
        "religion_simplified": (p.get("religion") or {}).get("simplified"),
        "reside_country": loc.get("reside_country"),
        "reside_subregion": loc.get("reside_subregion"),
    }


def observed_dims(f, allowed):
    out = {}
    for dim, (field, vmap) in CROSSWALK.items():
        sv = f.get(field)
        if sv is None:
            continue
        tv = vmap.get(str(sv).strip().lower(), "__MISS__")
        if tv in ("__MISS__", None):
            continue
        if tv not in allowed[dim]:
            raise ValueError(f"{dim}: mapped {tv!r} not in allowed set (source={sv!r})")
        out[dim] = tv
    return out


def render(f):
    parts = []
    age = f.get("age")
    gen = f.get("gender")
    a = (
        None
        if (not age or age == "Prefer not to say")
        else age.replace(" years old", "")
    )
    gtxt = {
        "Male": "man",
        "Female": "woman",
        "Non-binary / third gender": "non-binary person",
    }.get(gen)
    who = (
        f"A {a}-year-old {gtxt}"
        if (a and gtxt)
        else (f"A {a}-year-old person" if a else (f"A {gtxt}" if gtxt else "A person"))
    )
    if f.get("reside_country") and f["reside_country"] != "Prefer not to say":
        who += f" based in {f['reside_country']}"
    parts.append(who + ".")

    def add(label, val, skip=("Prefer not to say", None, "prefer not to say")):
        if val and val not in skip:
            parts.append(f"{label}: {val}.")

    add("Ethnicity", f.get("ethnicity_simplified"))
    add("Religion", f.get("religion_simplified"))
    add("Education", f.get("education"))
    add("Marital status", f.get("marital_status"))
    add("Employment", f.get("employment_status"))
    add("English proficiency", f.get("english_proficiency"))

    sd = (f.get("self_description") or "").strip()
    if sd:
        parts.append(f'In their own words, they describe themselves as: "{sd}"')
    ss = (f.get("system_string") or "").strip()
    if ss:
        parts.append(f'What they want from an AI assistant: "{ss}"')

    fam, freq = f.get("lm_familiarity"), f.get("lm_frequency_use")
    if fam:
        u = f"They are {fam.lower()} with AI language models"
        if freq and freq != "None":
            u += f" and use them {freq.lower()}"
        parts.append(u + ".")

    prefs = f.get("stated_prefs") or {}
    top = sorted(
        (
            (v, k)
            for k, v in prefs.items()
            if isinstance(v, (int, float)) and k != "other"
        ),
        reverse=True,
    )[:4]
    if top:
        parts.append(
            "Top priorities for an AI assistant: " + ", ".join(k for _, k in top) + "."
        )
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default="dimensions.json")
    ap.add_argument("--out", default="out/prism_profiles.jsonl")
    args = ap.parse_args()

    import os

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    allowed = {
        d["id"]: set(d.get("values") or [])
        for d in json.load(open(args.schema))["dimensions"]
    }
    fp = hf_hub_download(
        "HannahRoseKirk/prism-alignment", "survey.jsonl", repo_type="dataset"
    )
    rows = [json.loads(line) for line in open(fp)]

    n = tot = 0
    with open(args.out, "w") as out:
        for p in rows:
            f = flatten(p)
            obs = observed_dims(f, allowed)
            out.write(
                json.dumps(
                    {"uuid": p["user_id"], "profile_text": render(f), "observed": obs},
                    ensure_ascii=False,
                )
                + "\n"
            )
            n += 1
            tot += len(obs)
    print(
        f"wrote {n:,} PRISM profiles -> {args.out}  (avg {tot / n:.1f} exact observed dims)"
    )


if __name__ == "__main__":
    main()
