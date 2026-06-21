# persona_adapter.py — Convert MatrAIx persona YAML files to OASIS-compatible UserInfo dicts.
# Handles dimension mapping (Big Five → MBTI, region → country, domain → topics),
# username generation, system prompt construction, and activity threshold derivation.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


BIG5_SCALE = {"Very low": 0.15, "Low": 0.30, "Medium": 0.50, "High": 0.70, "Very high": 0.85}

REGION_TO_COUNTRIES = {
    "North America": ["US", "Canada", "Mexico"],
    "Latin America": ["Brazil", "Argentina", "Colombia", "Chile", "Peru"],
    "Western Europe": ["UK", "Germany", "France", "Spain", "Netherlands", "Italy"],
    "Eastern Europe": ["Poland", "Romania", "Czech Republic", "Hungary", "Ukraine"],
    "Sub-Saharan Africa": ["Nigeria", "Kenya", "South Africa", "Ghana", "Ethiopia"],
    "MENA": ["Egypt", "Saudi Arabia", "UAE", "Turkey", "Morocco"],
    "South Asia": ["India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal"],
    "East Asia": ["China", "Japan", "South Korea", "Taiwan"],
    "Southeast Asia": ["Indonesia", "Philippines", "Vietnam", "Thailand", "Malaysia"],
    "Oceania": ["Australia", "New Zealand"],
}

DOMAIN_TO_TOPICS = {
    "Technology": ["Technology", "Science"],
    "Science & Research": ["Science", "Technology"],
    "Healthcare & Medicine": ["Health", "Science"],
    "Finance & Banking": ["Economics", "Business"],
    "Education & Training": ["Education", "Social Issues"],
    "Law & Policy": ["Politics", "Social Issues"],
    "Marketing & Advertising": ["Business", "Entertainment"],
    "Design & Creative": ["Entertainment", "Lifestyle"],
    "Media & Journalism": ["Entertainment", "Politics"],
    "Social Services & NGO": ["Social Issues", "Health"],
    "Engineering": ["Technology", "Science"],
    "Manufacturing & Industry": ["Business", "Technology"],
    "Retail & E-Commerce": ["Business", "Lifestyle"],
    "Hospitality & Tourism": ["Lifestyle", "Entertainment"],
    "Agriculture & Environment": ["Science", "Social Issues"],
    "Arts & Culture": ["Entertainment", "Lifestyle"],
    "Sports & Fitness": ["Sports", "Health"],
    "Real Estate": ["Business", "Economics"],
    "Logistics & Supply Chain": ["Business", "Technology"],
    "Government & Public Sector": ["Politics", "Social Issues"],
}

AGE_BRACKET_ACTIVITY = {
    "13–17": 0.08,
    "18–24": 0.06,
    "25–34": 0.04,
    "35–44": 0.03,
    "45–54": 0.02,
    "55–64": 0.015,
    "65+": 0.01,
}

URBANICITY_MULTIPLIER = {
    "Urban": 1.3,
    "Suburban": 1.0,
    "Rural": 0.7,
}

EXTRAVERSION_ACTIVITY_BOOST = {
    "Very low": 0.6,
    "Low": 0.8,
    "Medium": 1.0,
    "High": 1.2,
    "Very high": 1.5,
}


@dataclass
class OasisUserInfo:
    persona_id: str
    name: str
    user_name: str
    bio: str
    user_profile: str
    mbti: str
    gender: str
    age: int
    country: str
    profession: str
    interested_topics: list[str]
    active_threshold: list[float]
    big_five: dict[str, float]
    raw_dimensions: dict[str, Any] = field(default_factory=dict)

    def to_oasis_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "user_name": self.user_name,
            "description": self.bio,
            "profile": {
                "other_info": {
                    "user_profile": self.user_profile,
                    "mbti": self.mbti,
                    "gender": self.gender,
                    "age": self.age,
                    "country": self.country,
                    "profession": self.profession,
                    "interested_topics": self.interested_topics,
                    "active_threshold": self.active_threshold,
                }
            },
            "recsys_type": "twitter",
            "is_controllable": False,
        }


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def big5_to_numeric(dimensions: dict[str, Any]) -> dict[str, float]:
    return {
        "openness": BIG5_SCALE.get(dimensions.get("personality_big5_openness", "Medium"), 0.50),
        "conscientiousness": BIG5_SCALE.get(dimensions.get("personality_big5_conscientiousness", "Medium"), 0.50),
        "extraversion": BIG5_SCALE.get(dimensions.get("personality_big5_extraversion", "Medium"), 0.50),
        "agreeableness": BIG5_SCALE.get(dimensions.get("personality_big5_agreeableness", "Medium"), 0.50),
        "neuroticism": BIG5_SCALE.get(dimensions.get("personality_big5_neuroticism", "Medium"), 0.50),
    }


