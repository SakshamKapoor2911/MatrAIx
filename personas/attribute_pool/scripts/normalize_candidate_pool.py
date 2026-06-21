import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "candidate_pool_outputs"
OUT = INPUT_DIR / "normalized"
OUT.mkdir(parents=True, exist_ok=True)


TOP_LEVEL_CATEGORIES = [
    "Demographics & Population Grounding",
    "Life Context & Constraints",
    "Personality Traits",
    "Values, Goals & Motivations",
    "Worldview, Beliefs & Attitudes",
    "Cognitive & Capability Profile",
    "Behavioral Patterns & Preferences",
    "Social Identity, Relationships & Community",
    "Narrative Identity & Life History",
    "Domain-Specific Overlays",
]


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for",
    "from", "has", "have", "how", "i", "if", "in", "is", "it", "me",
    "my", "of", "on", "or", "r", "respondent", "s", "the", "their",
    "them", "they", "this", "to", "what", "when", "where", "which",
    "who", "why", "with", "you", "your",
}


DEEP_PERSONA_TOP_MAP = {
    "Demographic Information": ("Demographics & Population Grounding", "demographic information"),
    "Physical and Health Characteristics": ("Life Context & Constraints", "physical and health characteristics"),
    "Psychological and Cognitive Aspects": ("Cognitive & Capability Profile", "psychological and cognitive aspects"),
    "Cultural and Social Context": ("Social Identity, Relationships & Community", "cultural and social context"),
    "Relationships and Social Networks": ("Social Identity, Relationships & Community", "relationships and social networks"),
    "Career and Work Identity": ("Domain-Specific Overlays", "career and work identity"),
    "Education and Learning": ("Cognitive & Capability Profile", "education and learning"),
    "Hobbies, Interests, and Lifestyle": ("Behavioral Patterns & Preferences", "hobbies interests and lifestyle"),
    "Lifestyle and Daily Routine": ("Behavioral Patterns & Preferences", "lifestyle and daily routine"),
    "Core Values, Beliefs, and Philosophy": ("Values, Goals & Motivations", "core values beliefs and philosophy"),
    "Core Values, Beliefs, Philosophy": ("Values, Goals & Motivations", "core values beliefs and philosophy"),
    "Emotional and Relational Skills": ("Social Identity, Relationships & Community", "emotional and relational skills"),
    "Media Consumption and Engagement": ("Behavioral Patterns & Preferences", "media consumption and engagement"),
}


SCOPE_FACET_MAP = {
    "Demographic Information": ("Demographics & Population Grounding", "demographic information"),
    "Sociodemographic Behavior": ("Behavioral Patterns & Preferences", "sociodemographic behavior"),
    "Personal Values And Motivations": ("Values, Goals & Motivations", "personal values and motivations"),
    "Personal Values & Motivations": ("Values, Goals & Motivations", "personal values and motivations"),
    "Personality Traits": ("Personality Traits", "Big Five personality traits"),
    "Behavioral Patterns And Preferences": ("Behavioral Patterns & Preferences", "behavioral patterns and preferences"),
    "Behavioral Patterns & Preferences": ("Behavioral Patterns & Preferences", "behavioral patterns and preferences"),
    "Personal Identity And Life Narratives": ("Narrative Identity & Life History", "personal identity and life narratives"),
    "Personal Identity & Life Narratives": ("Narrative Identity & Life History", "personal identity and life narratives"),
    "Professional Identity And Career": ("Domain-Specific Overlays", "professional identity and career"),
    "Professional Identity & Career": ("Domain-Specific Overlays", "professional identity and career"),
}


def clean_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    value = str(value)
    value = value.replace("\u00a0", " ")
    value = value.replace("\ufeff", "")
    value = value.replace("鈥檚", "'s")
    value = value.replace("鈥檝", "'v")
    value = value.replace("鈥檓", "'m")
    value = value.replace("鈥檙", "'r")
    value = value.replace("鈥渟", '"s')
    value = value.replace("鈥?", "'")
    value = value.replace("â€™", "'")
    value = value.replace("â€œ", '"')
    value = value.replace("â€", '"')
    value = value.replace("â€“", "-")
    value = value.replace("â€”", "-")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def canonical_label(label):
    label = clean_text(label)
    label = re.sub(r"\s+\.\d+$", "", label)
    label = re.sub(r"^r['’]s\s+", "respondent's ", label, flags=re.I)
    label = label.strip(" \"'")
    return label


