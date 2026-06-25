# PR 73/81 Amazon Reviews 2023 Collaboration Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Selectively integrate PR 73's Amazon Reviews 2023 evidence-profile inference workflow and PR 81's Amazon collaboration adapter without regressing the current wiki collaboration runner or its per-run model provenance behavior.

**Architecture:** Keep the Amazon path parallel to the existing wiki path. PR 73 provides the Amazon review-memory and schema-mapping pipeline; PR 81 wraps that pipeline in the collaboration archive shape by converting user histories into a SQLite `profiles` table and running assigned index ranges. The generic wiki runner remains untouched except for shared validation/provenance compatibility.

**Tech Stack:** Python 3.11+, SQLite, JSONL/Gzip/Tar archives, pytest/unittest, existing `personas.existing_data_curation` scripts, OpenAI API for non-mock Amazon inference.

---

## File Structure

Core Amazon Reviews 2023 workflow from PR 73:
- Modify: `personas/existing_data_curation/modal_amazon_user_index.py`
  - Eligible Amazon reviewer pool, temporal train/validation split, fulfillment/template filtering, metadata sidecar export.
- Modify: `personas/existing_data_curation/scripts/infer_amazon_review_dimensions.py`
  - Evidence-profile review memory, product metadata attachment, rating-only summary, schema routing/recall, YAML export.
- Modify: `personas/existing_data_curation/amazon_review_evidence_mapping.json`
  - Broad evidence categories mapped to allowed persona schema categories.
- Create: `personas/existing_data_curation/scripts/evaluate_amazon_persona_rating_holdout.py`
  - Holdout evaluation against validation reviews.

Amazon collaboration adapter from PR 81:
- Create: `personas/existing_data_curation/protocols/amazon_review_persona_inference_v1/input.schema.json`
- Create: `personas/existing_data_curation/protocols/amazon_review_persona_inference_v1/output.schema.json`
- Create: `personas/existing_data_curation/protocols/amazon_review_persona_inference_v1/prompt.md`
- Create: `personas/existing_data_curation/protocols/amazon_review_persona_inference_v1/protocol_manifest.json`
- Create: `personas/existing_data_curation/wiki_collab/amazon_collab.py`
  - Amazon history JSONL to collaboration SQLite database.
- Create: `personas/existing_data_curation/scripts/build_amazon_collab_db.py`
  - CLI wrapper for the Amazon database builder.
- Create: `personas/existing_data_curation/worker_kit/run_amazon_range.py`
  - Offline Amazon range runner that calls the PR 73 evidence-profile pipeline.
- Create: `personas/existing_data_curation/scripts/validate_amazon_results.py`
  - Amazon-specific archive validator.
- Create: `tests/personas/existing_data_curation/test_amazon_review_core_unittest.py`
- Create: `tests/personas/existing_data_curation/test_amazon_collab_unittest.py`

Files to protect:
- Do not replace `personas/existing_data_curation/wiki_collab/collab_kit/*`.
- Do not replace `personas/existing_data_curation/worker_kit/run_range.py`.
- Do not revert the current per-unit model provenance changes in `assignment_runner.py`, `harness.py`, `merge_collab_results.py`, schemas, or docs.
- Do not import PR 73 sample output artifacts under `raw/amazon_reviews_2023/persona_dimension_inference/samples`.

## Integration Policy

Use selective patches, not branch merges:

```bash
git fetch origin pull/73/head:refs/remotes/origin/pr/73 pull/81/head:refs/remotes/origin/pr/81
git diff --binary HEAD..origin/pr/73 -- \
  personas/existing_data_curation/modal_amazon_user_index.py \
  personas/existing_data_curation/scripts/infer_amazon_review_dimensions.py \
  personas/existing_data_curation/amazon_review_evidence_mapping.json \
  personas/existing_data_curation/scripts/evaluate_amazon_persona_rating_holdout.py \
  > /tmp/pr73_amazon_core.patch
git show --binary --format= ae4735973aa7b6ddbd1b4de79752d5e401897b83 -- \
  personas/existing_data_curation/protocols/amazon_review_persona_inference_v1 \
  personas/existing_data_curation/wiki_collab/amazon_collab.py \
  personas/existing_data_curation/scripts/build_amazon_collab_db.py \
  personas/existing_data_curation/worker_kit/run_amazon_range.py \
  personas/existing_data_curation/scripts/validate_amazon_results.py \
  tests/personas/existing_data_curation/test_amazon_collab_unittest.py \
  > /tmp/pr81_amazon_adapter.patch
```

