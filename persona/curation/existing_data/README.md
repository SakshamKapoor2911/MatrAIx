# Existing Data Curation

This directory contains repo-local tools for building persona records from
external datasets. It is the clean PersonaBench home for the useful parts of
the old MatrAIx `personas/existing_data_curation/` pipeline.

The current import establishes the source manifests, Wikipedia-derived persona
foundation, collaborator packaging loop, and Amazon Reviews 2023 persona
pipeline. Optional Modal/HuggingFace indexing remains dependency-light by
default: helper code is present, but cloud dependencies are only needed when you
run that path.

## Current Scope

Available in this wave:

- external source manifests under `manifests/`
- Wikipedia person page extraction and cleanup scripts under `scripts/`
- local SQLite profile database builder
- worker-facing collaboration package creation
- plain `results.jsonl` validation, merge, and audit helpers
- Amazon Reviews 2023 history normalization, persona inference, package
  creation, validation, holdout evaluation, and small test fixtures
- Nemotron domain and survey selection fixtures with reproducible selection and
  plot-rendering helpers
- small JSONL fixtures under `examples/`

Deferred to follow-up PRs:

- optional dependency metadata and docs for Modal/HuggingFace cloud indexing
- React curation cockpit
- full generated persona outputs

## Layout

```text
persona/curation/existing_data/
  manifests/      Dataset and grounding-source metadata.
  protocols/      Prompt/schema contracts for evidence-profile inference.
  samples/        Small fixtures suitable for git.
  scripts/        Repo-local curation CLIs.
  wiki_collab/    Shared wiki collaboration contracts and worker kit.
  worker_kit/     Owner-side range runner utilities.
  examples/       Small fixtures suitable for git.
```

Generated data should go under ignored local directories such as `raw/`,
`outputs/`, or `logs/`; it should not be committed.

## Wikipedia Profile Database

Build a local SQLite profile database from cleaned Wikipedia person-page JSONL
or JSONL.GZ files:

```bash
python persona/curation/existing_data/scripts/build_wiki_profile_db.py \
  --clean-dir /path/to/person_pages_clean \
  --out-db /tmp/personabench-wiki-profiles.sqlite \
  --manifest /tmp/personabench-wiki-profiles.manifest.json \
  --dataset-id personabench_wiki_profiles_v1
```

The database stores stable `global_idx`, `task_id`, `qid`, title, source URL,
profile text, and input hash fields. These fields are the identity surface used
by validation and merge tools.

## Assignment Metadata

Create half-open range assignments from a profile database manifest and a
protocol manifest:

```bash
python persona/curation/existing_data/scripts/make_wiki_assignments.py \
  --dataset-manifest /tmp/personabench-wiki-profiles.manifest.json \
  --protocol-dir persona/curation/existing_data/protocols/persona_attribution_v1 \
  --workers alice,bob,carol \
  --chunk-size 50000 \
  --out /tmp/personabench-wiki-assignments.jsonl
```

This helper supports the archived result flow in `validate_wiki_results.py` and
expects a protocol manifest you supply locally. The plain worker-package flow
below uses the unified `make_package.py` entrypoint instead.

## Collaboration Packages

Create a worker-facing package from a supported source. The unified
`make_package.py` entrypoint currently supports `--source wiki` and
`--source amazon`.

For a local Wikipedia profile SQLite database:

```bash
python persona/curation/existing_data/scripts/make_package.py \
  --source wiki \
  --db /tmp/personabench-wiki-profiles.sqlite \
  --dimensions persona/schema/dimensions.json \
  --range 0:100 \
  --out-dir /tmp/personabench_packages/A_0_100_alice \
  --assignment-id A_0_100 \
  --worker-id alice \
  --dataset-id personabench_wiki_profiles_v1 \
  --dataset-sha256 DATASET_SHA256 \
  --force
```

