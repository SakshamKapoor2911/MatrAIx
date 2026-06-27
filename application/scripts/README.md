# Application Scripts

[`generate_application_job.py`](generate_application_job.py) samples personas and
writes a multi-trial job YAML plus a `.meta.json` sidecar under
`configs/jobs/application-task-job-recipe/` by default.

Generated job recipes are ignored by git unless a maintainer explicitly curates
one into the repository. Use `--out` to write to a temporary path while testing.

The script supports:

- `--sample-size`
- repeated or comma-separated `--stratify`
- `--name`
- `--job-name`
- `--dataset`
