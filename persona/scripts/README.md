# Persona scripts

| Script | Purpose |
|--------|---------|
| [`generate_dev_personas.py`](generate_dev_personas.py) | Generate consistent dev YAML from `persona/schema/dimensions.json` |
| [`generate_persona_job.py`](generate_persona_job.py) | Sample personas → Harbor grounding job YAML |

**Dev pool:** `uv run python persona/scripts/generate_dev_personas.py` → `persona/datasets/_generated/bench-dev-2000/` (ignored by git; see `--task` / `--stratum-min` for grounding cell top-up)

**Grounding jobs** read confounders from the task catalog when present (filter pool → stratify on probe only). Default for catalog tasks with confounders. Use `--controlled-probe` for anchor-based cohorts; `--no-controlled-probe` disables anchor mode explicitly.
