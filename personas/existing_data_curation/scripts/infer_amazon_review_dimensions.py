#!/usr/bin/env python3
"""Infer the 1,339 persona schema dimensions from Amazon review histories.

The script is intentionally conservative: it asks the model to return only
schema attributes that are directly supported by review text, ratings, dates,
or reviewed categories. Unknown or weakly-supported dimensions are omitted.

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
REPO_ROOT = BASE_DIR.parent.parent
DEFAULT_SCHEMA_PATH = REPO_ROOT / "personas" / "dimensions+new.json"
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


SYSTEM_PROMPT = """You infer persona schema attributes from Amazon review histories.

Core rule: return an attribute only when the evidence is directly supported by the supplied reviews. If the reviews do not support a schema dimension, omit it.

Evidence standards:
- Use explicit statements from the reviewer when available.
- Product category, product title, rating, repeat purchases, and review wording can support interests, preferences, habits, skills, expertise, and shopping behavior.
- Do not infer protected or sensitive demographics, health status, family status, socioeconomic status, or identity from stereotypes or product purchases alone. Infer those only when the reviewer explicitly states them or the evidence is unusually direct.
- Do not infer occupation, age, gender, region, politics, religion, or medical conditions unless directly stated.
- Prefer lower confidence when evidence is suggestive but still grounded.
- If a schema dimension has enumerated values, choose only one of the provided values. If no listed value fits, omit the dimension.

Return compact JSON only."""


EVIDENCE_PROFILE_SYSTEM_PROMPT = """You create compact evidence profiles from Amazon review histories.

Core rule: record only evidence directly supported by review text, product title, rating, category, or repeated review behavior. Do not make persona claims from stereotypes.

Use the provided broad evidence categories as the organizing guide. Capture explicit self-statements separately from behavioral signals. Do not infer protected or sensitive demographics, health status, family status, socioeconomic status, occupation, region, politics, or religion unless the reviewer explicitly states it in the evidence.

Return compact JSON only."""


SCHEMA_MAPPING_SYSTEM_PROMPT = """You map compact Amazon-review evidence profiles to persona schema attributes.

Core rule: return an attribute only when the compact evidence profile directly supports it. If the evidence profile does not support a schema dimension, omit it.

Evidence standards:
- Prefer explicit self-statements and repeated behavioral evidence.
- For each inferred dimension, choose exactly one allowed value from that dimension.
- Every inferred dimension must cite profile evidence item ids and original review ids.
- Do not infer sensitive demographics, health, family, socioeconomic, political, religious, or identity attributes unless the profile contains explicit quoted self-statements.
- Use confidence between 0 and 1. Use >=0.8 only for explicit or repeated evidence.