The package contains `tasks.jsonl`, `dimensions.json`, `assignment.json`,
`package_manifest.json`, `run_assignment.sh`, and `collab_kit/`. The worker
returns `results.jsonl`; generated `.tar.gz` packages and returned files should
stay outside git.

The source-specific scripts `make_collab_package.py` and
`make_amazon_collab_package.py` remain available as lower-level builders, but
new packaging runs should prefer `make_package.py` so wiki and Amazon packages
share one owner-facing interface.

The convenience wrapper `scripts/make_package.sh` is an owner-side template for
the same flow. It defaults to wiki packages; set `SOURCE=amazon` and
`USER_HISTORIES=/path/to/user_histories.jsonl` to package Amazon histories.
Edit the local `CLEAN_DIR` if your cleaned Wikipedia text lives somewhere else.

## Amazon Reviews 2023

Use `samples/amazon_reviews_2023/user_histories_sample.jsonl` for a local smoke
test that does not require the full dataset:

```bash
python persona/curation/existing_data/scripts/make_package.py \
  --source amazon \
  --user-histories persona/curation/existing_data/samples/amazon_reviews_2023/user_histories_sample.jsonl \
  --dimensions persona/schema/dimensions.json \
  --range 0:2 \
  --out-dir /tmp/personabench_amazon_collab_A0001 \
  --assignment-id A0001 \
  --worker-id smoke \
  --dataset-id amazon_reviews_2023_sample \
  --dataset-sha256 dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd \
  --force
```

For real data, build or retrieve user histories externally, keep them under an
ignored local path such as `raw/amazon_reviews_2023/`, then run:

```bash
python persona/curation/existing_data/scripts/select_amazon_top_reviewers.py \
  --repo-id MatrAIx/MatrAIx \
  --artifact amazon/modal_artifacts/amazon_reviews_2018_2023_eligible_users_min30_verified70_text2000 \
  --top-k 10000 \
  --output-dir persona/curation/existing_data/outputs/amazon_reviews_2023/top_reviewers

python persona/curation/existing_data/scripts/export_hf_amazon_user_histories.py \
  --user-ids persona/curation/existing_data/outputs/amazon_reviews_2023/top_reviewers/amazon_top_10000_rich_persona_reviewer_ids_2018_2023.txt \
  --max-users 100 \
  --output persona/curation/existing_data/raw/amazon_reviews_2023/user_histories.jsonl
```

The reviewer selector ranks the eligible-user HF Parquet artifact by text
volume, text-review count, category breadth, history length, review count, and
verified-purchase share. It writes a ranked JSONL/CSV table, user-id list,
summary JSON, and Markdown report under ignored `outputs/`. Upload reusable
queues to external storage instead of committing them.

The HF export path reads user-bucketed Parquet artifacts and writes the
`user_histories.jsonl` format consumed by inference and packaging. You can also
produce the same JSONL from the Modal/HuggingFace indexing helpers or another
trusted preprocessing job.

```bash
python persona/curation/existing_data/scripts/infer_amazon_review_dimensions.py \
  --user-histories /path/to/user_histories.jsonl \
  --schema-path persona/schema/dimensions.json \
  --evidence-mapping-path persona/curation/existing_data/amazon_review_evidence_mapping.json \
  --output persona/curation/existing_data/raw/amazon_reviews_2023/persona_dimension_inference/inferred_dimensions.jsonl
```

Real inference requires the configured OpenAI-compatible model environment; add
`--dry-run` when you only want to inspect prompts locally. Returned Amazon
worker archives can be checked with
`scripts/validate_amazon_results.py`; rating-holdout evaluation and readable
reports live in `evaluate_amazon_persona_rating_holdout.py` and
`render_amazon_inference_report.py`.

The rating-holdout evaluator writes blind prediction targets that can be scored
against persona-grounded model predictions:

```bash
python persona/curation/existing_data/scripts/evaluate_amazon_persona_rating_holdout.py \
  --user-histories persona/curation/existing_data/raw/amazon_reviews_2023/user_histories.jsonl

python persona/curation/existing_data/scripts/predict_amazon_persona_holdout_ratings.py \
  --prediction-targets persona/curation/existing_data/raw/amazon_reviews_2023/persona_rating_holdout_eval/prediction_targets.jsonl \
  --inference-output persona/curation/existing_data/raw/amazon_reviews_2023/persona_dimension_inference/inferred_dimensions.jsonl \
  --dry-run
```

Remove `--dry-run` and set `OPENAI_API_KEY` to write
`persona_predictions.jsonl`, then pass that file back to
`evaluate_amazon_persona_rating_holdout.py --predictions`.

The optional Modal/HuggingFace indexing helpers in `modal_amazon_user_index.py`
need extra cloud/data dependencies:

```bash
pip install -e ".[amazon-modal]"
```

## Nemotron Selection Fixtures

Small Nemotron selection fixtures live under `samples/`:

- `samples/nemotron_domain_selection/`: domain-specific selected-user
  summaries and CSV metrics.
- `samples/nemotron_survey_selection/`: a deterministic 50-person general
  survey sample.

The full Nemotron curated persona YAML pool is external. If you have it
locally, keep it under the ignored path
`persona/curation/existing_data/raw/nemotron_personas_usa/curated_personas/`.

Regenerate a survey sample from a local curated-persona pool:

```bash
python persona/curation/existing_data/scripts/select_nemotron_survey_users.py \
  --curated-dir persona/curation/existing_data/raw/nemotron_personas_usa/curated_personas \
  --output-dir persona/curation/existing_data/outputs/nemotron_survey_selection
```

Render domain-selection SVG plots from the committed CSV fixtures:

```bash
python persona/curation/existing_data/scripts/render_nemotron_domain_selection_plots.py
```

Generated plots and regenerated selections default to ignored `outputs/`
directories. Commit only small curated fixtures that are needed for tests or
documentation.

## Validate And Merge Results

Validate a returned archive against the owner-side SQLite database and
assignment identity:

```bash
python persona/curation/existing_data/scripts/validate_wiki_results.py \
  --archive /path/to/results_alice_persona_attribution_v1_0000000000_0000050000.tar.gz \
  --db /tmp/personabench-wiki-profiles.sqlite \
  --assignment-json /path/to/assignment.json \
  --prompt-sha256 PROMPT_SHA256 \
  --report /tmp/personabench-wiki-validation-report.json
```

Merge accepted archives into a deduplicated JSONL.GZ:

```bash
python persona/curation/existing_data/scripts/merge_wiki_results.py \
  --archive /path/to/results_alice.tar.gz \
  --out /tmp/personabench-wiki-merged.jsonl.gz
```

For plain worker-package returns, merge one or more `results.jsonl` files:

```bash
python persona/curation/existing_data/scripts/merge_collab_results.py \
  --results /path/to/alice/results.jsonl \
  --package-manifest /path/to/alice/package_manifest.json \
  --dimensions persona/schema/dimensions.json \
  --db /tmp/personabench-wiki-profiles.sqlite \
  --out /tmp/personabench-wiki-merged.jsonl.gz \
  --report /tmp/personabench-wiki-merge-report.json
```

## External Artifacts

Do not commit large generated data, raw dumps, local SQLite profile databases,
or worker archives. Upload them externally and record the published URL in
`migration/matraix/README.md`.

Expected external artifacts include:

- cleaned Wikipedia person-page JSONL shards
- SQLite profile databases and manifests
- generated worker packages and returned result archives
- full curated persona YAML outputs
- Amazon reviewer queues, review histories, profile databases, and inference
  outputs

After uploading an artifact, replace the corresponding `TODO` in
`migration/matraix/README.md` with the published URL and link that URL from the
workflow section above if it is required to reproduce a command.

## Provenance

The source pipeline was migrated from local MatrAIx branch
`codex/amazon-review-collab-integration` at commit `87fe1dafb`. The source
branch contains additional generated artifacts and UI work that remain outside
this clean module.