Expected commit order:
1. Existing runner provenance/resume fix, if not already committed.
2. PR 73 Amazon core workflow.
3. PR 81 Amazon collaboration adapter adapted to the final PR 73 API.
4. Docs and verification fixes.

### Task 1: Protect Current Runner Behavior

**Files:**
- Verify: `personas/existing_data_curation/wiki_collab/collab_kit/assignment_runner.py`
- Verify: `personas/existing_data_curation/wiki_collab/collab_kit/harness.py`
- Verify: `personas/existing_data_curation/scripts/merge_collab_results.py`
- Verify: `tests/personas/existing_data_curation/test_collab_kit.py`
- Verify: `tests/personas/existing_data_curation/test_merge_collab_results.py`
- Verify: `tests/personas/existing_data_curation/test_assignment_runner.py`

- [ ] **Step 1: Confirm the current worktree shape**

Run:

```bash
git status --short
```

Expected: existing runner/provenance files may be modified; unrelated untracked artifacts may exist. Do not delete or reset them.

- [ ] **Step 2: Re-run the current collaboration tests before importing Amazon code**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation -q
```

Expected: the current collaboration suite passes. At the time this plan was written, the expected result was `85 passed`.

- [ ] **Step 3: Optionally commit the protected runner state**

Run only if the user wants commit checkpoints:

```bash
git add \
  personas/existing_data_curation/scripts/make_collab_package.py \
  personas/existing_data_curation/scripts/merge_collab_results.py \
  personas/existing_data_curation/wiki_collab/README.md \
  personas/existing_data_curation/wiki_collab/collab_kit/README.md \
  personas/existing_data_curation/wiki_collab/collab_kit/assignment_runner.py \
  personas/existing_data_curation/wiki_collab/collab_kit/harness.py \
  personas/existing_data_curation/wiki_collab/collab_kit/schemas/result.output.schema.json \
  tests/personas/existing_data_curation/test_collab_kit.py \
  tests/personas/existing_data_curation/test_merge_collab_results.py \
  tests/personas/existing_data_curation/test_assignment_runner.py
git commit -m "fix: preserve collab model provenance across resumes"
```

Expected: one checkpoint commit. If commits are not desired, skip this step and keep the protected files out of later patch imports.

### Task 2: Add Failing Tests for PR 73 Amazon Core

**Files:**
- Create: `tests/personas/existing_data_curation/test_amazon_review_core_unittest.py`

- [ ] **Step 1: Create the unit test file**

```python
import argparse
import unittest

from personas.existing_data_curation.modal_amazon_user_index import (
    temporal_train_validation_split,
)
from personas.existing_data_curation.scripts.infer_amazon_review_dimensions import (
    attach_product_metadata_sidecar,
    review_corpus_stats,
    validate_temporal_split_user_row,
)


