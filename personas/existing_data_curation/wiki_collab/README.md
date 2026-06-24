# Offline Wiki Collaboration

This directory contains two collaboration flows:

1. **Recommended outbound worker package**: the owner sends a small package with
   `tasks.jsonl`, `dimensions.json`, `assignment.json`, and `collab_kit/`.
   Collaborators edit only `collab_kit/solver.py` and return `results.jsonl`.
2. **Advanced SQLite range runner**: the owner shares a full SQLite database and
   protocol directories, and workers return `.tar.gz` result archives. This is
   useful for large internal runs, but it is not the simplest starter-code
   interface for external collaborators.

For the current 1339-dimension attribution work, prefer the worker package
flow. It gives collaborators only the files they need and keeps the exchange
contract small.

## Recommended: Owner Creates A Worker Package

Build a canonical SQLite database from the cleaned Wikipedia profiles:

```bash
python3 personas/existing_data_curation/scripts/build_wiki_profile_db.py \
  --clean-dir /data2/zonglin/wiki_dumps/enwiki/20260601/person_text_derivatives/person_pages_clean \
  --out-db /tmp/matraix-wiki-profiles-20260601-v1.sqlite \
  --manifest /tmp/matraix-wiki-profiles-20260601-v1.manifest.json \
  --dataset-id matraix_wiki_profiles_20260601_v1
```

Create one package for a collaborator:

```bash
python3 personas/existing_data_curation/scripts/make_collab_package.py \
  --db /tmp/matraix-wiki-profiles-20260601-v1.sqlite \
  --dimensions personas/dimensions+new.json \
  --range 0:100 \
  --out-dir /tmp/matraix_assignment_A0001 \
  --assignment-id A0001 \
  --worker-id alice \
  --dataset-id matraix_wiki_profiles_20260601_v1 \
  --dataset-sha256 DATASET_SHA256
```

The package directory, and the generated `.tar.gz`, contain:

```text
assignment.json
tasks.jsonl
dimensions.json
README.md
collab_kit/
```

Send the `.tar.gz` to the collaborator. They work inside the package, edit
`collab_kit/solver.py` if they want to improve the assignment method, and send
back `results.jsonl`.

To send only one category of dimensions, use a category name or slug:

```bash
python3 personas/existing_data_curation/scripts/make_collab_package.py \
  --db /tmp/matraix-wiki-profiles-20260601-v1.sqlite \
  --dimensions personas/dimensions+new.json \
  --range 0:100 \
  --categories demographic_core \
  --out-dir /tmp/matraix_assignment_A0001_demographic_core \
  --assignment-id A0001-demographic-core \
  --worker-id alice \
  --dataset-id matraix_wiki_profiles_20260601_v1 \
  --dataset-sha256 DATASET_SHA256
```

Collaborator quickstart from the unpacked package:

```bash
cd collab_kit
./run.sh --tasks ../tasks.jsonl --dimensions ../dimensions.json \
  --out ../results.jsonl --backend mock
python3 conformance.py --results ../results.jsonl \
  --dimensions ../dimensions.json --tasks ../tasks.jsonl
```

The mock backend proves the files and contract line up. For a real run, the
collaborator edits `solver.py` to call their preferred model/API while keeping
the output contract unchanged.

## Advanced: SQLite Range Extraction

## Owner Publishes Once

Build a canonical SQLite database from the cleaned Wikipedia profiles:

```bash
python personas/existing_data_curation/scripts/build_wiki_profile_db.py \
  --clean-dir /data2/zonglin/wiki_dumps/enwiki/20260601/person_text_derivatives/person_pages_clean \
  --out-db /tmp/matraix-wiki-profiles-20260601-v1.sqlite \
  --manifest /tmp/matraix-wiki-profiles-20260601-v1.manifest.json \
  --dataset-id matraix_wiki_profiles_20260601_v1
```

Publish these files to collaborators:

```text
matraix-wiki-profiles-20260601-v1.sqlite
matraix-wiki-profiles-20260601-v1.manifest.json
personas/existing_data_curation/worker_kit/
personas/existing_data_curation/protocols/persona_attribution_v1/
```

## Owner Assigns Ranges

Create assignment rows:

```bash
python personas/existing_data_curation/scripts/make_wiki_assignments.py \
  --dataset-manifest /tmp/matraix-wiki-profiles-20260601-v1.manifest.json \
  --protocol-dir personas/existing_data_curation/protocols/persona_attribution_v1 \
  --workers alice,bob,carol \
  --chunk-size 50000 \
  --out /tmp/wiki_assignments.jsonl
```

Email each collaborator their `worker_id`, `dataset_id`, `dataset_sha256`,
`protocol_id`, `protocol_sha256`, and half-open range `[range_start, range_end)`.

## Collaborator Runs A Range

Mock smoke test:

```bash
python personas/existing_data_curation/worker_kit/run_range.py \
  --db matraix-wiki-profiles-20260601-v1.sqlite \
  --protocol personas/existing_data_curation/protocols/persona_attribution_v1 \
  --range 0:50000 \
  --backend mock \
  --concurrency 8 \
  --worker-id alice \
  --dataset-id matraix_wiki_profiles_20260601_v1 \
  --dataset-sha256 DATASET_SHA256
```

