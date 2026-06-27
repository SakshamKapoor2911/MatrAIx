"""Render persona YAML dimensions into wiki-style agent profile text via dimensions.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_CATALOG_PATH = "persona/schema/dimensions.json"


@lru_cache(maxsize=4)
def load_dimension_catalog(catalog_path: str) -> dict[str, Any]:
    path = Path(catalog_path)
    if not path.is_file():
        path = _repo_root() / catalog_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_id: dict[str, dict[str, Any]] = {}
    for row in payload.get("dimensions") or []:
        if isinstance(row, dict) and row.get("id"):
            by_id[str(row["id"])] = row
    return {
        "schema_version": payload.get("schemaVersion"),
        "by_id": by_id,
        "probe_fields": payload.get("personaYamlProbeFields") or {},
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def dimension_meta(
    dimension_id: str, *, catalog_path: str = DEFAULT_CATALOG_PATH
) -> dict[str, Any] | None:
    return load_dimension_catalog(catalog_path)["by_id"].get(dimension_id)


def probe_path_for_dimension(
    dimension_id: str, *, catalog_path: str = DEFAULT_CATALOG_PATH
) -> str:
    catalog = load_dimension_catalog(catalog_path)
    for path, meta in catalog["probe_fields"].items():
        if isinstance(meta, dict) and meta.get("dimensionId") == dimension_id:
            return str(path)
    return f"dimensions.{dimension_id}"


def values_for_dimension(
    dimension_id: str, *, catalog_path: str = DEFAULT_CATALOG_PATH
) -> list[str]:
    meta = dimension_meta(dimension_id, catalog_path=catalog_path)
    if not meta:
        return []
    return [str(v) for v in meta.get("values") or []]


def _article_for(value: str) -> str:
    if not value:
        return "a"
    first = value.strip()[0].lower()
    if first in "aeiou":
        return "an"
    return "a"


def _dim_value(dimensions: dict[str, Any], key: str) -> str | None:
    raw = dimensions.get(key)
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {
        "none",
        "n/a",
        "none notable",
        "not applicable",
    }:
        return None
    return text


def _describe_age(age: str) -> str:
    if age == "65+":
        return "I am 65 or older"
    if "-" in age:
        low, high = age.split("-", 1)
        return f"I am between {low} and {high} years old"
    return f"I am {age} years old"


def _with_article(value: str) -> str:
    return f"{_article_for(value)} {value.lower()}"


def _paragraph(*sentences: str | None) -> str:
    parts = [s.strip().rstrip(".") for s in sentences if s and s.strip()]
    if not parts:
        return ""
    return " ".join(f"{part}." for part in parts)


def _narrative_identity(dimensions: dict[str, Any]) -> str:
    age = _dim_value(dimensions, "age_bracket")
    region = _dim_value(dimensions, "region")
    gender = _dim_value(dimensions, "gender_identity")
    urbanicity = _dim_value(dimensions, "urbanicity")
    socioeconomic = _dim_value(dimensions, "socioeconomic_band")
    cultural = _dim_value(dimensions, "cultural_background")
    life_stage = _dim_value(dimensions, "life_stage")
    life_events = _dim_value(dimensions, "major_life_events")

    opener = _describe_age(age) if age else "I am a person with a distinct background"
    if region and urbanicity:
        opener = (
            f"{opener}, based in {region} and living in "
            f"{_with_article(urbanicity)} setting"
        )
    elif region:
        opener = f"{opener}, based in {region}"
    elif urbanicity:
        opener = f"{opener}, living in {_with_article(urbanicity)} setting"

    return _paragraph(
        opener,
        f"I identify as {gender}" if gender else None,
        (
            f"I come from a {cultural} cultural background and sit in "
            f"{_with_article(socioeconomic)} socioeconomic band"
            if cultural and socioeconomic
            else (
                f"I come from a {cultural} cultural background"
                if cultural
                else (
                    f"My socioeconomic position is {_with_article(socioeconomic)} band"
                    if socioeconomic
                    else None
                )
            )
        ),
        (
            f"I am in the {life_stage} stage of life, with {life_events.lower()} "
            f"as a defining recent experience"
            if life_stage and life_events
            else (f"I am in the {life_stage} stage of life" if life_stage else None)
        ),
        (
            f"A defining recent experience for me has been {life_events.lower()}"
            if life_events and not life_stage
            else None
        ),
    )


def _narrative_education_career(dimensions: dict[str, Any]) -> str:
    education = _dim_value(dimensions, "highest_education")
    field = _dim_value(dimensions, "academic_field")
    institution = _dim_value(dimensions, "institution_tier")
    research = _dim_value(dimensions, "research_output")
    domain = _dim_value(dimensions, "domain")
    specialty = _dim_value(dimensions, "subject_specialty")
    stance = _dim_value(dimensions, "domain_characteristics")
    seniority = _dim_value(dimensions, "seniority")
    company = _dim_value(dimensions, "company_size")
    role = _dim_value(dimensions, "role_function")
    years = _dim_value(dimensions, "years_experience")
    linkedin = _dim_value(dimensions, "linkedin_activity")
    tech = _dim_value(dimensions, "tech_savviness")
    expertise = _dim_value(dimensions, "expertise_gap")

    edu_bits: list[str] = []
    if education:
        edu_bits.append(f"{education.lower()} as my highest formal credential")
    if field:
        edu_bits.append(f"with formal study in {field.lower()}")
    if institution:
        edu_bits.append(f"through a path best described as {institution.lower()}")

    edu = None
    if edu_bits:
        edu = "I completed " + ", ".join(edu_bits)

    work_bits: list[str] = []
    if domain:
        work_bits.append(f"{domain.lower()}")
    if specialty:
        work_bits.append(f"with a specialty in {specialty.lower()}")
    if stance:
        work_bits.append(f"approaching the field as {stance.lower()}")
    work = (
        "Professionally, I work in "
        + ", ".join(work_bits[:-1])
        + (", " + work_bits[-1] if len(work_bits) > 1 else work_bits[0])
        if work_bits
        else None
    )

    role_line = None
    if seniority or role or company or years:
        chunks = []
        if seniority:
            chunks.append(f"at a {seniority.lower()} level")
        if role:
            chunks.append(f"in {role.lower()}")
        if company:
            chunks.append(f"within {company.lower()} organization")
        if years:
            chunks.append(f"with {years} years of experience in the field")
        role_line = "I am positioned " + ", ".join(chunks)

    return _paragraph(
        edu,
        work,
        role_line,
        f"My published or research footprint is {research.lower()}"
        if research
        else None,
        f"On professional networks I am {linkedin.lower()}" if linkedin else None,
        f"I am {tech.lower()} with technology" if tech else None,
        f"Relative to the task at hand, I am approaching it as {expertise.lower()}"
        if expertise
        else None,
    )


def _narrative_language(dimensions: dict[str, Any]) -> str:
    primary = _dim_value(dimensions, "primary_language")
    english = _dim_value(dimensions, "english_proficiency")
    multilingual = _dim_value(dimensions, "multilingualism")
    register = _dim_value(dimensions, "register")

    lang = None
    if primary:
        lang = f"My primary language is {primary}"
        if multilingual:
            lang += f", and I am {multilingual.lower()} overall"
    elif multilingual:
        lang = f"I am {multilingual.lower()} in my language use"

    return _paragraph(
        lang,
        f"My English proficiency is {english}" if english else None,
        f"I usually speak in a {register.lower()} register" if register else None,
    )


def _narrative_personality(dimensions: dict[str, Any]) -> str:
    trait = _dim_value(dimensions, "dominant_trait")
    risk = _dim_value(dimensions, "risk_tolerance")
    decision = _dim_value(dimensions, "decision_style")
    values = _dim_value(dimensions, "values_priority")
    politics = _dim_value(dimensions, "political_lean")
    religion = _dim_value(dimensions, "religiosity")
    neurotype = _dim_value(dimensions, "neurotype")
    spending = _dim_value(dimensions, "economic_motivation")
    learning = _dim_value(dimensions, "learning_style")
    media = _dim_value(dimensions, "media_diet")
    accessibility = _dim_value(dimensions, "accessibility_needs")
    modality = _dim_value(dimensions, "modality_pref")

    personality = None
    if trait or risk or decision:
        chunks = []
        if trait:
            chunks.append(f"{trait.lower()} is my most pronounced trait")
        if risk:
            chunks.append(f"I have a {risk.lower()} appetite for risk")
        if decision:
            chunks.append(f"I make decisions in an {decision.lower()} way")
        personality = "Personality-wise, " + ", ".join(chunks)

    worldview = None
    if values or politics or religion or neurotype or spending:
        chunks = []
        if values:
            chunks.append(f"{values} ranks first among my personal values")
        if religion:
            chunks.append(f"I am {religion.lower()} in my relationship to religion")
        if politics:
            chunks.append(f"politically I am {politics.lower()}")
        if neurotype:
            chunks.append(f"my cognitive profile is {neurotype.lower()}")
        if spending:
            chunks.append(f"my spending posture is {spending.lower()}")
        worldview = "In worldview and motivation, " + ", ".join(chunks)

    habits = None
    if learning or media or accessibility or modality:
        chunks = []
        if learning:
            chunks.append(
                f"I absorb information best through {learning.lower()} learning"
            )
        if media:
            chunks.append(f"my media diet is {media.lower()}")
        if accessibility:
            chunks.append(f"I have {accessibility.lower()} accessibility needs")
        if modality:
            chunks.append(f"I prefer {modality.lower()} answer formats")
        habits = "Day to day, " + ", ".join(chunks)

    return _paragraph(personality, worldview, habits)


def _narrative_interaction(dimensions: dict[str, Any]) -> str:
    mood = _dim_value(dimensions, "emotional_state")
    intent = _dim_value(dimensions, "intent")
    complexity = _dim_value(dimensions, "query_complexity")
    tone = _dim_value(dimensions, "tone_expected")
    trust = _dim_value(dimensions, "trust_level")
    safety = _dim_value(dimensions, "safety_sensitivity")
    urgency = _dim_value(dimensions, "time_pressure")
    prior = _dim_value(dimensions, "prior_context")
    device = _dim_value(dimensions, "device_context")

    state = None
    if mood or intent or complexity:
        chunks = []
        if mood:
            chunks.append(f"I am {mood.lower()}")
        if intent:
            chunks.append(f"my goal is to {intent.lower()}")
        if complexity:
            chunks.append(f"my request tends to be {complexity.lower()}")
        state = "Right now, " + ", ".join(chunks)

    context = None
    if tone or trust or safety or urgency or prior or device:
        chunks = []
        if tone:
            chunks.append(f"I want {tone.lower()} replies")
        if trust:
            chunks.append(f"I am {trust.lower()} toward the assistant")
        if safety:
            chunks.append(f"the topic sits in a {safety.lower()} risk class")
        if urgency:
            chunks.append(
                "I feel no particular time pressure"
                if urgency.lower().startswith("no")
                else f"I am under {urgency.lower()} time pressure"
            )
        if prior:
            chunks.append(f"this builds on {prior.lower()}")
        if device:
            chunks.append(f"I am interacting from {device.lower()}")
        context = "In this interaction, " + ", ".join(chunks)

    return _paragraph(state, context)


def _narrative_communication_style(
    dimensions: dict[str, Any],
    *,
    by_id: dict[str, dict[str, Any]],
) -> str:
    voice_keys = (
        "cog_verbosity",
        "cog_formality",
        "cog_directness",
        "cog_humor",
        "cog_politeness",
        "cog_emoji_use",
        "cog_use_of_jargon",
        "cog_precision_of_language",
    )
    thinking_keys = (
        "cog_abstraction",
        "cog_big_picture_vs_detail",
        "cog_risk_framing",
        "cog_skepticism",
        "cog_optimism",
        "cog_curiosity",
        "cog_numeracy_comfort",
        "cog_visual_vs_verbal",
        "cog_reading_vs_watching",
    )
    habit_keys = (
        "cog_assertiveness",
        "cog_conflict_approach",
        "cog_feedback_receptiveness",
        "cog_question_asking",
        "cog_decision_speed",
        "cog_patience",
        "cog_attention_span",
        "cog_learning_pace",
        "cog_multitasking",
        "cog_perfectionism",
        "cog_procrastination",
        "cog_open_mindedness",
        "cog_ambiguity_tolerance",
        "cog_emotional_expressiveness",
        "cog_empathy_expression",
        "cog_confidence_calibration",
        "cog_detail_orientation",
        "cog_storytelling",
    )

    def _phrase(keys: tuple[str, ...]) -> str | None:
        parts: list[str] = []
        for dim_id in keys:
            text = _dim_value(dimensions, dim_id)
            if not text:
                continue
            meta = by_id.get(dim_id)
            label = str(
                (meta or {}).get("label") or dim_id.removeprefix("cog_")
            ).lower()
            parts.append(f"{text.lower()} {label}")
        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return f"{parts[0]} and {parts[1]}"
        return ", ".join(parts[:-1]) + f", and {parts[-1]}"

    voice = _phrase(voice_keys)
    thinking = _phrase(thinking_keys)
    habits = _phrase(habit_keys)

    return _paragraph(
        f"My voice tends to be {voice}" if voice else None,
        f"My thinking style is {thinking}" if thinking else None,
        f"In conversation I am {habits}" if habits else None,
    )


def build_dimension_narrative(
    dimensions: dict[str, Any],
    *,
    catalog_path: str = DEFAULT_CATALOG_PATH,
) -> list[str]:
    """Wiki-style first-person biography paragraphs for agent roleplay."""
    catalog = load_dimension_catalog(catalog_path)
    by_id = catalog["by_id"]

    paragraphs = [
        _narrative_identity(dimensions),
        _narrative_education_career(dimensions),
        _narrative_language(dimensions),
        _narrative_personality(dimensions),
        _narrative_interaction(dimensions),
        _narrative_communication_style(dimensions, by_id=by_id),
    ]
    return [p for p in paragraphs if p]


def build_template_context_extras(
    dimensions: dict[str, Any],
    *,
    catalog_path: str = DEFAULT_CATALOG_PATH,
) -> dict[str, Any]:
    return {
        "dimension_profile_narrative": build_dimension_narrative(
            dimensions, catalog_path=catalog_path
        ),
        "dimension_catalog_path": catalog_path,
    }
