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
import sys
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


def select_reviews(reviews: list[dict[str, Any]], max_reviews: int) -> list[dict[str, Any]]:
    reviews = sorted(reviews, key=lambda row: normalize_timestamp(row.get("timestamp")) or 0)
    if max_reviews <= 0 or len(reviews) <= max_reviews:
        return reviews
    if max_reviews == 1:
        return [reviews[-1]]
    last = len(reviews) - 1
    indices = sorted({round(i * last / (max_reviews - 1)) for i in range(max_reviews)})
    return [reviews[idx] for idx in indices]


def build_review_context(
    reviews: list[dict[str, Any]],
    max_reviews: int,
    max_review_text_chars: int,
    max_total_chars: int,
) -> list[dict[str, Any]]:
    context = []
    total_chars = 0
    for idx, review in enumerate(select_reviews(reviews, max_reviews), start=1):
        text = compact_text(review.get("text"), max_review_text_chars)
        title = compact_text(review.get("title"), 180)
        row = {
            "review_id": f"r{idx:04d}",
            "date": timestamp_to_date(review.get("timestamp")),
            "category": review.get("category"),
            "rating": review.get("rating"),
            "title": title,
            "text": text,
            "verified_purchase": review.get("verified_purchase"),
            "helpful_vote": review.get("helpful_vote", review.get("helpful_votes")),
        }
        total_chars += len(json.dumps(row, ensure_ascii=False))
        if max_total_chars and total_chars > max_total_chars:
            break
        context.append(row)
    return context


def prompt_payload(
    user_row: dict[str, Any],
    dimension_batch: list[dict[str, Any]],
    review_context: list[dict[str, Any]],
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
        "review_evidence": review_context,
    }


def evidence_profile_payload(
    user_row: dict[str, Any],
    review_context: list[dict[str, Any]],
    mapping: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task": "build_compact_amazon_review_evidence_profile",
        "user_id": user_row.get("user_id"),
        "instructions": [
            "Summarize only evidence supported by the supplied reviews.",
            "Organize evidence using the broad evidence categories.",
            "Keep claims short and grounded.",
            "Each evidence item must cite at least one review_id and include a short exact quote from that review when text/title supports the claim.",
            "Use explicit_self_statement for occupation, family, health, location, politics, religion, or other sensitive/personal claims only when directly stated.",
            "Omit unsupported categories instead of guessing.",
        ],
        "broad_evidence_categories": mapping.get("evidence_categories", []),
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
                time.sleep(min(60, 2**attempt))
                continue
            raise RuntimeError(f"OpenAI API error {err.code}: {error_body[:1000]}") from err
        except urllib.error.URLError as err:
            if attempt < retries - 1:
                time.sleep(min(60, 2**attempt))
                continue
            raise RuntimeError(f"OpenAI request failed after retries: {err}") from err
    raise RuntimeError("OpenAI request failed after retries")


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
    review_context: list[dict[str, Any]],
    mapping: dict[str, Any],
    args: argparse.Namespace,
    api_key: str,
    existing_profiles: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    user_id = str(user_row.get("user_id", ""))
    if user_id in existing_profiles and not args.overwrite_profiles:
        profile_row = existing_profiles[user_id]
        return profile_row.get("evidence_profile") or {}, profile_row.get("rejected_evidence_items") or [], False
    payload = {
        "model": args.model,
        "temperature": args.temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": EVIDENCE_PROFILE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    evidence_profile_payload(user_row, review_context, mapping),
                    ensure_ascii=False,
                ),
            },
        ],
    }
    response = openai_request(payload, api_key)
    model_output = parse_model_json(response)
    valid_review_ids = {row["review_id"] for row in review_context}
    profile, rejected = normalize_evidence_profile(model_output, user_id, valid_review_ids)
    profile_row = {
        "source": "amazon_reviews_2023",
        "user_id": user_row.get("user_id"),
        "review_count": len(user_row.get("reviews") or []),
        "review_context_count": len(review_context),
        "model": args.model,
        "status": "ok",
        "evidence_profile": profile,
        "rejected_evidence_items": rejected,
    }
    write_jsonl(args.evidence_profiles_output, [profile_row], append=args.evidence_profiles_output.exists())
    existing_profiles[user_id] = profile_row
    return profile, rejected, True


