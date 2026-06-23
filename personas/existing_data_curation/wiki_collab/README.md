# Offline Wiki Range Extraction

This directory defines the primitive offline range-based collaboration flow for running
LLM extraction over a shared Wikipedia profile database.

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

Give each collaborator their `worker_id`, `dataset_id`, `dataset_sha256`,
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

Claude Code / Codex / API usage is routed through command adapters. This is a
command-adapter integration for subscriptions and API CLIs; it is not a native
ACP client implementation. The runner exposes backend names such as
`claude-code-acp` and `codex-acp` because the worker selects those surfaces, but
the local contract is deliberately simpler:

```text
stdin: rendered protocol prompt
stdout: JSON matching personas/existing_data_curation/protocols/persona_attribution_v1/output.schema.json
```

The built-in wrappers below are intended to be copy-pasteable starting points
for collaborators who already have Claude Code or Codex CLI authenticated.

### Claude Code Subscription

```bash
export WIKI_COLLAB_CLAUDE_CMD='python personas/existing_data_curation/wiki_collab/claude_json_backend.py'
python personas/existing_data_curation/worker_kit/run_range.py \
  --db matraix-wiki-profiles-20260601-v1.sqlite \
  --protocol personas/existing_data_curation/protocols/persona_attribution_v1 \
  --range 0:50000 \
  --backend claude-code-acp \
  --model claude-opus-4-8 \
  --effort high \
  --concurrency 4 \
  --worker-id alice \
  --dataset-id matraix_wiki_profiles_20260601_v1 \
  --dataset-sha256 DATASET_SHA256
```

`claude_json_backend.py` calls `claude -p --output-format json --json-schema ...`
and normalizes Claude Code's structured output into the runner's `fields` JSON.
If the local Claude CLI uses a different model alias, set
`WIKI_COLLAB_CLAUDE_CLI_MODEL`, for example:

```bash
export WIKI_COLLAB_CLAUDE_CLI_MODEL=opus
```

### Codex Subscription

```bash
export WIKI_COLLAB_CODEX_CMD='python personas/existing_data_curation/wiki_collab/codex_json_backend.py'
python personas/existing_data_curation/worker_kit/run_range.py \
  --db matraix-wiki-profiles-20260601-v1.sqlite \
  --protocol personas/existing_data_curation/protocols/persona_attribution_v1 \
  --range 50000:100000 \
  --backend codex-acp \
  --model gpt-5.5 \
  --effort high \
  --concurrency 4 \
  --worker-id bob \
  --dataset-id matraix_wiki_profiles_20260601_v1 \
  --dataset-sha256 DATASET_SHA256
```

`codex_json_backend.py` calls `codex exec - --output-schema ...` and writes the
final structured response through `--output-last-message`. Runner effort values
are recorded exactly in provenance; the Codex CLI wrapper maps `--effort max` to
Codex CLI's `model_reasoning_effort="xhigh"` because Codex CLI accepts
`low|medium|high|xhigh`.

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
