# Offline Wiki Collaboration Email Templates

## Assignment Email

Subject: MatrAIx wiki extraction assignment `{assignment_id}`

Hi `{worker_id}`,

Please run this assignment:

```text
assignment_id: {assignment_id}
worker_id: {worker_id}
dataset_id: {dataset_id}
dataset_sha256: {dataset_sha256}
protocol_id: {protocol_id}
protocol_sha256: {protocol_sha256}
range: [{range_start}, {range_end})
```

Download once:

```text
dataset: {dataset_download_url}
worker_kit: {worker_kit_download_url}
protocol: {protocol_download_url}
```

Example command:

```bash
python personas/existing_data_curation/worker_kit/run_range.py \
  --db matraix-wiki-profiles.sqlite \
  --protocol personas/existing_data_curation/protocols/persona_attribution_v1 \
  --range {range_start}:{range_end} \
  --backend mock \
  --concurrency 4 \
  --worker-id {worker_id} \
  --dataset-id {dataset_id} \
  --dataset-sha256 {dataset_sha256}
```

You may use `mock`, `claude-code-acp`, `codex-acp`, `openai-api`, `anthropic-api`, or `external-command`. If you omit `--model`, the runner defaults to `gpt-5.5` for Codex/OpenAI and `claude-opus-4-8` for Claude/Anthropic. Effort defaults to `max`, but you may override it; the chosen effort must be recorded and will appear in the audit report.

Please return:

```text
results_{worker_id}_{protocol_id}_{range_start_10d}_{range_end_10d}.tar.gz
```

The archive must contain:

```text
results.jsonl.gz
failures.jsonl.gz
run_manifest.json
```

Thanks.

## Return Email

Subject: MatrAIx wiki extraction return `{assignment_id}`

Hi,

Attached or linked:

```text
assignment_id: {assignment_id}
worker_id: {worker_id}
result_archive: {result_archive_name}
backend: {backend}
requested_model: {requested_model}
range: [{range_start}, {range_end})
```

Notes:

```text
{notes}
```