def infer_user(
    user_row: dict[str, Any],
    dimensions: list[dict[str, Any]],
    args: argparse.Namespace,
    api_key: str,
) -> dict[str, Any]:
    reviews = user_row.get("reviews") or []
    if not isinstance(reviews, list) or not reviews:
        return {
            "user_id": user_row.get("user_id"),
            "status": "skipped_no_reviews",
            "inferred_attributes": [],
            "rejected_attributes": [],
        }
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
    for dimension_batch in batched(dimensions, args.dimensions_per_call):
        request_count += 1
        task = prompt_payload(user_row, dimension_batch, review_context)
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
    return {
        "source": "amazon_reviews_2023",
        "schema_path": str(args.schema_path),
        "schema_dimension_count": len(dimensions),
        "user_id": user_row.get("user_id"),
        "review_count": len(reviews),
        "review_context_count": len(review_context),
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
    reviews = user_row.get("reviews") or []
    if not isinstance(reviews, list) or not reviews:
        return {
            "user_id": user_row.get("user_id"),
            "status": "skipped_no_reviews",
            "inferred_attributes": [],
            "rejected_attributes": [],
        }
    review_context = build_review_context(
        reviews,
        max_reviews=args.max_reviews_per_user,
        max_review_text_chars=args.max_review_text_chars,
        max_total_chars=args.max_review_context_chars,
    )
    valid_review_ids = {row["review_id"] for row in review_context}
    evidence_profile, rejected_evidence, profile_created = build_or_load_evidence_profile(
        user_row,
        review_context,
        mapping,
        args,
        api_key,
        existing_profiles,
    )
    all_valid = []
    all_rejected = []
    request_count = 1 if profile_created else 0
    for dimension_batch in batched(dimensions, args.dimensions_per_call):
        request_count += 1
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
    return {
        "source": "amazon_reviews_2023",
        "inference_mode": "evidence_profile",
        "schema_path": str(args.schema_path),
        "schema_dimension_count": len(dimensions),
        "evidence_mapping_path": str(args.evidence_mapping_path),
        "user_id": user_row.get("user_id"),
        "review_count": len(reviews),
        "review_context_count": len(review_context),
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
) -> int:
    rows = []
    for user_index, user_row in enumerate(iter_jsonl_or_gz(history_path), start=1):
        if args.max_users and user_index > args.max_users:
            break
        reviews = user_row.get("reviews") or []
        review_context = build_review_context(
            reviews,
            max_reviews=args.max_reviews_per_user,
            max_review_text_chars=args.max_review_text_chars,
            max_total_chars=args.max_review_context_chars,
        )
        if args.inference_mode == "evidence_profile":
            if mapping is None:
                raise ValueError("Evidence mapping is required for evidence_profile dry run.")
            rows.append(
                {
                    "user_id": user_row.get("user_id"),
                    "stage": "evidence_profile",
                    "system_prompt": EVIDENCE_PROFILE_SYSTEM_PROMPT,
                    "user_payload": evidence_profile_payload(user_row, review_context, mapping),
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
                    "user_payload": prompt_payload(user_row, dimension_batch, review_context),
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
        help=f"Reusable compact profile JSONL. Default: {DEFAULT_EVIDENCE_PROFILE_PATH}",
    )
    parser.add_argument(
        "--overwrite-profiles",
        action="store_true",
        help="Regenerate compact evidence profiles instead of reusing existing profile rows.",
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
        count = write_dry_run_prompts(args.user_histories, dimensions, mapping, args)
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
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(130)
