import csv
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pdfplumber


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset"
OLD = ROOT / "old_attributes"
OUT = ROOT / "candidate_pool_outputs"
OUT.mkdir(exist_ok=True)

TARGET_HIGH_QUALITY_COUNT = 9935


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


def clean_text(value):
    if value is None:
        return ""
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\u00a0", " ")
    value = value.replace("\ufeff", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def slugify(value, max_len=80):
    value = clean_text(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:max_len].strip("_") or "candidate"


def stable_id(source, original_id, label):
    base = f"{source}|{original_id}|{label}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]
    return f"{slugify(source, 24)}__{slugify(original_id or label, 64)}__{digest}"


def classify(text, source="", raw_category="", subcategory_hint=""):
    hay = " ".join([text or "", source or "", raw_category or "", subcategory_hint or ""]).lower()

    if any(k in source.lower() for k in ["ipip", "facet", "bfi", "hexaco"]):
        return "Personality Traits", subcategory_hint or "psychometric traits"
    if "schwartz" in source.lower() or "self-determination" in source.lower():
        return "Values, Goals & Motivations", subcategory_hint or "values and motivation"

    rules = [
        (
            "Demographics & Population Grounding",
            "demographics",
            [
                "age", "gender", "sex", "race", "ethnic", "ethnicity", "nationality",
                "citizen", "country", "region", "state", "city", "zipcode", "language",
                "marital", "household", "income category", "education level",
                "highest level of education", "occupation class",
            ],
        ),
        (
            "Life Context & Constraints",
            "life context and constraints",
            [
                "health", "disability", "difficulty", "housing", "dwelling", "income",
                "financial", "debt", "employment", "work week", "caregiving",
                "family responsibilities", "stress", "lonely", "safety", "access",
                "transportation", "mobility", "childcare",
            ],
        ),
        (
            "Personality Traits",
            "personality traits",
            [
                "personality", "trait", "outgoing", "sociable", "organized",
                "dependable", "anxious", "curious", "compassionate", "trusting",
                "dominant", "quiet", "energy", "respectful", "emotional",
            ],
        ),
        (
            "Values, Goals & Motivations",
            "values goals and motivations",
            [
                "value", "values", "important to me", "goal", "motivation",
                "achievement", "security", "autonomy", "benevolence", "tradition",
                "self-direction", "ambition", "purpose", "moral priority",
                "make my parents proud", "rich", "humble", "successful",
            ],
        ),
        (
            "Worldview, Beliefs & Attitudes",
            "worldview beliefs and attitudes",
            [
                "politic", "government", "trust", "religion", "religious", "church",
                "attitude", "opinion", "belief", "believe", "climate", "environment",
                "immigration", "inequality", "abortion", "gun", "tax", "policy",
                "democracy", "science", "world", "future", "superpower",
                "discrimination", "globalization", "institution",
            ],
        ),
        (
            "Cognitive & Capability Profile",
            "cognitive and capability profile",
            [
                "skill", "expertise", "literacy", "numeracy", "proficiency",
                "knowledge", "reasoning", "problem-solving", "problem solving",
                "decision", "learning", "education", "digital", "ai tools",
                "internet", "language proficiency", "competence", "ability",
            ],
        ),
        (
            "Behavioral Patterns & Preferences",
            "behavioral patterns and preferences",
            [
                "hobby", "hobbies", "interest", "routine", "weekend", "media",
                "social media", "podcast", "tv", "shopping", "travel", "dine",
                "takeout", "exercise", "sports", "food", "culinary", "preference",
                "consume", "use the internet", "dating apps",
            ],
        ),
        (
            "Social Identity, Relationships & Community",
            "social identity relationships and community",
            [
                "community", "relationship", "friends", "family", "neighbor",
                "cultural background", "culture", "social network", "belonging",
                "membership", "organization", "civic", "local community",
                "represented", "welcome", "people from different cultural",
            ],
        ),
        (
            "Narrative Identity & Life History",
            "narrative identity and life history",
            [
                "life story", "story of your life", "childhood", "formative",
                "turning point", "crossroads", "personal journey", "identity changed",
                "setbacks", "memory", "influence on your journey",
            ],
        ),
    ]

    for category, subcategory, keywords in rules:
        if any(k in hay for k in keywords):
            return category, subcategory

    if "career" in hay or "professional" in hay or "domain" in hay:
        return "Domain-Specific Overlays", "career and professional identity"
    return "Domain-Specific Overlays", subcategory_hint or "uncategorized candidate"


def make_candidate(
    source,
    original_id,
    label,
    definition="",
    question_text="",
    raw_category="",
    subcategory="",
    source_type="",
    evidence_level="Medium",
    inclusion_tier="B_peer_reviewed_or_curated",
    theoretical_basis="",
    license_notes="",
    source_url="",
    extraction_method="",
    values=None,
    high_quality=True,
    notes="",
    quality_score=0,
):
    label = clean_text(label)
    definition = clean_text(definition)
    question_text = clean_text(question_text)
    raw_category = clean_text(raw_category)
    category, inferred_subcat = classify(
        " ".join([label, definition, question_text]), source, raw_category, subcategory
    )
    subcategory = clean_text(subcategory) or inferred_subcat
    values = values or []
    return {
        "candidate_id": stable_id(source, f"{raw_category}|{original_id}", label),
        "source": source,
        "source_type": source_type,
        "original_id": clean_text(original_id),
        "name": slugify(label),
        "label": label,
        "definition": definition,
        "question_text": question_text,
        "raw_category": raw_category,
        "primary_category": category,
        "subcategory": subcategory,
        "data_type": "categorical" if values else "unknown_or_scale",
        "values_json": json.dumps(values, ensure_ascii=False),
        "evidence_level": evidence_level,
        "inclusion_tier": inclusion_tier,
        "theoretical_basis": theoretical_basis,
        "license_notes": license_notes,
        "source_url": source_url,
        "extraction_method": extraction_method,
        "include_high_quality": bool(high_quality),
        "quality_score": quality_score,
        "notes": notes,
    }


def add_existing_matraix(candidates):
    path = OLD / "attributes_after_deduplication_1.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    dims = data.get("dimensions", [])
    for d in dims:
        description = d.get("description", "")
        is_auto_deeppersona = (
            "Attribute-level extraction from DeepPersona" in description
            or "Confidence: auto" in description
        )
        candidates.append(
            make_candidate(
                source="MatrAIx existing Yuexing 1K attributes",
                source_type="local_curated_schema",
                original_id=d.get("id", ""),
                label=d.get("label") or d.get("id", ""),
                definition=description,
                raw_category=d.get("category", ""),
                values=d.get("values", []),
                evidence_level="Low" if is_auto_deeppersona else "Medium",
                inclusion_tier=(
                    "C_local_auto_extraction_review_needed"
                    if is_auto_deeppersona
                    else "B_local_curated"
                ),
                theoretical_basis=(
                    "Local DeepPersona-derived auto extraction; requires review and grounding"
                    if is_auto_deeppersona
                    else "Existing MatrAIx/Yuexing attribute work; to be mapped into theory-grounded schema"
                ),
                license_notes="Local project artifact; verify provenance before external release",
                source_url=str(path),
                extraction_method="local_json_dimensions",
                high_quality=not is_auto_deeppersona,
                quality_score=38 if is_auto_deeppersona else 72,
                notes=(
                    "Local file marks this as DeepPersona auto extraction; kept out of high-quality pool by default."
                    if is_auto_deeppersona
                    else ""
                ),
            )
        )


def add_deeppersona_extended(candidates):
    for filename in ["proposed_ATTR_sourced.json", "proposed_new_dimensions_ATTRLEVEL.json"]:
        path = OLD / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        dims = data.get("proposed_dimensions", [])
        for d in dims:
            candidates.append(
                make_candidate(
                    source=f"DeepPersona auto-extracted local proposal ({filename})",
                    source_type="llm_mined_persona_taxonomy",
                    original_id=d.get("id", ""),
                    label=d.get("label") or d.get("id", ""),
                    definition=d.get("description", ""),
                    raw_category=d.get("category", ""),
                    subcategory=d.get("source_top", ""),
                    values=d.get("values", []),
                    evidence_level="Low",
                    inclusion_tier="C_llm_mined_review_needed",
                    theoretical_basis="DeepPersona data-driven taxonomy; requires review and grounding",
                    license_notes="Verify DeepPersona dataset/paper license before reuse",
                    source_url=str(path),
                    extraction_method="local_json_proposed_dimensions",
                    high_quality=False,
                    quality_score=35,
                    notes="Included in raw extended pool only by default.",
                )
            )


def parse_gss_variables():
    page_dir = DATASET / "gss_codebook_pages"
    rows = []
    order = 0
    for page in sorted(page_dir.glob("hcbkx*.htm")):
        text = page.read_text(encoding="utf-8", errors="ignore")
        current = []
        pattern = re.compile(
            r'<tr[^>]*id="(?P<hid>\d+\.HEADING)"[^>]*>.*?<a[^>]*>(?P<h>.*?)</a>.*?</tr>'
            r'|<tr>\s*<td><a href\s*=\s*"(?P<href>[^"]+)">(?P<var>[^<]+)</a></td>\s*<td>(?P<label>.*?)</td>\s*</tr>',
            re.S | re.I,
        )
        for m in pattern.finditer(text):
            if m.group("h"):
                heading = clean_text(m.group("h"))
                if heading.isupper() or "VARIABLES" in heading.upper() or "INFORMATION" in heading.upper():
                    current = [heading]
                else:
                    if not current:
                        current = ["Uncategorized"]
                    if len(current) == 1:
                        current.append(heading)
                    else:
                        current[-1] = heading
            elif m.group("var"):
                order += 1
                rows.append(
                    {
                        "order": order,
                        "var": clean_text(m.group("var")),
                        "label": clean_text(m.group("label")),
                        "heading": " > ".join(current),
                        "href": clean_text(m.group("href")),
                    }
                )
    return rows


def gss_is_admin(row):
    s = f"{row['var']} {row['label']} {row['heading']}".lower()
    if row["var"].lower() in {"year", "id"}:
        return True
    if row["heading"].startswith("CASE IDENTIFICATION"):
        return True
    admin_words = [
        "weight",
        "ballot",
        "id number",
        "case id",
        "sample",
        "version",
        "release",
        "interview",
        "interviewer",
        "subsample",
        "form ",
        "random",
        "post-stratification",
        "record number",
        "serial number",
    ]
    return any(word in s for word in admin_words)


def gss_relevance_score(row):
    s = f"{row['var']} {row['label']} {row['heading']}".lower()
    score = 70
    boosts = [
        ("trust", 16),
        ("relig", 14),
        ("polit", 14),
        ("health", 14),
        ("family", 12),
        ("work", 12),
        ("income", 12),
        ("education", 12),
        ("attitude", 12),
        ("happiness", 12),
        ("social", 12),
        ("community", 12),
        ("climate", 12),
        ("environment", 12),
        ("immigration", 10),
        ("race", 10),
        ("gender", 10),
        ("media", 10),
        ("internet", 10),
        ("vote", 10),
        ("neighbor", 10),
        ("crime", 8),
        ("belief", 8),
        ("opinion", 8),
        ("volunteer", 8),
        ("relationship", 8),
    ]
    for word, bump in boosts:
        if word in s:
            score += bump
    penalties = [
        ("recoded", -10),
        ("summary", -8),
        ("index", -5),
        ("score", -5),
        ("experimental", -8),
        ("version", -20),
    ]
    for word, penalty in penalties:
        if word in s:
            score += penalty
    return score


def add_gss(candidates):
    seen = set()
    for row in parse_gss_variables():
        if gss_is_admin(row):
            continue
        key = (row["label"].lower(), row["heading"].lower())
        if key in seen:
            continue
        seen.add(key)
        score = gss_relevance_score(row)
        candidates.append(
            make_candidate(
                source="GSS 1972-2024 Cumulative Codebook",
                source_type="official_social_survey_variable",
                original_id=row["var"],
                label=row["label"],
                definition=row["label"],
                raw_category=row["heading"],
                evidence_level="High",
                inclusion_tier="A_official_survey_variable",
                theoretical_basis="General Social Survey: nationally representative U.S. social survey variables",
                license_notes="Use GSS/NORC citation and data terms; variable metadata used as source grounding",
                source_url="https://sda.berkeley.edu/sdaweb/docs/gss24rel3/DOC/hcbk.htm",
                extraction_method="parsed_sda_html_codebook",
                high_quality=True,
                quality_score=score,
            )
        )


def add_ipip(candidates):
    item_path = DATASET / "ipip_alphabeticalitemlist.htm"
    if item_path.exists():
        text = item_path.read_text(encoding="windows-1252", errors="ignore")
        pattern = re.compile(
            r"<tr[^>]*>\s*<td[^>]*>\s*<p[^>]*>(?P<item>.*?)</p>\s*</td>\s*"
            r"<td[^>]*>\s*<p[^>]*>(?P<code>.*?)</p>",
            re.S | re.I,
        )
        seen_items = set()
        for m in pattern.finditer(text):
            item = clean_text(m.group("item"))
            code = clean_text(m.group("code")).rstrip("*")
            if not item or len(item) < 4:
                continue
            if len(item) > 180 or "technical report" in item.lower() or "survey numbers" in item.lower():
                continue
            key = item.lower()
            if key in seen_items:
                continue
            seen_items.add(key)
            candidates.append(
                make_candidate(
                    source="IPIP item pool",
                    source_type="public_domain_psychometric_item",
                    original_id=code,
                    label=item,
                    definition=f"IPIP self-report item: {item}",
                    question_text=item,
                    raw_category="Personality item pool",
                    subcategory="IPIP personality items",
                    evidence_level="High",
                    inclusion_tier="A_psychometric_item",
                    theoretical_basis="International Personality Item Pool; public-domain personality measurement items",
                    license_notes="IPIP items and scales are public domain per official IPIP site",
                    source_url="https://ipip.ori.org/alphabeticalitemlist.htm",
                    extraction_method="parsed_official_html_item_table",
                    high_quality=True,
                    quality_score=96,
                )
            )

    scale_path = DATASET / "ipip_scale_labels.htm"
    if scale_path.exists():
        text = scale_path.read_text(encoding="iso-8859-1", errors="ignore")
        m = re.search(r"<H3[^>]*>(.*?)</H3>", text, re.S | re.I)
        if m:
            parts = re.split(r"<br\s*/?>", m.group(1), flags=re.I)
            seen = set()
            for part in parts:
                clean = clean_text(part)
                if not clean:
                    continue
                label = re.split(r"\s*\(", clean)[0].strip()
                if not label or label.lower() in seen:
                    continue
                seen.add(label.lower())
                candidates.append(
                    make_candidate(
                        source="IPIP scale labels",
                        source_type="public_domain_psychometric_scale",
                        original_id=label,
                        label=label,
                        definition=f"IPIP construct/scale label: {label}",
                        raw_category="Personality scale labels",
                        subcategory="IPIP personality scales",
                        evidence_level="High",
                        inclusion_tier="A_psychometric_scale",
                        theoretical_basis="International Personality Item Pool scale labels",
                        license_notes="IPIP items and scales are public domain per official IPIP site",
                        source_url="https://ipip.ori.org/newIndexofScaleLabels.htm",
                        extraction_method="parsed_official_html_scale_index",
                        high_quality=True,
                        quality_score=98,
                    )
                )


def add_facet_map(candidates):
    path = DATASET / "facetmap_labels_definitions.html"
    if not path.exists():
        return
    table = pd.read_html(path)[0]
    table.columns = ["facet", "definition"]
    for _, row in table.iloc[1:].iterrows():
        facet = clean_text(row["facet"])
        definition = clean_text(row["definition"])
        if not facet:
            continue
        candidates.append(
            make_candidate(
                source="Facet MAP",
                source_type="open_access_psychometric_facet",
                original_id=facet,
                label=facet,
                definition=definition,
                raw_category="70 narrow personality facets",
                subcategory="Facet MAP personality facets",
                evidence_level="High",
                inclusion_tier="A_psychometric_facet",
                theoretical_basis="Facet-level Multidimensional Assessment of Personality",
                license_notes="Open-access facet labels/definitions; verify item-use terms before redistribution",
                source_url="https://facetmap.org/facet-labels-and-definitions/",
                extraction_method="parsed_facetmap_table",
                high_quality=True,
                quality_score=99,
            )
        )


def add_standard_psych_constructs(candidates):
    bfi2 = {
        "Extraversion": ["Sociability", "Assertiveness", "Energy Level"],
        "Agreeableness": ["Compassion", "Respectfulness", "Trust"],
        "Conscientiousness": ["Organization", "Productiveness", "Responsibility"],
        "Negative Emotionality": ["Anxiety", "Depression", "Emotional Volatility"],
        "Open-Mindedness": ["Intellectual Curiosity", "Aesthetic Sensitivity", "Creative Imagination"],
    }
    for domain, facets in bfi2.items():
        candidates.append(
            make_candidate(
                source="BFI-2",
                source_type="validated_personality_inventory",
                original_id=domain,
                label=domain,
                definition=f"Big Five Inventory-2 domain: {domain}",
                raw_category="Big Five domain",
                subcategory="BFI-2 domains",
                evidence_level="High",
                inclusion_tier="A_psychometric_domain",
                theoretical_basis="Big Five / BFI-2",
                license_notes="BFI-2 is available for personal/research use; verify terms for redistribution",
                source_url="https://www.colby.edu/academics/departments-and-programs/psychology/research-opportunities/personality-lab/the-bfi-2/",
                extraction_method="manual_from_official_domain_facet_structure",
                high_quality=True,
                quality_score=99,
            )
        )
        for facet in facets:
            candidates.append(
                make_candidate(
                    source="BFI-2",
                    source_type="validated_personality_inventory",
                    original_id=f"{domain}:{facet}",
                    label=facet,
                    definition=f"BFI-2 facet under {domain}",
                    raw_category="Big Five facet",
                    subcategory="BFI-2 facets",
                    evidence_level="High",
                    inclusion_tier="A_psychometric_facet",
                    theoretical_basis="Big Five / BFI-2",
                    license_notes="BFI-2 is available for personal/research use; verify terms for redistribution",
                    source_url="https://www.colby.edu/academics/departments-and-programs/psychology/research-opportunities/personality-lab/the-bfi-2/",
                    extraction_method="manual_from_official_domain_facet_structure",
                    high_quality=True,
                    quality_score=99,
                )
            )

    hexaco = {
        "Honesty-Humility": ["Sincerity", "Fairness", "Greed Avoidance", "Modesty"],
        "Emotionality": ["Fearfulness", "Anxiety", "Dependence", "Sentimentality"],
        "Extraversion": ["Social Self-Esteem", "Social Boldness", "Sociability", "Liveliness"],
        "Agreeableness": ["Forgivingness", "Gentleness", "Flexibility", "Patience"],
        "Conscientiousness": ["Organization", "Diligence", "Perfectionism", "Prudence"],
        "Openness to Experience": ["Aesthetic Appreciation", "Inquisitiveness", "Creativity", "Unconventionality"],
        "Altruism": [],
    }
    for domain, facets in hexaco.items():
        candidates.append(
            make_candidate(
                source="HEXACO-PI-R",
                source_type="validated_personality_inventory",
                original_id=domain,
                label=domain,
                definition=f"HEXACO personality domain: {domain}",
                raw_category="HEXACO domain",
                subcategory="HEXACO domains",
                evidence_level="High",
                inclusion_tier="A_psychometric_domain",
                theoretical_basis="HEXACO model of personality",
                license_notes="Use HEXACO materials according to official research terms",
                source_url="https://hexaco.org/scaledescriptions",
                extraction_method="manual_from_official_scale_descriptions",
                high_quality=True,
                quality_score=99,
            )
        )
        for facet in facets:
            candidates.append(
                make_candidate(
                    source="HEXACO-PI-R",
                    source_type="validated_personality_inventory",
                    original_id=f"{domain}:{facet}",
                    label=facet,
                    definition=f"HEXACO facet under {domain}",
                    raw_category="HEXACO facet",
                    subcategory="HEXACO facets",
                    evidence_level="High",
                    inclusion_tier="A_psychometric_facet",
                    theoretical_basis="HEXACO model of personality",
                    license_notes="Use HEXACO materials according to official research terms",
                    source_url="https://hexaco.org/scaledescriptions",
                    extraction_method="manual_from_official_scale_descriptions",
                    high_quality=True,
                    quality_score=99,
                )
            )

    schwartz = [
        "Self-Direction",
        "Stimulation",
        "Hedonism",
        "Achievement",
        "Power",
        "Security",
        "Conformity",
        "Tradition",
        "Benevolence",
        "Universalism",
    ]
    for value in schwartz:
        candidates.append(
            make_candidate(
                source="Schwartz Theory of Basic Values",
                source_type="validated_value_theory",
                original_id=value,
                label=value,
                definition=f"Schwartz basic human value: {value}",
                raw_category="Basic human values",
                subcategory="Schwartz values",
                evidence_level="High",
                inclusion_tier="A_value_theory_construct",
                theoretical_basis="Schwartz Theory of Basic Human Values",
                license_notes="Use as theory/source grounding; do not copy proprietary survey instruments without checking terms",
                source_url="https://scholarworks.gvsu.edu/orpc/vol2/iss1/11/",
                extraction_method="manual_from_schwartz_10_value_model",
                high_quality=True,
                quality_score=98,
            )
        )

    for need in ["Autonomy", "Competence", "Relatedness"]:
        candidates.append(
            make_candidate(
                source="Self-Determination Theory",
                source_type="validated_motivation_theory",
                original_id=need,
                label=need,
                definition=f"Basic psychological need in Self-Determination Theory: {need}",
                raw_category="Basic psychological needs",
                subcategory="motivation and psychological needs",
                evidence_level="High",
                inclusion_tier="A_motivation_theory_construct",
                theoretical_basis="Self-Determination Theory",
                license_notes="Theory construct; cite Deci & Ryan / SDT source",
                source_url="https://selfdeterminationtheory.org/theory/",
                extraction_method="manual_from_sdt_core_needs",
                high_quality=True,
                quality_score=98,
            )
        )


def add_wvs(candidates):
    path = DATASET / "wvs7_master_questionnaire.pdf"
    if not path.exists():
        return
    full_text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            full_text.append(page.extract_text() or "")
    text = "\n".join(full_text)
    lines = [clean_text(line) for line in text.splitlines()]
    seen = set()
    current_section = ""
    section_pattern = re.compile(r"^[A-Z][A-Z ,/&\-]+$")
    q_pattern = re.compile(r"^(Q\d+[A-Z]?)\s+(.+)$")
    for line in lines:
        if section_pattern.match(line) and len(line) > 8 and "WVS" not in line:
            current_section = line.title()
        m = q_pattern.match(line)
        if not m:
            continue
        qid, qtext = m.group(1), m.group(2)
        qtext = re.sub(r"\s+\d+(\s+\d+)*$", "", qtext).strip()
        if len(qtext) < 5:
            continue
        key = (qid, qtext.lower())
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            make_candidate(
                source="World Values Survey Wave 7 Questionnaire",
                source_type="official_cross_national_survey_question",
                original_id=qid,
                label=qtext,
                definition=qtext,
                question_text=qtext,
                raw_category=current_section,
                evidence_level="High",
                inclusion_tier="A_official_survey_question",
                theoretical_basis="World Values Survey: cross-national values, beliefs, attitudes, and behavior",
                license_notes="Use WVS citation/data terms; questionnaire metadata used as source grounding",
                source_url="https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp",
                extraction_method="pdf_questionnaire_qid_line_extraction",
                high_quality=True,
                quality_score=92,
            )
        )


