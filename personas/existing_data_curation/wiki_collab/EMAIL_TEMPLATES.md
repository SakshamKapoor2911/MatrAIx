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
package_manifest.json
run_assignment.sh
README.md
collab_kit/
```

Smoke test after unpacking (no credentials needed):

```bash
./run_assignment.sh
# choose "Mock smoke test" from the menu
./run_assignment.sh --validate
```

Real run — same code, your own account. Use whichever you have:

```bash
./run_assignment.sh
# choose Codex or Claude Code, effort, parallelism, then "Real run / resume"
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
