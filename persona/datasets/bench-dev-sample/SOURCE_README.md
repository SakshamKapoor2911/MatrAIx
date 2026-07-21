# bench-dev-sample source

Synthetic dev persona pool for docs, smoke tests, Harbor tasks, and Playground UI.

| Field | Value |
|-------|-------|
| Checked-in count | 200 (`persona_0001` … `persona_0200`) |
| Schema | v2 YAML (`persona_id`, `version`, `source`, `dimensions`) |
| Persona version | `1.0` |
| Source labels | `Nemotron`, `OASIS`, `PersonaHub`, `PRIMEX` (random per persona) |
| Smoke | `persona_0042.yaml` |
| Dimensions | **124** — standard `load_dev_dimension_ids()` set: core (index 1–47) + all `cog_*` + food/diet (`lstyle_diet_type`, habits, dietary restriction, `att_veganism`, `fam_nutrition`) + all `cuis_*` |
| UI grouping | `persona/schema/dimension_categories.json` |

Personas are sampled so **linked dimensions stay consistent** (no counterfactual combos like `18–24` + `Retirement`, or `Student` + `VP`). Independent dims (`economic_motivation`, cognitive style, food prefs, etc.) are random.

After a full regenerate, re-append food/cuisine dims without reshuffling the original core/`cog_*` values:

```bash
uv run python persona/scripts/augment_dev_personas_food_dims.py
```

Regenerate:

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --count 200 \
  --seed 42 \
  --out persona/datasets/bench-dev-sample \
  --smoke-id 0042 \
  --version 1.0 \
  --manifest-name bench-dev-sample \
  --manifest-description "Dev persona pool for docs, smoke tests, and Playground UI."
```

Optional stratum top-up for grounding jobs:

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --count 2000 \
  --seed 42 \
  --task persona/tasks/example-survey_product-feedback \
  --stratum-min 2
```
