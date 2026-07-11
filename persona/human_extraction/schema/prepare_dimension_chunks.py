#!/usr/bin/env python3
"""Build stable, semantic Stack Overflow extraction dimension chunks.

Source and output
-----------------
The authoritative input is ``persona/schema/dimensions.json``. The tracked
output is ``persona/human_extraction/schema/dimension_chunks.jsonl``. Each
JSONL line is one self-contained, nested chunk object containing:

* a stable chunk ID, conceptual label, and description;
* source categories, size, ordered dimension IDs, and full source dimension
  metadata (including allowed values for later JSON Schema construction);
* an explicit semantic justification when its size is outside the preferred
  range; and
* nested manifest context with the source catalog hash, grouping policy,
  manifest version, chunk ordinal, and total chunk count.

Grouping policy
---------------
The reviewed ``GROUP_SPECS`` below use category as the primary signal, explicit
source-order ID spans or named ID sets for coherent subtopics, and deliberate
merges for small related categories. The target is 30 dimensions per chunk and
the preferred range is 20 through 35. A chunk outside that range is rejected
unless its group specification supplies a non-empty ``size_exception``.

Validation and determinism
--------------------------
Before rendering, the script validates catalog structure, IDs, indexes, value
sets, defaults, selector endpoints, chunk IDs, exact one-time coverage, and
size-exception policy. Dimensions retain authoritative index order inside each
chunk. JSON serialization and the source hash are canonical and contain no
timestamps, so identical inputs and grouping rules produce identical output.

Usage from the repository root
------------------------------
Write or refresh the tracked artifact::

    python persona/human_extraction/schema/prepare_dimension_chunks.py

Validate the source and fail if the tracked JSONL is missing or stale::

    python persona/human_extraction/schema/prepare_dimension_chunks.py --check

Validate and print the chunk summary without reading or writing the output::

    python persona/human_extraction/schema/prepare_dimension_chunks.py --dry-run

``--source`` and ``--output`` may be supplied for explicit paths. This script
only prepares the schema-first artifact; the current Stack Overflow extractor
does not consume it yet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = REPO_ROOT / "persona" / "schema" / "dimensions.json"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "persona"
    / "human_extraction"
    / "schema"
    / "dimension_chunks.jsonl"
)
SOURCE_REPOSITORY_PATH = "persona/schema/dimensions.json"
MANIFEST_VERSION = "1.0"
TARGET_SIZE = 30
PREFERRED_MIN_SIZE = 20
PREFERRED_MAX_SIZE = 35
DIMENSION_ID_PATTERN = re.compile(r"[a-z][a-z0-9_]*\Z")


class ValidationError(ValueError):
    """Raised when the catalog, grouping rules, or manifest is invalid."""


@dataclass(frozen=True)
class Selector:
    """Select all, an inclusive source-order span, or named IDs in a category."""

    category: str
    start_id: str | None = None
    end_id: str | None = None
    dimension_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class GroupSpec:
    chunk_id: str
    label: str
    description: str
    selectors: tuple[Selector, ...]
    size_exception: str | None = None


def all_of(category: str) -> Selector:
    return Selector(category=category)


def span(category: str, start_id: str, end_id: str) -> Selector:
    return Selector(category=category, start_id=start_id, end_id=end_id)


def named(category: str, *dimension_ids: str) -> Selector:
    return Selector(category=category, dimension_ids=tuple(dimension_ids))


# These boundaries were reviewed against every ID, label, and description in
# the 1,290-dimension catalog.  Spans follow authoritative source order; named
# selections are used where source order does not follow the concept boundary.
GROUP_SPECS: tuple[GroupSpec, ...] = (
    GroupSpec(
        "demographics_identity_household",
        "Identity, household, and cultural demographics",
        "Core identity, household composition, social position, and broad cultural background.",
        (
            all_of("Demographic: Core"),
            all_of("Demographic: Cultural"),
            all_of("Demographic: Family"),
        ),
    ),
    GroupSpec(
        "demographics_life_course",
        "Life course and formative events",
        "Life stage, mobility, adversity, relationships, and other formative experiences.",
        (all_of("Demographic: Life Events"),),
    ),
    GroupSpec(
        "languages_core_europe",
        "Language profile and European languages",
        "Overall language profile plus familiarity with European language families.",
        (
            named(
                "Linguistic: Language",
                "primary_language",
                "english_proficiency",
                "multilingualism",
                "lang_english",
                "lang_french",
                "lang_portuguese",
                "lang_russian",
                "lang_german",
                "lang_italian",
                "lang_turkish",
                "lang_dutch",
                "lang_polish",
                "lang_ukrainian",
                "lang_greek",
                "lang_czech",
                "lang_hungarian",
                "lang_romanian",
                "lang_swedish",
                "lang_norwegian",
                "lang_danish",
                "lang_finnish",
                "lang_serbian",
                "lang_croatian",
                "lang_bulgarian",
                "lang_slovak",
            ),
        ),
    ),
    GroupSpec(
        "languages_asia_africa",
        "Asian and African languages",
        "Familiarity with languages primarily associated with Asia and Africa.",
        (
            named(
                "Linguistic: Language",
                "lang_mandarin",
                "lang_cantonese",
                "lang_spanish",
                "lang_hindi",
                "lang_arabic",
                "lang_bengali",
                "lang_japanese",
                "lang_korean",
                "lang_vietnamese",
                "lang_thai",
                "lang_indonesian",
                "lang_malay",
                "lang_swahili",
                "lang_persian",
                "lang_hebrew",
                "lang_tagalog",
                "lang_urdu",
                "lang_tamil",
                "lang_telugu",
                "lang_marathi",
                "lang_punjabi",
                "lang_gujarati",
                "lang_hausa",
                "lang_yoruba",
                "lang_igbo",
                "lang_amharic",
                "lang_zulu",
                "lang_afrikaans",
            ),
        ),
    ),
    GroupSpec(
        "expertise_computing_data",
        "Computing and data expertise",
        "General expertise calibration, data fields, and core computing specialties.",
        (
            span("Expertise: Domains", "domain", "fam_data_science"),
            span("Expertise: Domains", "fam_cybersecurity", "fam_ux_research"),
        ),
    ),
    GroupSpec(
        "expertise_health_life_sciences",
        "Health and life-science expertise",
        "Clinical medicine, molecular life science, public health, and human performance.",
        (
            span("Expertise: Domains", "fam_cardiology", "fam_immunology"),
            span("Expertise: Domains", "fam_molecular_biology", "fam_physical_chemistry"),
            span("Expertise: Domains", "fam_agronomy", "fam_sports_science"),
        ),
    ),
    GroupSpec(
        "expertise_law_economics_business",
        "Law, economics, and business expertise",
        "Legal, financial, economic, marketing, operations, and management specialties.",
        (
            span("Expertise: Domains", "fam_constitutional_law", "fam_behavioral_economics"),
            span("Expertise: Domains", "fam_journalism", "fam_actuarial_science"),
        ),
    ),
    GroupSpec(
        "expertise_engineering_environment",
        "Engineering, physical science, and environment",
        "Engineering, physical and earth sciences, infrastructure, energy, and transport.",
        (
            span("Expertise: Domains", "fam_structural_engineering", "fam_control_systems"),
            span("Expertise: Domains", "fam_particle_physics", "fam_ecology"),
            span(
                "Expertise: Domains",
                "fam_geographic_information_systems",
                "fam_maritime_navigation",
            ),
        ),
    ),
    GroupSpec(
        "expertise_humanities_creative_service",
        "Humanities, creative, and service expertise",
        "Education, humanities, social science, design, creative production, and public service.",
        (
            span("Expertise: Domains", "fam_curriculum_design", "fam_pedagogy"),
            span("Expertise: Domains", "fam_sociology", "fam_landscape_design"),
            span("Expertise: Domains", "fam_graphic_design", "fam_typography"),
            span("Expertise: Domains", "fam_hospitality_management", "fam_3d_modeling"),
            span("Expertise: Domains", "fam_military_strategy", "fam_library_science"),
        ),
        "Keeping the connected humanities, creative-production, and service fields together is clearer than an arbitrary split.",
    ),
    GroupSpec(
        "personality_character_strengths",
        "Character strengths and dispositions",
        "Broad character traits, strengths, interpersonal virtues, and adaptive dispositions.",
        (all_of("Personality: Character"),),
    ),
    GroupSpec(
        "learning_academic_background",
        "Academic background and subjects",
        "Education level, institutional context, and familiarity with school subjects.",
        (all_of("Learning: Academic"),),
    ),
    GroupSpec(
        "industries_economy_infrastructure",
        "Industry context: economy and infrastructure",
        "Role context and industries spanning technology, finance, production, infrastructure, health, and hospitality.",
        (span("Professional: Industry", "company_size", "ind_media"),),
    ),
    GroupSpec(
        "industries_public_creative_services",
        "Industry context: public, creative, and services",
        "Media, public, transport, professional-service, consumer, sports, and arts industries.",
        (span("Professional: Industry", "ind_entertainment", "ind_fine_art"),),
    ),
    GroupSpec(
        "professional_developer_context",
        "Career and developer participation context",
        "Career stage, work setting, developer role, community participation, and open-source collaboration.",
        (
            all_of("Professional: Career"),
            all_of("Behavior: Work"),
            all_of("Developer: Professional Context"),
            all_of("Developer: Community Behavior"),
            all_of("Developer: Open Source Behavior"),
        ),
    ),
    GroupSpec(
        "psychology_decision_relational_state",
        "Decision, relational, and situational psychology",
        "Risk and closure tendencies, relational orientation, learning style, and current interaction state.",
        (
            all_of("Risk & Decision"),
            all_of("Personality: MBTI"),
            all_of("State: Emotional"),
            all_of("Learning: Style"),
            all_of("Personality: Relationships"),
            named("Worldview: Beliefs", "dospert_health_safety_risk_tolerance"),
        ),
    ),
    GroupSpec(
        "values_personal_priorities",
        "Personal values and priorities",
        "Everyday priorities covering family, achievement, freedom, community, ethics, and identity.",
        (span("Values & Motivation", "values_priority", "val_privacy"),),
    ),
    GroupSpec(
        "values_formal_constructs",
        "Formal value and motivation constructs",
        "Schwartz values, self-determination needs, need for cognition, and moral foundations.",
        (
            span("Values & Motivation", "schwartz_value_self_direction", "need_for_cognition"),
            span("Worldview: Beliefs", "mft_care_harm", "mft_liberty_oppression"),
        ),
    ),
    GroupSpec(
        "worldview_institutions_change",
        "Worldview: institutions and technological change",
        "Political, institutional, economic, scientific, and technology-related beliefs and attitudes.",
        (span("Worldview: Beliefs", "political_lean", "att_rapid_change"),),
    ),
    GroupSpec(
        "worldview_civic_consumer_life",
        "Worldview: civic and everyday life",
        "Attitudes about technology adoption, consumption, rights, work, transport, cities, and education.",
        (span("Worldview: Beliefs", "att_new_technology", "acad_political_theory"),),
    ),
    GroupSpec(
        "communication_cognitive_style",
        "Communication and cognitive style",
        "Tone plus reasoning, explanation, interaction, and response-style preferences.",
        (all_of("Linguistic: Communication"),),
        "The 35 tightly coupled cognitive-style axes and two communication context fields are more useful as one schema.",
    ),
    GroupSpec(
        "behavior_preferences_time",
        "Behavioral preferences and time orientation",
        "Media and accessibility preferences, pet peeves, trade-off preferences, and temporal habits.",
        (all_of("Behavior: Time"), all_of("Behavior: Preferences")),
        "Keeping the preference trade-offs with their closely related time-orientation axes avoids a tiny three-item chunk.",
    ),
    GroupSpec(
        "skills_communication_technical_management",
        "Communication, technical, and management skills",
        "Writing, speaking, software, analysis, leadership, reasoning, and language skills.",
        (span("Expertise: Skills", "skill_writing", "skill_interpretation"),),
    ),
    GroupSpec(
        "skills_creative_practical_applied",
        "Creative, practical, and applied skills",
        "Design and media craft, household and financial skills, learning, facilitation, and commercial skills.",
        (span("Expertise: Skills", "skill_design_thinking", "skill_selling"),),
    ),
    GroupSpec(
        "tools_data_productivity_business",
        "Data, productivity, and business tools",
        "Data analysis, knowledge work, collaboration, CRM, enterprise, document, and planning tools.",
        (
            named(
                "Skills: Tools",
                "tool_excel", "tool_google_sheets", "tool_python", "tool_r", "tool_sql",
                "tool_tableau", "tool_power_bi", "tool_looker", "tool_notion", "tool_obsidian",
                "tool_jira", "tool_linear", "tool_slack", "tool_microsoft_teams", "tool_salesforce",
                "tool_hubspot", "tool_sap", "tool_oracle_erp", "tool_word", "tool_powerpoint",
                "tool_keynote", "tool_trello", "tool_asana",
            ),
        ),
    ),
    GroupSpec(
        "tools_software_cloud_development",
        "Software, cloud, and development tools",
        "Source control, infrastructure, cloud, IDE, statistics, game, web, and API development tools.",
        (
            named(
                "Skills: Tools",
                "tool_git", "tool_github", "tool_gitlab", "tool_docker", "tool_kubernetes",
                "tool_terraform", "tool_aws", "tool_azure", "tool_google_cloud", "tool_vs_code",
                "tool_jetbrains_ides", "tool_vim", "tool_jupyter", "tool_matlab", "tool_stata",
                "tool_spss", "tool_sas", "tool_linux_cli", "tool_unity", "tool_unreal_engine",
                "tool_wordpress", "tool_webflow", "tool_postman",
            ),
        ),
    ),
    GroupSpec(
        "tools_design_commerce_ai",
        "Design, commerce, and AI tools",
        "Creative design and engineering, commerce and finance, communication, AI, and automation tools.",
        (
            named(
                "Skills: Tools",
                "tool_figma", "tool_sketch", "tool_photoshop", "tool_illustrator", "tool_indesign",
                "tool_after_effects", "tool_premiere_pro", "tool_canva", "tool_blender", "tool_autocad",
                "tool_solidworks", "tool_revit", "tool_shopify", "tool_stripe", "tool_quickbooks",
                "tool_xero", "tool_zoom", "tool_airtable", "tool_chatgpt", "tool_claude",
                "tool_github_copilot", "tool_midjourney", "tool_zapier",
            ),
        ),
    ),
    GroupSpec(
        "interests_society_technology_life",
        "Interests: society, technology, and daily life",
        "Public affairs, science, finance, family, home, transport, and active-life interests.",
        (span("Interests: Topics", "topic_politics", "topic_running"),),
    ),
    GroupSpec(
        "interests_arts_spiritual_outdoors_games",
        "Interests: arts, spirituality, outdoors, and games",
        "Visual and performing arts, literature, belief, contemplative practice, nature, and games.",
        (span("Interests: Topics", "topic_photography", "topic_social_media"),),
    ),
    GroupSpec(
        "interests_community_craft_growth",
        "Interests: community, craft, and personal growth",
        "Community and environment, food and drink, making, emerging technology, entrepreneurship, and growth.",
        (span("Interests: Topics", "topic_volunteering", "topic_mindfulness"),),
    ),
    GroupSpec(
        "culture_country_familiarity",
        "Country and regional cultural familiarity",
        "Familiarity with the catalog's country and regional cultures.",
        (span("Interests: Culture", "cult_united_states", "cult_portugal"),),
        "The forty parallel country-culture fields form one indivisible lookup concept and are clearer together.",
    ),
    GroupSpec(
        "lifestyle_consumption_routines",
        "Lifestyle, consumption, and routines",
        "Daily consumption, planning, media, finance, devices, travel, hobbies, and volunteering patterns.",
        (span("Interests: Culture", "lstyle_smoking", "lstyle_volunteering"),),
    ),
    GroupSpec(
        "media_music_genres",
        "Music genre interests",
        "Interest across popular, traditional, regional, electronic, and specialist music genres.",
        (span("Interests: Media", "musg_pop", "musg_bollywood"),),
    ),
    GroupSpec(
        "media_film_genres",
        "Film genre interests",
        "Interest across mainstream, genre, independent, historical, and art-house film.",
        (span("Interests: Media", "filmg_action", "filmg_disaster"),),
    ),
    GroupSpec(
        "media_book_genres",
        "Book genre interests",
        "Interest across fiction, nonfiction, poetry, graphic, travel, culinary, and essay forms.",
        (span("Interests: Media", "bookg_literary_fiction", "bookg_essays"),),
    ),
    GroupSpec(
        "food_cuisine_interests",
        "Cuisine and food interests",
        "Interest in regional cuisines and dietary or specialty food traditions.",
        (all_of("Interests: Food"),),
    ),
    GroupSpec(
        "sports_interests",
        "Sports and physical-activity interests",
        "Interest across team, individual, combat, outdoor, strength, mind-body, and precision sports.",
        (all_of("Interests: Sports"),),
        "The forty parallel sport-interest fields form one cohesive inventory and do not have a principled split.",
    ),
    GroupSpec(
        "personality_big_five_facets",
        "Big Five facets",
        "The catalog's original thirty Big Five facet-level traits.",
        (span("Personality: Big Five", "big5_imagination", "big5_vulnerability"),),
    ),
    GroupSpec(
        "personality_bfi2",
        "BFI-2 domains and facets",
        "The five BFI-2 domains and fifteen associated facet scores.",
        (span("Personality: Big Five", "bfi2_domain_extraversion", "bfi2_facet_creative_imagination"),),
    ),
    GroupSpec(
        "health_physical_fitness_lifestyle",
        "Physical health, fitness, and health lifestyle",
        "General, sensory, mobility, mental, accessibility, fitness, diet, and substance-use health context.",
        (
            all_of("Health: Fitness"),
            all_of("Health: Lifestyle"),
            all_of("Health: Physical"),
        ),
    ),
    GroupSpec(
        "hobbies_crafts_collecting_nature",
        "Hobbies: crafts, collecting, and nature",
        "Textile and material crafts, collecting, gardening, animal keeping, observation, and geocaching.",
        (span("Interests: Hobbies", "hob_knitting", "hob_rock_climbing"),),
    ),
    GroupSpec(
        "hobbies_adventure_food_performance",
        "Hobbies: adventure, food, and performance",
        "Outdoor adventure, food craft, dance and performance, visual making, genealogy, and cosplay.",
        (span("Interests: Hobbies", "hob_bouldering", "hob_cosplay"),),
    ),
    GroupSpec(
        "behavior_habits",
        "Recurring habits and self-management",
        "Routine practices involving reflection, planning, food, health, devices, organization, and communication.",
        (all_of("Behavior: Habits"),),
    ),
    GroupSpec(
        "code_style_maintenance",
        "Code style, quality, and maintenance",
        "Code-writing conventions, structure, testing, maintenance, debugging, security, and onboarding.",
        (
            span("Skills: Programming", "code_comment_style", "code_refactoring_frequency"),
            named("Professional: Industry", "code_function_length"),
            all_of("Developer: Code Maintenance"),
        ),
    ),
    GroupSpec(
        "programming_languages",
        "Programming language proficiency",
        "Proficiency across general-purpose, systems, functional, data, shell, legacy, and query languages.",
        (span("Skills: Programming", "prog_python", "prog_graphql"),),
    ),
    GroupSpec(
        "developer_ai_tools_workflows",
        "Developer AI adoption, agents, and workflows",
        "AI and agent adoption, task fit, trust and control, workflow impact, and technology evaluation criteria.",
        (
            all_of("Developer: AI Adoption"),
            all_of("Developer: Agent Adoption"),
            all_of("Developer: AI Workflow Tasks"),
            all_of("Developer: Technology Evaluation"),
        ),
        "These thirty-nine fields jointly describe one developer-AI adoption model; separating evaluation from use would weaken it.",
    ),
)


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_and_validate_catalog(path: Path) -> dict[str, Any]:
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"source catalog not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"source catalog is not valid JSON: {path}: {exc}") from exc

    if not isinstance(catalog, dict):
        raise ValidationError("source catalog root must be a JSON object")
    dimensions = catalog.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise ValidationError("source catalog dimensions must be a non-empty array")
    if catalog.get("targetDimensions") != len(dimensions):
        raise ValidationError(
            "targetDimensions does not equal the dimensions array length: "
            f"{catalog.get('targetDimensions')!r} != {len(dimensions)}"
        )

    seen_ids: set[str] = set()
    required = ("id", "label", "category", "description", "values", "index")
    for expected_index, dimension in enumerate(dimensions, start=1):
        if not isinstance(dimension, dict):
            raise ValidationError(f"dimension {expected_index} must be an object")
        missing = [field for field in required if field not in dimension]
        if missing:
            raise ValidationError(
                f"dimension {expected_index} is missing required fields: {', '.join(missing)}"
            )
        dimension_id = dimension["id"]
        if not isinstance(dimension_id, str) or not DIMENSION_ID_PATTERN.fullmatch(dimension_id):
            raise ValidationError(f"invalid dimension id at index {expected_index}: {dimension_id!r}")
        if dimension_id in seen_ids:
            raise ValidationError(f"duplicate dimension id: {dimension_id}")
        seen_ids.add(dimension_id)
        if dimension["index"] != expected_index:
            raise ValidationError(
                f"dimension {dimension_id} has index {dimension['index']!r}; expected {expected_index}"
            )
        for field in ("label", "category", "description"):
            if not isinstance(dimension[field], str) or not dimension[field].strip():
                raise ValidationError(f"dimension {dimension_id} has invalid {field}")
        values = dimension["values"]
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(value, str) or not value for value in values)
            or len(values) != len(set(values))
        ):
            raise ValidationError(f"dimension {dimension_id} has invalid or duplicate values")
        default = dimension.get("defaultValue")
        defaults = default if isinstance(default, list) else [default]
        if any(value is not None and value not in values for value in defaults):
            raise ValidationError(
                f"dimension {dimension_id} has defaultValue outside its allowed values"
            )
        if "phrase" in dimension and not isinstance(dimension["phrase"], str):
            raise ValidationError(f"dimension {dimension_id} has a non-string phrase")
    return catalog


def _selector_ids(
    selector: Selector,
    category_dimensions: dict[str, list[dict[str, Any]]],
) -> list[str]:
    dimensions = category_dimensions.get(selector.category)
    if dimensions is None:
        raise ValidationError(f"group selector references missing category: {selector.category}")
    category_ids = [dimension["id"] for dimension in dimensions]
    if selector.dimension_ids:
        missing = [dimension_id for dimension_id in selector.dimension_ids if dimension_id not in category_ids]
        if missing:
            raise ValidationError(
                f"selector for {selector.category} references missing IDs: {', '.join(missing)}"
            )
        return list(selector.dimension_ids)
    if selector.start_id is None and selector.end_id is None:
        return category_ids
    if selector.start_id is None or selector.end_id is None:
        raise ValidationError(f"selector for {selector.category} has an incomplete span")
    try:
        start = category_ids.index(selector.start_id)
        end = category_ids.index(selector.end_id)
    except ValueError as exc:
        raise ValidationError(
            f"selector span for {selector.category} has a missing endpoint: "
            f"{selector.start_id}..{selector.end_id}"
        ) from exc
    if start > end:
        raise ValidationError(
            f"selector span for {selector.category} is reversed: "
            f"{selector.start_id}..{selector.end_id}"
        )
    return category_ids[start : end + 1]


def build_manifest(
    catalog: dict[str, Any],
    *,
    source_path: str = SOURCE_REPOSITORY_PATH,
) -> dict[str, Any]:
    dimensions: list[dict[str, Any]] = catalog["dimensions"]
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_id: dict[str, dict[str, Any]] = {}
    source_position: dict[str, int] = {}
    for position, dimension in enumerate(dimensions):
        by_category[dimension["category"]].append(dimension)
        by_id[dimension["id"]] = dimension
        source_position[dimension["id"]] = position

    chunk_ids = [spec.chunk_id for spec in GROUP_SPECS]
    if len(chunk_ids) != len(set(chunk_ids)):
        duplicates = sorted(
            chunk_id for chunk_id, count in Counter(chunk_ids).items() if count > 1
        )
        raise ValidationError(f"duplicate chunk IDs in grouping rules: {', '.join(duplicates)}")

    assignments: dict[str, str] = {}
    selected_by_chunk: dict[str, list[str]] = {}
    for spec in GROUP_SPECS:
        selected: set[str] = set()
        for selector in spec.selectors:
            for dimension_id in _selector_ids(selector, by_category):
                if dimension_id in selected:
                    raise ValidationError(
                        f"chunk {spec.chunk_id} selects {dimension_id} more than once"
                    )
                selected.add(dimension_id)
                previous = assignments.get(dimension_id)
                if previous is not None:
                    raise ValidationError(
                        f"dimension {dimension_id} is assigned to both {previous} and {spec.chunk_id}"
                    )
                assignments[dimension_id] = spec.chunk_id
        selected_by_chunk[spec.chunk_id] = sorted(selected, key=source_position.__getitem__)

    catalog_ids = [dimension["id"] for dimension in dimensions]
    missing = [dimension_id for dimension_id in catalog_ids if dimension_id not in assignments]
    extra = sorted(set(assignments) - set(catalog_ids))
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing ({len(missing)}): {', '.join(missing[:20])}")
        if extra:
            details.append(f"unknown ({len(extra)}): {', '.join(extra[:20])}")
        raise ValidationError("group coverage is not exact; " + "; ".join(details))

    chunks: list[dict[str, Any]] = []
    for spec in GROUP_SPECS:
        dimension_ids = selected_by_chunk[spec.chunk_id]
        size = len(dimension_ids)
        outside_preferred = size < PREFERRED_MIN_SIZE or size > PREFERRED_MAX_SIZE
        if outside_preferred and not spec.size_exception:
            raise ValidationError(
                f"chunk {spec.chunk_id} has size {size} outside "
                f"{PREFERRED_MIN_SIZE}..{PREFERRED_MAX_SIZE} without a justification"
            )
        if not outside_preferred and spec.size_exception:
            raise ValidationError(
                f"chunk {spec.chunk_id} has an unnecessary size exception at size {size}"
            )
        source_categories = list(
            dict.fromkeys(by_id[dimension_id]["category"] for dimension_id in dimension_ids)
        )
        chunk: dict[str, Any] = {
            "chunk_id": spec.chunk_id,
            "label": spec.label,
            "description": spec.description,
            "source_categories": source_categories,
            "size": size,
            "dimension_ids": dimension_ids,
            "dimensions": [by_id[dimension_id] for dimension_id in dimension_ids],
        }
        if spec.size_exception:
            chunk["size_exception"] = spec.size_exception
        chunks.append(chunk)

    flattened = [dimension_id for chunk in chunks for dimension_id in chunk["dimension_ids"]]
    counts = Counter(flattened)
    duplicates = sorted(dimension_id for dimension_id, count in counts.items() if count > 1)
    if len(flattened) != len(catalog_ids) or set(flattened) != set(catalog_ids) or duplicates:
        raise ValidationError("final manifest coverage/uniqueness validation failed")

    category_chunks: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        for category in chunk["source_categories"]:
            category_chunks[category].append(chunk["chunk_id"])
    split_categories = {
        category: chunk_list
        for category, chunk_list in category_chunks.items()
        if len(chunk_list) > 1
    }
    merged_chunks = {
        chunk["chunk_id"]: chunk["source_categories"]
        for chunk in chunks
        if len(chunk["source_categories"]) > 1
    }
    sizes = [chunk["size"] for chunk in chunks]
    exceptions = [
        {
            "chunk_id": chunk["chunk_id"],
            "size": chunk["size"],
            "reason": chunk["size_exception"],
        }
        for chunk in chunks
        if "size_exception" in chunk
    ]

    return {
        "manifest_version": MANIFEST_VERSION,
        "source_catalog": {
            "path": source_path,
            "schema_version": catalog.get("schemaVersion"),
            "canonical_json_sha256": canonical_sha256(catalog),
            "dimension_count": len(dimensions),
        },
        "grouping": {
            "strategy": (
                "Reviewed semantic groups using category as the primary signal, explicit ID boundaries "
                "for subtopics, and merges for small related categories."
            ),
            "dimension_order": "ascending authoritative dimension index within each chunk",
            "target_size": TARGET_SIZE,
            "preferred_min_size": PREFERRED_MIN_SIZE,
            "preferred_max_size": PREFERRED_MAX_SIZE,
            "size_exception_policy": (
                "Every chunk outside the preferred range must carry a non-empty semantic justification."
            ),
        },
        "summary": {
            "chunk_count": len(chunks),
            "covered_dimension_count": len(flattened),
            "unique_dimension_count": len(counts),
            "min_chunk_size": min(sizes),
            "median_chunk_size": statistics.median(sizes),
            "max_chunk_size": max(sizes),
            "size_exceptions": exceptions,
            "split_categories": split_categories,
            "merged_chunks": merged_chunks,
        },
        "chunks": chunks,
    }


def render_manifest(manifest: dict[str, Any]) -> str:
    """Render one self-contained, nested chunk object per JSONL record."""
    lines = []
    chunk_count = manifest["summary"]["chunk_count"]
    for chunk_number, chunk in enumerate(manifest["chunks"], start=1):
        record = {
            **chunk,
            "manifest_context": {
                "manifest_version": manifest["manifest_version"],
                "chunk_number": chunk_number,
                "chunk_count": chunk_count,
                "source_catalog": manifest["source_catalog"],
                "grouping": manifest["grouping"],
            },
        }
        lines.append(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        )
    return "\n".join(lines) + "\n"


def write_manifest(path: Path, rendered: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered)


def print_summary(manifest: dict[str, Any]) -> None:
    summary = manifest["summary"]
    print(
        "chunks={chunk_count} dimensions={covered_dimension_count} "
        "sizes(min/median/max)={min_chunk_size}/{median_chunk_size}/{max_chunk_size}".format(
            **summary
        )
    )
    exceptions = summary["size_exceptions"]
    if exceptions:
        print(
            f"size exceptions ({len(exceptions)}): "
            + ", ".join(f"{item['chunk_id']}={item['size']}" for item in exceptions)
        )
    else:
        print("size exceptions (0): none")
    splits = summary["split_categories"]
    print(
        f"category splits ({len(splits)}): "
        + (", ".join(f"{category}={len(chunks)}" for category, chunks in splits.items()) or "none")
    )
    merges = summary["merged_chunks"]
    print(
        f"category merges ({len(merges)} chunks): "
        + (", ".join(f"{chunk_id}={len(categories)}" for chunk_id, categories in merges.items()) or "none")
    )
    print(
        f"coverage=exact unique={summary['unique_dimension_count']} "
        f"total={summary['covered_dimension_count']}"
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="authoritative dimensions catalog",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="generated chunk manifest",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="validate and fail if the tracked manifest is missing or stale",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the summary without reading or writing the output",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        catalog = load_and_validate_catalog(args.source)
        source_path = (
            SOURCE_REPOSITORY_PATH
            if args.source.resolve() == DEFAULT_SOURCE.resolve()
            else args.source.as_posix()
        )
        manifest = build_manifest(catalog, source_path=source_path)
        rendered = render_manifest(manifest)
        print_summary(manifest)
        if args.dry_run:
            print("dry-run=ok (no files written)")
            return 0
        if args.check:
            try:
                existing = args.output.read_text(encoding="utf-8")
            except FileNotFoundError:
                print(f"ERROR: manifest is missing: {args.output}", file=sys.stderr)
                return 1
            if existing != rendered:
                print(
                    f"ERROR: manifest is stale; regenerate with {Path(__file__).name}: {args.output}",
                    file=sys.stderr,
                )
                return 1
            print(f"check=ok output={args.output}")
            return 0
        write_manifest(args.output, rendered)
        print(f"wrote={args.output}")
        return 0
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