def add_scope(candidates):
    path = DATASET / "scope_structured.jsonl"
    if not path.exists():
        readme = DATASET / "scope_persona_README.md"
        facets = [
            "Demographic Information",
            "Sociodemographic Behavior",
            "Personal Values & Motivations",
            "Personality Traits (Big Five)",
            "Behavioral Patterns & Preferences",
            "Personal Identity & Life Narratives",
            "Professional Identity & Career",
        ]
        for facet in facets:
            candidates.append(
                make_candidate(
                    source="SCOPE-Persona",
                    source_type="persona_dataset_framework_facet",
                    original_id=facet,
                    label=facet,
                    definition=f"SCOPE persona framework facet: {facet}",
                    raw_category="SCOPE facets",
                    evidence_level="Medium",
                    inclusion_tier="B_peer_reviewed_persona_framework",
                    theoretical_basis="SCOPE sociopsychological persona framework",
                    license_notes="CC BY-NC 4.0; research-use restrictions per dataset card",
                    source_url="https://huggingface.co/datasets/Salesforce/SCOPE-Persona",
                    extraction_method="readme_facet_list",
                    high_quality=True,
                    quality_score=86,
                )
            )
        return

    seen = set()
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            for facet, qas in obj.items():
                if facet == "uuid" or not isinstance(qas, dict):
                    continue
                for question, answer in qas.items():
                    question = clean_text(question)
                    if not question:
                        continue
                    key = (facet, question.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(
                        make_candidate(
                            source="SCOPE-Persona structured protocol",
                            source_type="persona_dataset_questionnaire_item",
                            original_id=f"{facet}:{len(seen)}",
                            label=question,
                            definition=question,
                            question_text=question,
                            raw_category=facet.replace("_", " ").title(),
                            evidence_level="Medium",
                            inclusion_tier="B_peer_reviewed_persona_framework",
                            theoretical_basis="SCOPE sociopsychological persona protocol",
                            license_notes="CC BY-NC 4.0; research-use restrictions per dataset card",
                            source_url="https://huggingface.co/datasets/Salesforce/SCOPE-Persona",
                            extraction_method="jsonl_question_key_extraction",
                            high_quality=True,
                            quality_score=86,
                        )
                    )
            if len(seen) >= 141:
                break


def add_primex(candidates):
    path = DATASET / "apple_ml_primex" / "primexdata.csv"
    if not path.exists():
        return
    df = pd.read_csv(path, nrows=1)
    skip = [
        "timing -",
        "q_totalduration",
        "identity",
        "please mark this statement",
        "click count",
        "first click",
        "last click",
        "page submit",
    ]
    seen = set()
    for i, col in enumerate(df.columns, start=1):
        label = clean_text(col)
        low = label.lower()
        if not label or any(k in low for k in skip):
            continue
        if low in seen:
            continue
        seen.add(low)
        candidates.append(
            make_candidate(
                source="Apple ML-PrimeX",
                source_type="public_opinion_worldview_dataset_variable",
                original_id=f"col_{i}",
                label=label,
                definition=label,
                question_text=label if "?" in label or len(label.split()) > 3 else "",
                raw_category="PrimeX worldview/opinion/demographic variable",
                evidence_level="Medium",
                inclusion_tier="B_research_dataset_variable",
                theoretical_basis="PrimeX: worldview, opinion, explanation; includes PI-18 Primal World Beliefs",
                license_notes="CC BY-NC-ND 4.0; use for grounding/inspiration, not direct derived redistribution without review",
                source_url="https://github.com/apple/ml-primex",
                extraction_method="csv_column_extraction_filtered",
                high_quality=True,
                quality_score=84,
            )
        )


def add_nemotron_oasis(candidates):
    nemotron_fields = [
        "professional_persona",
        "sports_persona",
        "arts_persona",
        "travel_persona",
        "culinary_persona",
        "persona",
        "cultural_background",
        "skills_and_expertise",
        "skills_and_expertise_list",
        "hobbies_and_interests",
        "hobbies_and_interests_list",
        "career_goals_and_ambitions",
        "sex",
        "age",
        "marital_status",
        "education_level",
        "bachelors_field",
        "occupation",
        "city",
        "state",
        "zipcode",
        "country",
    ]
    for field in nemotron_fields:
        candidates.append(
            make_candidate(
                source="NVIDIA Nemotron-Personas-USA",
                source_type="synthetic_persona_dataset_field",
                original_id=field,
                label=field.replace("_", " ").title(),
                definition=f"Nemotron-Personas-USA field: {field}",
                raw_category="Nemotron dataset fields",
                evidence_level="Medium",
                inclusion_tier="B_persona_dataset_schema_field",
                theoretical_basis="Population-grounded synthetic persona fields",
                license_notes="CC BY 4.0 per dataset card",
                source_url="https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA",
                extraction_method="readme_dataset_info_features",
                high_quality=True,
                quality_score=80,
            )
        )

    oasis_path = DATASET / "oasis" / "user_data_36.json"
    if oasis_path.exists():
        try:
            data = json.loads(oasis_path.read_text(encoding="utf-8"))
            fields = sorted({k for item in data if isinstance(item, dict) for k in item.keys()})
        except Exception:
            fields = ["age", "gender", "mbti", "country", "profession", "interested_topics", "persona", "bio"]
    else:
        fields = ["age", "gender", "mbti", "country", "profession", "interested_topics", "persona", "bio"]
    for field in fields:
        if field in {"realname", "username"}:
            continue
        candidates.append(
            make_candidate(
                source="OASIS Reddit user profiles",
                source_type="agent_simulation_profile_field",
                original_id=field,
                label=field.replace("_", " ").title(),
                definition=f"OASIS user profile field: {field}",
                raw_category="OASIS Reddit user profile fields",
                evidence_level="Medium",
                inclusion_tier="B_persona_dataset_schema_field",
                theoretical_basis="Social-media agent simulation persona fields",
                license_notes="Apache-2.0 repository license; verify dataset terms",
                source_url="https://github.com/camel-ai/oasis/blob/main/data/reddit/user_data_36.json",
                extraction_method="local_json_field_extraction",
                high_quality=True,
                quality_score=78,
            )
        )


def add_personahub_extended(candidates, max_lines=20000):
    path = DATASET / "tencent_personahub" / "ElitePersonas" / "elite_personas.part1.jsonl"
    if not path.exists():
        return
    domains = set()
    fields = [
        "general domain (top 1 percent)",
        "specific domain (top 1 percent)",
        "general domain (top 0.1 percent)",
        "specific domain (top 0.1 percent)",
    ]
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            for field in fields:
                value = clean_text(obj.get(field, ""))
                if value and value.lower() != "none":
                    domains.add((field, value))
    for field, value in sorted(domains):
        candidates.append(
            make_candidate(
                source="Tencent PersonaHub sampled domain labels",
                source_type="large_scale_persona_dataset_domain_label",
                original_id=f"{field}:{value}",
                label=value,
                definition=f"PersonaHub elite persona domain label from {field}: {value}",
                raw_category=field,
                evidence_level="Low",
                inclusion_tier="C_llm_mined_domain_label_review_needed",
                theoretical_basis="PersonaHub role/domain expansion; useful for domain overlays after review",
                license_notes="CC BY-NC-SA 4.0 per dataset card; sampled labels only",
                source_url="https://huggingface.co/datasets/proj-persona/PersonaHub",
                extraction_method=f"sampled_first_{max_lines}_jsonl_lines",
                high_quality=False,
                quality_score=42,
                notes="Extended pool only by default.",
            )
        )


def add_acs_curated(candidates):
    path = DATASET / "acs_pums" / "acs_pums_curated_variables.csv"
    if not path.exists():
        return
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for _, row in df.iterrows():
        try:
            values = json.loads(row.get("values_json", "") or "[]")
        except Exception:
            values = []
        candidate = make_candidate(
            source="ACS PUMS curated variables",
            source_type="official_population_survey_variable",
            original_id=row["acs_variable"],
            label=row["label"],
            definition=row["definition"],
            raw_category=row["primary_category"],
            subcategory=row["subcategory"],
            values=values,
            evidence_level="High",
            inclusion_tier="A_official_population_grounding_variable",
            theoretical_basis="American Community Survey Public Use Microdata Sample: official U.S. population, household, housing, education, employment, income, disability, language, migration, and access variables",
            license_notes="U.S. Census Bureau public data/documentation; cite ACS PUMS data dictionary and verify release-specific variable definitions",
            source_url=row.get("source_url", ""),
            extraction_method="curated_from_official_acs_pums_data_dictionary",
            high_quality=True,
            quality_score=int(float(row.get("quality_score", "96") or 96)),
            notes=row.get("notes", ""),
        )
        candidate["primary_category"] = row["primary_category"]
        candidate["subcategory"] = row["subcategory"]
        candidate["data_type"] = row["data_type"]
        candidate["values_json"] = row.get("values_json", "[]")
        candidates.append(candidate)


def dedupe_candidates(candidates):
    deduped = []
    seen_exact = set()
    for c in candidates:
        key = (
            c["source"].lower(),
            c["original_id"].lower(),
            c["label"].lower(),
            c["raw_category"].lower(),
        )
        if key in seen_exact:
            continue
        seen_exact.add(key)
        deduped.append(c)
    return deduped


def select_high_quality(candidates):
    high = [c for c in candidates if c["include_high_quality"]]
    non_gss = [c for c in high if c["source"] != "GSS 1972-2024 Cumulative Codebook"]
    gss = [c for c in high if c["source"] == "GSS 1972-2024 Cumulative Codebook"]
    room = max(0, TARGET_HIGH_QUALITY_COUNT - len(non_gss))
    gss_sorted = sorted(gss, key=lambda c: (-int(c["quality_score"]), c["original_id"]))
    selected = non_gss + gss_sorted[:room]
    return sorted(selected, key=lambda c: (c["source"], c["primary_category"], c["label"].lower()))


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


def write_summary(candidates, high_quality):
    summary_rows = []
    for source, rows in sorted(defaultdict(list, {s: [r for r in candidates if r["source"] == s] for s in set(r["source"] for r in candidates)}).items()):
        hq_count = sum(1 for r in high_quality if r["source"] == source)
        ext_count = len(rows)
        evidence = Counter(r["evidence_level"] for r in rows)
        tiers = Counter(r["inclusion_tier"] for r in rows)
        summary_rows.append(
            {
                "source": source,
                "raw_extended_count": ext_count,
                "high_quality_count": hq_count,
                "evidence_levels": json.dumps(dict(evidence), ensure_ascii=False),
                "inclusion_tiers": json.dumps(dict(tiers), ensure_ascii=False),
            }
        )
    write_csv(OUT / "candidate_pool_source_summary.csv", summary_rows)

    cat_counts = Counter(r["primary_category"] for r in high_quality)
    source_counts = Counter(r["source"] for r in high_quality)
    extended_source_counts = Counter(r["source"] for r in candidates)
    report = [
        "# Candidate Pool Build Report",
        "",
        "Generated by `aggregate_candidate_pool.py`.",
        "",
        f"- High-quality pool count: {len(high_quality)}",
        f"- Raw extended pool count: {len(candidates)}",
        f"- High-quality target count: {TARGET_HIGH_QUALITY_COUNT}",
        "",
        "## High-Quality Category Counts",
        "",
    ]
    for category in TOP_LEVEL_CATEGORIES:
        report.append(f"- {category}: {cat_counts.get(category, 0)}")
    report += ["", "## High-Quality Source Counts", ""]
    for source, count in source_counts.most_common():
        report.append(f"- {source}: {count}")
    report += ["", "## Raw Extended Source Counts", ""]
    for source, count in extended_source_counts.most_common():
        report.append(f"- {source}: {count}")
    report += [
        "",
        "## Quality Notes",
        "",
        "- The high-quality pool prioritizes official survey variables, public-domain psychometric items/scales, validated personality/value constructs, SCOPE protocol questions, PrimeX variables, Nemotron/OASIS schema fields, and the local MatrAIx/Yuexing 1K attributes.",
        "- GSS has more high-quality official variables than fit comfortably in the requested 5k-10k range, so the main high-quality pool includes the highest-scoring GSS variables and the raw extended pool retains all parsed GSS candidates.",
        "- DeepPersona auto-extractions and sampled PersonaHub domain labels are retained in the raw extended pool only by default because they are useful for coverage but need review, deduplication, and grounding before becoming final attributes.",
        "- This is a candidate pool, not a final schema. The next step is normalization, deduplication, and source-grounded graph construction.",
    ]
    (OUT / "candidate_pool_build_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main():
    candidates = []
    add_existing_matraix(candidates)
    add_deeppersona_extended(candidates)
    add_gss(candidates)
    add_ipip(candidates)
    add_facet_map(candidates)
    add_standard_psych_constructs(candidates)
    add_wvs(candidates)
    add_scope(candidates)
    add_primex(candidates)
    add_nemotron_oasis(candidates)
    add_personahub_extended(candidates)
    add_acs_curated(candidates)

    candidates = dedupe_candidates(candidates)
    high_quality = select_high_quality(candidates)

    write_csv(OUT / "candidate_pool_raw_extended.csv", candidates)
    write_jsonl(OUT / "candidate_pool_raw_extended.jsonl", candidates)
    write_csv(OUT / "candidate_pool_high_quality.csv", high_quality)
    write_jsonl(OUT / "candidate_pool_high_quality.jsonl", high_quality)
    write_summary(candidates, high_quality)

    print(json.dumps({
        "high_quality_count": len(high_quality),
        "raw_extended_count": len(candidates),
        "output_dir": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
