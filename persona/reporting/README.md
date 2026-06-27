# Persona grounding reporting

After a multi-persona Harbor job completes, **aggregate** per-trial `verifier/grounding.json`
files (written by each persona bench task's verifier). This script does not re-score trials.

Harbor `reward.txt` = schema gate + probe grounding (same pass/fail as `grounding.json` when `PERSONABENCH_PROBE_DIMENSION` is set). Adhoc runs without probe env skip grounding and reward on schema only.

```bash
uv run python persona/reporting/eval_grounding_job.py jobs/<job_name> \
  --meta configs/jobs/persona-task-grounding-job-recipe/<name>.meta.json
```

The `--meta` sidecar is written next to the job YAML by `persona/scripts/generate_persona_job.py`.

Writes `persona_grounding_report.json` with `dim_grounding_mean`, `pass_rate`, and `counterfactual_rate`.