Return compact JSON only."""


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
                "values in personas/dimensions+new.json before export."
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
                "review_id": f"r{idx:06d}",
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


def select_context_rows(rows: list[dict[str, Any]], max_reviews: int) -> list[dict[str, Any]]:
    if max_reviews <= 0 or len(rows) <= max_reviews:
        return rows
    if max_reviews == 1:
        return [rows[-1]]
    last = len(rows) - 1
    indices = sorted({round(i * last / (max_reviews - 1)) for i in range(max_reviews)})
    return [rows[idx] for idx in indices]


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
) -> list[dict[str, Any]]:
    rows = select_context_rows(
        context_rows_for_reviews(reviews, max_review_text_chars, include_textless=include_textless),
        max_reviews,
    )
    context = []
    total_chars = 0
    for row in rows:
        total_chars += len(json.dumps(row, ensure_ascii=False))
        if max_total_chars and total_chars > max_total_chars:
            break
        context.append(row)
    return context


def prompt_payload(
    user_row: dict[str, Any],
    dimension_batch: list[dict[str, Any]],
    review_context: list[dict[str, Any]],
    corpus_stats: dict[str, Any] | None = None,
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
    return {
        "task": "infer_supported_persona_schema_dimensions_from_amazon_reviews",
        "user_id": user_row.get("user_id"),
        "instructions": [
            "Return only dimensions with direct support from the review evidence.",
            "Omit unknown, weak, stereotyped, or unsupported dimensions.",
            "Use category_review_summary as aggregate behavioral context; evidence quotes must still come from review_evidence.",
            "Use construction_corpus_summary for aggregate rating-only behavior; do not cite rating-only aggregate stats as direct evidence quotes.",
            "Use product name/category only to interpret the reviewed item; do not infer sensitive attributes from product stereotypes.",
            "For each inferred dimension, choose exactly one allowed value from that dimension.",
            "Every inferred dimension must include at least one review_id and a short evidence quote copied from that review.",
            "Use confidence between 0 and 1. Use >=0.8 only for explicit or repeated evidence.",
        ],
        "output_json_schema": {
            "inferred_attributes": [
                {
                    "dimension_id": "schema dimension id",
                    "value": "one allowed value for that dimension",
                    "confidence": "number from 0 to 1",
                    "evidence_review_ids": ["review ids used as support"],
                    "evidence_quotes": ["short exact quotes from review text/title"],
                    "reasoning": "brief grounded rationale",
                }
            ]
        },
        "schema_dimensions": dimensions,
        "category_review_summary": user_row.get("category_review_stats", {}),
        "construction_corpus_summary": corpus_stats or user_row.get("review_corpus_stats", {}),
        "review_evidence": review_context,
    }


def evidence_profile_payload(
    user_row: dict[str, Any],
    review_context: list[dict[str, Any]],
    mapping: dict[str, Any],
    corpus_stats: dict[str, Any] | None = None,
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
            "Keep claims short and grounded.",
            "Each evidence item must cite at least one review_id and include a short exact quote from that review when text/title supports the claim.",
            "Use explicit_self_statement for occupation, family, health, location, politics, religion, or other sensitive/personal claims only when directly stated.",
            "Omit unsupported categories instead of guessing.",
        ],
        "broad_evidence_categories": mapping.get("evidence_categories", []),
        "category_review_summary": user_row.get("category_review_stats", {}),
        "construction_corpus_summary": corpus_stats or user_row.get("review_corpus_stats", {}),
        "output_json_schema": {
            "evidence_profile": {
                "user_id": "source user id",
                "overview": "brief grounded summary, not a persona biography",
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
                        "evidence_type": "explicit_self_statement | repeated_behavior | product_interest | preference | expertise_signal | communication_style",
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
    return {
        "task": "map_compact_amazon_review_evidence_profile_to_schema_dimensions",
        "user_id": user_row.get("user_id"),
        "instructions": [
            "Return only dimensions directly supported by the compact evidence profile.",
            "Omit unknown, weak, stereotyped, or unsupported dimensions.",
            "For each inferred dimension, choose exactly one allowed value from that dimension.",
            "Every inferred dimension must include at least one evidence_item_id and at least one original review_id.",
            "Use confidence between 0 and 1. Use >=0.8 only for explicit or repeated evidence.",
        ],
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
    normalized = {
        "user_id": user_id,
        "overview": compact_text(profile.get("overview"), 1200),
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
                            evidence_profile_payload(user_row, window_context, mapping, corpus_stats),
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
            "evidence_items": (
                profile_items[: args.max_window_evidence_items]
                if args.max_window_evidence_items
                else profile_items
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
                    evidence_profile_payload(user_row, review_context, mapping, corpus_stats),
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


def infer_user(
    user_row: dict[str, Any],
    dimensions: list[dict[str, Any]],
    args: argparse.Namespace,
    api_key: str,
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
    review_context = build_review_context(
        reviews,
        max_reviews=args.max_reviews_per_user,
        max_review_text_chars=args.max_review_text_chars,
        max_total_chars=args.max_review_context_chars,
    )
    valid_review_ids = {row["review_id"] for row in review_context}
    all_valid = []
    all_rejected = []
    request_count = 0
    dimension_batches = list(batched(dimensions, args.dimensions_per_call))
    for batch_index, dimension_batch in enumerate(dimension_batches, start=1):
        request_count += 1
        log(
            f"user={user_row.get('user_id')} raw_schema batch "
            f"{batch_index}/{len(dimension_batches)} dimensions={len(dimension_batch)}"
        )
        task = prompt_payload(user_row, dimension_batch, review_context, corpus_stats)
        payload = {
            "model": args.model,
            "temperature": args.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(task, ensure_ascii=False)},
            ],
        }
        response = openai_request(payload, api_key)
        model_output = parse_model_json(response)
        valid, rejected = validate_inferences(model_output, dimension_batch, valid_review_ids)
        all_valid.extend(valid)
        all_rejected.extend(rejected)
        log(
            f"user={user_row.get('user_id')} raw_schema batch "
            f"{batch_index}/{len(dimension_batches)} done valid={len(valid)} rejected={len(rejected)}"
        )
    return {
        "source": "amazon_reviews_2023",
        "schema_path": str(args.schema_path),
        "schema_dimension_count": len(dimensions),
        "user_id": user_row.get("user_id"),
        "review_count": len(reviews),
        "review_corpus_stats": corpus_stats,
        "review_context_count": len(review_context),
        "review_context_chars": serialized_context_chars(review_context),
        "model": args.model,
        "request_count": request_count,
        "status": "ok",
        "inferred_attributes": all_valid,
        "rejected_attributes": all_rejected,
    }


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
    review_context = build_review_context(
        reviews,
        max_reviews=args.max_reviews_per_user,
        max_review_text_chars=args.max_review_text_chars,
        max_total_chars=args.max_review_context_chars,
        include_textless=False,
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
    all_valid = []
    all_rejected = []
    request_count = profile_request_count
    dimension_batches = list(batched(dimensions, args.dimensions_per_call))
    for batch_index, dimension_batch in enumerate(dimension_batches, start=1):
        request_count += 1
        log(
            f"user={user_row.get('user_id')} schema_mapping batch "
            f"{batch_index}/{len(dimension_batches)} dimensions={len(dimension_batch)} "
            f"evidence_items={len(evidence_profile.get('evidence_items') or [])}"
        )
        task = schema_mapping_payload(user_row, dimension_batch, evidence_profile)
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
            f"user={user_row.get('user_id')} schema_mapping batch "
            f"{batch_index}/{len(dimension_batches)} done valid={len(valid)} rejected={len(rejected)}"
        )
    return {
        "source": "amazon_reviews_2023",
        "inference_mode": "evidence_profile",
        "schema_path": str(args.schema_path),
        "schema_dimension_count": len(dimensions),
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
    mapping: dict[str, Any] | None,
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
        include_textless = args.inference_mode != "evidence_profile"
        review_context = build_review_context(
            reviews,
            max_reviews=args.max_reviews_per_user,
            max_review_text_chars=args.max_review_text_chars,
            max_total_chars=args.max_review_context_chars,
            include_textless=include_textless,
        )
        if args.inference_mode == "evidence_profile":
            if mapping is None:
                raise ValueError("Evidence mapping is required for evidence_profile dry run.")
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
                    ),
                }
            )
            placeholder_profile = {
                "user_id": user_row.get("user_id"),
                "overview": "DRY RUN PLACEHOLDER: schema-mapping prompts require a model-created evidence profile.",
                "evidence_items": [],
            }
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
            continue
        for batch_index, dimension_batch in enumerate(
            batched(dimensions, args.dimensions_per_call), start=1
        ):
            rows.append(
                {
                    "user_id": user_row.get("user_id"),
                    "batch_index": batch_index,
                    "system_prompt": SYSTEM_PROMPT,
                    "user_payload": prompt_payload(
                        user_row,
                        dimension_batch,
                        review_context,
                        corpus_stats,
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
        "--inference-mode",
        choices=("raw_reviews", "evidence_profile"),
        default="raw_reviews",
        help="raw_reviews preserves the original pipeline; evidence_profile extracts a compact profile first.",
    )
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
        help="In evidence_profile mode, keep all selected dimensions instead of filtering to Amazon-supported schema categories.",
    )
    parser.add_argument("--max-users", type=int, default=0, help="0 means all users.")
    parser.add_argument("--max-reviews-per-user", type=int, default=80)
    parser.add_argument("--max-review-text-chars", type=int, default=900)
    parser.add_argument("--max-review-context-chars", type=int, default=70_000)
    parser.add_argument(
        "--window-summary-threshold-chars",
        type=int,
        default=120_000,
        help=(
            "In evidence_profile mode, summarize construction reviews in temporal "
            "windows when total construction review text exceeds this many characters. "
            "Use 0 to disable windowing."
        ),
    )
    parser.add_argument(
        "--window-summary-max-chars",
        type=int,
        default=60_000,
        help="Approximate max serialized review-context characters per temporal summary window.",
    )
    parser.add_argument(
        "--window-summary-max-rows",
        type=int,
        default=200,
        help="Max review/rating rows per temporal summary window.",
    )
    parser.add_argument(
        "--max-window-evidence-items",
        type=int,
        default=100,
        help="Max evidence items retained after concatenating window evidence profiles.",
    )
    parser.add_argument("--dimensions-per-call", type=int, default=40)
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
    product_metadata = load_product_metadata_sidecar(args.product_metadata_sidecar)
    if product_metadata:
        log(
            f"Loaded {len(product_metadata):,} product metadata lookup keys "
            f"from {args.product_metadata_sidecar}"
        )
    mapping = None
    explicit_dimension_filter = bool(args.dimension_categories or args.dimension_ids)
    if args.inference_mode == "evidence_profile":
        mapping = load_evidence_mapping(args.evidence_mapping_path)
    dimensions = filter_dimensions(
        dimensions,
        category_filter=parse_csv_filter(args.dimension_categories),
        id_filter=parse_csv_filter(args.dimension_ids),
    )
    if (
        args.inference_mode == "evidence_profile"
        and mapping is not None
        and not args.no_amazon_default_schema_filter
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
    if args.inference_mode == "evidence_profile":
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
        if args.inference_mode == "evidence_profile":
            if mapping is None:
                raise ValueError("Evidence mapping is required for evidence_profile mode.")
            result = infer_user_from_evidence_profile(
                user_row,
                dimensions,
                mapping,
                args,
                api_key,
                existing_profiles,
            )
        else:
            result = infer_user(user_row, dimensions, args, api_key)
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