def big5_to_mbti(big5: dict[str, float]) -> str:
    e_i = "E" if big5["extraversion"] >= 0.50 else "I"
    s_n = "N" if big5["openness"] >= 0.50 else "S"
    t_f = "F" if big5["agreeableness"] >= 0.50 else "T"
    j_p = "J" if big5["conscientiousness"] >= 0.50 else "P"
    return f"{e_i}{s_n}{t_f}{j_p}"


def map_gender(gender_identity: str) -> str:
    mapping = {
        "Man": "male",
        "Woman": "female",
        "Non-binary": "non-binary",
        "Self-described": "non-binary",
        "Prefer not to say": "unknown",
    }
    return mapping.get(gender_identity, "unknown")


def map_country(region: str, seed: int = 0) -> str:
    countries = REGION_TO_COUNTRIES.get(region, ["Unknown"])
    return countries[seed % len(countries)]


def map_topics(domain: str) -> list[str]:
    return DOMAIN_TO_TOPICS.get(domain, ["Technology", "Science"])


def compute_activity_threshold(dimensions: dict[str, Any]) -> list[float]:
    age_bracket = dimensions.get("age_bracket", "25–34")
    urbanicity = dimensions.get("urbanicity", "Suburban")
    extraversion = dimensions.get("personality_big5_extraversion", "Medium")

    base = AGE_BRACKET_ACTIVITY.get(age_bracket, 0.03)
    urban_mult = URBANICITY_MULTIPLIER.get(urbanicity, 1.0)
    extra_mult = EXTRAVERSION_ACTIVITY_BOOST.get(extraversion, 1.0)

    hourly_prob = base * urban_mult * extra_mult
    hourly_prob = min(hourly_prob, 0.20)

    peak_hours = [8, 9, 12, 13, 18, 19, 20, 21, 22]
    thresholds = []
    for hour in range(24):
        if hour in peak_hours:
            thresholds.append(round(hourly_prob * 1.5, 4))
        elif hour < 6:
            thresholds.append(round(hourly_prob * 0.2, 4))
        else:
            thresholds.append(round(hourly_prob, 4))

    return thresholds


def build_user_profile(persona: dict[str, Any], dimensions: dict[str, Any]) -> str:
    name = persona.get("name", "Unknown")
    age = persona.get("age", "unknown")
    title = persona.get("title", "")
    description = persona.get("description", "")

    region = dimensions.get("region", "")
    education = dimensions.get("highest_education", "")
    domain = dimensions.get("domain", "")
    seniority = dimensions.get("seniority", "")
    intent = dimensions.get("intent", "")
    emotional_state = dimensions.get("emotional_state", "")
    marital_status = dimensions.get("marital_status", "")
    children = dimensions.get("children", "")
    language = dimensions.get("primary_language", "")

    openness = dimensions.get("personality_big5_openness", "Medium")
    conscientiousness = dimensions.get("personality_big5_conscientiousness", "Medium")
    extraversion = dimensions.get("personality_big5_extraversion", "Medium")
    agreeableness = dimensions.get("personality_big5_agreeableness", "Medium")
    neuroticism = dimensions.get("personality_big5_neuroticism", "Medium")

    parts = [
        f"{name} is a {age}-year-old {seniority.lower()} professional in {domain.lower()}.",
        f"Based in {region}, education level: {education}.",
    ]

    if marital_status or children:
        parts.append(f"Personal life: {marital_status}, {children.lower()}.")

    parts.append(
        f"Personality: openness={openness.lower()}, conscientiousness={conscientiousness.lower()}, "
        f"extraversion={extraversion.lower()}, agreeableness={agreeableness.lower()}, "
        f"neuroticism={neuroticism.lower()}."
    )

    if emotional_state:
        parts.append(f"Current disposition: {emotional_state.lower()}.")

    if intent:
        parts.append(f"Primary motivation: {intent}.")

    if language:
        parts.append(f"Native language: {language}.")

    return " ".join(parts)


