# bench-dev-sample source

Synthetic dev persona pool for docs, smoke tests, Harbor tasks, and PersonaEval UI.

| Field | Value |
|-------|-------|
| Checked-in count | 200 (`persona_0001` … `persona_0200`) |
| Schema | v2 YAML (`persona_id`, `version`, `source`, `dimensions`) |
| Persona version | `1.0` |
| Source labels | `Nemotron`, `OASIS`, `PersonaHub`, `PRIMEX` (random per persona) |
| Smoke | `persona_0042.yaml` |
| Dimensions | **82** — catalog index 1–47 (core) + all `cog_*` communication dims |
| UI grouping | `persona/schema/dimension_categories.json` |

Personas are sampled so **linked dimensions stay consistent** (no counterfactual combos like `18–24` + `Retirement`, or `Student` + `VP`). Independent dims (`economic_motivation`, cognitive style, etc.) are random.

Regenerate:

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --count 200 \
  --seed 42 \
  --out persona/datasets/bench-dev-sample \
  --smoke-id 0042 \
  --version 1.0 \
  --manifest-name bench-dev-sample \
  --manifest-description "Dev persona pool for docs, smoke tests, and PersonaEval UI."
```

Optional stratum top-up for grounding jobs:

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --count 2000 \
  --seed 42 \
  --task persona/tasks/example-survey_product-feedback \
  --stratum-min 2
```
