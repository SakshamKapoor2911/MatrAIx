# Persona Existing Data Curation

This folder contains owner-side tools for creating extractable collaborator
packages from existing datasets. These packages are plain `.tar.gz` archives
that a collaborator can unpack and run locally; they are not Harbor registry
packages.

## Package Owner Data Setup

The code in this folder does not vendor the full source datasets. A package
owner must prepare one normalized input layer per dataset, then use the wrapper
scripts to slice that layer into collaborator packages.

Recommended portable layout:

```text
${MATRIX_DATA_ROOT}/
  wiki/enwiki_20260601/person_pages_clean/*.jsonl.gz
  amazon_reviews_2023/user_histories.jsonl.gz
```

Use a local data root of your choice, for example:

```bash
export MATRIX_DATA_ROOT=/path/to/matraix_existing_data
```

You can use any paths as long as you pass them to the wrappers or set the
environment variables described below.

## Wiki Packages

Wiki package generation consumes a clean English Wikipedia person profile layer.
Each `.jsonl` or `.jsonl.gz` row should contain at least:

```json
{
  "page_id": 123,
  "qid": "Q...",
  "title": "Person Name",
  "source_url": "https://en.wikipedia.org/wiki/...",
  "profile_text": "clean biography text"
}
```

`profile_text` may also be named `plain_text` or `text`.

Set `WIKI_CLEAN_DIR` to the local clean profile layer:

```bash
WIKI_CLEAN_DIR=${MATRIX_DATA_ROOT}/wiki/enwiki_20260601/person_pages_clean \
persona/existing_data_curation/scripts/make_package.sh 0:100 alice
```

The wrapper builds a reusable owner-only SQLite profile database under `TMPDIR` or the optional `MATRIX_PACKAGE_CACHE_ROOT`, slices the requested half-open range, and writes packages under `MATRIX_PACKAGE_OUT_ROOT` or the same cache root.

## Amazon Review Packages

Amazon package generation consumes normalized Amazon Reviews 2023 user-history
JSONL/JSONL.GZ, one user per row:

```json
{
  "user_id": "A...",
  "review_count": 42,
  "reviews": [
    {
      "timestamp": 1700000000,
      "category": "Books",
      "rating": 5,
      "title": "...",
      "text": "..."
    }
  ]
}
```

The package builder needs at least `user_id` or `reviewer_id`, plus a `reviews`
list. Each usable review should have a non-empty title/product title or review
text. The renderer also uses optional fields such as `date`, `parent_asin`,
`asin`, `verified_purchase`, and `helpful_vote` when present.

### Export From Hugging Face

The normal data entrypoint is the reindexed Hugging Face artifact documented in
`configs/amazon_reviews_2023.json`:

```text
repo_id: MatrAIx2026/MatrAIx2026
artifact: amazon/modal_artifacts/amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000
```

If the dataset is gated for your account, run `huggingface-cli login` first.
The exporter requires `huggingface_hub` and `pyarrow` at runtime.

Export selected reviewer histories:

```bash
python3 persona/existing_data_curation/scripts/export_hf_amazon_user_histories.py \
  --user-ids /path/to/reviewer_ids.md \
  --output "${MATRIX_DATA_ROOT}/amazon_reviews_2023/user_histories.jsonl.gz"
```

`--user-ids` can be a Markdown/text file containing Amazon reviewer IDs or a
JSONL/JSONL.GZ file with `user_id` fields.

Then create collaborator packages:

```bash
persona/existing_data_curation/scripts/make_amazon_package.sh \
  "${MATRIX_DATA_ROOT}/amazon_reviews_2023/user_histories.jsonl.gz" \
  0:100 alice
```

Pass `all` as the fourth argument to include every persona dimension instead of
the Amazon-supported subset:

```bash
persona/existing_data_curation/scripts/make_amazon_package.sh \
  "${MATRIX_DATA_ROOT}/amazon_reviews_2023/user_histories.jsonl.gz" \
  0:100 alice all
```

### Amazon Downstream Workflows

The imported Amazon extraction and holdout-prediction workflows are
subscription-based. They do not require an API key. Authenticate your local
`codex` or `claude` CLI subscription, then choose the backend with
`--llm-backend`.

Prepare persona-dimension inferences:

```bash
python3 persona/existing_data_curation/amazon/extraction/infer_amazon_review_dimensions.py \
  --user-histories "${MATRIX_DATA_ROOT}/amazon_reviews_2023/user_histories.jsonl.gz" \
  --llm-backend codex \
  --output "${MATRIX_DATA_ROOT}/amazon_reviews_2023/inferred_dimensions.jsonl"
```

Prepare blind rating-holdout targets and score baselines:

```bash
python3 persona/existing_data_curation/amazon/evaluation/evaluate_amazon_persona_rating_holdout.py \
  --user-histories "${MATRIX_DATA_ROOT}/amazon_reviews_2023/user_histories.jsonl.gz" \
  --output-dir "${MATRIX_DATA_ROOT}/amazon_reviews_2023/rating_holdout"
```

Predict held-out ratings with the constructed personas:

```bash
python3 persona/existing_data_curation/amazon/evaluation/predict_amazon_persona_holdout_ratings.py \
  --prediction-targets "${MATRIX_DATA_ROOT}/amazon_reviews_2023/rating_holdout/prediction_targets.jsonl" \
  --inference-output "${MATRIX_DATA_ROOT}/amazon_reviews_2023/inferred_dimensions.jsonl" \
  --llm-backend codex \
  --output "${MATRIX_DATA_ROOT}/amazon_reviews_2023/rating_holdout/persona_predictions.jsonl"
```

Use `--llm-backend claude --model opus` for Claude Code subscriptions. Use
`--dry-run` on either LLM script to write prompts without invoking a backend.

For Claude Code subscriptions, `--model opus` selects the model and
`--llm-effort` selects the reasoning budget passed to `claude --effort`.
Supported effort values are `low`, `medium`, `high`, `xhigh`, and `max`.
Use `--llm-effort high` for extraction/inference because schema mapping is
quality-sensitive. Use `--llm-effort medium` for large prediction runs, then
raise it to `high` for final evaluations or unstable batches. Reserve `xhigh`
or `max` for small final checks because they are slower and consume more
subscription capacity.

## Collaborator Contract

Each archive contains `assignment.json`, `tasks.jsonl`, `dimensions.json`,
`package_manifest.json`, `run_assignment.sh`, and `collab_kit/`. Collaborators
unpack the archive, run `./run_assignment.sh`, and return `results.jsonl`. They
do not need the source Wiki/Amazon data or the owner-side SQLite cache.