def build_bio(persona: dict[str, Any], dimensions: dict[str, Any]) -> str:
    title = persona.get("title", "")
    domain = dimensions.get("domain", "")
    region = dimensions.get("region", "")
    intent = dimensions.get("intent", "")

    parts = []
    if title:
        parts.append(title)
    if region:
        parts.append(f"Based in {region}")
    if intent:
        parts.append(f"Driven to {intent}")
    return " | ".join(parts) if parts else f"Professional in {domain}"


def parse_persona_yaml(filepath: Path) -> dict[str, Any]:
    raw = yaml.safe_load(filepath.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid persona YAML (not a mapping): {filepath}")
    return raw


def adapt_single_persona(raw: dict[str, Any], index: int = 0) -> OasisUserInfo:
    metadata = raw.get("metadata", {})
    persona = raw.get("persona", {})
    dimensions = persona.get("dimensions", {})

    persona_id = metadata.get("id", f"ID{index:04d}")
    name = persona.get("name", f"Agent_{index}")
    age = persona.get("age", 30)

    user_name = f"{slugify(name)}_{persona_id.lower()}"
    gender = map_gender(dimensions.get("gender_identity", ""))
    country = map_country(dimensions.get("region", "North America"), seed=index)
    profession = dimensions.get("domain", "Technology")
    topics = map_topics(profession)
    big5 = big5_to_numeric(dimensions)
    mbti = big5_to_mbti(big5)
    active_threshold = compute_activity_threshold(dimensions)
    user_profile = build_user_profile(persona, dimensions)
    bio = build_bio(persona, dimensions)

    return OasisUserInfo(
        persona_id=persona_id,
        name=name,
        user_name=user_name,
        bio=bio,
        user_profile=user_profile,
        mbti=mbti,
        gender=gender,
        age=age,
        country=country,
        profession=profession,
        interested_topics=topics,
        active_threshold=active_threshold,
        big_five=big5,
        raw_dimensions=dimensions,
    )


def load_personas_from_directory(
    directory: str | Path, max_agents: int | None = None
) -> list[OasisUserInfo]:
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Persona directory not found: {directory}")

    yaml_files = sorted(directory.glob("*.yaml"))
    if not yaml_files:
        yaml_files = sorted(directory.glob("*.yml"))

    if not yaml_files:
        raise FileNotFoundError(f"No YAML files found in: {directory}")

    if max_agents is not None:
        yaml_files = yaml_files[:max_agents]

    results = []
    for idx, filepath in enumerate(yaml_files):
        raw = parse_persona_yaml(filepath)
        user_info = adapt_single_persona(raw, index=idx)
        results.append(user_info)

    return results


def load_personas_from_files(filepaths: list[str | Path]) -> list[OasisUserInfo]:
    results = []
    for idx, filepath in enumerate(filepaths):
        filepath = Path(filepath)
        if not filepath.is_file():
            raise FileNotFoundError(f"Persona file not found: {filepath}")
        raw = parse_persona_yaml(filepath)
        user_info = adapt_single_persona(raw, index=idx)
        results.append(user_info)
    return results


def personas_to_oasis_dicts(personas: list[OasisUserInfo]) -> list[dict[str, Any]]:
    return [p.to_oasis_dict() for p in personas]


def personas_to_oasis_csv_rows(
    personas: list[OasisUserInfo],
    following_lists: list[list[int]] | None = None,
    activity_frequency: int = 100,
) -> list[dict[str, str]]:
    rows = []
    for i, p in enumerate(personas):
        following = following_lists[i] if following_lists else []
        rows.append({
            "user_id": str(i),
            "name": p.name,
            "username": p.user_name,
            "description": p.bio,
            "user_char": p.user_profile,
            "following_agentid_list": repr(following),
            "previous_tweets": "[]",
            "activity_level": repr(["active"] * 24),
            "activity_level_frequency": repr([activity_frequency] * 24),
            "tweets_id": "0",
        })
    return rows


def export_oasis_csv(
    personas: list[OasisUserInfo],
    output_path: str | Path,
    following_lists: list[list[int]] | None = None,
    activity_frequency: int = 100,
) -> Path:
    import csv

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = personas_to_oasis_csv_rows(personas, following_lists, activity_frequency)
    fieldnames = [
        "user_id", "name", "username", "description", "user_char",
        "following_agentid_list", "previous_tweets", "activity_level",
        "activity_level_frequency", "tweets_id",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return output_path
