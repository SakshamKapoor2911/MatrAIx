#!/usr/bin/env python3
"""Infer the 1,339 persona schema dimensions from Amazon review histories.

The script is evidence-grounded but recall-oriented: it asks the model to
return strongly supported attributes and weak/suggestive non-sensitive
attributes when review text, ratings, dates, or reviewed categories provide
some support. Unsupported attributes are omitted.

Input JSONL rows should contain:
- user_id
- reviews: list of normalized Amazon review dicts with category/title/text/rating/timestamp

Output JSONL rows contain one record per user with validated inferred dimensions.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BASE_DIR.parents[2]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "persona" / "schema" / "dimensions.json"
DEFAULT_OUTPUT_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "inferred_dimensions.jsonl"
)
DEFAULT_EVIDENCE_PROFILE_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "evidence_profiles.jsonl"
)
DEFAULT_EVIDENCE_MAPPING_PATH = BASE_DIR / "amazon_review_evidence_mapping.json"
DEFAULT_MODEL = os.environ.get("OPENAI_LLM_MODEL", "gpt-4.1-mini")


EVIDENCE_PROFILE_SYSTEM_PROMPT = """You create compact evidence profiles from Amazon review histories.

Core rule: record only evidence directly supported by review text, product title, rating, category, or repeated review behavior. Do not make persona claims from stereotypes.

Use the provided broad evidence categories as the organizing guide. Capture both strong and weak/suggestive non-sensitive signals so downstream schema mapping can choose more attributes with calibrated confidence. Preserve repeated health, family, religion, politics, or identity-adjacent product/context evidence as context signals when present, but separate those from asserted personal attributes. Do not assert protected or sensitive demographics, health status, family status, socioeconomic status, occupation, region, politics, religion, or identity unless the reviewer explicitly states it in the evidence.

Return compact JSON only."""


SCHEMA_MAPPING_SYSTEM_PROMPT = """You map compact Amazon-review evidence profiles to persona schema attributes.

Core rule: maximize useful non-sensitive persona coverage while staying evidence-grounded. Return strongly supported attributes and weak/suggestive non-sensitive attributes when the compact evidence profile provides some support. If the evidence profile provides no support for a schema dimension, omit it.

Evidence standards:
- Prefer explicit self-statements and repeated behavioral evidence.
- Include weak but plausible non-sensitive attributes when evidence is suggestive; mark them with lower confidence and explain the limited support.
- Repeated sensitive-adjacent product/context evidence may support non-sensitive interests, needs, values, preferences, or topical engagement with calibrated confidence.
- For each inferred dimension, choose exactly one allowed value from that dimension.
- Every inferred dimension must cite profile evidence item ids and original review ids.
- Do not assert sensitive demographics, health conditions, family status, socioeconomic status, political affiliation, religious identity, or identity attributes unless the profile contains explicit quoted self-statements. Product purchases alone can support contextual interests or needs, not identity/status labels.
- Use confidence between 0 and 1. Use 0.35-0.6 for weak/suggestive non-sensitive attributes, 0.6-0.8 for moderate repeated evidence, and >=0.8 only for explicit or strongly repeated evidence.

Return compact JSON only."""


SCHEMA_CATEGORY_ROUTER_SYSTEM_PROMPT = """You route compact Amazon-review evidence profiles to persona schema categories.

Core rule: select schema categories that are likely to contain supported attributes for this user. Be recall-oriented: include weak but plausible non-sensitive category matches when the evidence profile provides some support. Do not select sensitive identity/status/condition categories from product stereotypes alone; select those only for explicit self-statements or when the category can be used as contextual topical engagement.

