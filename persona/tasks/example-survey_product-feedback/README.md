# Product concept survey (ClearQueue) — persona bench

> **Persona bench** — validates **dimension grounding** via MCQ checkpoints.
> Parallel **application** example (open-text, no grounding):
> [`application/tasks/example-survey_product-feedback`](../../../application/tasks/example-survey_product-feedback)

| Field | Value |
|-------|-------|
| Harbor name | `personabench/persona-bench-dim-047-survey-product-feedback` |
| Probe dimension | **`economic_motivation`** (index **47**) → `dimensions.economic_motivation` |
| Output | `/app/output/survey_responses.json` |
| Metrics | `reward.txt` = schema gate + probe grounding · `grounding.json` = detail |

## Design (4×7 spending-posture MCQ)

Each continued question (**q0–q6**) isolates **one spending axis** with four options in a 1:1 mapping to probe postures. Trying the free tier is normal for every posture — forks are **whether/when you would pay**, not whether you would try free. Scoring is **oracle alignment ≥ 80%** (6/7 on continued); `alignment_rate` and per-question detail are in `grounding.json`.

| Question | Axis | Cost-sensitive | Value-driven | Premium-seeking | Indifferent |
|----------|------|----------------|--------------|-----------------|-------------|
| q0 | Pay intent after free trial | `q0_use_free_wont_pay` | `q0_pay_when_roi_clear` | `q0_subscribe_paid_launch` | `q0_free_never_decide_tier` |
| q1 | Plus vs Pro | `q1_reject_both_tiers` | `q1_plus_after_sustained_use` | `q1_happy_plus_or_pro` | `q1_wont_compare_tiers` |
| q2 | Prepay lock-in | `q2_monthly_cancel_anytime` | `q2_annual_after_long_use` | `q2_prepay_annual_plus` | `q2_billing_no_preference` |
| q3 | $1 promo | `q3_skip_even_one_dollar` | `q3_one_dollar_try_cancel` | `q3_grab_dollar_promo` | `q3_ignore_promo` |
| q4 | Switch / pay | `q4_seek_free_alternative` | `q4_compare_pay_if_wins` | `q4_pay_best_no_hunt` | `q4_switch_only_effortless` |
| q5 | Ads | `q5_ads_not_worth_paying` | `q5_ads_pay_if_plus_useful` | `q5_pay_primarily_adfree` | `q5_ads_irrelevant_to_tier` |
| q6 | Overall price | `q6_too_expensive_stay_free` | `q6_fair_if_use_justifies` | `q6_premium_price_ok` | `q6_pricing_unnoticed` |

Decline path: `q0_not_interested` on q0 only (`participation: declined`).

- **Stimulus** — neutral ClearQueue pricing brief + MCQ form (`survey_questions.md`).
- **Verifier** — `test_state.py` (schema) + `test_grounding.py` (oracle whitelist).
- **Sampling** — task catalog defines fixed confounders; job generator filters the pool, stratifies on `economic_motivation` only, and synthesizes missing probe strata when needed. Use `--controlled-probe` for legacy anchor mode.

## Smoke

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p persona/tasks/example-survey_product-feedback
```

## Grounding job

Generate a local recipe first (`--sample-size-per-value-group 2`, seed 42):

```bash
uv run python persona/scripts/generate_persona_job.py \
  --task persona/tasks/example-survey_product-feedback \
  --sample-size-per-value-group 2
```

Then run the generated job and aggregate verifier output:

```bash
uv run harbor run -c configs/jobs/persona-task-grounding-job-recipe/<job-slug>.yaml
uv run python persona/reporting/eval_grounding_job.py jobs/<job_name> \
  --meta configs/jobs/persona-task-grounding-job-recipe/<job-slug>.meta.json
```

The generated YAML and sidecar metadata are ignored by git until a maintainer
promotes a specific recipe to `configs/jobs/`.

Use `--controlled-probe` to clone one anchor persona and vary only the probe dimension (legacy). To stratify across the full pool without catalog confounders, pass a task with no `grounding.confounders` entry or set `"confounders": {}` in the job spec.

## Task catalog confounders

Probe + confounders live in **`grounding.toml`** in this task directory. `generate_persona_job.py` reads it automatically when you pass `--task persona/tasks/example-survey_product-feedback`.

## Copying this task

1. One catalog dimension → `bench_dim_index` + `bench_dim_id`.
2. **Neutral stimulus** + **4×N bijective MCQ forks** (one option per posture per question).
3. Controlled-probe jobs sweep all probe values on one anchor persona.
4. Oracle matrix in `test_grounding.py` — never in `instruction.md`.
