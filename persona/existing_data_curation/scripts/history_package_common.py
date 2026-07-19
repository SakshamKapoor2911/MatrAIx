#!/usr/bin/env python3
"""Source-neutral helpers for building history-based collaborator packages.

Shared by the Amazon and Stack Overflow package builders: selecting items
spread across time, rendering CV-fold sections, char-budget truncation that
keeps a minimum number of visible folds, and evidence-mapping dimension
filtering. Nothing here knows about reviews or posts specifically; builders
render their own items to text before calling into this module.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from persona.existing_data_curation.wiki_collab.core import load_jsonl

FOLD_TEXT_SEPARATOR = "\n\n"
FOLD_TRUNCATION_MARKER = "[fold truncated]"


def require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def compact_text(value: Any, max_chars: int) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    if max_chars <= 16:
        return text[:max_chars]
    return text[: max_chars - 15].rstrip() + " ... [truncated]"


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


def sorted_by_time(
    items: Iterable[dict[str, Any]],
    timestamp_of: Callable[[dict[str, Any]], int | None],
) -> list[dict[str, Any]]:
    indexed = [(idx, dict(item)) for idx, item in enumerate(items)]
    indexed.sort(
        key=lambda pair: (
            timestamp_of(pair[1]) is None,
            timestamp_of(pair[1]) or 0,
            pair[0],
        )
    )
    return [item for _idx, item in indexed]


def spread_across_time(items: list[Any], max_items: int) -> list[Any]:
    if len(items) <= max_items:
        return items
    if max_items == 1:
        return [items[len(items) // 2]]
    last = len(items) - 1
    chosen_indexes = [round(pos * last / (max_items - 1)) for pos in range(max_items)]
    return [items[idx] for idx in chosen_indexes]


def render_fold(fold_id: int, total_folds: int, rendered_item_texts: list[str]) -> str:
    lines = [f"=== Fold {fold_id}/{total_folds} ==="]
    lines.extend(rendered_item_texts)
    return "\n\n".join(lines)


def build_cv_fold_texts(
    rendered_items: list[tuple[str, str]],
    effective_cv_folds: int,
    *,
    id_field: str,
) -> list[dict[str, Any]]:
    """Round-robin (item_id, rendered_text) pairs into fold sections."""
    items_by_fold: list[list[tuple[str, str]]] = [[] for _ in range(effective_cv_folds)]
    for idx, rendered_item in enumerate(rendered_items):
        items_by_fold[idx % effective_cv_folds].append(rendered_item)

    fold_texts = []
    for fold_idx, fold_items in enumerate(items_by_fold, start=1):
        fold_texts.append(
            {
                "fold_id": fold_idx,
                id_field: [item_id for item_id, _ in fold_items],
                "profile_text": render_fold(
                    fold_idx,
                    effective_cv_folds,
                    [text for _item_id, text in fold_items],
                ),
            }
        )
    return fold_texts


def join_fold_texts(fold_texts: list[dict[str, Any]]) -> str:
    return FOLD_TEXT_SEPARATOR.join(
        str(fold["profile_text"]) for fold in fold_texts if fold["profile_text"]
    )


def _fold_heading(fold: dict[str, Any], effective_cv_folds: int) -> str:
    text = str(fold.get("profile_text") or "")
    if text:
        return text.splitlines()[0]
    return f"=== Fold {fold.get('fold_id', '?')}/{effective_cv_folds} ==="


def _minimum_fold_text(fold: dict[str, Any], effective_cv_folds: int) -> str:
    return f"{_fold_heading(fold, effective_cv_folds)}\n{FOLD_TRUNCATION_MARKER}"


def _minimum_join_chars(
    fold_texts: list[dict[str, Any]],
    *,
    effective_cv_folds: int,
) -> int:
    if not fold_texts:
        return 0
    return sum(
        len(_minimum_fold_text(fold, effective_cv_folds)) for fold in fold_texts
    ) + len(FOLD_TEXT_SEPARATOR) * (len(fold_texts) - 1)


def _truncate_fold_text(
    text: str,
    *,
    minimum_text: str,
    max_chars: int,
) -> str:
    if len(text) <= max_chars:
        return text

    marker = "\n" + FOLD_TRUNCATION_MARKER
    prefix_chars = max_chars - len(marker)
    heading = minimum_text.splitlines()[0]
    if prefix_chars <= len(heading):
        return minimum_text

    prefix = text[:prefix_chars].rstrip()
    if len(prefix) < len(heading) or not prefix.startswith(heading):
        prefix = heading
    return prefix + marker


def limit_fold_texts_for_profile(
    fold_texts: list[dict[str, Any]],
    max_profile_text_chars: int,
    *,
    effective_min_support: int,
) -> list[dict[str, Any]]:
    if len(join_fold_texts(fold_texts)) <= max_profile_text_chars:
        return fold_texts

    effective_cv_folds = len(fold_texts)
    min_visible_folds = min(effective_min_support, effective_cv_folds)
    min_required_chars = _minimum_join_chars(
        fold_texts[:min_visible_folds],
        effective_cv_folds=effective_cv_folds,
    )
    if max_profile_text_chars < min_required_chars:
        raise ValueError(
            "max_profile_text_chars is too small to include at least "
            f"{min_visible_folds} fold "
            f"sections: got {max_profile_text_chars}, need at least "
            f"{min_required_chars}"
        )

    limited_folds: list[dict[str, Any]] = []
    used_chars = 0
    visible_folds = 0

    for idx, fold in enumerate(fold_texts):
        limited_fold = dict(fold)
        separator_chars = len(FOLD_TEXT_SEPARATOR) if visible_folds else 0
        remaining_chars = max_profile_text_chars - used_chars - separator_chars
        required_future_folds = max(0, min_visible_folds - (visible_folds + 1))
        future_folds = fold_texts[idx + 1 : idx + 1 + required_future_folds]
        future_reserve_chars = _minimum_join_chars(
            future_folds,
            effective_cv_folds=effective_cv_folds,
        )
        if future_folds:
            future_reserve_chars += len(FOLD_TEXT_SEPARATOR)

        available_chars = remaining_chars - future_reserve_chars
        minimum_text = _minimum_fold_text(fold, effective_cv_folds)
        if available_chars < len(minimum_text):
            limited_fold["profile_text"] = ""
            limited_folds.append(limited_fold)
            continue

        limited_fold["profile_text"] = _truncate_fold_text(
            str(fold["profile_text"]),
            minimum_text=minimum_text,
            max_chars=available_chars,
        )
        used_chars += separator_chars + len(limited_fold["profile_text"])
        visible_folds += 1
        limited_folds.append(limited_fold)

    return limited_folds


def load_history_range(
    path: Path, range_start: int, range_end: int
) -> list[tuple[int, dict[str, Any]]]:
    expected_count = range_end - range_start
    rows: list[tuple[int, dict[str, Any]]] = []
    for offset, row in enumerate(load_jsonl(path)):
        if offset < range_start:
            continue
        if offset >= range_end:
            break
        rows.append((offset, row))
    if len(rows) != expected_count:
        raise ValueError(
            f"range [{range_start}, {range_end}) expected {expected_count} rows, got "
            f"{len(rows)}"
        )
    return rows


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


def supported_schema_categories(mapping: dict[str, Any]) -> set[str]:
    supported: set[str] = set()
    for evidence_category in mapping.get("evidence_categories", []):
        for category in evidence_category.get("schema_categories", []):
            supported.add(str(category))
    return supported


def filter_supported_dimensions(
    dimensions: list[dict[str, Any]],
    mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    supported = supported_schema_categories(mapping)
    skip_by_default = set(mapping.get("skip_by_default_schema_categories", []))
    filtered = []
    for dim in dimensions:
        category = str(dim["category"])
        if category_matches(category, skip_by_default):
            continue
        if category_matches(category, supported):
            filtered.append(dim)
    return filtered