Return compact JSON only."""


SCHEMA_SIGNAL_CHECKLIST = [
    {
        "schema_area": "interests_and_topics",
        "preserve": [
            "specific product topics, hobbies, sports, foods, media genres, cultural interests, and recurring category clusters",
            "explicit likes/dislikes and repeated engagement patterns, with product/category context",
        ],
    },
    {
        "schema_area": "preferences_habits_and_decision_style",
        "preserve": [
            "price/value sensitivity, quality standards, durability, comfort, convenience, aesthetics, safety, brand loyalty, and tolerance for tradeoffs",
            "routines and use contexts such as DIY, home organization, gifting, cooking, parenting/caregiving, pets, travel, work, study, and entertainment",
        ],
    },
    {
        "schema_area": "skills_expertise_and_learning",
        "preserve": [
            "technical vocabulary, tool use, comparative evaluation, troubleshooting, domain-specific criteria, and repeated knowledgeable reviews",
            "software/programming, tools, crafts, cooking, fitness, finance, health, education, professional, and other skill or expertise signals when directly supported",
        ],
    },
    {
        "schema_area": "values_motivations_and_personality",
        "preserve": [
            "grounded priorities such as reliability, frugality, learning, creativity, productivity, sustainability, comfort, safety, and care for others",
            "review-supported traits such as detail orientation, cautiousness, novelty seeking, patience, discipline, kindness, and problem solving",
        ],
    },
    {
        "schema_area": "communication_and_linguistic_style",
        "preserve": [
            "review length/detail, directness, emotional tone, critique style, explanation depth, and recurring language patterns",
            "evidence useful for linguistic, learning-style, and personality dimensions",
        ],
    },
    {
        "schema_area": "explicit_only_personal_facts",
        "preserve": [
            "direct quotes for occupation, education, family role, location, life stage, health context, identity, politics, religion, or other sensitive facts",
            "also record when these areas are unsupported so downstream schema mapping does not guess",
        ],
    },
    {
        "schema_area": "sensitive_adjacent_context",
        "preserve": [
            "repeated product/context evidence related to health, family/caregiving, religion, politics, or identity as contextual interests, needs, or topical engagement",
            "avoid converting this context into an asserted condition, affiliation, identity, or family status unless there is an explicit self-statement",
        ],
    },
]


def log(message: str) -> None:
    print(f"[amazon_dimension_inference] {message}", flush=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def iter_jsonl_or_gz(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]], append: bool = False) -> int:
    ensure_dir(path.parent)
    count = 0
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def load_product_metadata_sidecar(path: Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Product metadata sidecar not found: {path}")
    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    for row in iter_jsonl_or_gz(path):
        parent_asin = row.get("parent_asin")
        source_category = row.get("source_category")
        if parent_asin and source_category:
            metadata[(str(parent_asin), str(source_category))] = row
            metadata.setdefault((str(parent_asin), ""), row)
    return metadata


def attach_product_metadata_sidecar(
    user_row: dict[str, Any],
    metadata: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    if not metadata:
        return user_row
    for field in ("reviews", "validation_reviews"):
        reviews = user_row.get(field) or []
        if not isinstance(reviews, list):
            continue
        for review in reviews:
            if not isinstance(review, dict) or review.get("product_metadata"):
                continue
            parent_asin = review.get("parent_asin")
            if not parent_asin:
                continue
            category = str(review.get("category") or "")
            row = metadata.get((str(parent_asin), category)) or metadata.get((str(parent_asin), ""))
            if row:
                review["product_metadata"] = row
    return user_row


def yaml_key(value: Any) -> str:
    key = str(value)
    if key and all(char.isalnum() or char in "_-" for char in key) and not key[0].isdigit():
        return key
    return json.dumps(key, ensure_ascii=False)


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def yaml_dump(data: Any, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(data, dict):
        if not data:
            return f"{prefix}{{}}"
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{yaml_key(key)}:")
                lines.append(yaml_dump(value, indent + 2))
            elif isinstance(value, list):
                lines.append(f"{prefix}{yaml_key(key)}:")
                lines.append(yaml_dump(value, indent))
            else:
                lines.append(f"{prefix}{yaml_key(key)}: {yaml_scalar(value)}")
        return "\n".join(lines)
    if isinstance(data, list):
        if not data:
            return f"{prefix}[]"
        lines = []
        for item in data:
            if isinstance(item, dict | list):
                lines.append(f"{prefix}-")
                lines.append(yaml_dump(item, indent + 2))
            else:
                lines.append(f"{prefix}- {yaml_scalar(item)}")
        return "\n".join(lines)
    return f"{prefix}{yaml_scalar(data)}"


def write_yaml(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(yaml_dump(data) + "\n", encoding="utf-8")


def persona_yaml_document(rows: list[dict[str, Any]], source_jsonl: Path) -> dict[str, Any]:
    personas = []
    for index, row in enumerate(rows, start=1):
        user_id = str(row.get("user_id") or f"user_{index:04d}")
        evidence_profile = row.get("evidence_profile") or {}
        overview = compact_text(evidence_profile.get("overview"), 1200)
        inferred_attributes = row.get("inferred_attributes") or []
        dimensions = {
            str(attr["dimension_id"]): attr.get("value")
            for attr in sorted(
                inferred_attributes,
                key=lambda item: str(item.get("dimension_id") or ""),
            )
            if attr.get("dimension_id") and attr.get("value") is not None
        }
        personas.append(
            {
                "id": f"amazon_user_{index:04d}",
                "name": user_id,
                "title": "Amazon review-derived persona",
                "description": overview
                or (
                    f"Persona attributes inferred from Amazon Reviews 2023 "
                    f"construction history for user {user_id}."
                ),
                "dimensions": dimensions,
            }
        )

    return {
        "metadata": {
            "title": "Amazon Reviews 2023 Persona Attributes",
            "description": (
                "Behavior-grounded personas inferred from Amazon review histories. "
                "Only schema-supported attributes are included; unsupported "
                "dimensions are omitted."
            ),
            "count": len(personas),
            "generation_date": datetime.now(timezone.utc).date().isoformat(),
            "source": "amazon_reviews_2023",
            "source_jsonl": str(source_jsonl),
            "format": "personas_yaml_v1",
            "validation": (
                "Inferred attribute values are validated against the allowed "
                "values in persona/schema/dimensions.json before export."
            ),
        },
        "personas": personas,
    }


def write_inference_yaml(jsonl_path: Path, yaml_path: Path) -> int:
    rows = list(iter_jsonl_or_gz(jsonl_path))
    write_yaml(yaml_path, persona_yaml_document(rows, jsonl_path))
    return len(rows)


def load_schema(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    dimensions = data.get("dimensions", [])
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError(f"No dimensions list found in schema: {path}")
    for dim in dimensions:
        missing = {"id", "label", "category", "description", "values"} - set(dim)
        if missing:
            raise ValueError(f"Dimension missing required keys {sorted(missing)}: {dim}")
    return dimensions


def load_evidence_mapping(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        mapping = json.load(fh)
    categories = mapping.get("evidence_categories", [])
    if not isinstance(categories, list) or not categories:
        raise ValueError(f"No evidence_categories list found in mapping: {path}")
    return mapping


def parse_csv_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    parsed = {part.strip() for part in value.split(",") if part.strip()}
    return parsed or None


def filter_dimensions(
    dimensions: list[dict[str, Any]],
    category_filter: set[str] | None,
    id_filter: set[str] | None,
) -> list[dict[str, Any]]:
    filtered = []
    for dim in dimensions:
        if category_filter and dim["category"] not in category_filter:
            continue
        if id_filter and dim["id"] not in id_filter:
            continue
        filtered.append(dim)
    return filtered


def category_matches(category: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("*") and category.startswith(pattern[:-1]):
            return True
        if category == pattern:
            return True
    return False


def amazon_supported_schema_categories(mapping: dict[str, Any]) -> set[str]:
    supported = set()
    for evidence_category in mapping.get("evidence_categories", []):
        for category in evidence_category.get("schema_categories", []):
            supported.add(str(category))
    return supported


def filter_amazon_supported_dimensions(
    dimensions: list[dict[str, Any]],
    mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    supported = amazon_supported_schema_categories(mapping)
    skip_by_default = set(mapping.get("skip_by_default_schema_categories", []))
    filtered = []
    for dim in dimensions:
        category = str(dim["category"])
        if category_matches(category, skip_by_default):
            continue
        if category_matches(category, supported):
            filtered.append(dim)
    return filtered


def batched(items: list[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    if size <= 0:
        raise ValueError("--dimensions-per-call must be positive")
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def normalize_timestamp(value: Any) -> int | None:
    if value is None:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp < 0:
        return None
    if timestamp < 10_000_000_000:
        timestamp *= 1000
    return timestamp


def timestamp_to_date(value: Any) -> str | None:
    timestamp = normalize_timestamp(value)
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()


def compact_text(value: Any, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def review_corpus_stats(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_reviews = sorted(reviews, key=lambda row: normalize_timestamp(row.get("timestamp")) or 0)
    text_chars = 0
    text_reviews = 0
    rating_count = 0
    rating_only_count = 0
    category_counts: dict[str, int] = {}
    rating_only_rating_counts: dict[str, int] = {}
    rating_only_product_counts: dict[str, int] = {}
    rating_only_main_category_counts: dict[str, int] = {}
    rating_only_category_counts: dict[str, int] = {}
    for review in sorted_reviews:
        category = str(review.get("category") or "Unknown")
        category_counts[category] = category_counts.get(category, 0) + 1
        text = " ".join(str(review.get("text") or "").split())
        if text:
            text_reviews += 1
            text_chars += len(text)
        if review.get("rating") is not None:
            rating_count += 1
            if not text:
                rating_only_count += 1
                try:
                    rating = float(review.get("rating"))
                    rating_key = str(int(rating)) if rating.is_integer() else str(rating)
                except (TypeError, ValueError):
                    rating_key = str(review.get("rating"))
                rating_only_rating_counts[rating_key] = (
                    rating_only_rating_counts.get(rating_key, 0) + 1
                )
                product = product_context(review)
                product_name = product.get("name")
                if product_name:
                    rating_only_product_counts[product_name] = (
                        rating_only_product_counts.get(product_name, 0) + 1
                    )
                main_category = product.get("main_category") or category
                if main_category:
                    rating_only_main_category_counts[main_category] = (
                        rating_only_main_category_counts.get(main_category, 0) + 1
                    )
                product_categories = product.get("categories") or [category]
                for product_category in product_categories:
                    rating_only_category_counts[product_category] = (
                        rating_only_category_counts.get(product_category, 0) + 1
                    )

    def top_counts(counts: dict[str, int], limit: int = 25) -> dict[str, int]:
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit])

    return {
        "row_count": len(sorted_reviews),
        "text_review_count": text_reviews,
        "rating_count": rating_count,
        "rating_only_count": rating_only_count,
        "text_chars": text_chars,
        "first_date": timestamp_to_date(sorted_reviews[0].get("timestamp")) if sorted_reviews else None,
        "last_date": timestamp_to_date(sorted_reviews[-1].get("timestamp")) if sorted_reviews else None,
        "category_counts": dict(sorted(category_counts.items())),
        "rating_only_summary": {
            "row_count": rating_only_count,
            "rating_counts": dict(sorted(rating_only_rating_counts.items())),
            "top_product_names": top_counts(rating_only_product_counts),
            "top_main_categories": top_counts(rating_only_main_category_counts),
            "top_product_categories": top_counts(rating_only_category_counts),
        },
    }


def validate_temporal_split_user_row(user_row: dict[str, Any], args: argparse.Namespace) -> None:
    if args.allow_unsplit_histories:
        return
    user_id = user_row.get("user_id")
    temporal_split = user_row.get("temporal_split")
    validation_reviews = user_row.get("validation_reviews")
    if not isinstance(temporal_split, dict):
        raise ValueError(
            f"Input history for user {user_id} is missing temporal_split. "
            "Persona inference expects reviews to contain only the construction "
            "split and validation_reviews to contain the held-out split. Re-export "
            "histories with modal_amazon_user_index.py::export_user_histories, or "
            "pass --allow-unsplit-histories only for debugging/ablations."
        )
    if temporal_split.get("method") != "per_user_temporal":
        raise ValueError(
            f"Input history for user {user_id} has unsupported temporal split "
            f"method: {temporal_split.get('method')!r}."
        )
    try:
        train_fraction = float(temporal_split.get("train_fraction"))
    except (TypeError, ValueError):
        train_fraction = None
    if train_fraction is None or not 0 < train_fraction < 1:
        raise ValueError(
            f"Input history for user {user_id} has invalid temporal train_fraction: "
            f"{temporal_split.get('train_fraction')!r}."
        )
    if not isinstance(validation_reviews, list) or not validation_reviews:
        raise ValueError(
            f"Input history for user {user_id} is missing nonempty validation_reviews. "
            "Refusing to infer personas from an unsplit or all-construction history."
        )


def product_context(review: dict[str, Any]) -> dict[str, Any]:
    metadata = review.get("product_metadata")
    if not isinstance(metadata, dict):
        return {}
    product = {}
    title = compact_text(metadata.get("title"), 220)
    if title:
        product["name"] = title
    main_category = compact_text(metadata.get("main_category"), 120)
    if main_category:
        product["main_category"] = main_category
    categories = []
    categories_json = metadata.get("categories_json")
    if categories_json:
        try:
            parsed_categories = json.loads(categories_json)
        except (TypeError, ValueError):
            parsed_categories = []
        if isinstance(parsed_categories, list):
            for value in parsed_categories:
                if isinstance(value, list):
                    categories.extend(str(part) for part in value if part)
                elif value:
                    categories.append(str(value))
    compact_categories = []
    seen = set()
    for category in categories:
        category = compact_text(category, 80)
        if category and category not in seen:
            seen.add(category)
            compact_categories.append(category)
        if len(compact_categories) >= 6:
            break
    if compact_categories:
        product["categories"] = compact_categories
    return product


def context_rows_for_reviews(
    reviews: list[dict[str, Any]],
    max_review_text_chars: int,
    include_textless: bool = True,
) -> list[dict[str, Any]]:
    sorted_reviews = sorted(reviews, key=lambda row: normalize_timestamp(row.get("timestamp")) or 0)
    rows = []
    for idx, review in enumerate(sorted_reviews, start=1):
        text = compact_text(review.get("text"), max_review_text_chars)
        if not include_textless and not text:
            continue
        title = compact_text(review.get("title"), 180)
        rows.append(
            {
                "review_id": str(review.get("review_id") or f"r{idx:06d}"),
                "date": timestamp_to_date(review.get("timestamp")),
                "category": review.get("category"),
                "rating": review.get("rating"),
                "title": title,
                "text": text,
                "verified_purchase": review.get("verified_purchase"),
                "helpful_vote": review.get("helpful_vote", review.get("helpful_votes")),
                "product": product_context(review),
            }
        )
    return rows


def serialized_context_chars(context: list[dict[str, Any]]) -> int:
    return sum(len(json.dumps(row, ensure_ascii=False)) for row in context)


FIRST_PERSON_MARKERS = (
    "i",
    "i am",
    "im",
    "i'm",
    "ive",
    "i've",
    "i use",
    "i used",
    "i bought",
    "i needed",
    "i wanted",
    "i found",
    "i think",
    "i feel",
    "i noticed",
    "i wear",
    "i read",
    "i cook",
    "i work",
    "i travel",
    "me",
    "my",
    "mine",
    "myself",
    "we",
    "we are",
    "we're",
    "we have",
    "we've",
    "our",
    "ours",
    "for my",
    "for our",
    "my kid",
    "my kids",
    "my child",
    "my children",
    "my toddler",
    "my baby",
    "my son",
    "my daughter",
    "my wife",
    "my husband",
    "my spouse",
    "my partner",
    "my mom",
    "my mother",
    "my dad",
    "my father",
    "my parent",
    "my parents",
    "my family",
    "my home",
    "my house",
    "my office",
    "my classroom",
    "my students",
    "my dog",
    "my puppy",
    "my cat",
    "my kitten",
    "my pet",
)

PREFERENCE_VALUE_MARKERS = (
    "i like",
    "i love",
    "i prefer",
    "i dislike",
    "i hate",
    "i wanted",
    "i needed",
    "i wish",
    "i recommend",
    "i would recommend",
    "recommend",
    "highly recommend",
    "do not recommend",
    "favorite",
    "must have",
    "go to",
    "important",
    "worth",
    "not worth",
    "worth it",
    "worth the money",
    "waste of money",
    "value",
    "good value",
    "great value",
    "budget",
    "quality",
    "high quality",
    "poor quality",
    "well made",
    "cheaply made",
    "durable",
    "durability",
    "lasts",
    "long lasting",
    "comfortable",
    "uncomfortable",
    "comfort",
    "safe",
    "safety",
    "secure",
    "security",
    "easy to use",
    "easy to clean",
    "easy to install",
    "easy to assemble",
    "easy setup",
    "hard to use",
    "hard to clean",
    "hard to install",
    "convenient",
    "convenience",
    "reliable",
    "unreliable",
    "sturdy",
    "flimsy",
    "affordable",
    "expensive",
    "cheap",
    "price",
    "pricey",
    "overpriced",
    "inexpensive",
    "saves time",
    "time saver",
    "space saving",
    "compact",
    "portable",
    "lightweight",
    "heavy duty",
    "eco friendly",
    "non toxic",
    "organic",
    "natural",
    "fragrance free",
    "scented",
    "unscented",
)

COMPARISON_REASONING_MARKERS = (
    "better than",
    "worse than",
    "compared to",
    "compare to",
    "comparison",
    "similar to",
    "different from",
    "because",
    "since",
    "so that",
    "therefore",
    "as a result",
    "after trying",
    "i tried",
    "i have tried",
    "we tried",
    "tried several",
    "tried many",
    "after using",
    "after wearing",
    "after reading",
    "works better",
    "works well",
    "works great",
    "worked great",
    "worked well",
    "doesn't work",
    "didn't work",
    "did not work",
    "does not work",
    "instead of",
    "rather than",
    "the reason",
    "pros",
    "cons",
    "pro",
    "con",
    "downside",
    "upside",
    "however",
    "but",
    "although",
    "unless",
    "except",
    "versus",
    "vs",
    "best",
    "worst",
    "least",
    "most",
)

DOMAIN_DETAIL_MARKERS = (
    "install",
    "installed",
    "installation",
    "assemble",
    "assembled",
    "assembly",
    "recipe",
    "recipes",
    "ingredient",
    "ingredients",
    "measurement",
    "measurements",
    "ounce",
    "ounces",
    "inch",
    "inches",
    "feet",
    "pound",
    "pounds",
    "watt",
    "watts",
    "voltage",
    "volt",
    "amps",
    "battery",
    "charging",
    "charger",
    "bluetooth",
    "wifi",
    "usb",
    "hdmi",
    "software",
    "application",
    "mobile app",
    "settings",
    "setup",
    "configuration",
    "compatible",
    "compatibility",
    "material",
    "fabric",
    "cotton",
    "leather",
    "metal",
    "plastic",
    "wood",
    "stainless steel",
    "size",
    "sizing",
    "fit",
    "fits",
    "fitting",
    "training",
    "exercise",
    "workout",
    "reps",
    "miles",
    "calories",
    "repair",
    "fixed",
    "replacement",
    "replace",
    "tool",
    "tools",
    "screw",
    "screws",
    "mount",
    "mounted",
    "bracket",
    "manual",
    "instructions",
    "directions",
    "tutorial",
    "chapter",
    "plot",
    "character",
    "author",
    "narrator",
    "edition",
    "screen",
    "resolution",
    "camera",
    "lens",
    "audio",
    "sound",
    "bass",
    "volume",
)

SENSITIVE_ADJACENT_MARKERS = (
    "pain",
    "back pain",
    "neck pain",
    "joint pain",
    "chronic",
    "doctor",
    "nurse",
    "hospital",
    "clinic",
    "medical",
    "medicine",
    "medication",
    "health",
    "healthy",
    "therapy",
    "therapist",
    "physical therapy",
    "anxiety",
    "stress",
    "sleep",
    "insomnia",
    "allergy",
    "allergies",
    "diabetic",
    "diabetes",
    "blood pressure",
    "arthritis",
    "injury",
    "surgery",
    "recovery",
    "posture",
    "brace",
    "mobility",
    "wheelchair",
    "walker",
    "cane",
    "pregnant",
    "pregnancy",
    "maternity",
    "nursing",
    "breastfeeding",
    "baby",
    "babies",
    "kid",
    "kids",
    "child",
    "children",
    "toddler",
    "teen",
    "teenager",
    "parent",
    "parenting",
    "grandparent",
    "grandma",
    "grandpa",
    "caregiver",
    "elderly",
    "church",
    "bible",
    "prayer",
    "religion",
    "religious",
    "christian",
    "catholic",
    "jewish",
    "muslim",
    "islam",
    "hindu",
    "buddhist",
    "spiritual",
    "devotional",
    "worship",
    "politic",
    "political",
    "election",
    "vote",
    "voting",
    "democrat",
    "republican",
    "conservative",
    "liberal",
    "activism",
    "activist",
    "identity",
    "gender",
    "lgbt",
    "lgbtq",
    "pride",
    "race",
    "racial",
    "ethnic",
    "culture",
    "cultural",
    "disability",
    "disabled",
    "accessibility",
    "accessible",
    "senior",
    "veteran",
    "military",
)


def marker_pattern(marker: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![a-z0-9]){re.escape(marker.lower())}(?![a-z0-9])")


FIRST_PERSON_PATTERNS = tuple(marker_pattern(marker) for marker in FIRST_PERSON_MARKERS)
PREFERENCE_VALUE_PATTERNS = tuple(marker_pattern(marker) for marker in PREFERENCE_VALUE_MARKERS)
COMPARISON_REASONING_PATTERNS = tuple(
    marker_pattern(marker) for marker in COMPARISON_REASONING_MARKERS
)
DOMAIN_DETAIL_PATTERNS = tuple(marker_pattern(marker) for marker in DOMAIN_DETAIL_MARKERS)
SENSITIVE_ADJACENT_PATTERNS = tuple(
    marker_pattern(marker) for marker in SENSITIVE_ADJACENT_MARKERS
)
PERSONA_SIGNAL_PATTERN_GROUPS = (
    FIRST_PERSON_PATTERNS,
    PREFERENCE_VALUE_PATTERNS,
    COMPARISON_REASONING_PATTERNS,
    DOMAIN_DETAIL_PATTERNS,
    SENSITIVE_ADJACENT_PATTERNS,
)


def normalize_marker_text(text: str) -> str:
    return re.sub(r"[\u2018\u2019]", "'", text.lower())


def marker_count(normalized_text: str, patterns: Iterable[re.Pattern[str]]) -> int:
    return sum(1 for pattern in patterns if pattern.search(normalized_text))


def has_marker(normalized_text: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    return any(pattern.search(normalized_text) for pattern in patterns)


def has_any_marker(normalized_text: str, pattern_groups: Iterable[Iterable[re.Pattern[str]]]) -> bool:
    return any(has_marker(normalized_text, patterns) for patterns in pattern_groups)


def review_marker_features(text: str) -> dict[str, int | bool]:
    normalized = re.sub(r"[\u2018\u2019]", "'", text.lower())
    return {
        "first_person": marker_count(normalized, FIRST_PERSON_PATTERNS),
        "preference_value": marker_count(normalized, PREFERENCE_VALUE_PATTERNS),
        "comparison_reasoning": marker_count(normalized, COMPARISON_REASONING_PATTERNS),
        "domain_detail": marker_count(normalized, DOMAIN_DETAIL_PATTERNS),
        "sensitive_adjacent": marker_count(normalized, SENSITIVE_ADJACENT_PATTERNS),
        "has_persona_signal": has_any_marker(normalized, PERSONA_SIGNAL_PATTERN_GROUPS),
    }


def review_informativeness_score(
    row: dict[str, Any],
    category_counts: dict[str, int],
) -> float:
    text = str(row.get("text") or "")
    title = str(row.get("title") or "")
    combined = f"{title} {text}".lower()
    features = review_marker_features(combined)
    text_len = len(text)
    score = min(text_len / 500, 1.0) * 5.0
    score += min(len(text.split()) / 120, 1.0) * 2.0
    score += int(features["first_person"]) * 1.8
    score += int(features["preference_value"]) * 1.6
    score += int(features["comparison_reasoning"]) * 1.8
    score += int(features["domain_detail"]) * 1.0
    score += int(features["sensitive_adjacent"]) * 1.4
    if any(char.isdigit() for char in combined):
        score += 0.8
    try:
        helpful_vote = int(row.get("helpful_vote") or 0)
    except (TypeError, ValueError):
        helpful_vote = 0
    score += min(helpful_vote, 20) / 20
    category = str(row.get("category") or "Unknown")
    score += min(3.0, 8.0 / max(category_counts.get(category, 1), 1) ** 0.5)
    has_persona_signal = bool(features["has_persona_signal"])
    if text_len < 30 and not has_persona_signal:
        score -= 8.0
    elif text_len < 50 and not has_persona_signal:
        score -= 4.0
    return score


def select_temporal_context_rows(rows: list[dict[str, Any]], max_reviews: int) -> list[dict[str, Any]]:
    if max_reviews <= 0 or len(rows) <= max_reviews:
        return rows
    if max_reviews == 1:
        return [rows[-1]]
    last = len(rows) - 1
    indices = sorted({round(i * last / (max_reviews - 1)) for i in range(max_reviews)})
    return [rows[idx] for idx in indices]


def select_category_temporal_context_rows(
    rows: list[dict[str, Any]],
    max_reviews: int,
    max_seed_categories: int = 24,
) -> list[dict[str, Any]]:
    if max_reviews <= 0 or len(rows) <= max_reviews:
        return rows
    if max_reviews == 1:
        return [rows[-1]]

    half_max = max(1, max_reviews // 2)
    last = len(rows) - 1
    selected_indices = {
        round(i * last / (half_max - 1))
        for i in range(half_max)
    } if half_max > 1 else {last}
    category_indices: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        category = str(row.get("category") or "Unknown")
        category_indices.setdefault(category, []).append(index)
    top_categories = sorted(
        category_indices,
        key=lambda category: (-len(category_indices[category]), category),
    )[:max_seed_categories]
    for category in top_categories:
        if len(selected_indices) >= max_reviews:
            break
        indices = category_indices[category]
        midpoint = indices[len(indices) // 2]
        selected_indices.add(midpoint)

    if len(selected_indices) < max_reviews:
        temporal_fill_indices = (
            {round(i * last / (max_reviews - 1)) for i in range(max_reviews)}
            if max_reviews > 1
            else {last}
        )
        for index in sorted(temporal_fill_indices):
            if len(selected_indices) >= max_reviews:
                break
            selected_indices.add(index)

    return [rows[index] for index in sorted(selected_indices)[:max_reviews]]


def add_evenly_spaced_indices(
    candidate_indices: list[int],
    selected_indices: set[int],
    target_count: int,
) -> None:
    if target_count <= 0 or not candidate_indices:
        return
    if target_count == 1:
        selected_indices.add(candidate_indices[-1])
        return
    last = len(candidate_indices) - 1
    for i in range(target_count):
        if len(selected_indices) >= target_count:
            break
        selected_indices.add(candidate_indices[round(i * last / (target_count - 1))])


def select_informative_category_temporal_context_rows(
    rows: list[dict[str, Any]],
    max_reviews: int,
    max_seed_categories: int = 32,
) -> list[dict[str, Any]]:
    if max_reviews <= 0 or len(rows) <= max_reviews:
        return rows
    if max_reviews == 1:
        scored = [
            (review_informativeness_score(row, {}), index)
            for index, row in enumerate(rows)
        ]
        return [rows[max(scored)[1]]]

    category_counts: dict[str, int] = {}
    category_indices: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        category = str(row.get("category") or "Unknown")
        category_counts[category] = category_counts.get(category, 0) + 1
        category_indices.setdefault(category, []).append(index)
    scores = [
        review_informativeness_score(row, category_counts)
        for row in rows
    ]
    selected_indices: set[int] = set()

    temporal_target = max(1, round(max_reviews * 0.25))
    category_target = max(1, round(max_reviews * 0.25))
    top_target = max_reviews - temporal_target - category_target

    non_generic_indices = [
        index
        for index, row in enumerate(rows)
        if scores[index] >= 0 or len(str(row.get("text") or "")) >= 50
    ]
    add_evenly_spaced_indices(
        non_generic_indices or list(range(len(rows))),
        selected_indices,
        temporal_target,
    )

    ranked_categories = sorted(
        category_indices,
        key=lambda category: (
            len(category_indices[category]),
            -max(scores[index] for index in category_indices[category]),
            category,
        ),
    )
    diverse_categories = (
        ranked_categories[: max_seed_categories // 2]
        + sorted(
            ranked_categories[max_seed_categories // 2 :],
            key=lambda category: (
                -max(scores[index] for index in category_indices[category]),
                category,
            ),
        )[: max_seed_categories // 2]
    )
    for category in diverse_categories:
        if len(selected_indices) >= temporal_target + category_target:
            break
        best_index = max(category_indices[category], key=lambda index: (scores[index], -index))
        selected_indices.add(best_index)

    ranked_indices = sorted(
        range(len(rows)),
        key=lambda index: (scores[index], len(str(rows[index].get("text") or "")), -index),
        reverse=True,
    )
    for index in ranked_indices:
        if len(selected_indices) >= max_reviews:
            break
        if scores[index] < 0 and len(selected_indices) >= temporal_target + category_target + top_target:
            continue
        selected_indices.add(index)

    if len(selected_indices) < max_reviews:
        for index in range(len(rows)):
            if len(selected_indices) >= max_reviews:
                break
            selected_indices.add(index)

    return [rows[index] for index in sorted(selected_indices)[:max_reviews]]


def select_context_rows(
    rows: list[dict[str, Any]],
    max_reviews: int,
    strategy: str = "temporal",
) -> list[dict[str, Any]]:
    if strategy == "informative_category_temporal":
        return select_informative_category_temporal_context_rows(rows, max_reviews)
    if strategy == "category_temporal":
        return select_category_temporal_context_rows(rows, max_reviews)
    return select_temporal_context_rows(rows, max_reviews)


def split_context_rows_into_windows(
    rows: list[dict[str, Any]],
    max_window_chars: int,
    max_window_rows: int,
) -> list[list[dict[str, Any]]]:
    windows: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for row in rows:
        row_chars = len(json.dumps(row, ensure_ascii=False))
        if current and (
            (max_window_chars and current_chars + row_chars > max_window_chars)
            or (max_window_rows and len(current) >= max_window_rows)
        ):
            windows.append(current)
            current = []
            current_chars = 0
        current.append(row)
        current_chars += row_chars
    if current:
        windows.append(current)
    return windows


def build_review_context(
    reviews: list[dict[str, Any]],
    max_reviews: int,
    max_review_text_chars: int,
    max_total_chars: int,
    include_textless: bool = True,
    selection_strategy: str = "temporal",
) -> list[dict[str, Any]]:
    rows = select_context_rows(
        context_rows_for_reviews(reviews, max_review_text_chars, include_textless=include_textless),
        max_reviews,
        strategy=selection_strategy,
    )
    context = []
    total_chars = 0
    for row in rows:
        total_chars += len(json.dumps(row, ensure_ascii=False))
        if max_total_chars and total_chars > max_total_chars:
            break
        context.append(row)
    return context


def effective_max_reviews_for_user(
    reviews: list[dict[str, Any]],
    corpus_stats: dict[str, Any],
    args: argparse.Namespace,
) -> int:
    base_max = args.max_reviews_per_user
    if (
        args.no_adaptive_power_review_cap
        or args.power_user_max_reviews <= base_max
    ):
        return base_max
    if (
        len(reviews) >= args.power_user_min_reviews
        or int(corpus_stats.get("text_chars") or 0) >= args.power_user_min_text_chars
    ):
        return args.power_user_max_reviews
    return base_max


def limit_evidence_items(
    evidence_items: list[dict[str, Any]],
    max_items: int,
) -> list[dict[str, Any]]:
    if max_items <= 0 or len(evidence_items) <= max_items:
        return evidence_items
    indexed_items = list(enumerate(evidence_items))
    indexed_items.sort(
        key=lambda item: (
            -float(item[1].get("confidence") or 0.0),
            -len(item[1].get("support") or []),
            item[0],
        )
    )
    kept_indices = {index for index, _ in indexed_items[:max_items]}
    return [item for index, item in enumerate(evidence_items) if index in kept_indices]



def evidence_profile_payload(
    user_row: dict[str, Any],
    review_context: list[dict[str, Any]],
    mapping: dict[str, Any],
    corpus_stats: dict[str, Any] | None = None,
    target_evidence_items: int | None = None,
) -> dict[str, Any]:
    return {
        "task": "build_compact_amazon_review_evidence_profile",
        "user_id": user_row.get("user_id"),
        "instructions": [
            "Summarize only evidence supported by the supplied reviews.",
            "Organize evidence using the broad evidence categories.",
            "Use category_review_summary as aggregate behavioral context, especially category frequency and rating patterns.",
            "Use construction_corpus_summary for aggregate rating-only behavior; review_evidence contains text-bearing rows only when text-only context is enabled.",
            "Use product name/category only to interpret the reviewed item; do not infer sensitive attributes from product stereotypes.",
            "Preserve repeated health, family/caregiving, religion, politics, or identity-adjacent product/context evidence as contextual needs or topical engagement, not as asserted personal status unless explicitly stated.",
            "Use schema_signal_checklist to preserve information likely to support the downstream 1,339-dimension persona schema without copying the whole schema.",
            "Preserve weak or suggestive non-sensitive signals as candidate evidence when they may support schema attributes; label them with lower confidence.",
            "Preserve enough distinct evidence to support downstream schema extraction; do not collapse unrelated interests, preferences, habits, skills, and values into one generic claim.",
            "Prefer concrete, reusable evidence over biography-like prose.",
            "Keep claims short and grounded.",
            "Each evidence item must cite at least one review_id and include a short exact quote from that review when text/title supports the claim.",
            "Use explicit_self_statement for occupation, family, health, location, politics, religion, or other sensitive/personal claims only when directly stated.",
            "For power reviewers, preserve recurring patterns across categories, rating behavior, decision criteria, expertise signals, and review-writing style.",
            "Omit unsupported categories instead of guessing.",
        ],
        "broad_evidence_categories": mapping.get("evidence_categories", []),
        "schema_signal_checklist": SCHEMA_SIGNAL_CHECKLIST,
        "extraction_settings": {
            "target_evidence_items": target_evidence_items,
            "memory_density": "preserve distinct grounded signals across evidence categories",
            "avoid": "long prose, duplicate claims, unsupported persona biography",
        },
        "category_review_summary": user_row.get("category_review_stats", {}),
        "construction_corpus_summary": corpus_stats or user_row.get("review_corpus_stats", {}),
        "output_json_schema": {
            "evidence_profile": {
                "user_id": "source user id",
                "overview": "brief grounded summary, not a persona biography",
                "structured_memory": {
                    "product_interests": ["concise grounded bullets"],
                    "consumption_preferences": ["concise grounded bullets"],
                    "rating_behavior": ["concise aggregate patterns from ratings/categories"],
                    "decision_style": ["concise grounded bullets"],
                    "expertise_signals": ["concise grounded bullets"],
                    "behavioral_habits": ["concise grounded bullets"],
                    "values_and_motivations": ["concise grounded bullets"],
                    "communication_style": ["concise grounded bullets"],
                    "explicit_self_statements": ["directly quoted or explicitly stated facts only"],
                    "sensitive_adjacent_context": ["repeated sensitive-adjacent product/context signals without asserted identity/status claims"],
                    "unsupported_or_sensitive_boundaries": ["claims that should not be inferred"],
                },
                "evidence_items": [
                    {
                        "evidence_item_id": "e1",
                        "broad_category_id": "one broad evidence category id",
                        "claim": "short grounded claim",
                        "support": [
                            {
                                "review_id": "review ids used as support",
                                "quote": "short exact quote from review title/text",
                            }
                        ],
                        "schema_category_hints": ["schema categories this evidence could support"],
                        "confidence": "number from 0 to 1",
                        "evidence_type": "explicit_self_statement | repeated_behavior | suggestive_behavior | sensitive_adjacent_context | product_interest | preference | expertise_signal | communication_style",
                    }
                ],
                "unsupported_or_blocked": [
                    {
                        "topic": "schema area or claim type",
                        "reason": "why Amazon reviews do not support it for this user",
                    }
                ],
            }
        },
        "review_evidence": review_context,
    }


def schema_mapping_payload(
    user_row: dict[str, Any],
    dimension_batch: list[dict[str, Any]],
    evidence_profile: dict[str, Any],
    recall_focus: bool = False,
) -> dict[str, Any]:
    dimensions = [
        {
            "id": dim["id"],
            "label": dim["label"],
            "category": dim["category"],
            "description": dim["description"],
            "allowed_values": dim["values"],
        }
        for dim in dimension_batch
    ]
    instructions = [
        "Return strongly supported dimensions and weak/suggestive non-sensitive dimensions supported by the compact evidence profile.",
        "Omit unsupported dimensions. Do not use product stereotypes as evidence for sensitive identity/status/condition dimensions.",
        "Repeated sensitive-adjacent product/context evidence can support interests, topical engagement, needs, values, or preferences, but not asserted health conditions, family status, religion, politics, identity, or other sensitive attributes unless explicitly self-stated.",
        "Use structured_memory to find candidate supported attributes, but cite evidence_item_ids and original review_ids for every returned attribute.",
        "For each inferred dimension, choose exactly one allowed value from that dimension.",
        "Every inferred dimension must include at least one evidence_item_id and at least one original review_id.",
        "Use confidence between 0 and 1. Use 0.35-0.6 for weak/suggestive non-sensitive attributes, 0.6-0.8 for moderate repeated evidence, and >=0.8 only for explicit or strongly repeated evidence.",
    ]
    if recall_focus:
        instructions.extend(
            [
                "This is a recall-focused second pass over high-value persona dimensions. Actively search for low-to-moderate confidence attributes that may have been missed in the broad pass.",
                "Prefer returning a weak but evidence-cited non-sensitive attribute over omitting it when the evidence plausibly supports one allowed value.",
                "Use confidence 0.2-0.35 for very weak but evidence-cited attributes, 0.35-0.6 for weak/suggestive attributes, 0.6-0.8 for moderate repeated evidence, and >=0.8 only for explicit or strongly repeated evidence.",
                "For sensitive-adjacent categories, return contextual needs/interests/preferences when supported; assert sensitive status or identity only from explicit self-statements.",
            ]
        )
    return {
        "task": "map_compact_amazon_review_evidence_profile_to_schema_dimensions",
        "user_id": user_row.get("user_id"),
        "instructions": instructions,
        "recall_focus": recall_focus,
        "output_json_schema": {
            "inferred_attributes": [
                {
                    "dimension_id": "schema dimension id",
                    "value": "one allowed value for that dimension",
                    "confidence": "number from 0 to 1",
                    "evidence_item_ids": ["compact profile evidence item ids"],
                    "evidence_review_ids": ["original review ids used as support"],
                    "evidence_quotes": ["short exact quotes copied from profile support"],
                    "reasoning": "brief grounded rationale",
                }
            ]
        },
        "schema_dimensions": dimensions,
        "compact_evidence_profile": evidence_profile,
    }


def schema_category_summaries(dimensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_category: dict[str, list[dict[str, Any]]] = {}
    for dim in dimensions:
        by_category.setdefault(str(dim["category"]), []).append(dim)
    summaries = []
    for category, category_dims in sorted(by_category.items()):
        samples = []
        for dim in category_dims[:8]:
            samples.append(
                {
                    "id": dim["id"],
                    "label": dim["label"],
                    "description": compact_text(dim.get("description"), 160),
                    "allowed_values": dim.get("values", [])[:8],
                }
            )
        summaries.append(
            {
                "category": category,
                "dimension_count": len(category_dims),
                "sample_dimensions": samples,
            }
        )
    return summaries


def schema_category_routing_payload(
    user_row: dict[str, Any],
    dimensions: list[dict[str, Any]],
    evidence_profile: dict[str, Any],
    always_include_patterns: list[str],
) -> dict[str, Any]:
    return {
        "task": "route_compact_amazon_review_evidence_profile_to_schema_categories",
        "user_id": user_row.get("user_id"),
        "instructions": [
            "Select schema categories that are likely to contain at least one supported persona attribute for this user.",
            "Be recall-oriented: include categories with weak/suggestive non-sensitive support and explain the limited support.",
            "Use compact_evidence_profile evidence items and structured_memory; do not invent facts outside the profile.",
            "Repeated sensitive-adjacent product/context evidence can support contextual interests, topical engagement, needs, values, or preferences, but not asserted health conditions, family status, religion, politics, identity, or other sensitive attributes unless explicitly self-stated.",
            "Do not select categories that have no support in the evidence profile.",
            "Return exact category strings from schema_categories only.",
        ],
        "always_include_patterns": always_include_patterns,
        "output_json_schema": {
            "selected_categories": [
                {
                    "category": "exact schema category string",
                    "confidence": "number from 0 to 1",
                    "evidence_item_ids": ["compact profile evidence item ids"],
                    "reasoning": "brief grounded reason",
                }
            ]
        },
        "schema_categories": schema_category_summaries(dimensions),
        "compact_evidence_profile": evidence_profile,
    }


def normalize_schema_category_routes(
    model_output: dict[str, Any],
    dimensions: list[dict[str, Any]],
    min_confidence: float,
    always_include_patterns: list[str],
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    available_categories = sorted({str(dim["category"]) for dim in dimensions})
    selected = {
        category
        for category in available_categories
        if category_matches(category, always_include_patterns)
    }
    valid_routes = []
    rejected_routes = []
    available = set(available_categories)
    for item in model_output.get("selected_categories", []):
        if not isinstance(item, dict):
            rejected_routes.append({"item": item, "reason": "not_object"})
            continue
        category = str(item.get("category") or "")
        if category not in available:
            rejected_routes.append({"item": item, "reason": "unknown_category"})
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            rejected_routes.append({"item": item, "reason": "invalid_confidence"})
            continue
        if confidence < min_confidence:
            rejected_routes.append({"item": item, "reason": "below_min_confidence"})
            continue
        selected.add(category)
        valid_routes.append(
            {
                "category": category,
                "confidence": round(max(0.0, min(1.0, confidence)), 3),
                "evidence_item_ids": item.get("evidence_item_ids") or [],
                "reasoning": item.get("reasoning", ""),
            }
        )
    return sorted(selected), valid_routes, rejected_routes


def filter_dimensions_by_categories(
    dimensions: list[dict[str, Any]],
    categories: set[str],
) -> list[dict[str, Any]]:
    return [dim for dim in dimensions if str(dim["category"]) in categories]


def dedupe_inferred_attributes(attributes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_dimension: dict[str, dict[str, Any]] = {}
    for attr in attributes:
        dim_id = str(attr.get("dimension_id") or "")
        if not dim_id:
            continue
        current = by_dimension.get(dim_id)
        if current is None or float(attr.get("confidence") or 0) > float(
            current.get("confidence") or 0
        ):
            by_dimension[dim_id] = attr
    return sorted(by_dimension.values(), key=lambda item: str(item.get("dimension_id") or ""))


def run_schema_mapping_batches(
    user_row: dict[str, Any],
    dimensions: list[dict[str, Any]],
    evidence_profile: dict[str, Any],
    valid_review_ids: set[str],
    args: argparse.Namespace,
    api_key: str,
    stage_name: str = "schema_mapping",
    recall_focus: bool = False,
    dimensions_per_call: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    all_valid = []
    all_rejected = []
    request_count = 0
    batch_size = dimensions_per_call or args.dimensions_per_call
    dimension_batches = list(batched(dimensions, batch_size))
    for batch_index, dimension_batch in enumerate(dimension_batches, start=1):
        request_count += 1
        log(
            f"user={user_row.get('user_id')} {stage_name} batch "
            f"{batch_index}/{len(dimension_batches)} dimensions={len(dimension_batch)} "
            f"evidence_items={len(evidence_profile.get('evidence_items') or [])}"
        )
        task = schema_mapping_payload(
            user_row,
            dimension_batch,
            evidence_profile,
            recall_focus=recall_focus,
        )
        payload = {
            "model": args.model,
            "temperature": args.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SCHEMA_MAPPING_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(task, ensure_ascii=False)},
            ],
        }
        response = openai_request(payload, api_key)
        model_output = parse_model_json(response)
        valid, rejected = validate_inferences(model_output, dimension_batch, valid_review_ids)
        all_valid.extend(valid)
        all_rejected.extend(rejected)
        log(
            f"user={user_row.get('user_id')} {stage_name} batch "
            f"{batch_index}/{len(dimension_batches)} done valid={len(valid)} rejected={len(rejected)}"
        )
    return all_valid, all_rejected, request_count


def openai_request(
    payload: dict[str, Any],
    api_key: str,
    timeout: int = 180,
    retries: int = 6,
) -> dict[str, Any]:
    if os.environ.get("OPENAI_FORCE_CURL") == "1":
        for attempt in range(retries):
            try:
                return openai_request_with_curl(payload, api_key, timeout=timeout)
            except RuntimeError as err:
                if attempt < retries - 1:
                    sleep_seconds = min(60, 2**attempt)
                    log(
                        f"OpenAI curl error: {err}; retry {attempt + 2}/{retries} "
                        f"after {sleep_seconds}s"
                    )
                    time.sleep(sleep_seconds)
                    continue
                raise
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            error_body = err.read().decode("utf-8", errors="replace")
            if err.code in {429, 500, 502, 503, 504} and attempt < retries - 1:
                sleep_seconds = min(60, 2**attempt)
                log(
                    f"OpenAI HTTP {err.code}; retry {attempt + 2}/{retries} "
                    f"after {sleep_seconds}s"
                )
                time.sleep(sleep_seconds)
                continue
            raise RuntimeError(f"OpenAI API error {err.code}: {error_body[:1000]}") from err
        except urllib.error.URLError as err:
            if attempt < retries - 1:
                sleep_seconds = min(60, 2**attempt)
                log(
                    f"OpenAI network error: {err}; retry {attempt + 2}/{retries} "
                    f"after {sleep_seconds}s"
                )
                time.sleep(sleep_seconds)
                continue
            log(f"OpenAI urllib failed after retries: {err}; trying curl fallback")
            return openai_request_with_curl(payload, api_key, timeout=timeout)
    raise RuntimeError("OpenAI request failed after retries")


def openai_request_with_curl(payload: dict[str, Any], api_key: str, timeout: int = 180) -> dict[str, Any]:
    body_path = None
    header_path = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False) as body_file:
            body_file.write(json.dumps(payload).encode("utf-8"))
            body_path = body_file.name
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as header_file:
            header_path = header_file.name
            header_file.write(f"Authorization: Bearer {api_key}\n")
            header_file.write("Content-Type: application/json\n")
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "--fail-with-body",
                "--connect-timeout",
                str(min(timeout, 60)),
                "--max-time",
                str(timeout),
                "-X",
                "POST",
                "-H",
                f"@{header_path}",
                "--data-binary",
                f"@{body_path}",
                "https://api.openai.com/v1/chat/completions",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"OpenAI curl request failed with exit {result.returncode}: "
                f"{(result.stderr or result.stdout)[:1000]}"
            )
        return json.loads(result.stdout)
    finally:
        for path in (body_path, header_path):
            if path:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass


def parse_model_json(response: dict[str, Any]) -> dict[str, Any]:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as err:
        raise ValueError(f"Unexpected OpenAI response shape: {response}") from err
    if isinstance(content, list):
        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return json.loads(content)


def validate_inferences(
    model_output: dict[str, Any],
    dimension_batch: list[dict[str, Any]],
    valid_review_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dimensions_by_id = {dim["id"]: dim for dim in dimension_batch}
    valid = []
    rejected = []
    for item in model_output.get("inferred_attributes", []):
        if not isinstance(item, dict):
            rejected.append({"item": item, "reason": "not_object"})
            continue
        dim_id = item.get("dimension_id")
        dim = dimensions_by_id.get(dim_id)
        if dim is None:
            rejected.append({"item": item, "reason": "unknown_dimension_id"})
            continue
        value = item.get("value")
        if value not in dim["values"]:
            rejected.append({"item": item, "reason": "value_not_in_schema"})
            continue
        evidence_ids = item.get("evidence_review_ids") or []
        if not isinstance(evidence_ids, list) or not set(evidence_ids).issubset(valid_review_ids):
            rejected.append({"item": item, "reason": "invalid_evidence_review_ids"})
            continue
        if not evidence_ids:
            rejected.append({"item": item, "reason": "missing_evidence"})
            continue
        try:
            confidence = float(item.get("confidence"))
        except (TypeError, ValueError):
            rejected.append({"item": item, "reason": "invalid_confidence"})
            continue
        if confidence < 0 or confidence > 1:
            rejected.append({"item": item, "reason": "confidence_out_of_range"})
            continue
        valid.append(
            {
                "dimension_id": dim_id,
                "label": dim["label"],
                "category": dim["category"],
                "value": value,
                "confidence": round(confidence, 3),
                "evidence_item_ids": item.get("evidence_item_ids") or [],
                "evidence_review_ids": evidence_ids,
                "evidence_quotes": item.get("evidence_quotes") or [],
                "reasoning": item.get("reasoning", ""),
            }
        )
    return valid, rejected


def normalize_evidence_profile(
    model_output: dict[str, Any],
    user_id: Any,
    valid_review_ids: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile = model_output.get("evidence_profile", model_output)
    if not isinstance(profile, dict):
        return {"user_id": user_id, "overview": "", "evidence_items": []}, [
            {"item": model_output, "reason": "profile_not_object"}
        ]
    normalized_items = []
    rejected = []
    for idx, item in enumerate(profile.get("evidence_items") or [], start=1):
        if not isinstance(item, dict):
            rejected.append({"item": item, "reason": "not_object"})
            continue
        support = item.get("support") or []
        if not isinstance(support, list):
            rejected.append({"item": item, "reason": "support_not_list"})
            continue
        normalized_support = []
        invalid_review_id = False
        for support_item in support:
            if not isinstance(support_item, dict):
                continue
            review_id = support_item.get("review_id")
            if review_id not in valid_review_ids:
                invalid_review_id = True
                continue
            normalized_support.append(
                {
                    "review_id": review_id,
                    "quote": compact_text(support_item.get("quote"), 240),
                }
            )
        if invalid_review_id or not normalized_support:
            rejected.append({"item": item, "reason": "invalid_or_missing_support"})
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))
        normalized_items.append(
            {
                "evidence_item_id": str(item.get("evidence_item_id") or f"e{idx}"),
                "broad_category_id": str(item.get("broad_category_id") or ""),
                "claim": compact_text(item.get("claim"), 360),
                "support": normalized_support,
                "schema_category_hints": item.get("schema_category_hints") or [],
                "confidence": round(confidence, 3),
                "evidence_type": str(item.get("evidence_type") or ""),
            }
        )
    structured_memory = profile.get("structured_memory") or {}
    if isinstance(structured_memory, dict):
        structured_memory = {
            str(key): [
                compact_text(item, 260)
                for item in value[:20]
            ]
            for key, value in structured_memory.items()
            if isinstance(value, list)
        }
    else:
        structured_memory = {}
    normalized = {
        "user_id": user_id,
        "overview": compact_text(profile.get("overview"), 1200),
        "structured_memory": structured_memory,
        "evidence_items": normalized_items,
        "unsupported_or_blocked": profile.get("unsupported_or_blocked") or [],
    }
    return normalized, rejected


def evidence_profile_review_ids(evidence_profile: dict[str, Any]) -> set[str]:
    review_ids: set[str] = set()
    for item in evidence_profile.get("evidence_items") or []:
        if not isinstance(item, dict):
            continue
        for support in item.get("support") or []:
            if isinstance(support, dict) and support.get("review_id"):
                review_ids.add(str(support["review_id"]))
    return review_ids


def completed_user_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done = set()
    for row in iter_jsonl_or_gz(path):
        user_id = row.get("user_id")
        if user_id:
            done.add(str(user_id))
    return done


def load_completed_rows_by_user(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows = {}
    for row in iter_jsonl_or_gz(path):
        user_id = row.get("user_id")
        if user_id:
            rows[str(user_id)] = row
    return rows


def build_or_load_evidence_profile(
    user_row: dict[str, Any],
    reviews: list[dict[str, Any]],
    review_context: list[dict[str, Any]],
    corpus_stats: dict[str, Any],
    mapping: dict[str, Any],
    args: argparse.Namespace,
    api_key: str,
    existing_profiles: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    user_id = str(user_row.get("user_id", ""))
    if user_id in existing_profiles and not args.overwrite_profiles:
        profile_row = existing_profiles[user_id]
        return profile_row.get("evidence_profile") or {}, profile_row.get("rejected_evidence_items") or [], 0

    all_context_rows = review_context
    all_context_chars = serialized_context_chars(all_context_rows)
    should_window = (
        args.window_summary_threshold_chars > 0
        and corpus_stats.get("text_chars", 0) > args.window_summary_threshold_chars
    )
    request_count = 0

    if should_window:
        windows = split_context_rows_into_windows(
            all_context_rows,
            max_window_chars=args.window_summary_max_chars,
            max_window_rows=args.window_summary_max_rows,
        )
        profile_items = []
        rejected = []
        overview_parts = []
        structured_memory: dict[str, list[str]] = {}
        unsupported_or_blocked = []
        for window_index, window_context in enumerate(windows, start=1):
            log(
                f"user={user_id} evidence_profile window {window_index}/{len(windows)} "
                f"rows={len(window_context)} chars={serialized_context_chars(window_context):,}"
            )
            payload = {
                "model": args.model,
                "temperature": args.temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": EVIDENCE_PROFILE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            evidence_profile_payload(
                                user_row,
                                window_context,
                                mapping,
                                corpus_stats,
                                target_evidence_items=max(10, args.max_evidence_items // max(len(windows), 1)),
                            ),
                            ensure_ascii=False,
                        ),
                    },
                ],
            }
            response = openai_request(payload, api_key)
            request_count += 1
            model_output = parse_model_json(response)
            valid_review_ids = {row["review_id"] for row in window_context}
            window_profile, window_rejected = normalize_evidence_profile(
                model_output,
                user_id,
                valid_review_ids,
            )
            if window_profile.get("overview"):
                overview_parts.append(f"Window {window_index}: {window_profile['overview']}")
            for key, values in (window_profile.get("structured_memory") or {}).items():
                if not isinstance(values, list):
                    continue
                target = structured_memory.setdefault(str(key), [])
                for value in values:
                    if value not in target:
                        target.append(value)
            for item_index, item in enumerate(window_profile.get("evidence_items") or [], start=1):
                item = dict(item)
                item["evidence_item_id"] = f"w{window_index}_{item.get('evidence_item_id') or item_index}"
                profile_items.append(item)
            unsupported_or_blocked.extend(window_profile.get("unsupported_or_blocked") or [])
            rejected.extend(
                {
                    **item,
                    "window_index": window_index,
                }
                for item in window_rejected
            )
            log(
                f"user={user_id} evidence_profile window {window_index}/{len(windows)} "
                f"done evidence_items={len(window_profile.get('evidence_items') or [])} "
                f"rejected={len(window_rejected)}"
            )

        profile = {
            "user_id": user_id,
            "overview": compact_text(" ".join(overview_parts), 1200),
            "structured_memory": {
                key: values[:20]
                for key, values in sorted(structured_memory.items())
            },
            "evidence_items": limit_evidence_items(
                profile_items,
                args.max_evidence_items or args.max_window_evidence_items,
            ),
            "unsupported_or_blocked": unsupported_or_blocked,
        }
        profile_row = {
            "source": "amazon_reviews_2023",
            "user_id": user_row.get("user_id"),
            "review_count": len(reviews),
            "review_corpus_stats": corpus_stats,
            "review_context_count": len(all_context_rows),
            "review_context_chars": all_context_chars,
            "model": args.model,
            "status": "ok",
            "profile_build_mode": "windowed",
            "window_summary": {
                "threshold_text_chars": args.window_summary_threshold_chars,
                "window_count": len(windows),
                "max_window_chars": args.window_summary_max_chars,
                "max_window_rows": args.window_summary_max_rows,
                "max_window_evidence_items": args.max_window_evidence_items,
                "max_evidence_items": args.max_evidence_items,
            },
            "evidence_profile": profile,
            "rejected_evidence_items": rejected,
        }
        write_jsonl(args.evidence_profiles_output, [profile_row], append=args.evidence_profiles_output.exists())
        existing_profiles[user_id] = profile_row
        return profile, rejected, request_count

    payload = {
        "model": args.model,
        "temperature": args.temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": EVIDENCE_PROFILE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    evidence_profile_payload(
                        user_row,
                        review_context,
                        mapping,
                        corpus_stats,
                        target_evidence_items=args.max_evidence_items,
                    ),
                    ensure_ascii=False,
                ),
            },
        ],
    }
    log(
        f"user={user_id} evidence_profile single_context "
        f"rows={len(review_context)} chars={serialized_context_chars(review_context):,}"
    )
    response = openai_request(payload, api_key)
    request_count += 1
    model_output = parse_model_json(response)
    valid_review_ids = {row["review_id"] for row in review_context}
    profile, rejected = normalize_evidence_profile(model_output, user_id, valid_review_ids)
    profile["evidence_items"] = limit_evidence_items(
        profile.get("evidence_items") or [],
        args.max_evidence_items,
    )
    profile_row = {
        "source": "amazon_reviews_2023",
        "user_id": user_row.get("user_id"),
        "review_count": len(user_row.get("reviews") or []),
        "review_corpus_stats": corpus_stats,
        "review_context_count": len(review_context),
        "review_context_chars": serialized_context_chars(review_context),
        "model": args.model,
        "status": "ok",
        "profile_build_mode": "single_context",
        "window_summary": {
            "threshold_text_chars": args.window_summary_threshold_chars,
            "source_context_chars": all_context_chars,
        },
        "evidence_profile": profile,
        "rejected_evidence_items": rejected,
    }
    write_jsonl(args.evidence_profiles_output, [profile_row], append=args.evidence_profiles_output.exists())
    existing_profiles[user_id] = profile_row
    log(
        f"user={user_id} evidence_profile single_context done "
        f"evidence_items={len(profile.get('evidence_items') or [])} rejected={len(rejected)}"
    )
    return profile, rejected, request_count



def infer_user_from_evidence_profile(
    user_row: dict[str, Any],
    dimensions: list[dict[str, Any]],
    mapping: dict[str, Any],
    args: argparse.Namespace,
    api_key: str,
    existing_profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    validate_temporal_split_user_row(user_row, args)
    reviews = user_row.get("reviews") or []
    if not isinstance(reviews, list) or not reviews:
        return {
            "user_id": user_row.get("user_id"),
            "status": "skipped_no_reviews",
            "inferred_attributes": [],
            "rejected_attributes": [],
        }
    corpus_stats = review_corpus_stats(reviews)
    max_reviews = effective_max_reviews_for_user(reviews, corpus_stats, args)
    review_context = build_review_context(
        reviews,
        max_reviews=max_reviews,
        max_review_text_chars=args.max_review_text_chars,
        max_total_chars=args.max_review_context_chars,
        include_textless=False,
        selection_strategy=args.context_selection_strategy,
    )
    log(
        f"user={user_row.get('user_id')} selected review context "
        f"rows={len(review_context)} max_reviews={max_reviews} "
        f"strategy={args.context_selection_strategy}"
    )
    evidence_profile, rejected_evidence, profile_request_count = build_or_load_evidence_profile(
        user_row,
        reviews,
        review_context,
        corpus_stats,
        mapping,
        args,
        api_key,
        existing_profiles,
    )
    valid_review_ids = evidence_profile_review_ids(evidence_profile) or {
        row["review_id"] for row in review_context
    }
    request_count = profile_request_count
    routed_categories: list[str] = []
    valid_routes: list[dict[str, Any]] = []
    rejected_routes: list[dict[str, Any]] = []
    routed_dimensions = dimensions
    if args.schema_routing_mode == "category":
        request_count += 1
        always_include_patterns = sorted(parse_csv_filter(args.schema_router_always_include) or [])
        log(
            f"user={user_row.get('user_id')} schema_category_routing "
            f"categories={len({dim['category'] for dim in dimensions})}"
        )
        task = schema_category_routing_payload(
            user_row,
            dimensions,
            evidence_profile,
            always_include_patterns,
        )
        payload = {
            "model": args.model,
            "temperature": args.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SCHEMA_CATEGORY_ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(task, ensure_ascii=False)},
            ],
        }
        response = openai_request(payload, api_key)
        model_output = parse_model_json(response)
        routed_categories, valid_routes, rejected_routes = normalize_schema_category_routes(
            model_output,
            dimensions,
            args.schema_router_min_confidence,
            always_include_patterns,
        )
        routed_dimensions = filter_dimensions_by_categories(dimensions, set(routed_categories))
        if not routed_dimensions:
            routed_dimensions = dimensions
            rejected_routes.append(
                {
                    "item": model_output,
                    "reason": "empty_route_fell_back_to_all_dimensions",
                }
            )
        log(
            f"user={user_row.get('user_id')} schema_category_routing done "
            f"categories={len(routed_categories)} dimensions={len(routed_dimensions)} "
            f"rejected={len(rejected_routes)}"
        )
    all_valid, all_rejected, mapping_request_count = run_schema_mapping_batches(
        user_row,
        routed_dimensions,
        evidence_profile,
        valid_review_ids,
        args,
        api_key,
        stage_name="schema_mapping",
    )
    request_count += mapping_request_count
    recall_pass_dimension_count = 0
    recall_pass_valid_count = 0
    recall_pass_rejected_count = 0
    if args.schema_routing_mode == "recall":
        recall_patterns = sorted(parse_csv_filter(args.recall_pass_categories) or [])
        recall_dimensions = [
            dim
            for dim in dimensions
            if category_matches(str(dim["category"]), recall_patterns)
        ]
        seen_dimensions = {str(attr.get("dimension_id") or "") for attr in all_valid}
        recall_dimensions = [
            dim for dim in recall_dimensions if str(dim["id"]) not in seen_dimensions
        ]
        recall_pass_dimension_count = len(recall_dimensions)
        if recall_dimensions:
            valid, rejected, recall_request_count = run_schema_mapping_batches(
                user_row,
                recall_dimensions,
                evidence_profile,
                valid_review_ids,
                args,
                api_key,
                stage_name="schema_recall_mapping",
                recall_focus=True,
                dimensions_per_call=args.recall_dimensions_per_call,
            )
            request_count += recall_request_count
            recall_pass_valid_count = len(valid)
            recall_pass_rejected_count = len(rejected)
            all_valid = dedupe_inferred_attributes(all_valid + valid)
            all_rejected.extend(rejected)
        log(
            f"user={user_row.get('user_id')} schema_recall_mapping done "
            f"dimensions={recall_pass_dimension_count} valid={recall_pass_valid_count} "
            f"rejected={recall_pass_rejected_count}"
        )
    else:
        all_valid = dedupe_inferred_attributes(all_valid)
    return {
        "source": "amazon_reviews_2023",
        "inference_mode": "evidence_profile",
        "schema_routing_mode": args.schema_routing_mode,
        "schema_path": str(args.schema_path),
        "schema_dimension_count": len(dimensions),
        "schema_mapped_dimension_count": len(routed_dimensions),
        "schema_routed_category_count": len(routed_categories),
        "schema_routed_categories": routed_categories,
        "schema_category_routes": valid_routes,
        "rejected_schema_category_routes": rejected_routes,
        "recall_pass_dimension_count": recall_pass_dimension_count,
        "recall_pass_valid_count": recall_pass_valid_count,
        "recall_pass_rejected_count": recall_pass_rejected_count,
        "evidence_mapping_path": str(args.evidence_mapping_path),
        "user_id": user_row.get("user_id"),
        "review_count": len(reviews),
        "review_corpus_stats": corpus_stats,
        "review_context_count": len(review_context),
        "review_context_chars": serialized_context_chars(review_context),
        "evidence_item_count": len(evidence_profile.get("evidence_items") or []),
        "model": args.model,
        "request_count": request_count,
        "status": "ok",
        "evidence_profile": evidence_profile,
        "rejected_evidence_items": rejected_evidence,
        "inferred_attributes": all_valid,
        "rejected_attributes": all_rejected,
    }


def write_dry_run_prompts(
    history_path: Path,
    dimensions: list[dict[str, Any]],
    mapping: dict[str, Any],
    args: argparse.Namespace,
    product_metadata: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> int:
    rows = []
    for user_index, user_row in enumerate(iter_jsonl_or_gz(history_path), start=1):
        user_row = attach_product_metadata_sidecar(user_row, product_metadata or {})
        if args.max_users and user_index > args.max_users:
            break
        validate_temporal_split_user_row(user_row, args)
        reviews = user_row.get("reviews") or []
        corpus_stats = review_corpus_stats(reviews) if isinstance(reviews, list) else {}
        max_reviews = (
            effective_max_reviews_for_user(reviews, corpus_stats, args)
            if isinstance(reviews, list)
            else args.max_reviews_per_user
        )
        review_context = build_review_context(
            reviews,
            max_reviews=max_reviews,
            max_review_text_chars=args.max_review_text_chars,
            max_total_chars=args.max_review_context_chars,
            include_textless=False,
            selection_strategy=args.context_selection_strategy,
        )
        rows.append(
            {
                "user_id": user_row.get("user_id"),
                "stage": "evidence_profile",
                "system_prompt": EVIDENCE_PROFILE_SYSTEM_PROMPT,
                "user_payload": evidence_profile_payload(
                    user_row,
                    review_context,
                    mapping,
                    corpus_stats,
                    target_evidence_items=args.max_evidence_items,
                ),
            }
        )
        placeholder_profile = {
            "user_id": user_row.get("user_id"),
            "overview": "DRY RUN PLACEHOLDER: schema-mapping prompts require a model-created evidence profile.",
            "structured_memory": {},
            "evidence_items": [],
        }
        if args.schema_routing_mode == "category":
            always_include_patterns = sorted(parse_csv_filter(args.schema_router_always_include) or [])
            rows.append(
                {
                    "user_id": user_row.get("user_id"),
                    "stage": "schema_category_routing",
                    "system_prompt": SCHEMA_CATEGORY_ROUTER_SYSTEM_PROMPT,
                    "user_payload": schema_category_routing_payload(
                        user_row,
                        dimensions,
                        placeholder_profile,
                        always_include_patterns,
                    ),
                    "dry_run_note": (
                        "Schema mapping prompts below use all selected dimensions because "
                        "dry-run does not call the router to determine routed categories."
                    ),
                }
            )
        for batch_index, dimension_batch in enumerate(
            batched(dimensions, args.dimensions_per_call), start=1
        ):
            rows.append(
                {
                    "user_id": user_row.get("user_id"),
                    "stage": "schema_mapping",
                    "batch_index": batch_index,
                    "system_prompt": SCHEMA_MAPPING_SYSTEM_PROMPT,
                    "user_payload": schema_mapping_payload(
                        user_row,
                        dimension_batch,
                        placeholder_profile,
                    ),
                }
            )
        if args.schema_routing_mode == "recall":
            recall_patterns = sorted(parse_csv_filter(args.recall_pass_categories) or [])
            recall_dimensions = [
                dim
                for dim in dimensions
                if category_matches(str(dim["category"]), recall_patterns)
            ]
            for batch_index, dimension_batch in enumerate(
                batched(recall_dimensions, args.recall_dimensions_per_call), start=1
            ):
                rows.append(
                    {
                        "user_id": user_row.get("user_id"),
                        "stage": "schema_recall_mapping",
                        "batch_index": batch_index,
                        "system_prompt": SCHEMA_MAPPING_SYSTEM_PROMPT,
                        "user_payload": schema_mapping_payload(
                            user_row,
                            dimension_batch,
                            placeholder_profile,
                            recall_focus=True,
                        ),
                    }
                )
    return write_jsonl(args.dry_run_prompts_path, rows)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-histories",
        type=Path,
        required=True,
        help="JSONL or JSONL.GZ with user_id and reviews list.",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Persona schema path. Default: {DEFAULT_SCHEMA_PATH}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output JSONL path. Default: {DEFAULT_OUTPUT_PATH}",
    )
    parser.add_argument(
        "--yaml-output",
        type=Path,
        default=None,
        help="Optional YAML copy of the final inference JSONL output.",
    )
    parser.add_argument(
        "--product-metadata-sidecar",
        type=Path,
        default=None,
        help=(
            "Optional compact product metadata JSONL from "
            "modal_amazon_user_index.py::export_history_metadata. "
            "Loaded in memory and attached to reviews before prompt construction."
        ),
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--evidence-mapping-path",
        type=Path,
        default=DEFAULT_EVIDENCE_MAPPING_PATH,
        help=f"Broad Amazon-review evidence mapping config. Default: {DEFAULT_EVIDENCE_MAPPING_PATH}",
    )
    parser.add_argument(
        "--evidence-profiles-output",
        type=Path,
        default=DEFAULT_EVIDENCE_PROFILE_PATH,
        help=(
            "Reusable review-memory JSONL written before schema mapping. "
            f"Default: {DEFAULT_EVIDENCE_PROFILE_PATH}"
        ),
    )
    parser.add_argument(
        "--review-memory-output",
        dest="evidence_profiles_output",
        type=Path,
        help=(
            "Alias for --evidence-profiles-output. Stores/reuses compact review "
            "summaries so schema extraction can be rerun without recompressing reviews."
        ),
    )
    parser.add_argument(
        "--overwrite-profiles",
        action="store_true",
        help="Regenerate compact review memory instead of reusing existing profile rows.",
    )
    parser.add_argument(
        "--no-amazon-default-schema-filter",
        action="store_true",
        help="Keep all selected dimensions instead of filtering to Amazon-supported schema categories.",
    )
    parser.add_argument("--max-users", type=int, default=0, help="0 means all users.")
    parser.add_argument("--max-reviews-per-user", type=int, default=80)
    parser.add_argument(
        "--power-user-min-reviews",
        type=int,
        default=1000,
        help="Users at or above this construction-row count can use the larger power-user review cap.",
    )
    parser.add_argument(
        "--power-user-min-text-chars",
        type=int,
        default=250_000,
        help="Users at or above this construction text size can use the larger power-user review cap.",
    )
    parser.add_argument(
        "--power-user-max-reviews",
        type=int,
        default=200,
        help="Adaptive max selected text reviews for power users.",
    )
    parser.add_argument(
        "--no-adaptive-power-review-cap",
        action="store_true",
        help="Disable adaptive power-user review caps and always use --max-reviews-per-user.",
    )
    parser.add_argument(
        "--context-selection-strategy",
        choices=("temporal", "category_temporal", "informative_category_temporal"),
        default="category_temporal",
        help="How to select a bounded review subset before evidence-profile compression.",
    )
    parser.add_argument("--max-review-text-chars", type=int, default=500)
    parser.add_argument("--max-review-context-chars", type=int, default=100_000)
    parser.add_argument(
        "--window-summary-threshold-chars",
        type=int,
        default=40_000,
        help=(
            "Summarize construction reviews in temporal "
            "windows when total construction review text exceeds this many characters. "
            "Use 0 to disable windowing."
        ),
    )
    parser.add_argument(
        "--window-summary-max-chars",
        type=int,
        default=40_000,
        help="Approximate max serialized review-context characters per temporal summary window.",
    )
    parser.add_argument(
        "--window-summary-max-rows",
        type=int,
        default=80,
        help="Max review/rating rows per temporal summary window.",
    )
    parser.add_argument(
        "--max-evidence-items",
        type=int,
        default=120,
        help="Max compact evidence items retained in reusable review memory.",
    )
    parser.add_argument(
        "--max-window-evidence-items",
        type=int,
        default=100,
        help="Backward-compatible alias used when --max-evidence-items is 0.",
    )
    parser.add_argument(
        "--schema-routing-mode",
        choices=("none", "category", "recall"),
        default="none",
        help=(
            "Extraction path. 'none' preserves direct full-schema mapping; "
            "'category' adds a schema-category router before mapping; "
            "'recall' runs full-schema mapping plus an extra recall-focused "
            "second pass over high-value categories."
        ),
    )
    parser.add_argument(
        "--schema-router-min-confidence",
        type=float,
        default=0.25,
        help="Minimum confidence for model-selected schema categories in category routing mode.",
    )
    parser.add_argument(
        "--schema-router-always-include",
        default=(
            "Interests:*,Behavior:*,Values & Motivation,Risk & Decision,"
            "Linguistic:*,Expertise:*,Personality:*,Health:*,"
            "Worldview: Beliefs,Demographic: Family,Demographic: Life Events,"
            "Social Identity, Relationships & Community"
        ),
        help=(
            "Comma-separated schema category patterns always included in category "
            "routing mode to reduce router recall loss."
        ),
    )
    parser.add_argument(
        "--recall-pass-categories",
        default=(
            "Personality:*,Values & Motivation,Risk & Decision,Behavior:*,"
            "Expertise:*,Health:*,Worldview: Beliefs,Demographic: Family,"
            "Demographic: Life Events,Social Identity, Relationships & Community"
        ),
        help=(
            "Comma-separated category patterns for the recall-focused second pass "
            "when --schema-routing-mode recall is used."
        ),
    )
    parser.add_argument(
        "--recall-dimensions-per-call",
        type=int,
        default=120,
        help="Dimension batch size for the recall-focused second pass.",
    )
    parser.add_argument("--dimensions-per-call", type=int, default=200)
    parser.add_argument(
        "--dimension-categories",
        default="",
        help="Optional comma-separated schema categories to infer.",
    )
    parser.add_argument(
        "--dimension-ids",
        default="",
        help="Optional comma-separated schema dimension IDs to infer.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output instead of appending/resuming.",
    )
    parser.add_argument(
        "--allow-unsplit-histories",
        action="store_true",
        help=(
            "Allow inference from legacy histories without temporal_split and "
            "validation_reviews. Intended only for debugging or ablations."
        ),
    )
    parser.add_argument(
        "--dry-run-prompts-path",
        type=Path,
        default=BASE_DIR
        / "raw"
        / "amazon_reviews_2023"
        / "persona_dimension_inference"
        / "dry_run_prompts.jsonl",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write prompts and exit without calling the OpenAI API.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    dimensions = load_schema(args.schema_path)
    mapping = load_evidence_mapping(args.evidence_mapping_path)
    product_metadata = load_product_metadata_sidecar(args.product_metadata_sidecar)
    if product_metadata:
        log(
            f"Loaded {len(product_metadata):,} product metadata lookup keys "
            f"from {args.product_metadata_sidecar}"
        )
    explicit_dimension_filter = bool(args.dimension_categories or args.dimension_ids)
    dimensions = filter_dimensions(
        dimensions,
        category_filter=parse_csv_filter(args.dimension_categories),
        id_filter=parse_csv_filter(args.dimension_ids),
    )
    if (
        not args.no_amazon_default_schema_filter
        and not explicit_dimension_filter
    ):
        before_count = len(dimensions)
        dimensions = filter_amazon_supported_dimensions(dimensions, mapping)
        log(
            "Applied Amazon-supported schema filter: "
            f"{before_count:,} -> {len(dimensions):,} dimensions"
        )
    if not dimensions:
        raise ValueError("No dimensions selected after filtering.")
    log(f"Selected {len(dimensions):,} schema dimensions")

    if args.dry_run:
        count = write_dry_run_prompts(
            args.user_histories,
            dimensions,
            mapping,
            args,
            product_metadata,
        )
        log(f"Wrote {count:,} dry-run prompts: {args.dry_run_prompts_path}")
        return 0

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required unless --dry-run is used.")

    done = set() if args.overwrite else completed_user_ids(args.output)
    existing_profiles: dict[str, dict[str, Any]] = {}
    if args.overwrite_profiles and args.evidence_profiles_output.exists():
        args.evidence_profiles_output.unlink()
    existing_profiles = load_completed_rows_by_user(args.evidence_profiles_output)
    append = not args.overwrite
    processed = 0
    written = 0
    for user_row in iter_jsonl_or_gz(args.user_histories):
        user_row = attach_product_metadata_sidecar(user_row, product_metadata)
        user_id = str(user_row.get("user_id", ""))
        if user_id in done:
            continue
        if args.max_users and processed >= args.max_users:
            break
        result = infer_user_from_evidence_profile(
            user_row,
            dimensions,
            mapping,
            args,
            api_key,
            existing_profiles,
        )
        write_jsonl(args.output, [result], append=append or written > 0)
        append = True
        processed += 1
        written += 1
        log(
            f"{user_id}: inferred {len(result.get('inferred_attributes', []))} "
            f"attributes across {result.get('request_count', 0)} requests"
        )
    log(f"Wrote {written:,} user inference rows: {args.output}")
    if args.yaml_output:
        yaml_rows = write_inference_yaml(args.output, args.yaml_output)
        log(f"Wrote {yaml_rows:,} user inference rows as YAML: {args.yaml_output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(130)
