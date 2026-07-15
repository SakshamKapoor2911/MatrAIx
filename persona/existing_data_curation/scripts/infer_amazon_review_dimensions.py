#!/usr/bin/env python3
"""Small Amazon-review helpers used by collaborator package builders.

The full Amazon inference pipeline lives outside this repo. These functions keep
packaging self-contained: they load normalized user-history JSONL, attach optional
product metadata sidecars, filter the persona schema to dimensions with
Amazon-review evidence support, and normalize review timestamps.
"""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_EVIDENCE_MAPPING_PATH = BASE_DIR / "amazon_review_evidence_mapping.json"


def iter_jsonl_or_gz(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc


def load_product_metadata_sidecar(
    path: Path | None,
) -> dict[tuple[str, str], dict[str, Any]]:
    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Product metadata sidecar not found: {path}")
    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    for row in iter_jsonl_or_gz(path):
        parent_asin = row.get("parent_asin")
        source_category = row.get("source_category")
        if parent_asin and source_category:
            key = (str(parent_asin), str(source_category))
            metadata[key] = row
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
            sidecar_row = metadata.get((str(parent_asin), category)) or metadata.get(
                (str(parent_asin), "")
            )
            if sidecar_row:
                review["product_metadata"] = sidecar_row
    return user_row


def load_evidence_mapping(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        mapping = json.load(fh)
    categories = mapping.get("evidence_categories", [])
    if not isinstance(categories, list) or not categories:
        raise ValueError(f"No evidence_categories list found in mapping: {path}")
    return mapping


def category_matches(category: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        pattern = str(pattern)
        if pattern.endswith("*") and category.startswith(pattern[:-1]):
            return True
        if category == pattern:
            return True
    return False


def amazon_supported_schema_categories(mapping: dict[str, Any]) -> set[str]:
    supported: set[str] = set()
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
