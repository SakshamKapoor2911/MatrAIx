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
range: [{range_start}, {range_end})
task_count: {task_count}
dimension_count: {dimension_count}
```

Download and unpack:

```text
assignment_package: {assignment_package_url}
```

The package contains:

```text
assignment.json
tasks.jsonl
dimensions.json
README.md
collab_kit/
```

Smoke test after unpacking (no credentials needed):

```bash
cd collab_kit
./run.sh --tasks ../tasks.jsonl --dimensions ../dimensions.json \
  --out ../results.jsonl --backend mock
python3 conformance.py --results ../results.jsonl \
  --dimensions ../dimensions.json --tasks ../tasks.jsonl
```

Real run — same code, your own account. Use whichever you have:

```bash
# Claude subscription (just have the `claude` CLI logged in):
./run.sh --tasks ../tasks.jsonl --dimensions ../dimensions.json \
  --out ../results.jsonl --backend claude-code-acp --jobs 6
# Codex subscription / API key: see collab_kit/README.md ("Run on your own account").
```

`solver.py` ships with our default extraction method and works as-is. You are
welcome to improve it for better results — just keep the output contract
unchanged.

Please return:

```text
results.jsonl
```

Thanks.

## Return Email

Subject: MatrAIx wiki extraction return `{assignment_id}`

Hi,

Attached or linked:

```text
assignment_id: {assignment_id}
worker_id: {worker_id}
results_file: results.jsonl
backend: {backend}
requested_model: {requested_model}
range: [{range_start}, {range_end})
```

Notes:

```text
{notes}
```