Claude Code / Codex / API usage is routed through command adapters. The command
must read the prompt from stdin and emit JSON matching the protocol output
schema to stdout:

```bash
export WIKI_COLLAB_CLAUDE_CMD='your-claude-wrapper-command'
python personas/existing_data_curation/worker_kit/run_range.py \
  --db matraix-wiki-profiles-20260601-v1.sqlite \
  --protocol personas/existing_data_curation/protocols/persona_attribution_v1 \
  --range 0:50000 \
  --backend claude-code-acp \
  --concurrency 4 \
  --worker-id alice \
  --dataset-id matraix_wiki_profiles_20260601_v1 \
  --dataset-sha256 DATASET_SHA256
```

```bash
export WIKI_COLLAB_CODEX_CMD='your-codex-wrapper-command'
python personas/existing_data_curation/worker_kit/run_range.py \
  --db matraix-wiki-profiles-20260601-v1.sqlite \
  --protocol personas/existing_data_curation/protocols/persona_attribution_v1 \
  --range 50000:100000 \
  --backend codex-acp \
  --concurrency 4 \
  --worker-id bob \
  --dataset-id matraix_wiki_profiles_20260601_v1 \
  --dataset-sha256 DATASET_SHA256
```

The runner returns:

```text
results_<worker_id>_<protocol_id>_<range_start>_<range_end>.tar.gz
```

The archive contains:

```text
results.jsonl.gz
failures.jsonl.gz
run_manifest.json
```

## Owner Validates A Returned Archive

Create one assignment JSON file from the assignment row:

```json
{
  "assignment_id": "A0001",
  "worker_id": "alice",
  "dataset_id": "matraix_wiki_profiles_20260601_v1",
  "dataset_sha256": "DATASET_SHA256",
  "protocol_id": "persona_attribution_v1",
  "protocol_sha256": "PROTOCOL_SHA256",
  "range_start": 0,
  "range_end": 50000,
  "status": "assigned"
}
```

Validate:

```bash
python personas/existing_data_curation/scripts/validate_wiki_results.py \
  --archive results_alice_persona_attribution_v1_0000000000_0000050000.tar.gz \
  --db matraix-wiki-profiles-20260601-v1.sqlite \
  --assignment-json assignment_A0001.json \
  --prompt-sha256 PROMPT_SHA256 \
  --report validation_A0001.json
```

Validation checks:

```text
archive members exist
dataset/protocol/range match assignment
global_idx stays inside the assigned half-open range
input_sha256 matches the local database
task_id and qid match the local database
prompt_sha256 and protocol_sha256 match
model and effort provenance is present
field rows have confidence, evidence, and assignment_type
duplicate global_idx values are rejected
```


## Owner Builds An Audit Report

After validating returned archives, build an audit report across workers,
models, efforts, coverage, field distributions, duplicate rows, and missing
assigned indices:

```bash
python personas/existing_data_curation/scripts/audit_wiki_results.py \
  --archive results_alice_persona_attribution_v1_0000000000_0000050000.tar.gz \
  --archive results_bob_persona_attribution_v1_0000050000_0000100000.tar.gz \
  --db matraix-wiki-profiles-20260601-v1.sqlite \
  --assignments wiki_assignments.jsonl \
  --prompt-sha256 PROMPT_SHA256 \
  --report audit_persona_attribution_v1.json
```

The audit report includes:

```text
accepted/rejected archive counts
returned/valid/failed row counts
assigned coverage and missing index samples
duplicate index samples
worker/backend/requested_model/reported_model/effort distributions
field_id, assignment_type, and confidence bucket distributions
per-archive validation errors and warnings
```

## Owner Merges Accepted Archives

Only merge archives after validation accepts them:

```bash
python personas/existing_data_curation/scripts/merge_wiki_results.py \
  --archive results_alice_persona_attribution_v1_0000000000_0000050000.tar.gz \
  --archive results_bob_persona_attribution_v1_0000050000_0000100000.tar.gz \
  --out /tmp/merged_persona_attribution_v1.jsonl.gz
```

The merge step refuses silent overwrites by skipping duplicate `global_idx`
rows already present in the merged output.


## Default Model And Effort

Collaborators may omit the model flag. The runner defaults by backend:

```text
codex-acp/openai-api: gpt-5.5
claude-code-acp/anthropic-api: claude-opus-4-8
mock: mock-model
```

The runner also defaults effort to max, but this is not a hard acceptance rule.
Collaborators can override effort, and the owner-side validator only requires
the chosen effort to be recorded in run_manifest.json and each result row
provenance. The audit report summarizes effort distribution by returned row.

Override either value explicitly:

```bash
python personas/existing_data_curation/worker_kit/run_range.py \
  --db matraix-wiki-profiles-20260601-v1.sqlite \
  --protocol personas/existing_data_curation/protocols/persona_attribution_v1 \
  --range 0:50000 \
  --backend codex-acp \
  --model gpt-5.5 \
  --effort max \
  --concurrency 4 \
  --worker-id alice \
  --dataset-id matraix_wiki_profiles_20260601_v1 \
  --dataset-sha256 DATASET_SHA256
```
