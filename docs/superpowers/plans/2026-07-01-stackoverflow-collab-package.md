# StackOverflow Collaborator Package Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Stack Overflow posting histories as a third collaborator-package source (alongside wiki and amazon) at full package-pipeline parity: HF exporter → normalized user histories → CV-fold package builder → collab kit support → owner DB for merge identity checks.

**Architecture:** A new shared module `history_package_common.py` receives the source-neutral fold/truncation machinery extracted from the amazon builder; the new SO builder and the amazon builder both import it (amazon's behavior stays byte-identical). The SO vertical mirrors the amazon vertical file-for-file. `collab_kit/solver.py` switches its fold-routing gate from source-string matching to duck-typing on `cv_fold_texts`.

**Tech Stack:** Python 3 stdlib only for everything shipped inside packages; `huggingface_hub` + `pyarrow` used lazily by the exporter only; pytest for tests; bash wrappers.

**Spec:** `docs/superpowers/specs/2026-07-01-stackoverflow-collab-package-design.md` (approved). Read it before starting a task if anything here seems ambiguous.

## Global Constraints

- Work on branch `stackoverflow-collab-package` (based on PR #143's head). The checkout currently lives in the worktree `/tmp/claude-1000/-home-wieeii-MatrAIx/d5e14661-8131-46ff-acac-3576fb06317b/scratchpad/pr143`; all paths below are relative to the repo root.
- Commits are sole-authored by the user (`wenqianf <qianfeng.wen@mail.utoronto.ca>` is already the repo git identity). **Never add a `Co-Authored-By:` trailer or any attribution footer to commits.**
- Do NOT modify: `persona/existing_data_curation/scripts/infer_amazon_review_dimensions.py`, `collab_kit/harness.py`, `collab_kit/assignment_runner.py`, `collab_kit/backends.py`, `collab_kit/conformance.py`, `collab_kit/schemas/*`, `wiki_collab/run_assignment.sh`, `scripts/merge_collab_results.py`.
- The amazon builder's CLI, task output, and its imports from `infer_amazon_review_dimensions.py` must not change. The two pre-existing amazon/wiki tests must pass unchanged (they are the refactor's regression proof).
- Source identity constants (use verbatim): source `stackoverflow_persona`, task_id `stackoverflow_persona:<user_id>`, qid `so_user:<user_id>`, title `Stack Overflow user <user_id>`, source_url `stackexchange://stackoverflow/user/<user_id>`, assignment prefix `SO_`, dataset id default `matraix_stackoverflow_persona_v1`, protocol id `stackoverflow_persona_inference_v1`.
- No private machine paths (`/data2/`, usernames) anywhere; wrappers must use the `SCRIPT_DIR` pattern.
- Test command (used in every task; the empty config isolates repo-level pytest config, mirroring PR #143's validation):

  ```bash
  : > /tmp/empty-pytest.ini
  PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
  ```

---

### Task 1: Extract shared fold module `history_package_common.py`

**Files:**
- Create: `persona/existing_data_curation/scripts/history_package_common.py`
- Modify: `persona/existing_data_curation/scripts/make_amazon_collab_package.py`
- Test: `tests/unit/matraix/test_persona_collab_packages.py`

**Interfaces:**
- Consumes: nothing new (moves existing code).
- Produces (later tasks import these from `persona.existing_data_curation.scripts.history_package_common`):
  - `FOLD_TEXT_SEPARATOR: str`, `FOLD_TRUNCATION_MARKER: str`
  - `require_positive(name: str, value: int) -> None`
  - `compact_text(value: Any, max_chars: int) -> str`
  - `normalize_timestamp(value: Any) -> int | None`
  - `timestamp_to_date(value: Any) -> str | None`
  - `sorted_by_time(items, timestamp_of) -> list[dict]`
  - `spread_across_time(items: list, max_items: int) -> list`
  - `render_fold(fold_id: int, total_folds: int, rendered_item_texts: list[str]) -> str`
  - `build_cv_fold_texts(rendered_items: list[tuple[str, str]], effective_cv_folds: int, *, id_field: str) -> list[dict]`
  - `join_fold_texts(fold_texts: list[dict]) -> str`
  - `limit_fold_texts_for_profile(fold_texts: list[dict], max_profile_text_chars: int, *, effective_min_support: int) -> list[dict]`
  - `load_history_range(path: Path, range_start: int, range_end: int) -> list[tuple[int, dict]]`
  - `load_evidence_mapping(path: Path) -> dict`
  - `category_matches(category: str, patterns) -> bool`
  - `supported_schema_categories(mapping: dict) -> set[str]`
  - `filter_supported_dimensions(dimensions: list[dict], mapping: dict) -> list[dict]`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/matraix/test_persona_collab_packages.py`:

```python
def test_build_cv_fold_texts_uses_custom_id_field() -> None:
    from persona.existing_data_curation.scripts.history_package_common import (
        build_cv_fold_texts,
    )

    fold_texts = build_cv_fold_texts(
        [
            ("p0001", "[p0001]\ntext: alpha"),
            ("p0002", "[p0002]\ntext: beta"),
            ("p0003", "[p0003]\ntext: gamma"),
        ],
        2,
        id_field="post_ids",
    )

    assert [fold["fold_id"] for fold in fold_texts] == [1, 2]
    assert fold_texts[0]["post_ids"] == ["p0001", "p0003"]
    assert fold_texts[1]["post_ids"] == ["p0002"]
    assert fold_texts[0]["profile_text"].startswith("=== Fold 1/2 ===")
    assert "[p0003]" in fold_texts[0]["profile_text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
: > /tmp/empty-pytest.ini
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py::test_build_cv_fold_texts_uses_custom_id_field -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'persona.existing_data_curation.scripts.history_package_common'`

- [ ] **Step 3: Create the shared module**

Create `persona/existing_data_curation/scripts/history_package_common.py` with exactly this content. Every function body is moved verbatim from `make_amazon_collab_package.py` (names de-underscored) except: `sorted_by_time` gains a `timestamp_of` callable parameter, `render_fold` takes pre-rendered item strings, `build_cv_fold_texts` is the extracted fold-assembly loop with a configurable id key, and the timestamp/evidence-mapping helpers are generic copies of the ones in `infer_amazon_review_dimensions.py` (that file is imported by amazon code and must not be modified).

```python
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
```

- [ ] **Step 4: Rewire the amazon builder to use the shared module**

In `persona/existing_data_curation/scripts/make_amazon_collab_package.py`:

1. Add to the import block (after the existing `make_collab_package` import):

```python
from persona.existing_data_curation.scripts.history_package_common import (  # noqa: E402
    build_cv_fold_texts,
    compact_text,
    join_fold_texts,
    limit_fold_texts_for_profile,
    load_history_range,
    require_positive,
    sorted_by_time,
    spread_across_time,
)
```

2. Delete these now-moved definitions entirely: `FOLD_TEXT_SEPARATOR`, `FOLD_TRUNCATION_MARKER`, `_require_positive`, `_compact_text`, `_sorted_reviews`, `_spread_across_time`, `_render_fold`, `_profile_text`, `_fold_heading`, `_minimum_fold_text`, `_minimum_join_chars`, `_truncate_fold_text`, `_limit_fold_texts_for_profile`, and the module-level `def load_history_range(...)`. Keep `load_jsonl`/`parse_range` imports from `wiki_collab.core` only if still referenced (`parse_range` is — by `main`; `load_jsonl` is not once `load_history_range` moves — remove it from that import).

3. Update call sites:
   - In `_render_review`: `_compact_text(...)` → `compact_text(...)`.
   - In `build_amazon_collab_package`: each `_require_positive(...)` → `require_positive(...)`.
   - In `build_task`:

```python
    sorted_reviews = sorted_by_time(usable_reviews, _review_timestamp)
    selected_reviews = spread_across_time(sorted_reviews, max_reviews_per_user)
```

   and replace the fold-assembly block (from `rendered_reviews = [...]` through the `cv_fold_texts = _limit_fold_texts_for_profile(...)` call) with:

```python
    rendered_reviews = [
        (
            f"r{idx:04d}",
            _render_review(
                review,
                rendered_review_id=f"r{idx:04d}",
                max_review_text_chars=max_review_text_chars,
            ),
        )
        for idx, review in enumerate(selected_reviews, start=1)
    ]
    cv_fold_texts = build_cv_fold_texts(
        rendered_reviews, effective_cv_folds, id_field="review_ids"
    )
    cv_fold_texts = limit_fold_texts_for_profile(
        cv_fold_texts,
        max_profile_text_chars,
        effective_min_support=effective_min_support,
    )
```

   and `"profile_text": _profile_text(cv_fold_texts),` → `"profile_text": join_fold_texts(cv_fold_texts),`.

- [ ] **Step 5: Run the full test file to verify everything passes**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
```
Expected: PASS — 6 passed (5 pre-existing + the new one). The pre-existing `test_amazon_collab_package_builds_extractable_archive` passing unchanged proves the move preserved behavior.

- [ ] **Step 6: Compile check and commit**

```bash
PYTHONPYCACHEPREFIX=/tmp/matraix_pycache_check python3 -m py_compile \
  persona/existing_data_curation/scripts/history_package_common.py \
  persona/existing_data_curation/scripts/make_amazon_collab_package.py
git add persona/existing_data_curation/scripts/history_package_common.py \
        persona/existing_data_curation/scripts/make_amazon_collab_package.py \
        tests/unit/matraix/test_persona_collab_packages.py
git commit -m "Extract shared history fold module from amazon package builder"
```

---

### Task 2: Source config and evidence mapping

**Files:**
- Create: `persona/existing_data_curation/configs/stackexchange_persona.json`
- Create: `persona/existing_data_curation/configs/stackoverflow_evidence_mapping.json`
- Test: `tests/unit/matraix/test_persona_collab_packages.py`

**Interfaces:**
- Produces: `configs/stackoverflow_evidence_mapping.json` loadable by `load_evidence_mapping` from Task 1; `configs/stackexchange_persona.json` with `source.repo_id` and `source.artifact_prefix` consumed by the Task 4 exporter.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/matraix/test_persona_collab_packages.py`:

```python
def test_stackoverflow_evidence_mapping_filters_catalog_categories() -> None:
    from persona.existing_data_curation.scripts.history_package_common import (
        filter_supported_dimensions,
        load_evidence_mapping,
    )

    repo_root = Path(__file__).resolve().parents[3]
    mapping = load_evidence_mapping(
        repo_root
        / "persona/existing_data_curation/configs/stackoverflow_evidence_mapping.json"
    )
    dimensions = [
        {"id": "d1", "category": "Skills: Programming"},
        {"id": "d2", "category": "Linguistic: Communication"},
        {"id": "d3", "category": "External: Datasets"},
        {"id": "d4", "category": "Interests: Food"},
    ]
    filtered = filter_supported_dimensions(dimensions, mapping)
    assert [dim["id"] for dim in filtered] == ["d1", "d2"]

    config = json.loads(
        (
            repo_root
            / "persona/existing_data_curation/configs/stackexchange_persona.json"
        ).read_text(encoding="utf-8")
    )
    assert config["source"]["repo_id"] == "MatrAIx2026/MatrAIx2026"
    assert config["source"]["artifact_prefix"] == "StackExchange_Persona"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py::test_stackoverflow_evidence_mapping_filters_catalog_categories -q
```
Expected: FAIL with `FileNotFoundError` for `stackoverflow_evidence_mapping.json`

- [ ] **Step 3: Create both config files**

Create `persona/existing_data_curation/configs/stackexchange_persona.json`:

```json
{
  "id": "stackexchange_persona",
  "source": {
    "type": "huggingface_parquet_year_batches",
    "repo_id": "MatrAIx2026/MatrAIx2026",
    "dataset_url": "https://huggingface.co/datasets/MatrAIx2026/MatrAIx2026",
    "artifact_prefix": "StackExchange_Persona",
    "layout": "StackExchange_Persona/<year>/stackoverflow_persona_batch_*.parquet"
  },
  "format": "partitioned parquet (by year)",
  "normalized_output": "user_histories.jsonl or user_histories.jsonl.gz",
  "package_builder_input": "Pass the normalized output to scripts/make_stackoverflow_package.sh as USER_HISTORIES_JSONL.",
  "persona_relevance": [
    "Longitudinal public Q&A posting histories",
    "Technical skills, tools, and domain expertise signals",
    "Topic and tag interests over time",
    "Problem-solving and learning behavior",
    "Communication style in public technical writing"
  ],
  "notes": "The dataset is gated on Hugging Face; request access before exporting. The exporter's parquet column-alias table is an assumption pending verification against the real artifact (see docs/superpowers/specs/2026-07-01-stackoverflow-collab-package-design.md)."
}
```

Create `persona/existing_data_curation/configs/stackoverflow_evidence_mapping.json`:

```json
{
  "description": "Broad evidence categories for compressing Stack Overflow posting histories before mapping to the MatrAIx persona schema.",
  "evidence_categories": [
    {
      "id": "technical_expertise",
      "label": "Technical expertise",
      "description": "Programming languages, frameworks, tools, and domains demonstrated through the tags, vocabulary, and depth of questions and answers.",
      "inferability": "allowed_from_behavior",
      "schema_categories": [
        "Skills: Programming",
        "Skills: Tools",
        "Expertise: Skills",
        "Expertise: Domains",
        "Professional: Industry",
        "Professional: Role",
        "Professional: Career"
      ]
    },
    {
      "id": "topic_interests",
      "label": "Topic interests",
      "description": "Recurring tags, technologies, and subject areas the user engages with over time.",
      "inferability": "allowed_from_behavior",
      "schema_categories": [
        "Interests: Topics",
        "Interests: Hobbies",
        "Expertise: Domains",
        "Learning: Academic"
      ]
    },
    {
      "id": "problem_solving_style",
      "label": "Problem-solving style",
      "description": "How the user formulates problems and evaluates solutions, such as debugging rigor, research-before-asking, tradeoff analysis, or preference for minimal examples.",
      "inferability": "allowed_from_behavior",
      "schema_categories": [
        "Risk & Decision",
        "Behavior: Preferences",
        "Personality: Big Five",
        "Personality: Character"
      ]
    },
    {
      "id": "learning_behavior",
      "label": "Learning behavior",
      "description": "Asking versus answering balance, self-answering, follow-up edits, and how the user acquires and shares knowledge.",
      "inferability": "allowed_from_behavior",
      "schema_categories": [
        "Learning: Style",
        "Learning: Academic",
        "Behavior: Habits",
        "Behavior: Time"
      ]
    },
    {
      "id": "communication_style",
      "label": "Communication style",
      "description": "Writing patterns in public technical prose, such as thoroughness, structure, directness, tone, and courtesy.",
      "inferability": "allowed_from_language",
      "schema_categories": [
        "Linguistic: Communication",
        "Linguistic: Language",
        "Learning: Style",
        "Personality: Big Five",
        "Personality: Character"
      ]
    },
    {
      "id": "values_and_motivations",
      "label": "Values and motivations",
      "description": "Grounded priorities reflected in posting behavior, such as helpfulness, correctness-seeking, craftsmanship, pragmatism, or knowledge-sharing.",
      "inferability": "allowed_from_behavior",
      "schema_categories": [
        "Values & Motivation",
        "Worldview: Beliefs",
        "Personality: Character"
      ]
    },
    {
      "id": "work_context",
      "label": "Work context",
      "description": "Work practices visible in posts, such as production-system contexts, team workflows, tooling stacks, or deadline pressure mentioned while asking or answering.",
      "inferability": "allowed_from_behavior",
      "schema_categories": [
        "Behavior: Work",
        "Behavior: Habits"
      ]
    },
    {
      "id": "explicit_self_statements",
      "label": "Explicit self-statements",
      "description": "Direct statements about the user, such as job, education, location, health context, or life circumstances. These must be quoted directly and must not be inferred from technical activity alone.",
      "inferability": "direct_only",
      "schema_categories": [
        "Demographic:*",
        "Health:*",
        "Professional:*",
        "Learning: Academic",
        "Personality: Relationships",
        "Worldview: Beliefs"
      ]
    }
  ],
  "skip_by_default_schema_categories": [
    "External: Datasets",
    "State: Emotional",
    "Narrative Identity & Life History"
  ],
  "direct_only_note": "Demographic, health condition, family status, occupation, geography, political affiliation, religious identity, and identity-like attributes require explicit quoted self-statements. Repeated technical or topical engagement can be preserved as skills, interests, preferences, or values, but should not be converted into asserted sensitive identity/status labels without explicit evidence."
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
```
Expected: PASS — 7 passed

- [ ] **Step 5: Commit**

```bash
git add persona/existing_data_curation/configs/stackexchange_persona.json \
        persona/existing_data_curation/configs/stackoverflow_evidence_mapping.json \
        tests/unit/matraix/test_persona_collab_packages.py
git commit -m "Add StackExchange persona source config and evidence mapping"
```

---

### Task 3: Stack Overflow package builder

**Files:**
- Create: `persona/existing_data_curation/scripts/make_stackoverflow_collab_package.py`
- Test: `tests/unit/matraix/test_persona_collab_packages.py`

**Interfaces:**
- Consumes: Task 1's `history_package_common` functions; `make_collab_package` public helpers (`build_archive`, `copy_collab_kit`, `copy_root_launcher`, `load_dimensions`, `prepare_out_dir`, `write_jsonl`, `write_package_manifest`); `wiki_collab.core` (`canonical_json`, `parse_range`, `sha256_file`, `sha256_text`, `write_json`); Task 2's `configs/stackoverflow_evidence_mapping.json`.
- Produces: `build_stackoverflow_collab_package(...) -> dict` and `build_task(row, *, global_idx, cv_folds, min_support_folds, max_posts_per_user, max_post_text_chars, max_profile_text_chars) -> dict` (used by tests); CLI `python3 .../make_stackoverflow_collab_package.py --user-histories ... --dimensions ... --range ... --out-dir ... --assignment-id ... --worker-id ... --dataset-id ... --dataset-sha256 ... [--cv-folds 3] [--min-support-folds 2] [--max-posts-per-user 90] [--max-post-text-chars 900] [--max-profile-text-chars 70000] [--all-dimensions] [--evidence-mapping PATH] [--no-archive] [--force]` (used by Task 7's wrapper).

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/matraix/test_persona_collab_packages.py`:

```python
def test_stackoverflow_collab_package_builds_extractable_archive(tmp_path: Path) -> None:
    from persona.existing_data_curation.scripts.make_stackoverflow_collab_package import (
        build_stackoverflow_collab_package,
    )
    from persona.existing_data_curation.wiki_collab.core import sha256_file

    histories = tmp_path / "so_histories.jsonl"
    _write_jsonl(
        histories,
        [
            {
                "user_id": "42",
                "posts": [
                    {
                        "post_id": "101",
                        "post_type": "question",
                        "timestamp": 1_704_067_200,
                        "tags": ["python", "pandas"],
                        "title": "How do I merge dataframes safely?",
                        "text": "I compared several approaches before asking here.",
                        "score": 12,
                        "accepted": None,
                    },
                    {
                        "post_id": "102",
                        "post_type": "answer",
                        "timestamp": 1_707_004_800,
                        "tags": ["python"],
                        "title": "",
                        "text": "Use explicit validation and check the docs first.",
                        "score": 30,
                        "accepted": True,
                    },
                ],
            }
        ],
    )

    out_dir = tmp_path / "SO_0_1_carol"
    summary = build_stackoverflow_collab_package(
        user_histories_path=histories,
        dimensions_path=_dimensions_file(tmp_path),
        out_dir=out_dir,
        assignment_id="SO_0_1",
        worker_id="carol",
        dataset_id="so_test",
        dataset_sha256=sha256_file(histories),
        range_start=0,
        range_end=1,
        cv_folds=2,
        min_support_folds=2,
        all_dimensions=True,
        force=True,
    )

    tasks = _read_jsonl(out_dir / "tasks.jsonl")
    assignment = json.loads((out_dir / "assignment.json").read_text())

    assert Path(summary["archive_path"]).is_file()
    assert tasks[0]["source"] == "stackoverflow_persona"
    assert tasks[0]["task_id"] == "stackoverflow_persona:42"
    assert tasks[0]["qid"] == "so_user:42"
    assert tasks[0]["effective_cv_folds"] == 2
    assert len(tasks[0]["cv_fold_texts"]) == 2
    assert tasks[0]["cv_fold_texts"][0]["post_ids"] == ["p0001"]
    assert tasks[0]["tags"] == ["pandas", "python"]
    assert "type: question" in tasks[0]["profile_text"]
    assert "accepted: true" in tasks[0]["profile_text"]
    assert assignment["source"] == "stackoverflow_persona"
    assert assignment["dimensions_scope"] == "all"
    assert assignment["max_posts_per_user"] == 90

    with tarfile.open(summary["archive_path"], "r:gz") as archive:
        names = set(archive.getnames())

    assert "SO_0_1_carol/tasks.jsonl" in names
    assert "SO_0_1_carol/README.md" in names
    assert "SO_0_1_carol/collab_kit/conformance.py" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py::test_stackoverflow_collab_package_builds_extractable_archive -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'persona.existing_data_curation.scripts.make_stackoverflow_collab_package'`

- [ ] **Step 3: Create the builder**

Create `persona/existing_data_curation/scripts/make_stackoverflow_collab_package.py`:

```python
#!/usr/bin/env python3
"""Create a worker-facing package from Stack Overflow user posting histories.

The package contains rendered posting-profile tasks only. Raw user history
JSONL and any owner-side database remain local.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from persona.existing_data_curation.scripts.history_package_common import (  # noqa: E402
    build_cv_fold_texts,
    compact_text,
    filter_supported_dimensions,
    join_fold_texts,
    limit_fold_texts_for_profile,
    load_evidence_mapping,
    load_history_range,
    normalize_timestamp,
    require_positive,
    sorted_by_time,
    spread_across_time,
    timestamp_to_date,
)
from persona.existing_data_curation.scripts.make_collab_package import (  # noqa: E402
    build_archive,
    copy_collab_kit,
    copy_root_launcher,
    load_dimensions,
    prepare_out_dir,
    write_jsonl,
    write_package_manifest,
)
from persona.existing_data_curation.wiki_collab.core import (  # noqa: E402
    canonical_json,
    parse_range,
    sha256_file,
    sha256_text,
    write_json,
)


SOURCE = "stackoverflow_persona"
DEFAULT_EVIDENCE_MAPPING_PATH = (
    Path(__file__).resolve().parent.parent
    / "configs"
    / "stackoverflow_evidence_mapping.json"
)


def _post_timestamp(post: dict[str, Any]) -> int | None:
    return normalize_timestamp(post.get("timestamp"))


def _post_date(post: dict[str, Any]) -> str:
    raw_date = post.get("date")
    if raw_date:
        return str(raw_date)
    return timestamp_to_date(post.get("timestamp")) or "unknown"


def _first_nonblank(post: dict[str, Any], keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = post.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _post_title(post: dict[str, Any]) -> str:
    return _first_nonblank(post, ("title",), "(untitled)")


def _post_title_evidence(post: dict[str, Any]) -> str:
    return _first_nonblank(post, ("title",))


def _post_text(post: dict[str, Any]) -> str:
    return _first_nonblank(post, ("text", "body"))


def _post_type(post: dict[str, Any]) -> str:
    value = str(post.get("post_type") or "").strip().lower()
    return value or "post"


def _post_tags(post: dict[str, Any]) -> list[str]:
    tags = post.get("tags")
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    if isinstance(tags, str) and tags.strip():
        return [part for part in (piece.strip() for piece in tags.split(",")) if part]
    return []


def _post_accepted(post: dict[str, Any]) -> str:
    accepted = post.get("accepted")
    if _post_type(post) == "answer" and isinstance(accepted, bool):
        return "true" if accepted else "false"
    return "n/a"


def _has_post_evidence(post: dict[str, Any]) -> bool:
    return bool(_post_title_evidence(post).strip() or _post_text(post).strip())


def _post_objects(raw_posts: list[Any], *, user_id: str) -> list[dict[str, Any]]:
    posts = []
    for idx, post in enumerate(raw_posts):
        if not isinstance(post, dict):
            raise ValueError(
                f"user {user_id}: bad post row {idx}: expected post object dict, "
                f"got {type(post).__name__}"
            )
        posts.append(dict(post))
    return posts


def _render_post(
    post: dict[str, Any],
    *,
    rendered_post_id: str,
    max_post_text_chars: int,
) -> str:
    tags = _post_tags(post)
    lines = [
        f"[{rendered_post_id}]",
        f"date: {_post_date(post)}",
        f"type: {_post_type(post)}",
        f"tags: {', '.join(tags) if tags else '(none)'}",
        f"title: {_post_title(post)}",
        f"score: {post.get('score', 'unknown')}",
        f"accepted: {_post_accepted(post)}",
        f"text: {compact_text(_post_text(post), max_post_text_chars)}",
    ]
    return "\n".join(lines)


def stackoverflow_input_payload(task: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable payload covered by input_sha256."""
    return {key: value for key, value in task.items() if key != "input_sha256"}


def build_task(
    row: dict[str, Any],
    *,
    global_idx: int,
    cv_folds: int,
    min_support_folds: int,
    max_posts_per_user: int,
    max_post_text_chars: int,
    max_profile_text_chars: int,
) -> dict[str, Any]:
    user_id = str(row.get("user_id") or "").strip()
    if not user_id:
        raise ValueError(f"global_idx {global_idx}: missing user_id")

    raw_posts = row.get("posts")
    if not isinstance(raw_posts, list):
        raise ValueError(f"user {user_id}: expected posts list")

    post_objects = _post_objects(raw_posts, user_id=user_id)
    usable_posts = [post for post in post_objects if _has_post_evidence(post)]
    if len(usable_posts) < 2:
        raise ValueError(
            f"user {user_id}: fewer than 2 usable posts with non-empty title or text "
            f"({len(usable_posts)} usable of {len(raw_posts)} raw posts)"
        )

    sorted_posts = sorted_by_time(usable_posts, _post_timestamp)
    selected_posts = spread_across_time(sorted_posts, max_posts_per_user)
    usable_post_count = len(selected_posts)
    effective_cv_folds = min(cv_folds, usable_post_count)
    if effective_cv_folds < 2:
        raise ValueError(
            f"user {user_id}: effective_cv_folds must be at least 2, got {effective_cv_folds}"
        )
    effective_min_support = min(min_support_folds, effective_cv_folds)
    if effective_min_support < 2:
        raise ValueError(
            f"user {user_id}: effective min_support_folds must be at least 2, got "
            f"{effective_min_support}"
        )

    rendered_posts = [
        (
            f"p{idx:04d}",
            _render_post(
                post,
                rendered_post_id=f"p{idx:04d}",
                max_post_text_chars=max_post_text_chars,
            ),
        )
        for idx, post in enumerate(selected_posts, start=1)
    ]
    cv_fold_texts = build_cv_fold_texts(
        rendered_posts, effective_cv_folds, id_field="post_ids"
    )
    cv_fold_texts = limit_fold_texts_for_profile(
        cv_fold_texts,
        max_profile_text_chars,
        effective_min_support=effective_min_support,
    )

    tags = sorted({tag for post in selected_posts for tag in _post_tags(post)})
    task = {
        "global_idx": global_idx,
        "task_id": f"{SOURCE}:{user_id}",
        "qid": f"so_user:{user_id}",
        "title": f"Stack Overflow user {user_id}",
        "source_url": f"stackexchange://stackoverflow/user/{user_id}",
        "profile_text": join_fold_texts(cv_fold_texts),
        "source": SOURCE,
        "user_id": user_id,
        "post_count": len(raw_posts),
        "selected_post_count": usable_post_count,
        "tags": tags,
        "cv_folds": cv_folds,
        "effective_cv_folds": effective_cv_folds,
        "min_support_folds": effective_min_support,
        "cv_fold_texts": cv_fold_texts,
    }
    task["input_sha256"] = sha256_text(canonical_json(stackoverflow_input_payload(task)))
    return task


def package_dimensions(
    dimensions_path: Path,
    *,
    all_dimensions: bool,
    evidence_mapping_path: Path,
) -> list[dict[str, Any]]:
    dimensions = load_dimensions(dimensions_path)
    if all_dimensions:
        return dimensions
    mapping = load_evidence_mapping(evidence_mapping_path)
    filtered = filter_supported_dimensions(dimensions, mapping)
    if not filtered:
        raise ValueError(
            "Stack Overflow-supported dimension filtering returned no dimensions"
        )
    return filtered


def write_stackoverflow_worker_readme(out_dir: Path) -> None:
    readme = """# MatrAIx Stack Overflow Attribution Assignment

You received a self-contained assignment package. Work inside this directory.
Requires Python 3.10+; no Python packages need to be installed.

Files:

- `assignment.json`: assignment metadata for this user range.
- `tasks.jsonl`: Stack Overflow user posting profiles to process.
- `dimensions.json`: persona dimensions and allowed values to fill.
- `package_manifest.json`: checksums for files that should not change.
- `run_assignment.sh`: the main entrypoint.
- `collab_kit/solver.py`: the starter code you may edit.
- `results.jsonl`: the file you send back after a passing run.

Each task represents one Stack Overflow user. The task `profile_text` is
rendered from the user's public posts: dates, types (question/answer), tags,
titles, scores, accepted status, and body text. Posts are split into CV
folds. The `cv_fold_texts` field lists each fold with its `fold_id`,
`post_ids`, and rendered `profile_text`; support evidence should come from
enough distinct folds for the task's `min_support_folds` setting.

Quickstart:

```bash
./run_assignment.sh
./run_assignment.sh --status
./run_assignment.sh --validate
```

Use the menu to choose Codex or Claude Code, effort, parallelism, smoke test,
environment/CLI health check, real run, and validation. The runner verifies
checksums before every action, saves settings in `.wiki_collab_settings.yaml`,
and resumes from `results.jsonl.progress.jsonl` if quota runs out. You may
improve `solver.py` to get better results; keep the output contract unchanged
and return only `results.jsonl` unless the owner asks for logs.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")


def build_stackoverflow_collab_package(
    *,
    user_histories_path: Path,
    dimensions_path: Path,
    out_dir: Path,
    assignment_id: str,
    worker_id: str,
    dataset_id: str,
    dataset_sha256: str,
    range_start: int,
    range_end: int,
    cv_folds: int = 3,
    min_support_folds: int = 2,
    max_posts_per_user: int = 90,
    max_post_text_chars: int = 900,
    max_profile_text_chars: int = 70000,
    all_dimensions: bool = False,
    evidence_mapping_path: Path = DEFAULT_EVIDENCE_MAPPING_PATH,
    create_archive: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    if not 0 <= range_start < range_end:
        raise ValueError(
            "range_start must be >= 0 and less than range_end, got "
            f"range_start={range_start}, range_end={range_end}"
        )
    require_positive("cv_folds", cv_folds)
    require_positive("min_support_folds", min_support_folds)
    if min_support_folds > cv_folds:
        raise ValueError(
            "min_support_folds must be <= cv_folds, got "
            f"min_support_folds={min_support_folds}, cv_folds={cv_folds}"
        )
    require_positive("max_posts_per_user", max_posts_per_user)
    require_positive("max_post_text_chars", max_post_text_chars)
    require_positive("max_profile_text_chars", max_profile_text_chars)

    prepare_out_dir(out_dir, force=force)
    histories = load_history_range(user_histories_path, range_start, range_end)
    tasks = [
        build_task(
            row,
            global_idx=global_idx,
            cv_folds=cv_folds,
            min_support_folds=min_support_folds,
            max_posts_per_user=max_posts_per_user,
            max_post_text_chars=max_post_text_chars,
            max_profile_text_chars=max_profile_text_chars,
        )
        for global_idx, row in histories
    ]
    dimensions = package_dimensions(
        dimensions_path,
        all_dimensions=all_dimensions,
        evidence_mapping_path=evidence_mapping_path,
    )

    tasks_path = out_dir / "tasks.jsonl"
    dimensions_out_path = out_dir / "dimensions.json"
    write_jsonl(tasks_path, tasks)
    dimensions_out_path.write_text(
        json.dumps(dimensions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copy_collab_kit(out_dir)
    copy_root_launcher(out_dir)
    write_stackoverflow_worker_readme(out_dir)

    dimensions_scope = "all" if all_dimensions else "stackoverflow_supported"
    assignment = {
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "source": SOURCE,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256,
        "range_start": range_start,
        "range_end": range_end,
        "task_count": len(tasks),
        "dimension_count": len(dimensions),
        "cv_folds": cv_folds,
        "min_support_folds": min_support_folds,
        "min_support_folds_requested": min_support_folds,
        "effective_min_support_policy": "cap_each_task_to_effective_cv_folds",
        "max_posts_per_user": max_posts_per_user,
        "max_post_text_chars": max_post_text_chars,
        "max_profile_text_chars": max_profile_text_chars,
        "dimensions_scope": dimensions_scope,
        "categories": dimensions_scope,
        "tasks_file": "tasks.jsonl",
        "tasks_sha256": sha256_file(tasks_path),
        "dimensions_file": "dimensions.json",
        "dimensions_sha256": sha256_file(dimensions_out_path),
        "kit": "collab_kit",
        "return_file": "results.jsonl",
    }
    write_json(out_dir / "assignment.json", assignment)
    write_package_manifest(out_dir, assignment)

    archive_path = build_archive(out_dir) if create_archive else None
    return {
        "package_dir": str(out_dir),
        "archive_path": str(archive_path) if archive_path else None,
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "task_count": len(tasks),
        "dimension_count": len(dimensions),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-histories", type=Path, required=True)
    parser.add_argument("--dimensions", type=Path, required=True)
    parser.add_argument("--range", required=True, dest="range_spec")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--assignment-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--cv-folds", type=int, default=3)
    parser.add_argument("--min-support-folds", type=int, default=2)
    parser.add_argument("--max-posts-per-user", type=int, default=90)
    parser.add_argument("--max-post-text-chars", type=int, default=900)
    parser.add_argument("--max-profile-text-chars", type=int, default=70000)
    parser.add_argument("--all-dimensions", action="store_true")
    parser.add_argument("--evidence-mapping", type=Path, default=DEFAULT_EVIDENCE_MAPPING_PATH)
    parser.add_argument("--no-archive", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    range_start, range_end = parse_range(args.range_spec)
    summary = build_stackoverflow_collab_package(
        user_histories_path=args.user_histories,
        dimensions_path=args.dimensions,
        out_dir=args.out_dir,
        assignment_id=args.assignment_id,
        worker_id=args.worker_id,
        dataset_id=args.dataset_id,
        dataset_sha256=args.dataset_sha256,
        range_start=range_start,
        range_end=range_end,
        cv_folds=args.cv_folds,
        min_support_folds=args.min_support_folds,
        max_posts_per_user=args.max_posts_per_user,
        max_post_text_chars=args.max_post_text_chars,
        max_profile_text_chars=args.max_profile_text_chars,
        all_dimensions=args.all_dimensions,
        evidence_mapping_path=args.evidence_mapping,
        create_archive=not args.no_archive,
        force=args.force,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
```
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
PYTHONPYCACHEPREFIX=/tmp/matraix_pycache_check python3 -m py_compile \
  persona/existing_data_curation/scripts/make_stackoverflow_collab_package.py
git add persona/existing_data_curation/scripts/make_stackoverflow_collab_package.py \
        tests/unit/matraix/test_persona_collab_packages.py
git commit -m "Add Stack Overflow collaborator package builder"
```

---

### Task 4: HF exporter

**Files:**
- Create: `persona/existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py`
- Test: `tests/unit/matraix/test_persona_collab_packages.py`

**Interfaces:**
- Consumes: Task 2's `configs/stackexchange_persona.json` (`source.repo_id`, `source.artifact_prefix`).
- Produces: CLI `python3 .../export_hf_stackoverflow_user_histories.py (--user-ids FILE | --all-users) [--years CSV] [--min-posts N] [--max-users N] [--output PATH] [--repo-id ID] [--artifact-prefix P] [--token T]`; module functions `list_relevant_shards`, `read_shard_rows`, `extract_user_rows`, `normalize_post`, `main` (tests monkeypatch the first two). Output rows: `{"user_id": str, "post_count": int, "posts": [normalized post]}` — the format Task 3 consumes. Like the amazon exporter, this file is self-contained (no repo imports) so owners can run it standalone; `huggingface_hub`/`pyarrow` import lazily inside functions.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/matraix/test_persona_collab_packages.py`:

```python
def test_hf_stackoverflow_exporter_writes_normalized_user_histories(
    tmp_path: Path, monkeypatch
) -> None:
    from persona.existing_data_curation.scripts import (
        export_hf_stackoverflow_user_histories as exporter,
    )

    user_ids = tmp_path / "so_user_ids.md"
    user_ids.write_text("# Users\n\n- 42\n- 777\n", encoding="utf-8")

    def fake_list_relevant_shards(*, repo_id, artifact_prefix, years, token):
        assert repo_id == "MatrAIx2026/MatrAIx2026"
        assert artifact_prefix == "StackExchange_Persona"
        assert years == {"2025"}
        return ["StackExchange_Persona/2025/stackoverflow_persona_batch_00001.parquet"]

    def fake_read_shard_rows(_repo_id, _filename, _token):
        return [
            {
                "OwnerUserId": 42,
                "Id": 102,
                "PostTypeId": 2,
                "CreationDate": "2024-02-04T00:00:00Z",
                "Tags": "<python>",
                "Title": None,
                "Body": "<p>Use explicit validation.</p>",
                "Score": 30,
            },
            {
                "OwnerUserId": 42,
                "Id": 101,
                "PostTypeId": 1,
                "CreationDate": "2024-01-01T00:00:00Z",
                "Tags": "<python><pandas>",
                "Title": "How do I merge dataframes safely?",
                "Body": "<p>I compared several approaches.</p>",
                "Score": 12,
            },
            {
                "OwnerUserId": 999,
                "Id": 300,
                "PostTypeId": 1,
                "CreationDate": "2024-03-01T00:00:00Z",
                "Tags": "",
                "Title": "Unrelated user",
                "Body": "skip me",
                "Score": 1,
            },
        ]

    monkeypatch.setattr(exporter, "list_relevant_shards", fake_list_relevant_shards)
    monkeypatch.setattr(exporter, "read_shard_rows", fake_read_shard_rows)

    output = tmp_path / "user_histories.jsonl"
    exit_code = exporter.main(
        [
            "--user-ids",
            str(user_ids),
            "--years",
            "2025",
            "--output",
            str(output),
        ]
    )

    histories = _read_jsonl(output)
    assert exit_code == 0
    assert len(histories) == 1
    record = histories[0]
    assert record["user_id"] == "42"
    assert record["post_count"] == 2
    first, second = record["posts"]
    assert first["post_id"] == "101"
    assert first["post_type"] == "question"
    assert first["tags"] == ["python", "pandas"]
    assert first["text"] == "I compared several approaches."
    assert first["date"] == "2024-01-01"
    assert second["post_type"] == "answer"
    assert second["title"] == ""
    assert second["site"] == "stackoverflow"


def test_hf_stackoverflow_exporter_accepts_user_grouped_rows(
    tmp_path: Path, monkeypatch
) -> None:
    from persona.existing_data_curation.scripts import (
        export_hf_stackoverflow_user_histories as exporter,
    )

    monkeypatch.setattr(
        exporter,
        "list_relevant_shards",
        lambda **_kwargs: ["StackExchange_Persona/2011/batch.parquet"],
    )
    monkeypatch.setattr(
        exporter,
        "read_shard_rows",
        lambda *_args: [
            {
                "user_id": "7",
                "posts": [
                    {
                        "post_id": "1",
                        "post_type": "question",
                        "timestamp": 1_300_000_000,
                        "tags": ["java"],
                        "title": "T",
                        "text": "B",
                        "score": 3,
                    }
                ],
            }
        ],
    )

    output = tmp_path / "grouped.jsonl"
    exit_code = exporter.main(["--all-users", "--output", str(output)])

    histories = _read_jsonl(output)
    assert exit_code == 0
    assert histories[0]["user_id"] == "7"
    assert histories[0]["posts"][0]["tags"] == ["java"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q -k stackoverflow_exporter
```
Expected: FAIL (both) with `ImportError: cannot import name 'export_hf_stackoverflow_user_histories'`

- [ ] **Step 3: Create the exporter**

Create `persona/existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py`:

```python
#!/usr/bin/env python3
"""Export Stack Overflow user posting histories from reindexed HF artifacts.

This is the package-owner retrieval path for Stack Overflow persona curation.
It reads year-partitioned Parquet batches from a Hugging Face dataset artifact
and writes the normalized JSONL format consumed by
``make_stackoverflow_package.sh``:

    {"user_id": "...", "post_count": 42, "posts": [...]}

The artifact layout is ``StackExchange_Persona/<year>/*.parquet``. The dataset
is gated; request access on Hugging Face and ``huggingface-cli login`` first.

The parquet column names are an assumption pending verification against the
gated artifact (see the design doc). The alias tables below accept both a
per-post row shape (one post per row, grouped by owner id) and a per-user row
shape (a user id plus a nested posts list). If neither shape matches, the
exporter fails with the columns it actually saw so the fix is a one-line
alias addition.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import gzip
from html import unescape
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Iterator


DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "configs" / "stackexchange_persona.json"
)
DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "outputs"
    / "stackexchange_persona"
    / "user_histories.jsonl"
)


def load_default_source_config(config_path: Path = DEFAULT_CONFIG_PATH) -> tuple[str, str]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    source = payload.get("source") or {}
    repo_id = source.get("repo_id")
    artifact_prefix = source.get("artifact_prefix")
    if not repo_id or not artifact_prefix:
        raise ValueError(
            f"{config_path}: expected source.repo_id and source.artifact_prefix"
        )
    return str(repo_id), str(artifact_prefix)


DEFAULT_REPO_ID, DEFAULT_ARTIFACT_PREFIX = load_default_source_config()

USER_ID_ALIASES = ("user_id", "owner_user_id", "OwnerUserId", "account_id")
POST_LIST_ALIASES = ("posts", "history", "records")
POST_ID_ALIASES = ("post_id", "Id", "id")
POST_TYPE_ALIASES = ("post_type", "PostTypeId", "post_type_id")
TIMESTAMP_ALIASES = ("timestamp", "creation_date", "CreationDate")
TAGS_ALIASES = ("tags", "Tags")
TITLE_ALIASES = ("title", "Title")
TEXT_ALIASES = ("text", "body", "Body")
SCORE_ALIASES = ("score", "Score")
ACCEPTED_ALIASES = ("accepted", "is_accepted", "accepted_answer")

POST_TYPE_ID_MAP = {"1": "question", "2": "answer"}
TAG_STRING_RE = re.compile(r"<([^<>]+)>")
HTML_TAG_RE = re.compile(r"<[^>]+>")
NUMERIC_USER_ID_RE = re.compile(r"\b\d{1,12}\b")


def log(message: str) -> None:
    print(f"[hf_stackoverflow_histories] {message}", flush=True)


def iter_jsonl_or_gz(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def load_user_ids(path: Path, limit: int = 0) -> list[str]:
    if path.suffix in {".jsonl", ".gz"}:
        ids = [
            str(row["user_id"])
            for row in iter_jsonl_or_gz(path)
            if row.get("user_id")
        ]
    else:
        ids = NUMERIC_USER_ID_RE.findall(path.read_text(encoding="utf-8"))

    deduped = list(dict.fromkeys(ids))
    if limit:
        deduped = deduped[:limit]
    if not deduped:
        raise ValueError(f"No user IDs found in {path}")
    return deduped


def _first_present(row: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for key in aliases:
        if key in row and row[key] is not None:
            return row[key]
    return None


def _parse_timestamp(value: Any) -> tuple[int | None, str | None]:
    """Return (epoch_seconds, iso_date) from epoch numbers or ISO strings."""
    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        timestamp = int(value)
        if timestamp <= 0:
            return None, None
        if timestamp > 10_000_000_000:
            timestamp //= 1000
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
        return timestamp, date
    text = str(value).strip()
    if not text:
        return None, None
    if text.isdigit():
        return _parse_timestamp(int(text))
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp()), parsed.date().isoformat()


def _parse_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(tag).strip() for tag in value if str(tag).strip()]
    text = str(value).strip()
    if not text:
        return []
    if "<" in text:
        return [tag for tag in TAG_STRING_RE.findall(text) if tag.strip()]
    return [part for part in (piece.strip() for piece in text.split(",")) if part]


def _strip_html(value: str) -> str:
    if "<" not in value:
        return value
    return " ".join(unescape(HTML_TAG_RE.sub(" ", value)).split())


def _post_type_of(row: dict[str, Any]) -> str:
    raw = _first_present(row, POST_TYPE_ALIASES)
    if raw is None:
        return "post"
    text = str(raw).strip().lower()
    return POST_TYPE_ID_MAP.get(text, text or "post")


def normalize_post(row: dict[str, Any]) -> dict[str, Any]:
    timestamp, date = _parse_timestamp(_first_present(row, TIMESTAMP_ALIASES))
    accepted = _first_present(row, ACCEPTED_ALIASES)
    return {
        "post_id": str(_first_present(row, POST_ID_ALIASES) or ""),
        "post_type": _post_type_of(row),
        "timestamp": timestamp,
        "date": date,
        "tags": _parse_tags(_first_present(row, TAGS_ALIASES)),
        "title": str(_first_present(row, TITLE_ALIASES) or ""),
        "text": _strip_html(str(_first_present(row, TEXT_ALIASES) or "")),
        "score": _first_present(row, SCORE_ALIASES),
        "accepted": accepted if isinstance(accepted, bool) else None,
        "site": "stackoverflow",
    }


def extract_user_rows(
    rows: list[dict[str, Any]], *, source_name: str
) -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Yield (user_id, [normalized posts]) from either supported parquet shape."""
    if not rows:
        return
    sample = rows[0]
    user_key = next((key for key in USER_ID_ALIASES if key in sample), None)
    if user_key is None:
        raise ValueError(
            f"{source_name}: no user id column; saw columns {sorted(sample)}, "
            f"expected one of {list(USER_ID_ALIASES)}"
        )

    posts_key = next(
        (key for key in POST_LIST_ALIASES if isinstance(sample.get(key), list)), None
    )
    if posts_key is not None:
        for row in rows:
            user_id = str(row.get(user_key) or "").strip()
            if not user_id:
                continue
            posts = [
                normalize_post(post)
                for post in (row.get(posts_key) or [])
                if isinstance(post, dict)
            ]
            yield user_id, posts
        return

    if not any(key in sample for key in TEXT_ALIASES + TITLE_ALIASES):
        raise ValueError(
            f"{source_name}: rows are neither user-grouped (no list column among "
            f"{list(POST_LIST_ALIASES)}) nor post-shaped (no column among "
            f"{list(TEXT_ALIASES + TITLE_ALIASES)}); saw columns {sorted(sample)}"
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        user_id = str(row.get(user_key) or "").strip()
        if not user_id:
            continue
        grouped[user_id].append(normalize_post(row))
    yield from grouped.items()


def list_relevant_shards(
    *,
    repo_id: str,
    artifact_prefix: str,
    years: set[str] | None,
    token: str | bool | None,
) -> list[str]:
    from huggingface_hub import list_repo_files

    files = list_repo_files(repo_id, repo_type="dataset", token=token)
    prefix = artifact_prefix.rstrip("/") + "/"
    wanted = []
    for filename in files:
        if not filename.startswith(prefix) or not filename.endswith(".parquet"):
            continue
        parts = filename[len(prefix) :].split("/")
        if len(parts) != 2:
            continue
        year_part, _batch_name = parts
        if years and year_part not in years:
            continue
        wanted.append(filename)
    return sorted(wanted)


def read_shard_rows(
    repo_id: str, filename: str, token: str | bool | None
) -> list[dict[str, Any]]:
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq

    local_path = hf_hub_download(
        repo_id=repo_id,
        repo_type="dataset",
        filename=filename,
        token=token,
    )
    return pq.read_table(local_path).to_pylist()


def _ordered_all_users(histories: dict[str, list[dict[str, Any]]]) -> list[str]:
    return sorted(
        histories,
        key=lambda user_id: (0, int(user_id)) if user_id.isdigit() else (1, user_id),
    )


def write_histories(
    path: Path,
    histories: dict[str, list[dict[str, Any]]],
    ordered_user_ids: list[str],
    *,
    min_posts: int,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    required = max(1, min_posts)
    count = 0
    with opener(path, "wt", encoding="utf-8") as fh:
        for user_id in ordered_user_ids:
            posts = sorted(
                histories.get(user_id, []),
                key=lambda post: (post.get("timestamp") is None, post.get("timestamp") or 0),
            )
            if len(posts) < required:
                continue
            fh.write(
                json.dumps(
                    {
                        "user_id": user_id,
                        "post_count": len(posts),
                        "posts": posts,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            count += 1
    return count


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--user-ids",
        type=Path,
        help="JSONL, Markdown, or text file containing Stack Overflow user IDs.",
    )
    selection.add_argument(
        "--all-users",
        action="store_true",
        help="Export every user found in the selected shards.",
    )
    parser.add_argument(
        "--years",
        default="",
        help="Comma-separated year folders to read (default: all available).",
    )
    parser.add_argument(
        "--min-posts",
        type=int,
        default=0,
        help="Skip users with fewer posts than this (0 means any non-empty history).",
    )
    parser.add_argument(
        "--repo-id",
        default=os.environ.get("STACKEXCHANGE_PERSONA_REPO_ID", DEFAULT_REPO_ID),
    )
    parser.add_argument(
        "--artifact-prefix",
        default=os.environ.get(
            "STACKEXCHANGE_PERSONA_ARTIFACT_PREFIX", DEFAULT_ARTIFACT_PREFIX
        ),
    )
    parser.add_argument("--max-users", type=int, default=0, help="0 means all user IDs.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--token",
        default=None,
        help="Optional HF token. If omitted, huggingface_hub uses local login state.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    token: str | bool | None = args.token or None
    years = {part.strip() for part in args.years.split(",") if part.strip()} or None

    requested_user_ids: list[str] | None = None
    selected_user_ids: set[str] | None = None
    if args.user_ids:
        requested_user_ids = load_user_ids(args.user_ids, limit=args.max_users)
        selected_user_ids = set(requested_user_ids)
        log(f"Loading {len(requested_user_ids):,} users from {args.repo_id}/{args.artifact_prefix}")
    else:
        log(f"Loading all users from {args.repo_id}/{args.artifact_prefix}")

    shards = list_relevant_shards(
        repo_id=args.repo_id,
        artifact_prefix=args.artifact_prefix,
        years=years,
        token=token,
    )
    if not shards:
        raise RuntimeError("No matching HF Parquet shards found for requested years.")
    log(f"Found {len(shards):,} matching Parquet shards")

    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, filename in enumerate(shards, start=1):
        log(f"[{index:,}/{len(shards):,}] {filename}")
        rows = read_shard_rows(args.repo_id, filename, token)
        for user_id, posts in extract_user_rows(rows, source_name=filename):
            if selected_user_ids is not None and user_id not in selected_user_ids:
                continue
            histories[user_id].extend(posts)

    if requested_user_ids is None:
        ordered_user_ids = _ordered_all_users(histories)
        if args.max_users:
            ordered_user_ids = ordered_user_ids[: args.max_users]
    else:
        ordered_user_ids = requested_user_ids

    written = write_histories(
        args.output, histories, ordered_user_ids, min_posts=args.min_posts
    )
    missing = len(ordered_user_ids) - written
    log(f"Wrote {written:,} user histories to {args.output}")
    if missing:
        log(f"{missing:,} requested users had no matching posts in selected shards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
```
Expected: PASS — 10 passed

- [ ] **Step 5: Commit**

```bash
PYTHONPYCACHEPREFIX=/tmp/matraix_pycache_check python3 -m py_compile \
  persona/existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py
git add persona/existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py \
        tests/unit/matraix/test_persona_collab_packages.py
git commit -m "Add HF Stack Overflow user-history exporter"
```

---

### Task 5: Solver fold-routing and prompt support

**Files:**
- Modify: `persona/existing_data_curation/wiki_collab/collab_kit/solver.py`
- Test: `tests/unit/matraix/test_persona_collab_packages.py`

**Interfaces:**
- Consumes: SO task shape from Task 3 (`source == "stackoverflow_persona"`, `cv_fold_texts` with `post_ids`, `min_support_folds`).
- Produces: `attribute()` routes ANY profile with a non-empty `cv_fold_texts` list through fold voting; `merge_fold_fields` (new name) with `merge_amazon_fold_fields` kept as an alias; `build_prompt` selects wording by `source`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/matraix/test_persona_collab_packages.py`:

```python
def _load_solver_module():
    import importlib.util

    repo_root = Path(__file__).resolve().parents[3]
    solver_path = (
        repo_root / "persona/existing_data_curation/wiki_collab/collab_kit/solver.py"
    )
    spec = importlib.util.spec_from_file_location(
        "collab_kit_solver_under_test", solver_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_solver_routes_fold_tasks_through_fold_voting(monkeypatch) -> None:
    solver = _load_solver_module()
    dimensions = [
        {
            "id": "att_online_reviews",
            "label": "Attitude: Online reviews",
            "category": "Behavior: Preferences",
            "description": "Stance toward online reviews.",
            "values": ["trusts reviews", "skeptical of reviews"],
        }
    ]
    so_profile = {
        "source": "stackoverflow_persona",
        "min_support_folds": 2,
        "profile_text": "combined",
        "cv_fold_texts": [
            {
                "fold_id": 1,
                "post_ids": ["p0001"],
                "profile_text": "=== Fold 1/2 ===\n[p0001]\ntext: I always trust reviews.",
            },
            {
                "fold_id": 2,
                "post_ids": ["p0002"],
                "profile_text": "=== Fold 2/2 ===\n[p0002]\ntext: Reviews guide me.",
            },
        ],
    }

    calls: list = []

    def fake_single_pass(profile, dims, backend, model, effort):
        calls.append(profile.get("cv_fold_id"))
        return [
            {
                "field_id": "att_online_reviews",
                "value": "trusts reviews",
                "confidence": 0.8,
                "evidence": "trust",
                "assignment_type": "direct",
            }
        ]

    monkeypatch.setattr(solver, "_attribute_single_pass", fake_single_pass)

    fields = solver.attribute(so_profile, dimensions, backend="claude-code-acp")
    assert calls == [1, 2]
    merged = {field["field_id"]: field for field in fields}
    assert merged["att_online_reviews"]["value"] == "trusts reviews"

    calls.clear()
    wiki_profile = {"qid": "Q1", "profile_text": "plain wiki text"}
    fields = solver.attribute(wiki_profile, dimensions, backend="claude-code-acp")
    assert calls == [None]
    assert fields[0]["value"] == "trusts reviews"

    prompt = solver.build_prompt(so_profile, dimensions)
    assert "Stack Overflow" in prompt
    assert solver.merge_fold_fields is solver.merge_amazon_fold_fields
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py::test_solver_routes_fold_tasks_through_fold_voting -q
```
Expected: FAIL — SO profile is not routed through folds (`calls == [None]` instead of `[1, 2]`) because the gate checks `source == "amazon_reviews_2023"`.

- [ ] **Step 3: Modify solver.py**

Three edits in `persona/existing_data_curation/wiki_collab/collab_kit/solver.py`:

1. In `build_prompt`, replace the opening selection (the `is_amazon = ...` block through the `else:` opening assignment) with:

```python
    source = str(profile.get("source") or "")
    is_amazon = source == "amazon_reviews_2023"
    is_stackoverflow = source == "stackoverflow_persona"
    if is_amazon:
        opening = (
            "You are extracting persona-attribution fields from Amazon review "
            "evidence for one reviewer."
        )
    elif is_stackoverflow:
        opening = (
            "You are extracting persona-attribution fields from a Stack Overflow "
            "user's public posting history."
        )
    else:
        opening = (
            "You are extracting persona-attribution fields from a "
            "Wikipedia-derived profile."
        )
```

2. In the same function, replace the `if is_amazon:` rules block (keeping the amazon lines byte-identical) with a three-way branch:

```python
    if is_amazon:
        lines += [
            "- Evidence for non-null values must come from the supplied review "
            "title/text in profile_text, not outside knowledge.",
            "- Private, sensitive, demographic, medical, financial, or psychological "
            "attributes require direct statements in the supplied review title/text; "
            "when unsure, prefer null/unsupported.",
        ]
    elif is_stackoverflow:
        lines += [
            "- Evidence for non-null values must come from the supplied post "
            "titles/bodies/tags in profile_text, not outside knowledge.",
            "- Skills, expertise, tools, and interests may be inferred from "
            "demonstrated posting behavior.",
            "- Private, sensitive, demographic, medical, financial, or psychological "
            "attributes require direct statements in the supplied posts; "
            "when unsure, prefer null/unsupported.",
        ]
    else:
        lines += [
            "- Do not infer private, sensitive, or psychological traits unless directly "
            "stated; when unsure, prefer null/unsupported.",
        ]
```

3. Rename `merge_amazon_fold_fields` to `merge_fold_fields` (same body; update its docstring first line to `"""Merge per-fold attribution outputs by exact field/value votes."""`), and immediately after the function add:

```python
# Backwards-compatible alias for kits already in the wild.
merge_amazon_fold_fields = merge_fold_fields
```

4. In `attribute`, replace the routing block:

```python
    if profile.get("cv_fold_texts"):
        fold_profiles = _fold_profiles(profile)
        fold_count = len(fold_profiles)
        default_support = min(2, fold_count)
        try:
            min_support = int(profile.get("min_support_folds") or default_support)
        except (TypeError, ValueError):
            min_support = default_support
        min_support = max(1, min_support)
        fold_outputs = [
            _attribute_single_pass(fold_profile, dimensions, backend, model, effort)
            for fold_profile in fold_profiles
        ]
        return merge_fold_fields(
            fold_outputs,
            dimensions,
            min_support_folds=min_support,
            fold_count=fold_count,
        )
```

Also update `_fold_profiles`'s docstring to `"""Return one profile per non-empty CV fold."""`.

- [ ] **Step 4: Run the full test file to verify everything passes**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
```
Expected: PASS — 11 passed

- [ ] **Step 5: Commit**

```bash
PYTHONPYCACHEPREFIX=/tmp/matraix_pycache_check python3 -m py_compile \
  persona/existing_data_curation/wiki_collab/collab_kit/solver.py
git add persona/existing_data_curation/wiki_collab/collab_kit/solver.py \
        tests/unit/matraix/test_persona_collab_packages.py
git commit -m "Route fold-structured tasks generically in collab solver"
```

---

### Task 6: Owner-side Stack Overflow database

**Files:**
- Create: `persona/existing_data_curation/wiki_collab/stackoverflow_collab.py`
- Create: `persona/existing_data_curation/scripts/build_stackoverflow_collab_db.py`
- Test: `tests/unit/matraix/test_persona_collab_packages.py`

**Interfaces:**
- Consumes: `wiki_collab.core` (`canonical_json`, `compute_input_sha256`, `load_jsonl`, `sha256_file`, `write_json`); `wiki_collab.amazon_collab.create_schema` (the shared `profiles` SQLite schema).
- Produces: `build_stackoverflow_profile_database(*, user_histories: Path, out_db: Path, manifest_path: Path, dataset_id: str, limit: int | None = None) -> dict`; `load_stackoverflow_profiles(db_path: Path, range_start: int, range_end: int) -> list[StackOverflowProfileRow]`; constants `STACKOVERFLOW_SOURCE_TYPE = "stackoverflow_persona"`, `STACKOVERFLOW_PROTOCOL_ID = "stackoverflow_persona_inference_v1"`. DB rows carry the same `task_id`/`qid` convention as package tasks so `merge_collab_results.py --db` identity checks match.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/matraix/test_persona_collab_packages.py`:

```python
def test_stackoverflow_collab_db_matches_package_identity(tmp_path: Path) -> None:
    from persona.existing_data_curation.wiki_collab.stackoverflow_collab import (
        build_stackoverflow_profile_database,
        load_stackoverflow_profiles,
    )

    histories = tmp_path / "so_db_histories.jsonl"
    _write_jsonl(
        histories,
        [
            {
                "user_id": "42",
                "posts": [
                    {"post_id": "1", "post_type": "question", "title": "T", "text": "A"},
                    {"post_id": "2", "post_type": "answer", "title": "", "text": "B"},
                ],
            }
        ],
    )

    manifest = build_stackoverflow_profile_database(
        user_histories=histories,
        out_db=tmp_path / "so_profiles.sqlite",
        manifest_path=tmp_path / "so_manifest.json",
        dataset_id="so_test",
    )
    assert manifest["row_count"] == 1
    assert manifest["source_type"] == "stackoverflow_persona"

    rows = load_stackoverflow_profiles(tmp_path / "so_profiles.sqlite", 0, 1)
    assert rows[0].task_id == "stackoverflow_persona:42"
    assert rows[0].qid == "so_user:42"
    assert rows[0].user_id == "42"
    assert rows[0].payload["posts"][0]["post_id"] == "1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py::test_stackoverflow_collab_db_matches_package_identity -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'persona.existing_data_curation.wiki_collab.stackoverflow_collab'`

- [ ] **Step 3: Create the module and CLI**

Create `persona/existing_data_curation/wiki_collab/stackoverflow_collab.py`:

```python
#!/usr/bin/env python3
"""Stack Overflow posting-history helpers for the offline persona collaboration runner."""

from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from pathlib import Path
from typing import Any

from persona.existing_data_curation.wiki_collab.amazon_collab import create_schema
from persona.existing_data_curation.wiki_collab.core import (
    canonical_json,
    compute_input_sha256,
    load_jsonl,
    sha256_file,
    write_json,
)


STACKOVERFLOW_SOURCE_TYPE = "stackoverflow_persona"
STACKOVERFLOW_PROTOCOL_ID = "stackoverflow_persona_inference_v1"


@dataclass(frozen=True)
class StackOverflowProfileRow:
    global_idx: int
    task_id: str
    qid: str
    title: str
    source_url: str
    user_id: str
    input_sha256: str
    payload: dict[str, Any]


def stackoverflow_input_payload(global_idx: int, user_row: dict[str, Any]) -> dict[str, Any]:
    user_id = str(user_row.get("user_id") or "")
    return {
        "global_idx": global_idx,
        "task_id": f"{STACKOVERFLOW_SOURCE_TYPE}:{user_id}",
        "qid": f"so_user:{user_id}",
        "source_type": STACKOVERFLOW_SOURCE_TYPE,
        "user_id": user_id,
        "posts": user_row.get("posts") or [],
        "metadata": user_row.get("metadata") or {},
    }


def build_stackoverflow_profile_database(
    *,
    user_histories: Path,
    out_db: Path,
    manifest_path: Path,
    dataset_id: str,
    limit: int | None = None,
) -> dict[str, Any]:
    out_db.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if out_db.exists():
        out_db.unlink()
    conn = sqlite3.connect(out_db)
    create_schema(conn)
    row_count = 0
    source_index = 0
    for source_index, user_row in enumerate(load_jsonl(user_histories), start=1):
        if limit is not None and row_count >= limit:
            break
        payload = stackoverflow_input_payload(row_count, user_row)
        input_sha256 = compute_input_sha256(payload)
        user_id = str(payload["user_id"])
        title = (
            f"Stack Overflow user {user_id}"
            if user_id
            else f"Stack Overflow user {row_count}"
        )
        conn.execute(
            """
            insert into profiles (
              global_idx, task_id, qid, title, source_url, source_type, user_id,
              profile_text, payload_json, input_sha256
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_count,
                payload["task_id"],
                payload["qid"],
                title,
                f"stackexchange://stackoverflow/user/{user_id}",
                STACKOVERFLOW_SOURCE_TYPE,
                user_id,
                _summary_text(payload),
                canonical_json(payload),
                input_sha256,
            ),
        )
        row_count += 1
    conn.commit()
    conn.close()
    manifest = {
        "dataset_id": dataset_id,
        "row_count": row_count,
        "db_file": out_db.name,
        "db_sha256": sha256_file(out_db),
        "source_type": STACKOVERFLOW_SOURCE_TYPE,
        "source_user_histories": str(user_histories),
        "source_row_count_read": source_index if row_count else 0,
        "format": "sqlite",
    }
    write_json(manifest_path, manifest)
    return manifest


def load_stackoverflow_profiles(
    db_path: Path, range_start: int, range_end: int
) -> list[StackOverflowProfileRow]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [
        _row_from_sqlite(dict(row))
        for row in conn.execute(
            """
            select global_idx, task_id, qid, title, source_url, user_id, payload_json, input_sha256
            from profiles
            where global_idx >= ? and global_idx < ?
            order by global_idx
            """,
            (range_start, range_end),
        )
    ]
    conn.close()
    return rows


def _row_from_sqlite(row: dict[str, Any]) -> StackOverflowProfileRow:
    return StackOverflowProfileRow(
        global_idx=int(row["global_idx"]),
        task_id=str(row["task_id"]),
        qid=str(row["qid"]),
        title=str(row["title"]),
        source_url=str(row["source_url"]),
        user_id=str(row["user_id"]),
        input_sha256=str(row["input_sha256"]),
        payload=json.loads(row["payload_json"]),
    )


def _summary_text(payload: dict[str, Any]) -> str:
    post_count = len(payload.get("posts") or [])
    return (
        f"Stack Overflow posting-derived user profile for {payload.get('user_id')}; "
        f"{post_count} posts."
    )
```

Create `persona/existing_data_curation/scripts/build_stackoverflow_collab_db.py`:

```python
#!/usr/bin/env python3
"""Build a canonical SQLite user database for Stack Overflow collaboration runs."""

from __future__ import annotations

import argparse

from persona.existing_data_curation.wiki_collab.stackoverflow_collab import (
    build_stackoverflow_profile_database,
)
from persona.existing_data_curation.wiki_collab.core import canonical_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-histories", required=True, type=str)
    parser.add_argument("--out-db", required=True, type=str)
    parser.add_argument("--manifest", required=True, type=str)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> int:
    from pathlib import Path

    args = parse_args()
    manifest = build_stackoverflow_profile_database(
        user_histories=Path(args.user_histories),
        out_db=Path(args.out_db),
        manifest_path=Path(args.manifest),
        dataset_id=args.dataset_id,
        limit=args.limit,
    )
    print(canonical_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the full test file to verify everything passes**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
```
Expected: PASS — 12 passed

- [ ] **Step 5: Commit**

```bash
PYTHONPYCACHEPREFIX=/tmp/matraix_pycache_check python3 -m py_compile \
  persona/existing_data_curation/wiki_collab/stackoverflow_collab.py \
  persona/existing_data_curation/scripts/build_stackoverflow_collab_db.py
git add persona/existing_data_curation/wiki_collab/stackoverflow_collab.py \
        persona/existing_data_curation/scripts/build_stackoverflow_collab_db.py \
        tests/unit/matraix/test_persona_collab_packages.py
git commit -m "Add Stack Overflow owner-side collab database"
```

---

### Task 7: Shell wrapper, README section, portability test

**Files:**
- Create: `persona/existing_data_curation/scripts/make_stackoverflow_package.sh`
- Modify: `persona/existing_data_curation/README.md`
- Modify: `tests/unit/matraix/test_persona_collab_packages.py` (extend `test_package_owner_scripts_document_portable_data_inputs`)

**Interfaces:**
- Consumes: Task 3's builder CLI; Task 4's exporter (documented in README); Task 2's config.
- Produces: `./make_stackoverflow_package.sh USER_HISTORIES_JSONL START:END [worker_id] [supported|all]`.

- [ ] **Step 1: Extend the portability test (failing first)**

In `tests/unit/matraix/test_persona_collab_packages.py`, replace the body of `test_package_owner_scripts_document_portable_data_inputs` with:

```python
def test_package_owner_scripts_document_portable_data_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    wiki_wrapper = (
        repo_root / "persona/existing_data_curation/scripts/make_package.sh"
    ).read_text(encoding="utf-8")
    amazon_wrapper = (
        repo_root / "persona/existing_data_curation/scripts/make_amazon_package.sh"
    ).read_text(encoding="utf-8")
    stackoverflow_wrapper = (
        repo_root
        / "persona/existing_data_curation/scripts/make_stackoverflow_package.sh"
    ).read_text(encoding="utf-8")
    amazon_exporter = (
        repo_root
        / "persona/existing_data_curation/scripts/export_hf_amazon_user_histories.py"
    ).read_text(encoding="utf-8")
    stackoverflow_exporter = (
        repo_root
        / "persona/existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py"
    ).read_text(encoding="utf-8")
    owner_readme = (
        repo_root / "persona/existing_data_curation/README.md"
    ).read_text(encoding="utf-8")
    amazon_manifest = json.loads(
        (
            repo_root / "persona/existing_data_curation/configs/amazon_reviews_2023.json"
        ).read_text(encoding="utf-8")
    )
    stackexchange_manifest = json.loads(
        (
            repo_root
            / "persona/existing_data_curation/configs/stackexchange_persona.json"
        ).read_text(encoding="utf-8")
    )

    checked_text = "\n".join(
        [
            wiki_wrapper,
            amazon_wrapper,
            stackoverflow_wrapper,
            amazon_exporter,
            stackoverflow_exporter,
            owner_readme,
        ]
    )
    assert "/data2/" not in checked_text
    assert "zonglin" not in checked_text
    assert 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"' in wiki_wrapper
    assert 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"' in amazon_wrapper
    assert (
        'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"'
        in stackoverflow_wrapper
    )
    assert ': "${WIKI_CLEAN_DIR:?Set WIKI_CLEAN_DIR' in wiki_wrapper
    assert '"MatrAIx/MatrAIx"' not in amazon_exporter
    assert '"MatrAIx/MatrAIx"' not in stackoverflow_exporter
    assert "load_default_source_config" in amazon_exporter
    assert "load_default_source_config" in stackoverflow_exporter
    assert amazon_manifest["source"]["repo_id"] == "MatrAIx2026/MatrAIx2026"
    assert amazon_manifest["format"] == "partitioned parquet"
    assert stackexchange_manifest["source"]["repo_id"] == "MatrAIx2026/MatrAIx2026"
    assert stackexchange_manifest["format"] == "partitioned parquet (by year)"
    assert "Stack Overflow Packages" in owner_readme
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py::test_package_owner_scripts_document_portable_data_inputs -q
```
Expected: FAIL with `FileNotFoundError` for `make_stackoverflow_package.sh`

- [ ] **Step 3: Create the wrapper**

Create `persona/existing_data_curation/scripts/make_stackoverflow_package.sh` (then `chmod +x` it):

```bash
#!/usr/bin/env bash
#
# Owner-side one-liner: turn a Stack Overflow user-history slice into a
# ready-to-send collaborator package.
#
#   ./make_stackoverflow_package.sh /path/to/user_histories.jsonl.gz 0:100 alice
#
# Collaborators receive a lightweight .tar.gz (tasks.jsonl + dimensions.json +
# collab_kit/) -- no raw source JSONL and no owner-side database.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${MATRIX_REPO_ROOT:-$(cd "${SCRIPT_DIR}/../../.." && pwd)}"
DATASET_ID="${STACKOVERFLOW_DATASET_ID:-matraix_stackoverflow_persona_v1}"
DIMENSIONS="${MATRIX_DIMENSIONS:-${REPO_ROOT}/persona/dimensions.json}"
CACHE_ROOT="${MATRIX_PACKAGE_CACHE_ROOT:-${TMPDIR:-/tmp}}"
OUT_ROOT="${MATRIX_PACKAGE_OUT_ROOT:-${CACHE_ROOT}/matraix_packages}"

USER_HISTORIES="${1:-}"
RANGE="${2:-}"
WORKER_ID="${3:-worker}"
DIMENSION_SCOPE="${4:-supported}"

if [[ -z "${USER_HISTORIES}" || ! -f "${USER_HISTORIES}" ]]; then
  echo "usage: $0 USER_HISTORIES_JSONL START:END [worker_id] [supported|all]" >&2
  exit 2
fi
if [[ -z "${RANGE}" || ! "${RANGE}" =~ ^[0-9]+:[0-9]+$ ]]; then
  echo "usage: $0 USER_HISTORIES_JSONL START:END [worker_id] [supported|all]" >&2
  echo "  e.g. $0 /data/stackoverflow/user_histories.jsonl.gz 0:100 alice" >&2
  exit 2
fi
if [[ "${DIMENSION_SCOPE}" != "supported" && "${DIMENSION_SCOPE}" != "all" ]]; then
  echo "dimension scope must be 'supported' or 'all'" >&2
  exit 2
fi

START="${RANGE%%:*}"
END="${RANGE##*:}"
ASSIGNMENT_ID="SO_${START}_${END}"
OUT_DIR="${OUT_ROOT}/${ASSIGNMENT_ID}_${WORKER_ID}"

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}"

DATASET_SHA256="$(python3 -c 'import hashlib,sys; d=hashlib.sha256(); f=open(sys.argv[1], "rb"); [d.update(c) for c in iter(lambda: f.read(1024*1024), b"")]; print(d.hexdigest())' "${USER_HISTORIES}")"

SCOPE_ARGS=()
[[ "${DIMENSION_SCOPE}" == "all" ]] && SCOPE_ARGS=(--all-dimensions)

echo ">> packaging Stack Overflow slice ${RANGE} for '${WORKER_ID}'"
python3 persona/existing_data_curation/scripts/make_stackoverflow_collab_package.py \
  --user-histories "${USER_HISTORIES}" \
  --dimensions "${DIMENSIONS}" \
  --range "${RANGE}" \
  --out-dir "${OUT_DIR}" \
  --assignment-id "${ASSIGNMENT_ID}" \
  --worker-id "${WORKER_ID}" \
  --dataset-id "${DATASET_ID}" \
  --dataset-sha256 "${DATASET_SHA256}" \
  --force \
  "${SCOPE_ARGS[@]}" >/dev/null

ARCHIVE="${OUT_DIR}.tar.gz"
echo ""
echo "done. send this file to your collaborator:"
echo "   ${ARCHIVE}"
```

Run `chmod +x persona/existing_data_curation/scripts/make_stackoverflow_package.sh`.

- [ ] **Step 4: Add the README section**

In `persona/existing_data_curation/README.md`:

1. In the "Package Owner Data Setup" recommended layout block, add a line so it reads:

```text
${MATRIX_DATA_ROOT}/
  wiki/enwiki_20260601/person_pages_clean/*.jsonl.gz
  amazon_reviews_2023/user_histories.jsonl.gz
  stackexchange_persona/user_histories.jsonl.gz
```

2. Insert this section between the end of "Amazon Downstream Workflows" and "## Collaborator Contract":

```markdown
## Stack Overflow Packages

Stack Overflow package generation consumes normalized user posting histories
(JSONL/JSONL.GZ, one user per row):

```json
{
  "user_id": "12345",
  "post_count": 42,
  "posts": [
    {
      "post_type": "question",
      "timestamp": 1700000000,
      "tags": ["python", "pandas"],
      "title": "...",
      "text": "...",
      "score": 12,
      "accepted": null
    }
  ]
}
```

The package builder needs `user_id` plus a `posts` list. Each usable post
should have a non-empty title or body text. The renderer also uses optional
fields such as `date`, `post_id`, and `accepted` when present.

### Export From Hugging Face

The data entrypoint is the gated artifact documented in
`configs/stackexchange_persona.json`:

```text
repo_id: MatrAIx2026/MatrAIx2026
artifact: StackExchange_Persona/<year>/stackoverflow_persona_batch_*.parquet
```

Request access to the dataset on Hugging Face and run `huggingface-cli login`
first. The exporter requires `huggingface_hub` and `pyarrow` at runtime. The
exporter's parquet column mapping is alias-driven and pending verification
against the gated artifact; if it reports unexpected columns, extend the alias
tables at the top of the script.

Export selected user histories:

```bash
python3 persona/existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py \
  --user-ids /path/to/so_user_ids.md \
  --output "${MATRIX_DATA_ROOT}/stackexchange_persona/user_histories.jsonl.gz"
```

`--user-ids` accepts a Markdown/text file with numeric Stack Overflow user IDs
or a JSONL/JSONL.GZ file with `user_id` fields. Use `--all-users` (optionally
with `--years 2024,2025` and `--min-posts 10`) to export everyone found in the
selected year folders.

Then create collaborator packages:

```bash
persona/existing_data_curation/scripts/make_stackoverflow_package.sh \
  "${MATRIX_DATA_ROOT}/stackexchange_persona/user_histories.jsonl.gz" \
  0:100 alice
```

Pass `all` as the fourth argument to include every persona dimension instead
of the Stack Overflow-supported subset (default scope filters via
`configs/stackoverflow_evidence_mapping.json`).
```

3. In the "## Collaborator Contract" closing sentence, change "They do not need the source Wiki/Amazon data" to "They do not need the source Wiki/Amazon/Stack Overflow data".

- [ ] **Step 5: Run the full test file and bash syntax check**

Run:
```bash
bash -n persona/existing_data_curation/scripts/make_stackoverflow_package.sh
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
```
Expected: bash exits 0; pytest PASS — 12 passed

- [ ] **Step 6: Commit**

```bash
git add persona/existing_data_curation/scripts/make_stackoverflow_package.sh \
        persona/existing_data_curation/README.md \
        tests/unit/matraix/test_persona_collab_packages.py
git commit -m "Add Stack Overflow package wrapper and docs"
```

---

### Task 8: End-to-end smoke, full validation, push, PR

**Files:**
- No new files (validation + delivery only).

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: End-to-end smoke test via the wrapper**

Build a real package from synthetic data through the shell wrapper (proves CLI + wrapper wiring, not just the Python API):

```bash
SMOKE=$(mktemp -d)
cat > "${SMOKE}/histories.jsonl" <<'EOF'
{"user_id": "42", "posts": [{"post_id": "1", "post_type": "question", "timestamp": 1700000000, "tags": ["python"], "title": "How to test?", "text": "Body one.", "score": 3}, {"post_id": "2", "post_type": "answer", "timestamp": 1707000000, "tags": ["python"], "title": "", "text": "Body two.", "score": 5, "accepted": true}]}
{"user_id": "43", "posts": [{"post_id": "3", "post_type": "question", "timestamp": 1690000000, "tags": ["bash"], "title": "Quoting?", "text": "Body three.", "score": 1}, {"post_id": "4", "post_type": "answer", "timestamp": 1695000000, "tags": ["bash"], "title": "", "text": "Body four.", "score": 2}]}
EOF
MATRIX_PACKAGE_OUT_ROOT="${SMOKE}/out" \
  persona/existing_data_curation/scripts/make_stackoverflow_package.sh \
  "${SMOKE}/histories.jsonl" 0:2 smoketester
tar -tzf "${SMOKE}/out/SO_0_2_smoketester.tar.gz" | head -5
rm -rf "${SMOKE}"
```

Expected: wrapper prints `done. send this file to your collaborator:` with the archive path; `tar -tzf` lists `SO_0_2_smoketester/...` entries including `tasks.jsonl`.

- [ ] **Step 2: Full validation suite (mirrors PR #143's)**

```bash
PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
bash -n persona/existing_data_curation/scripts/make_package.sh
bash -n persona/existing_data_curation/scripts/make_amazon_package.sh
bash -n persona/existing_data_curation/scripts/make_stackoverflow_package.sh
PYTHONPYCACHEPREFIX=/tmp/matraix_pycache_check python3 -m py_compile \
  persona/existing_data_curation/scripts/history_package_common.py \
  persona/existing_data_curation/scripts/make_amazon_collab_package.py \
  persona/existing_data_curation/scripts/make_stackoverflow_collab_package.py \
  persona/existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py \
  persona/existing_data_curation/scripts/build_stackoverflow_collab_db.py \
  persona/existing_data_curation/wiki_collab/stackoverflow_collab.py \
  persona/existing_data_curation/wiki_collab/collab_kit/solver.py
```

Expected: all pass, 12 pytest tests green.

- [ ] **Step 3: Push the branch and open the stacked PR**

```bash
git push -u origin stackoverflow-collab-package
gh pr create --repo MatrAIx-ai/MatrAIx --base main \
  --title "Add Stack Overflow persona collaboration packages" \
  --body "$(cat <<'EOF'
## Summary
- add a Stack Overflow source to the persona collaborator-package toolchain at parity with the amazon source: HF exporter, CV-fold package builder, evidence mapping, one-liner wrapper, and owner-side SQLite DB for merge identity checks
- extract the source-neutral fold/truncation machinery from the amazon builder into a shared `history_package_common.py` (amazon behavior unchanged, covered by its existing test)
- route fold-structured tasks generically in `collab_kit/solver.py` (duck-typed on `cv_fold_texts`) and add Stack Overflow prompt wording

> **Stacked on #143** — contains its commits; only the commits after `Document Amazon subscription effort choices` are new here. Rebase/merge after #143 lands.

## Notes for reviewers
- The HF `StackExchange_Persona` artifact is gated; the exporter's parquet column mapping is an alias table pending verification against the real schema (documented in the design doc and README). Everything else is exercised by unit tests.
- The SO owner DB stores `task_id`/`qid` matching the package tasks so `merge_collab_results.py --db` identity checks line up (the amazon DB currently uses a different `task_id` convention than amazon packages — reported separately on #143).

## Validation
- PYTHONPATH=. python3 -B -m pytest -c /tmp/empty-pytest.ini tests/unit/matraix/test_persona_collab_packages.py -q
- bash -n persona/existing_data_curation/scripts/make_stackoverflow_package.sh
- PYTHONPYCACHEPREFIX=/tmp/matraix_pycache_check python3 -m py_compile persona/existing_data_curation/scripts/history_package_common.py persona/existing_data_curation/scripts/make_stackoverflow_collab_package.py persona/existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py persona/existing_data_curation/wiki_collab/stackoverflow_collab.py
- end-to-end wrapper smoke test (synthetic 2-user history → SO_0_2 package archive)
EOF
)"
```

Expected: PR created targeting `main`. Report the PR URL to the user.

- [ ] **Step 4: Report schema-verification follow-up**

Remind the user (in the final summary, not in code): once they have HF access, run the exporter against one real shard (e.g. `--years 2025 --all-users --max-users 5 --min-posts 1`) and confirm the alias table matches; extend aliases if the error message lists unknown columns.

---

## Plan Self-Review (completed)

- **Spec coverage:** spec §1 identity → Tasks 3/6; §2 exporter → Task 4; §3 shared module → Task 1; §4 builder → Task 3; §5 mapping → Task 2; §6 solver → Task 5; §7 owner DB → Task 6; §8 wrapper/config/docs → Tasks 2/7; §9 tests → Tasks 1–7 + validation in Task 8; §10 follow-ups → Task 8 Step 4 and PR body note.
- **Placeholder scan:** no TBDs; every code step contains full code.
- **Type consistency:** `build_cv_fold_texts(rendered_items, effective_cv_folds, *, id_field)` consistent across Tasks 1/3; `merge_fold_fields` naming consistent between Task 5 code and test; exporter monkeypatch targets (`list_relevant_shards(*, repo_id, artifact_prefix, years, token)`, `read_shard_rows(repo_id, filename, token)`) match the module signatures.
