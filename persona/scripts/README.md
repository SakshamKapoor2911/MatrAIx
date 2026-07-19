# Persona scripts

| Script | Purpose |
|--------|---------|
| [`generate_dev_personas.py`](generate_dev_personas.py) | Generate consistent dev YAML from `persona/schema/dimensions.json` |
| [`generate_persona_job.py`](generate_persona_job.py) | Sample personas → Harbor grounding job YAML |

The production persona dataset is not ready yet. Synthetic generation here is
for **local coverage** so task authors can validate **task design** and
**persona-aware reporting / analysis** — not a stand-in for the final
population.

**Dev pool:** `uv run python persona/scripts/generate_dev_personas.py` → `persona/datasets/_generated/bench-dev-2000/` (ignored by git; see `--task` / `--stratum-min` for grounding cell top-up)

**Task strategy coverage** (before Playground / CLI sampling fails on the 200-person fixture):

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --strategy application/tasks/<task>/persona_strategy.json
```

Writes `persona/datasets/_generated/strategy-<task-slug>/` by expanding
`dimensionFilters` into strata and topping up each cell (default min derived
from `sampleSize` / `sampleSizePerValueGroup`). Then point the strategy
`"pool"` at that directory locally, or pass the pool path when sampling.

Playground / job launch also **auto top-ups** the same `_generated/` pool when
sampling hits a coverage error and filters are present; use the CLI when you
want the pool ready before opening the UI.

**Grounding jobs** read confounders from the task catalog when present (filter pool → stratify on probe only). Default for catalog tasks with confounders. Use `--controlled-probe` for anchor-based cohorts; `--no-controlled-probe` disables anchor mode explicitly.
