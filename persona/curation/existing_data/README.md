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
below uses `make_collab_package.py` instead.

## Collaboration Packages

Create a worker-facing package from a local profile SQLite database:

```bash
python persona/curation/existing_data/scripts/make_collab_package.py \
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

The convenience wrapper `scripts/make_package.sh` is an owner-side template for
the same flow. Edit the local `CLEAN_DIR` if your cleaned Wikipedia text lives
somewhere else.

## Amazon Reviews 2023

Use `samples/amazon_reviews_2023/user_histories_sample.jsonl` for a local smoke
test that does not require the full dataset:

```bash
python persona/curation/existing_data/scripts/make_amazon_collab_package.py \
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
- Amazon review histories, profile databases, and inference outputs

## Provenance

The source pipeline was migrated from local MatrAIx branch
`codex/amazon-review-collab-integration` at commit `87fe1dafb`. The source
branch contains additional generated artifacts and UI work that remain outside
this clean module.