class AmazonReviewCoreTests(unittest.TestCase):
    def test_temporal_split_keeps_latest_rows_for_validation(self):
        reviews = [
            {"review_id": "r3", "timestamp": 3000, "rating": 5, "text": "third"},
            {"review_id": "r1", "timestamp": 1000, "rating": 4, "text": "first"},
            {"review_id": "r5", "timestamp": 5000, "rating": 2, "text": "fifth"},
            {"review_id": "r2", "timestamp": 2000, "rating": 3, "text": "second"},
            {"review_id": "r4", "timestamp": 4000, "rating": 1, "text": "fourth"},
        ]

        construction, validation, summary = temporal_train_validation_split(
            reviews, train_fraction=0.8
        )

        self.assertEqual([row["review_id"] for row in construction], ["r1", "r2", "r3", "r4"])
        self.assertEqual([row["review_id"] for row in validation], ["r5"])
        self.assertEqual(summary["method"], "per_user_temporal")
        self.assertEqual(summary["construction_row_count"], 4)
        self.assertEqual(summary["validation_row_count"], 1)

    def test_product_metadata_sidecar_attaches_to_construction_and_validation(self):
        user_row = {
            "user_id": "u1",
            "reviews": [{"review_id": "r1", "parent_asin": "P1", "category": "Books"}],
            "validation_reviews": [
                {"review_id": "v1", "parent_asin": "P1", "category": "Books"}
            ],
        }
        metadata = {
            ("P1", "Books"): {
                "parent_asin": "P1",
                "source_category": "Books",
                "title": "Deep Work",
                "main_category": "Books",
            }
        }

        enriched = attach_product_metadata_sidecar(user_row, metadata)

        self.assertEqual(enriched["reviews"][0]["product_metadata"]["title"], "Deep Work")
        self.assertEqual(
            enriched["validation_reviews"][0]["product_metadata"]["title"], "Deep Work"
        )

    def test_review_corpus_stats_preserves_rating_only_behavior(self):
        reviews = [
            {
                "review_id": "r1",
                "category": "Books",
                "rating": 5,
                "text": "",
                "timestamp": 1000,
                "product_metadata": {
                    "title": "Mystery Puzzle",
                    "main_category": "Toys",
                    "categories_json": "[\"Toys\", \"Puzzles\"]",
                },
            },
            {
                "review_id": "r2",
                "category": "Books",
                "rating": 4,
                "text": "I compare translations carefully.",
                "timestamp": 2000,
            },
        ]

        stats = review_corpus_stats(reviews)

        self.assertEqual(stats["row_count"], 2)
        self.assertEqual(stats["text_review_count"], 1)
        self.assertEqual(stats["rating_count"], 2)
        self.assertEqual(stats["rating_only_count"], 1)
        self.assertEqual(stats["rating_only_summary"]["rating_counts"], {"5": 1})
        self.assertEqual(
            stats["rating_only_summary"]["top_product_names"], {"Mystery Puzzle": 1}
        )

    def test_temporal_validation_rejects_unsplit_histories_by_default(self):
        args = argparse.Namespace(allow_unsplit_histories=False)

        with self.assertRaisesRegex(ValueError, "missing temporal_split"):
            validate_temporal_split_user_row({"user_id": "u1", "reviews": []}, args)

    def test_temporal_validation_allows_legacy_histories_only_when_requested(self):
        args = argparse.Namespace(allow_unsplit_histories=True)

        validate_temporal_split_user_row({"user_id": "u1", "reviews": []}, args)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm it fails before PR 73 is imported**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_amazon_review_core_unittest.py -q
```

Expected: failure because current local Amazon scripts do not yet expose the PR 73 temporal split and metadata/stat helpers.

### Task 3: Import PR 73 Core Workflow

**Files:**
- Modify: `personas/existing_data_curation/modal_amazon_user_index.py`
- Modify: `personas/existing_data_curation/scripts/infer_amazon_review_dimensions.py`
- Modify: `personas/existing_data_curation/amazon_review_evidence_mapping.json`
- Create: `personas/existing_data_curation/scripts/evaluate_amazon_persona_rating_holdout.py`
- Test: `tests/personas/existing_data_curation/test_amazon_review_core_unittest.py`

- [ ] **Step 1: Check that the PR 73 patch applies**

Run:

```bash
git apply --check /tmp/pr73_amazon_core.patch
```

Expected: no output and exit code 0.

- [ ] **Step 2: Apply only the PR 73 core patch**

Run:

```bash
git apply --3way /tmp/pr73_amazon_core.patch
```

Expected: the four PR 73 core files are created or modified. No sample output artifacts are added.

- [ ] **Step 3: Verify raw-review mode is no longer expected**

Run:

```bash
rg -n "def infer_user\\(|--inference-mode|raw_reviews" \
  personas/existing_data_curation/scripts/infer_amazon_review_dimensions.py
