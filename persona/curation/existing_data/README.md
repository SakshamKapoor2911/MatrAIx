# Existing Data Curation

This directory contains repo-local tools for building persona records from
external datasets. It is the clean PersonaBench home for the useful parts of
the old MatrAIx `personas/existing_data_curation/` pipeline.

The current import establishes the source manifests and Wikipedia-derived
persona foundation. Collaboration packaging, Amazon Reviews 2023 integration,
and optional Modal/HuggingFace indexing are intentionally staged in follow-up
PRs so `main` remains reviewable.

## Current Scope

Available in this wave:

- external source manifests under `manifests/`
- Wikipedia person page extraction and cleanup scripts under `scripts/`
- local SQLite profile database builder
- wiki result archive validation and merge helpers
- small JSONL fixtures under `examples/`

Deferred to follow-up PRs:

- worker package creation and collaborator runner UX
- Amazon Reviews 2023 evidence and fold-voting pipeline
- optional Modal/HuggingFace cloud indexer
- React curation cockpit
- full generated persona outputs

## Layout

```text
persona/curation/existing_data/
  manifests/      Dataset and grounding-source metadata.
  scripts/        Repo-local curation CLIs.
  wiki_collab/    Shared wiki collaboration data contracts.
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

The protocol directory lands with the collaboration package PR. Until then,
this command is primarily a tested library path for `build_assignments()`.

## Validate And Merge Result Archives

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
branch contains additional Amazon and collaborator package work that is staged
for later PersonaBench PRs.