def slugify(value, max_len=96):
    value = canonical_label(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return (value[:max_len].strip("_") or "candidate")


def token_key(label, category=None):
    text = canonical_label(label).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = []
    for tok in text.split():
        if tok in STOPWORDS or len(tok) <= 1:
            continue
        if tok.endswith("ies") and len(tok) > 4:
            tok = tok[:-3] + "y"
        elif tok.endswith("s") and len(tok) > 4:
            tok = tok[:-1]
        tokens.append(tok)
    tokens = sorted(set(tokens))
    prefix = slugify(category or "", 32)
    return f"{prefix}::{'_'.join(tokens[:12])}"


def parse_values(values_json):
    if not values_json or values_json == "nan":
        return []
    try:
        values = json.loads(values_json)
    except Exception:
        return []
    if not isinstance(values, list):
        return []
    return [clean_text(v) for v in values if clean_text(v)]


def source_family(source, source_type):
    text = f"{source} {source_type}".lower()
    if any(k in text for k in ["ipip", "facet map", "hexaco", "bfi-2", "psychometric", "personality_inventory"]):
        return "psychometric"
    if "acs pums" in text or "official_population_survey" in text:
        return "official_population_survey"
    if "gss" in text or "world values survey" in text or "official_social_survey" in text:
        return "official_survey"
    if "primex" in text:
        return "research_dataset"
    if any(k in text for k in ["scope", "nemotron", "oasis", "personahub", "persona_dataset"]):
        return "persona_dataset"
    if "deeppersona" in text or "llm_mined" in text:
        return "llm_mined"
    if "matraix" in text or "yuexing" in text or "local_curated" in text:
        return "local_project"
    if "schwartz" in text or "self-determination" in text:
        return "validated_theory"
    return "other"


def quality_tier(inclusion_tier):
    tier = clean_text(inclusion_tier)
    if tier.startswith("A_"):
        return "A"
    if tier.startswith("B_"):
        return "B"
    if tier.startswith("C_"):
        return "C"
    return "Unknown"


def license_risk(source, license_notes):
    text = f"{source} {license_notes}".lower()
    if "cc by-nc-nd" in text or "non-commercial" in text or "cc-by-nc" in text or "cc by-nc" in text:
        return "medium_high"
    if "cc by-nc-sa" in text:
        return "medium_high"
    if "public domain" in text or "cc by 4.0" in text or "cc-by-4.0" in text or "apache" in text:
        return "low"
    if "census bureau public data" in text or "acs pums" in text:
        return "low"
    if "verify" in text:
        return "medium"
    return "unknown"


def source_specific_category(row):
    source = row["source"]
    source_type = row["source_type"]
    raw_category = clean_text(row["raw_category"])
    subcategory = clean_text(row["subcategory"])
    label = canonical_label(row["label"])
    text = f"{label} {row['definition']} {raw_category} {subcategory}".lower()

    if "IPIP" in source or source in {"Facet MAP", "HEXACO-PI-R", "BFI-2"}:
        if "Need for Cognition".lower() in label.lower():
            return "Cognitive & Capability Profile", "need for cognition"
        return "Personality Traits", normalize_subcategory(source, subcategory or raw_category)

    if source == "Schwartz Theory of Basic Values":
        return "Values, Goals & Motivations", "Schwartz values"
    if source == "Self-Determination Theory":
        return "Values, Goals & Motivations", "self-determination needs"

    if source == "ACS PUMS curated variables":
        return row["primary_category"], row["subcategory"]

    if "Tencent PersonaHub" in source:
        return "Domain-Specific Overlays", "domain labels and expertise areas"

    if "DeepPersona" in source:
        if subcategory in DEEP_PERSONA_TOP_MAP:
            category, subcat = DEEP_PERSONA_TOP_MAP[subcategory]
        else:
            category, subcat = DEEP_PERSONA_TOP_MAP.get(raw_category, (row["primary_category"], subcategory or raw_category))
        if subcategory == "Emotional and Relational Skills":
            if any(k in text for k in ["empathy", "anxiety", "emotion", "sensitivity", "confidence", "assert", "sociability", "patience", "temper", "attachment"]):
                category = "Personality Traits"
            elif any(k in text for k in ["communication", "conflict", "negotiation", "leadership", "decision", "problem", "regulation"]):
                category = "Cognitive & Capability Profile"
            else:
                category = "Social Identity, Relationships & Community"
        elif subcategory == "Psychological and Cognitive Aspects":
            if any(k in text for k in ["empathy", "anxiety", "emotion", "sensitivity", "confidence", "assert", "sociability", "patience", "temper", "attachment"]):
                category = "Personality Traits"
            elif any(k in text for k in ["skill", "analysis", "reasoning", "literacy", "learning", "knowledge", "decision", "problem", "expertise"]):
                category = "Cognitive & Capability Profile"
        if subcategory in {"Core Values, Beliefs, and Philosophy", "Core Values, Beliefs, Philosophy"}:
            if any(k in text for k in ["belief", "worldview", "politic", "relig", "trust", "attitude", "ideology"]):
                category = "Worldview, Beliefs & Attitudes"
            else:
                category = "Values, Goals & Motivations"
        return category, subcat

    if "SCOPE-Persona" in source:
        category, subcat = SCOPE_FACET_MAP.get(raw_category, (row["primary_category"], normalize_subcategory(source, subcategory or raw_category)))
        if category == "Behavioral Patterns & Preferences" and any(k in text for k in ["government", "climate", "tax", "trust", "political", "religion"]):
            category = "Worldview, Beliefs & Attitudes"
            subcat = "sociodemographic attitudes"
        return category, subcat

    if "Apple ML-PrimeX" in source:
        if re.match(r"col_10[3-9]$|col_11[0-9]$|col_12[0-1]$", row["original_id"]):
            return "Worldview, Beliefs & Attitudes", "primal world beliefs"
        if "explain your answer" in text:
            return "Worldview, Beliefs & Attitudes", "belief explanations"
        return heuristic_category(row)

    if "NVIDIA Nemotron" in source:
        field = row["original_id"].lower()
        if field in {"age", "sex", "marital_status", "education_level", "bachelors_field", "city", "state", "zipcode", "country"}:
            return "Demographics & Population Grounding", "nemotron demographic and geographic fields"
        if "skills" in field:
            return "Cognitive & Capability Profile", "skills and expertise"
        if "hobbies" in field or field in {"sports_persona", "arts_persona", "travel_persona", "culinary_persona"}:
            return "Behavioral Patterns & Preferences", "interests and preferences"
        if "cultural" in field:
            return "Social Identity, Relationships & Community", "cultural background"
        if "career" in field or "professional" in field or field == "occupation":
            return "Domain-Specific Overlays", "professional identity"
        return "Narrative Identity & Life History", "persona narrative summary"

    if "OASIS" in source:
        field = row["original_id"].lower()
        if field in {"age", "gender", "country"}:
            return "Demographics & Population Grounding", "social media profile demographics"
        if field == "mbti":
            return "Personality Traits", "MBTI-style personality label"
        if field == "profession":
            return "Domain-Specific Overlays", "professional identity"
        if field == "interested_topics":
            return "Behavioral Patterns & Preferences", "interests and topics"
        return "Narrative Identity & Life History", "profile narrative text"

    return heuristic_category(row)


def heuristic_category(row):
    label = canonical_label(row["label"])
    text = f"{label} {row['definition']} {row['question_text']} {row['raw_category']} {row['subcategory']}".lower()

    keyword_rules = [
        ("Demographics & Population Grounding", "demographic variables", [
            "age", "gender", "sex", "race", "ethnic", "hispanic", "nationality", "citizen",
            "country", "region", "state", "city", "language", "education level", "marital",
            "household", "birth", "parenthood",
        ]),
        ("Life Context & Constraints", "life context and constraints", [
            "health", "disability", "difficulty", "housing", "dwelling", "income", "financial",
            "employment", "work", "job", "caregiving", "stress", "safety", "transport",
            "mobility", "access", "debt", "poverty",
        ]),
        ("Personality Traits", "personality traits", [
            "personality", "trait", "outgoing", "sociable", "organized", "dependable",
            "anxious", "curious", "compassionate", "trusting", "dominant", "quiet",
            "energy", "respectful", "emotional", "modest", "humble", "assertive",
        ]),
        ("Values, Goals & Motivations", "values goals and motivations", [
            "important to me", "goal", "motivation", "achievement", "security", "autonomy",
            "benevolence", "tradition", "self-direction", "ambition", "purpose", "value",
            "priorities", "duty", "responsibility", "loyal", "help people",
        ]),
        ("Worldview, Beliefs & Attitudes", "worldview beliefs and attitudes", [
            "politic", "government", "trust", "religion", "church", "attitude", "opinion",
            "belief", "believe", "climate", "environment", "immigration", "inequality",
            "abortion", "gun", "tax", "policy", "democracy", "science", "future",
            "discrimination", "globalization", "institution", "threat", "favor or oppose",
        ]),
        ("Cognitive & Capability Profile", "cognitive and capability profile", [
            "skill", "expertise", "literacy", "numeracy", "proficiency", "knowledge",
            "reasoning", "problem-solving", "problem solving", "decision", "learning",
            "digital", "ai tools", "internet", "competence", "ability", "analysis",
        ]),
        ("Behavioral Patterns & Preferences", "behavioral patterns and preferences", [
            "hobby", "hobbies", "interest", "routine", "weekend", "media", "social media",
            "podcast", "tv", "shopping", "travel", "dine", "takeout", "exercise",
            "sports", "food", "culinary", "preference", "consume", "use", "hours per day",
            "frequency", "how often",
        ]),
        ("Social Identity, Relationships & Community", "social identity relationships and community", [
            "community", "relationship", "friends", "family", "neighbor", "cultural",
            "culture", "social network", "belonging", "membership", "organization",
            "civic", "local community", "represented", "welcome", "club", "association",
        ]),
        ("Narrative Identity & Life History", "narrative identity and life history", [
            "life story", "story of your life", "childhood", "formative", "turning point",
            "crossroads", "personal journey", "identity changed", "setbacks", "memory",
        ]),
    ]
    for category, subcat, keywords in keyword_rules:
        if any(k in text for k in keywords):
            return category, subcat
    if row["primary_category"] in TOP_LEVEL_CATEGORIES:
        return row["primary_category"], normalize_subcategory(row["source"], row["subcategory"])
    return "Domain-Specific Overlays", "uncategorized candidate"


def normalize_subcategory(source, subcategory):
    subcategory = canonical_label(subcategory).lower()
    subcategory = subcategory.replace("&", "and")
    subcategory = re.sub(r"[^a-z0-9]+", " ", subcategory)
    subcategory = re.sub(r"\s+", " ", subcategory).strip()
    if not subcategory:
        if "IPIP" in source:
            return "IPIP personality items"
        return "unspecified"
    return subcategory


def infer_data_type(row, category, subcategory, values):
    source = row["source"]
    source_type = row["source_type"]
    label = canonical_label(row["label"])
    text = f"{label} {row['definition']} {row['question_text']} {row['raw_category']} {subcategory}".lower()
    st = source_type.lower()

    if "psychometric_item" in st or source == "IPIP item pool":
        return "likert_self_report_item", "ordinal", {
            "scale_type": "IPIP self-report agreement/accuracy",
            "values": ["Very inaccurate", "Moderately inaccurate", "Neither accurate nor inaccurate", "Moderately accurate", "Very accurate"],
        }
    if "psychometric_scale" in st or "psychometric_facet" in st or "personality_inventory" in st or source in {"Facet MAP", "HEXACO-PI-R", "BFI-2"}:
        return "psychometric_construct", "construct", {"scale_type": "source-defined psychometric construct"}
    if "value_theory" in st or "motivation_theory" in st:
        return "theory_construct", "construct", {"scale_type": "theory construct"}
    if "domain_label" in st or "Tencent PersonaHub" in source:
        return "domain_label", "nominal", {"scale_type": "domain/expertise label"}
    if source == "ACS PUMS curated variables":
        dtype = row.get("data_type", "").lower()
        if dtype == "numeric":
            return "official_population_numeric_variable", "ratio_or_interval", {"scale_type": "ACS PUMS numeric variable"}
        if dtype == "ordinal":
            return "official_population_ordinal_variable", "ordinal", {"scale_type": "ACS PUMS ordered/coded variable", "values": values}
        if dtype == "boolean_or_binary":
            return "official_population_binary_variable", "nominal", {"scale_type": "ACS PUMS binary variable", "values": values}
        return "official_population_categorical_variable", "nominal", {"scale_type": "ACS PUMS categorical variable", "values": values}

    ordered_sets = [
        ["Very low", "Low", "Moderate", "High", "Very high"],
        ["Very high", "High", "Moderate", "Low", "Very low"],
        ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        ["Never", "Rarely", "Sometimes", "Often", "Always"],
    ]
    if values:
        value_lower = [v.lower() for v in values]
        if any(value_lower == [x.lower() for x in ordered] for ordered in ordered_sets):
            return "ordinal_scale", "ordinal", {"scale_type": "ordered source values", "values": values}
        if len(values) == 2 and any(v.lower() in {"yes", "no", "mentioned", "not mentioned"} for v in values):
            return "boolean_or_binary", "nominal", {"scale_type": "binary source values", "values": values}
        return "categorical", "nominal", {"scale_type": "source categorical values", "values": values}

    if any(k in text for k in ["tell me", "describe", "explain your answer", "provide your", "walk me through", "can you describe"]):
        return "free_text", "free_text", {"scale_type": "open-ended text response"}
    if re.search(r"\bhow often\b|\bhow frequently\b|\bhow likely\b|\bhow much\b|\brate your\b|\bhow concerned\b|\bhow important\b", text):
        return "ordinal_survey_item", "ordinal", {"scale_type": "source-defined ordinal survey response"}
    if re.search(r"\bselect\b|\bchoose\b|\bwhich of\b", text):
        if "one or more" in text or "up to" in text:
            return "multi_select", "nominal", {"scale_type": "source-defined multi-select"}
        return "categorical", "nominal", {"scale_type": "source-defined categorical response"}
    if re.search(r"\bdo you\b|\bshould\b|\bhave you\b|\bwould you\b", text):
        return "ordinal_or_binary_survey_item", "ordinal", {"scale_type": "source-defined yes/no or agreement response"}
    if "official_survey" in st or "official_population_survey" in st:
        return "survey_variable_source_defined", "source_defined", {"scale_type": "official survey codebook variable"}
    if "dataset_field" in st or "profile_field" in st:
        return "dataset_schema_field", "source_defined", {"scale_type": "dataset schema field"}
    return "unknown_or_source_defined", "source_defined", {"scale_type": "unknown/source-defined"}


def normalized_definition(row, label, category, subcategory, data_type):
    definition = clean_text(row["definition"])
    q = clean_text(row["question_text"])
    if definition and definition.lower() != label.lower():
        return definition
    if q:
        return f"Questionnaire item capturing {label}."
    if data_type == "domain_label":
        return f"Domain or expertise label candidate: {label}."
    return f"Candidate persona attribute for {subcategory} under {category}: {label}."


def make_aliases(row, label, canonical_name):
    aliases = []
    for value in [row.get("label", ""), row.get("name", ""), row.get("original_id", "")]:
        value = canonical_label(value).replace("_", " ")
        if value and value.lower() not in {a.lower() for a in aliases}:
            aliases.append(value)
    readable_name = canonical_name.replace("_", " ")
    if readable_name and readable_name.lower() not in {a.lower() for a in aliases}:
        aliases.append(readable_name)
    return aliases[:8]


def review_flags(row, category, subcategory, data_type, values):
    flags = []
    source = row["source"]
    source_type = row["source_type"]
    tier = quality_tier(row["inclusion_tier"])
    label = canonical_label(row["label"])
    text = f"{label} {row['definition']} {row['question_text']} {row['raw_category']} {subcategory}".lower()

    if tier == "C":
        flags.append("review_low_evidence_or_llm_mined")
    if "DeepPersona" in source:
        flags.append("review_deeppersona_auto_extraction")
    if "Tencent PersonaHub" in source:
        flags.append("domain_label_not_standalone_attribute")
    if data_type in {"unknown_or_source_defined", "survey_variable_source_defined"} and not values:
        flags.append("needs_value_schema_or_codebook_lookup")
    if data_type == "free_text":
        flags.append("free_text_should_be_structured_before_final_schema")
    if len(label.split()) <= 1 and "scale" not in source_type.lower() and data_type not in {"domain_label", "psychometric_construct", "theory_construct"}:
        flags.append("label_too_generic_review")
    if any(k in text for k in ["none / not applicable", "single, augmented", "confidence: auto"]):
        flags.append("auto_augmented_values_review")
    if category == "Domain-Specific Overlays":
        flags.append("domain_specific_not_core_by_default")
    return sorted(set(flags))


def application_relevance(category, subcategory, source_family_value):
    if category == "Personality Traits":
        return "general_personality_and_behavior_simulation"
    if category == "Worldview, Beliefs & Attitudes":
        return "survey_social_science_policy_and_alignment"
    if category == "Values, Goals & Motivations":
        return "motivation_preference_and_decision_simulation"
    if category == "Cognitive & Capability Profile":
        return "education_workflow_task_capability_simulation"
    if category == "Behavioral Patterns & Preferences":
        return "recommender_consumer_media_and_daily_behavior"
    if category == "Social Identity, Relationships & Community":
        return "social_network_community_and_civic_simulation"
    if category == "Demographics & Population Grounding":
        return "population_grounding_sampling_and_fairness_analysis"
    if category == "Life Context & Constraints":
        return "resource_constraint_health_and_life_context_simulation"
    if category == "Narrative Identity & Life History":
        return "long_form_persona_narrative_and_memory"
    return "domain_specific_module_selection"


def normalize_row(row):
    row = {k: clean_text(v) for k, v in row.items()}
    label = canonical_label(row["label"])
    values = parse_values(row.get("values_json", ""))
    category, subcategory = source_specific_category(row)
    subcategory = normalize_subcategory(row["source"], subcategory)
    data_type, measurement_level, value_schema = infer_data_type(row, category, subcategory, values)
    canon_name = slugify(label)
    family = source_family(row["source"], row["source_type"])
    flags = review_flags(row, category, subcategory, data_type, values)
    source_quality = int(float(row["quality_score"] or 0))
    tier = quality_tier(row["inclusion_tier"])
    if tier == "A":
        normalized_quality = min(100, max(source_quality, 90))
    elif tier == "B":
        normalized_quality = min(89, max(source_quality, 65))
    elif tier == "C":
        normalized_quality = min(59, max(source_quality, 25))
    else:
        normalized_quality = source_quality

    normalized = dict(row)
    normalized.update(
        {
            "canonical_label": label,
            "canonical_name": canon_name,
            "normalized_primary_category": category,
            "normalized_subcategory": subcategory,
            "normalized_definition": normalized_definition(row, label, category, subcategory, data_type),
            "normalized_data_type": data_type,
            "measurement_level": measurement_level,
            "normalized_value_schema_json": json.dumps(value_schema, ensure_ascii=False),
            "source_family": family,
            "quality_tier": tier,
            "normalized_quality_score": normalized_quality,
            "license_risk": license_risk(row["source"], row["license_notes"]),
            "dedup_key_strict": f"{slugify(category, 40)}::{slugify(label, 100)}",
            "dedup_key_loose": token_key(label, category),
            "alias_candidates_json": json.dumps(make_aliases(row, label, canon_name), ensure_ascii=False),
            "review_flags_json": json.dumps(flags, ensure_ascii=False),
            "needs_review": bool(flags),
            "is_questionnaire_item": data_type in {"likert_self_report_item", "ordinal_survey_item", "ordinal_or_binary_survey_item", "survey_variable_source_defined", "free_text"},
            "is_construct": data_type in {"psychometric_construct", "theory_construct"},
            "is_dataset_field": data_type == "dataset_schema_field",
            "is_domain_label": data_type == "domain_label",
            "is_generated_or_mined": tier == "C" or family == "llm_mined",
            "application_relevance": application_relevance(category, subcategory, family),
            "category_changed_from_aggregate": category != row.get("primary_category", ""),
        }
    )
    return normalized


def write_csv(path, rows):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_file(input_name, output_stem):
    df = pd.read_csv(INPUT_DIR / input_name, dtype=str, keep_default_na=False)
    rows = [normalize_row(row) for row in df.to_dict(orient="records")]
    write_csv(OUT / f"{output_stem}.csv", rows)
    write_jsonl(OUT / f"{output_stem}.jsonl", rows)
    return rows


def write_report(raw_rows, high_rows):
    source_summary = []
    for source, rows in sorted(group_by(raw_rows, "source").items()):
        hq = [r for r in high_rows if r["source"] == source]
        source_summary.append(
            {
                "source": source,
                "raw_normalized_count": len(rows),
                "high_quality_normalized_count": len(hq),
                "source_family": Counter(r["source_family"] for r in rows).most_common(1)[0][0],
                "quality_tiers": json.dumps(dict(Counter(r["quality_tier"] for r in rows)), ensure_ascii=False),
                "normalized_categories": json.dumps(dict(Counter(r["normalized_primary_category"] for r in rows)), ensure_ascii=False),
                "needs_review_count": sum(str(r["needs_review"]).lower() == "true" for r in rows),
            }
        )
    write_csv(OUT / "normalization_source_summary.csv", source_summary)

    review_counter = Counter()
    for row in raw_rows:
        for flag in json.loads(row["review_flags_json"]):
            review_counter[flag] += 1

    report = [
        "# Candidate Pool Normalization Report",
        "",
        "Generated by `normalize_candidate_pool.py`.",
        "",
        f"- Raw extended normalized rows: {len(raw_rows)}",
        f"- High-quality normalized rows: {len(high_rows)}",
        f"- Raw duplicate candidate_id count: {count_duplicates(raw_rows, 'candidate_id')}",
        f"- High-quality duplicate candidate_id count: {count_duplicates(high_rows, 'candidate_id')}",
        f"- Raw empty canonical_label count: {sum(1 for r in raw_rows if not r['canonical_label'])}",
        f"- High-quality empty canonical_label count: {sum(1 for r in high_rows if not r['canonical_label'])}",
        "",
        "## High-Quality Normalized Category Counts",
        "",
    ]
    for category in TOP_LEVEL_CATEGORIES:
        report.append(f"- {category}: {Counter(r['normalized_primary_category'] for r in high_rows).get(category, 0)}")
    report += ["", "## Raw Extended Normalized Category Counts", ""]
    for category in TOP_LEVEL_CATEGORIES:
        report.append(f"- {category}: {Counter(r['normalized_primary_category'] for r in raw_rows).get(category, 0)}")
    report += ["", "## Data Type Counts: High-Quality", ""]
    for dtype, count in Counter(r["normalized_data_type"] for r in high_rows).most_common():
        report.append(f"- {dtype}: {count}")
    report += ["", "## Data Type Counts: Raw Extended", ""]
    for dtype, count in Counter(r["normalized_data_type"] for r in raw_rows).most_common():
        report.append(f"- {dtype}: {count}")
    report += ["", "## Review Flag Counts", ""]
    for flag, count in review_counter.most_common():
        report.append(f"- {flag}: {count}")
    report += [
        "",
        "## Notes",
        "",
        "- This step normalizes fields and adds review flags; it does not merge duplicates.",
        "- `dedup_key_strict` and `dedup_key_loose` are prepared for Step 3 deduplication.",
        "- PersonaHub domain labels and DeepPersona auto-extractions remain useful coverage sources, but are flagged for review by default.",
        "- Official survey variables without value labels are marked `needs_value_schema_or_codebook_lookup` so Step 3/4 can fetch or infer exact scales.",
    ]
    (OUT / "normalization_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def group_by(rows, key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    return grouped


def count_duplicates(rows, key):
    counts = Counter(row[key] for row in rows)
    return sum(count - 1 for count in counts.values() if count > 1)


def main():
    raw_rows = normalize_file("candidate_pool_raw_extended.csv", "candidate_pool_raw_extended_normalized")
    high_rows = normalize_file("candidate_pool_high_quality.csv", "candidate_pool_high_quality_normalized")
    write_report(raw_rows, high_rows)
    print(json.dumps({
        "raw_extended_normalized": len(raw_rows),
        "high_quality_normalized": len(high_rows),
        "output_dir": str(OUT),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