```

Expected: no `def infer_user(`. The final PR 73 pipeline should be evidence-profile first; raw-review support should not be assumed by the adapter.

- [ ] **Step 4: Run the new PR 73 core tests**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_amazon_review_core_unittest.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Compile the imported core scripts**

Run:

```bash
python3 -m py_compile \
  personas/existing_data_curation/modal_amazon_user_index.py \
  personas/existing_data_curation/scripts/infer_amazon_review_dimensions.py \
  personas/existing_data_curation/scripts/evaluate_amazon_persona_rating_holdout.py
```

Expected: exit code 0.

### Task 4: Add Failing Tests for PR 81 Amazon Collaboration Adapter

**Files:**
- Create: `tests/personas/existing_data_curation/test_amazon_collab_unittest.py`

- [ ] **Step 1: Create the adapter test file**

```python
import gzip
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from personas.existing_data_curation.scripts.validate_amazon_results import (
    validate_amazon_archive,
    validate_attribute,
)
from personas.existing_data_curation.wiki_collab.amazon_collab import (
    build_amazon_profile_database,
)
from personas.existing_data_curation.wiki_collab.core import Assignment, load_protocol_manifest
from personas.existing_data_curation.worker_kit.run_amazon_range import (
    parse_args as parse_amazon_runner_args,
    run_amazon_range,
)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sample_user_row() -> dict:
    return {
        "user_id": "u1",
        "temporal_split": {"method": "per_user_temporal", "train_fraction": 0.8},
        "reviews": [
            {
                "review_id": "r1",
                "parent_asin": "B001",
                "category": "Books",
                "title": "Detailed notes",
                "text": "I annotate every chapter and compare translations.",
                "rating": 5,
                "timestamp": 1700000000000,
            }
        ],
        "validation_reviews": [
            {
                "review_id": "v1",
                "parent_asin": "B002",
                "category": "Books",
                "title": "Held out",
                "text": "This should not be used for persona construction.",
                "rating": 4,
                "timestamp": 1710000000000,
            }
        ],
    }


class AmazonCollabTests(unittest.TestCase):
    def test_mock_amazon_range_builds_valid_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            histories = tmp_path / "user_histories.jsonl"
            db = tmp_path / "amazon_profiles.sqlite"
            manifest_path = tmp_path / "dataset_manifest.json"
            schema = tmp_path / "schema.json"
            mapping = tmp_path / "mapping.json"
            out_dir = tmp_path / "runs"
            _write_jsonl(histories, [_sample_user_row()])
            _write_json(
                schema,
                {
                    "dimensions": [
                        {
                            "id": "test_interest",
                            "label": "Test Interest",
                            "category": "Interests",
                            "description": "A test interest dimension.",
                            "values": ["High", "Low"],
                        }
                    ]
                },
            )
            _write_json(
                mapping,
                {
                    "evidence_categories": [
                        {
                            "id": "interests",
                            "label": "Interests",
                            "schema_categories": ["Interests"],
                        }
                    ]
                },
            )
            dataset_manifest = build_amazon_profile_database(
                user_histories=histories,
                out_db=db,
                manifest_path=manifest_path,
                dataset_id="amazon-test-v1",
            )
            protocol_dir = Path(
                "personas/existing_data_curation/protocols/amazon_review_persona_inference_v1"
            )
            protocol = load_protocol_manifest(protocol_dir)
            assignment = Assignment(
                assignment_id="A0001",
                worker_id="alice",
                dataset_id="amazon-test-v1",
                dataset_sha256=dataset_manifest["db_sha256"],
                protocol_id=protocol.protocol_id,
                protocol_sha256=protocol.protocol_sha256,
                range_start=0,
                range_end=1,
            )
            args = parse_amazon_runner_args(
                [
                    "--db",
                    str(db),
                    "--protocol",
                    str(protocol_dir),
                    "--range",
                    "0:1",
                    "--worker-id",
                    "alice",
                    "--out-dir",
                    str(out_dir),
                    "--dataset-id",
                    "amazon-test-v1",
                    "--dataset-sha256",
                    dataset_manifest["db_sha256"],
                    "--backend",
                    "mock",
                    "--schema-path",
                    str(schema),
                    "--evidence-mapping-path",
                    str(mapping),
                    "--dimension-ids",
                    "test_interest",
                ]
            )
            archive = run_amazon_range(
                db_path=db,
                protocol_dir=protocol_dir,
                range_start=0,
                range_end=1,
                worker_id="alice",
                out_dir=out_dir,
                dataset_id="amazon-test-v1",
                dataset_sha256=dataset_manifest["db_sha256"],
                args=args,
            )
            report = validate_amazon_archive(
                archive_path=archive,
                db_path=db,
                assignment=assignment,
                expected_prompt_sha256=protocol.prompt_sha256,
                schema_path=schema,
            )
            with tarfile.open(archive, "r:gz") as tar:
                tar.extract("results.jsonl.gz", path=tmp_path)
            with gzip.open(tmp_path / "results.jsonl.gz", "rt", encoding="utf-8") as fh:
                rows = [json.loads(line) for line in fh]

        self.assertTrue(report.accepted, report.errors)
        self.assertEqual(report.valid_rows, 1)
        self.assertEqual(rows[0]["source_type"], "amazon_reviews_2023")
        self.assertEqual(rows[0]["provenance"]["backend"], "mock")
        self.assertEqual(rows[0]["provenance"]["inference_mode"], "evidence_profile")
        self.assertEqual(rows[0]["inferred_attributes"], [])

    def test_validation_rejects_validation_review_evidence_ids(self):
        errors = validate_attribute(
            {
                "dimension_id": "test_interest",
                "value": "High",
                "confidence": 0.9,
                "evidence_review_ids": ["v1"],
            },
            attr_index=0,
            global_idx=0,
            schema_by_id={
                "test_interest": {
                    "id": "test_interest",
                    "values": ["High", "Low"],
                }
            },
            valid_review_ids={"r1"},
        )

        self.assertTrue(
            any("evidence_review_ids not in construction reviews" in error for error in errors),
            errors,
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the adapter tests and confirm they fail before PR 81 is imported**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_amazon_collab_unittest.py -q
```

Expected: import failure because `wiki_collab.amazon_collab`, `run_amazon_range`, and `validate_amazon_results` do not exist yet.

### Task 5: Import PR 81 Adapter and Adapt It to Final PR 73

**Files:**
- Create: `personas/existing_data_curation/protocols/amazon_review_persona_inference_v1/*`
- Create: `personas/existing_data_curation/wiki_collab/amazon_collab.py`
- Create: `personas/existing_data_curation/scripts/build_amazon_collab_db.py`
- Create: `personas/existing_data_curation/worker_kit/run_amazon_range.py`
- Create: `personas/existing_data_curation/scripts/validate_amazon_results.py`
- Test: `tests/personas/existing_data_curation/test_amazon_collab_unittest.py`

- [ ] **Step 1: Apply the PR 81 adapter patch**

Run:

```bash
git apply --check /tmp/pr81_amazon_adapter.patch
git apply --3way /tmp/pr81_amazon_adapter.patch
```

Expected: only the listed adapter/protocol/test files are added. No generic wiki runner files are replaced.

- [ ] **Step 2: Remove stale raw-review imports from `run_amazon_range.py`**

In `personas/existing_data_curation/worker_kit/run_amazon_range.py`, make the import block from `infer_amazon_review_dimensions.py` match this shape:

```python
from personas.existing_data_curation.scripts.infer_amazon_review_dimensions import (
    DEFAULT_EVIDENCE_MAPPING_PATH,
    DEFAULT_MODEL,
    DEFAULT_SCHEMA_PATH,
    filter_amazon_supported_dimensions,
    filter_dimensions,
    infer_user_from_evidence_profile,
    load_evidence_mapping,
    load_schema,
    parse_csv_filter,
)
```

Expected: no import of `infer_user`; final PR 73 does not expose that function.

- [ ] **Step 3: Make Amazon collaboration always evidence-profile based**

Replace `select_dimensions` in `run_amazon_range.py` with:

```python
def select_dimensions(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dimensions = load_schema(args.schema_path)
    mapping = load_evidence_mapping(args.evidence_mapping_path)
    explicit_filter = bool(args.dimension_categories or args.dimension_ids)
    dimensions = filter_dimensions(
        dimensions,
        category_filter=parse_csv_filter(args.dimension_categories),
        id_filter=parse_csv_filter(args.dimension_ids),
    )
    if (
        not args.no_amazon_default_schema_filter
        and not explicit_filter
    ):
        dimensions = filter_amazon_supported_dimensions(dimensions, mapping)
    if not dimensions:
        raise ValueError("No dimensions selected after filtering.")
    return dimensions, mapping
```

Expected: the adapter has one supported production path: compact evidence profile to schema mapping.

- [ ] **Step 4: Remove the stale raw-review branch from `run_one`**

In `run_one`, use this decision block:

```python
if args.backend == "mock":
    inference_result = mock_inference(row, dimensions, args)
else:
    inference_result = infer_user_from_evidence_profile(
        row.payload,
        dimensions,
        mapping,
        args,
        api_key,
        existing_profiles,
    )
```

Expected: `mapping` is always required and no `raw_reviews` code path remains.

- [ ] **Step 5: Add the missing final-PR73 CLI args to `parse_args`**

In `parse_args`, keep `--backend` as `openai-api` or `mock`, and replace or add these arguments:

```python
parser.add_argument("--inference-mode", choices=("evidence_profile",), default="evidence_profile")
parser.add_argument("--max-reviews-per-user", type=int, default=80)
parser.add_argument("--power-user-min-reviews", type=int, default=1000)
parser.add_argument("--power-user-min-text-chars", type=int, default=250_000)
parser.add_argument("--power-user-max-reviews", type=int, default=200)
parser.add_argument("--no-adaptive-power-review-cap", action="store_true")
parser.add_argument(
    "--context-selection-strategy",
    choices=("temporal", "category_temporal", "informative_category_temporal"),
    default="category_temporal",
)
parser.add_argument("--max-review-text-chars", type=int, default=500)
parser.add_argument("--max-review-context-chars", type=int, default=100_000)
parser.add_argument("--window-summary-threshold-chars", type=int, default=40_000)
parser.add_argument("--window-summary-max-chars", type=int, default=40_000)
parser.add_argument("--window-summary-max-rows", type=int, default=80)
parser.add_argument("--max-evidence-items", type=int, default=120)
parser.add_argument("--max-window-evidence-items", type=int, default=100)
parser.add_argument(
    "--schema-routing-mode",
    choices=("none", "category", "recall"),
    default="recall",
)
parser.add_argument("--schema-router-min-confidence", type=float, default=0.25)
parser.add_argument(
    "--schema-router-always-include",
    default=(
        "Interests:*,Behavior:*,Values & Motivation,Risk & Decision,"
        "Linguistic:*,Expertise:*,Personality:*,Health:*,"
        "Worldview: Beliefs,Demographic: Family,Demographic: Life Events,"
        "Social Identity, Relationships & Community"
    ),
)
parser.add_argument(
    "--recall-pass-categories",
    default=(
        "Personality:*,Values & Motivation,Risk & Decision,Behavior:*,"
        "Expertise:*,Health:*,Worldview: Beliefs,Demographic: Family,"
        "Demographic: Life Events,Social Identity, Relationships & Community"
    ),
)
parser.add_argument("--recall-dimensions-per-call", type=int, default=120)
parser.add_argument("--dimensions-per-call", type=int, default=200)
parser.add_argument("--allow-unsplit-histories", action="store_true")
```

Expected: every attribute read by PR 73's `infer_user_from_evidence_profile` exists on the Amazon runner args. The collaboration runner defaults to `recall` for better attribute assignment; callers can pass `--schema-routing-mode category` to reduce cost.

- [ ] **Step 6: Ensure mock inference returns evidence-profile metadata**

Keep `mock_inference` returning this minimum shape:

```python
return {
    "source": AMAZON_SOURCE_TYPE,
    "inference_mode": args.inference_mode,
    "schema_routing_mode": args.schema_routing_mode,
    "schema_path": str(args.schema_path),
    "schema_dimension_count": len(dimensions),
    "schema_mapped_dimension_count": len(dimensions),
    "user_id": row.user_id,
    "review_count": len(row.payload.get("reviews") or []),
    "review_context_count": 0,
    "evidence_item_count": 0,
    "model": args.model,
    "request_count": 0,
    "status": "ok",
    "evidence_profile": {
        "user_id": row.user_id,
        "overview": "Mock Amazon collaboration run.",
        "evidence_items": [],
    },
    "rejected_evidence_items": [],
    "inferred_attributes": [],
    "rejected_attributes": [],
}
```

Expected: the mock path exercises archive creation and validation without network access.

### Task 6: Verify Amazon Validation Boundary

**Files:**
- Modify: `personas/existing_data_curation/scripts/validate_amazon_results.py`
- Test: `tests/personas/existing_data_curation/test_amazon_collab_unittest.py`

- [ ] **Step 1: Confirm validation only accepts construction-review evidence**

In `validate_result_row`, keep this construction-only review-id derivation:

```python
payload = json.loads(db_row["payload_json"])
valid_review_ids = _review_ids(payload.get("reviews") or [])
```

Expected: `validation_reviews` are not included in `valid_review_ids`.

- [ ] **Step 2: Confirm attribute validation rejects held-out review ids**

Keep this check in `validate_attribute`:

```python
elif not set(map(str, evidence_ids)).issubset(valid_review_ids):
    errors.append(
        f"row {global_idx} attribute {attr_index} evidence_review_ids not in construction reviews"
    )
```

Expected: attributes citing `validation_reviews` fail validation.

- [ ] **Step 3: Run the Amazon adapter tests**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_amazon_collab_unittest.py -q
```

Expected: all Amazon adapter tests pass.

### Task 7: Add Minimal Documentation

**Files:**
- Modify: `personas/existing_data_curation/README.md`
- Modify: `personas/existing_data_curation/wiki_collab/README.md`

- [ ] **Step 1: Add an Amazon Reviews 2023 collaboration section**

Add this concise command flow to `personas/existing_data_curation/README.md`:

```markdown
### Amazon Reviews 2023 collaboration flow

The Amazon Reviews 2023 path uses the evidence-profile workflow instead of the
Wikipedia single-prompt field extractor. Build temporal user histories first,
then convert them into a collaboration SQLite database:

```bash
python -m personas.existing_data_curation.scripts.build_amazon_collab_db \
  --user-histories raw/amazon_reviews_2023/user_histories.jsonl \
  --out-db raw/amazon_reviews_2023/amazon_profiles.sqlite \
  --manifest raw/amazon_reviews_2023/amazon_profiles_manifest.json \
  --dataset-id amazon-reviews-2023-persona-v1 \
  --product-metadata-sidecar raw/amazon_reviews_2023/user_histories.product_metadata.jsonl
```

Run an assigned range with a mock backend for smoke tests:

```bash
python -m personas.existing_data_curation.worker_kit.run_amazon_range \
  --db raw/amazon_reviews_2023/amazon_profiles.sqlite \
  --protocol personas/existing_data_curation/protocols/amazon_review_persona_inference_v1 \
  --range 0:10 \
  --worker-id alice \
  --dataset-id amazon-reviews-2023-persona-v1 \
  --dataset-sha256 <db_sha256_from_manifest> \
  --backend mock
```

For production OpenAI API runs, omit `--backend mock` and set `OPENAI_API_KEY`.
The collaboration runner defaults to `--schema-routing-mode recall` for higher
recall attribute assignment.
```

Expected: README gives the build DB and run range commands without implying that Amazon uses the wiki prompt.

- [ ] **Step 2: Add validation command**

Add this command example:

```markdown
Validate an Amazon result archive:

```bash
python -m personas.existing_data_curation.scripts.validate_amazon_results \
  --archive amazon_collab_runs/results_alice_amazon_review_persona_inference_v1_0000000000_0000000010.tar.gz \
  --db raw/amazon_reviews_2023/amazon_profiles.sqlite \
  --assignment-json assignments/alice_0000000000_0000000010.json \
  --prompt-sha256 <protocol_prompt_sha256> \
  --schema-path personas/dimensions+new.json
```
```

Expected: docs mention validation and construction-only evidence citations.

### Task 8: Full Verification

**Files:**
- Verify all modified and created files.

- [ ] **Step 1: Compile imported and new Python modules**

Run:

```bash
python3 -m py_compile \
  personas/existing_data_curation/modal_amazon_user_index.py \
  personas/existing_data_curation/scripts/infer_amazon_review_dimensions.py \
  personas/existing_data_curation/scripts/evaluate_amazon_persona_rating_holdout.py \
  personas/existing_data_curation/wiki_collab/amazon_collab.py \
  personas/existing_data_curation/scripts/build_amazon_collab_db.py \
  personas/existing_data_curation/worker_kit/run_amazon_range.py \
  personas/existing_data_curation/scripts/validate_amazon_results.py
```

Expected: exit code 0.

- [ ] **Step 2: Run targeted Amazon tests**

Run:

```bash
python3 -m pytest \
  tests/personas/existing_data_curation/test_amazon_review_core_unittest.py \
  tests/personas/existing_data_curation/test_amazon_collab_unittest.py \
  -q
```

Expected: all targeted Amazon tests pass.

- [ ] **Step 3: Re-run existing collaboration tests to catch regressions**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation -q
```

Expected: all tests pass, including current model-provenance resume tests and new Amazon tests.

- [ ] **Step 4: Check no unwanted PR artifacts were imported**

Run:

```bash
git status --short
rg -n "raw_reviews|def infer_user\\(" personas/existing_data_curation/worker_kit/run_amazon_range.py
git diff --name-only | rg "raw/amazon_reviews_2023|samples|results_.*\\.jsonl|\\.tar\\.gz$" || true
```

Expected:
- `run_amazon_range.py` has no raw-review branch.
- No sample inference artifacts or tarballs are in the diff.
- Protected wiki runner/provenance files are still present and not reverted.

## Self-Review

Spec coverage:
- Better attribute assignment: covered by PR 73 evidence-profile mapping, product metadata, rating-only summary, schema routing/recall, and `--schema-routing-mode recall` default in the Amazon collaboration runner.
- Amazon Reviews 2023 support: covered by PR 73 core workflow and PR 81 SQLite/range-runner/validator adapter.
- Current runner model-switch behavior: protected in Task 1 and regression-tested in Task 8.
- Validation design: covered by Amazon-specific archive validation and construction-only `evidence_review_ids`.

No-placeholder scan:
- The plan avoids `TBD`, `TODO`, and open-ended "add tests" steps.
- Every created test file includes concrete code.
- Every verification step includes exact commands and expected outcomes.

Type consistency:
- `run_amazon_range.py` imports only `infer_user_from_evidence_profile`, matching final PR 73.
- The Amazon runner args include every attribute used by PR 73 evidence-profile inference.
- Amazon validation uses `inferred_attributes`, not the wiki runner's `fields` array.

## Execution Choice

Plan complete and saved to `docs/superpowers/plans/2026-06-24-pr73-pr81-amazon-collab-integration.md`.

Recommended execution option: Subagent-driven task execution, with review after each of the four logical commits.
