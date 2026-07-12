# Purchase-intent survey

PersonaBench application (Type-1, survey) task, commerce-retail domain. The
persona is shown a real product they were considering and told that **one**
thing about it changed — its price or an attribute — then answers a short
structured purchase-intent survey. Measures how a single product change shifts
purchase intent.

The task is **dataset-driven**: it ships 494 real Amazon product cases (each
with one changed attribute), so a single task definition covers the whole set.

## The scenario

Harbor injects the persona; the environment supplies, in `/app/input/`:

- `cases.jsonl` — **494 product cases**, one JSON object per line. Each has the
  product (`product_name`, `brand`, `original_price`, `attributes`, `rating`, …)
  and a `change` block (`type` = `price`/`attribute`, which `attribute`, and the
  value `before`/`after`).
- `survey.md` — the six questions and their exact answer codes.

The persona completes the case whose `case_id` equals the `CASE_ID` environment
variable (default `1`) and writes its answers to
`/app/output/purchase_decision.json`.

## Running all 494 cases

A trial is one `(persona × case)` pair. Harbor already fans out over personas
(the job recipe lists them); this task adds the case axis via `CASE_ID`. To
collect the full set, run the task once per `case_id` `1..494`, varying
`CASE_ID` per trial — the same way personas are varied. Case selection is a
runtime concern, so the exact fan-out lives in the environment team's execution
layer; the data and the per-case contract are fixed here.

## Expected artifact

`/app/output/purchase_decision.json` — a single object with exactly six fields:

```json
{
  "purchase_intent": "probably_would_not",
  "price_fairness": "somewhat_high",
  "alternative_seeking": "yes",
  "purchase_timing": "wait_for_sale",
  "necessity_level": "nice_to_have",
  "reasoning": "..."
}
```

The verifier (`tests/test_state.py`) checks the schema: every field present,
each value in its allowed set, `reasoning` non-empty, no extra fields. See
`instruction.md` for the full field spec.

## Layout

- `instruction.md` — the task prompt (dataset + `CASE_ID` contract).
- `task.toml` — metadata + `[environment].definition`.
- `tests/` — verifier (`test_state.py` + `test.sh`).
- `solution/solve.sh` — reference solution (selects the case, posture-aware,
  schema-valid).
- `environment/task-environments/application/purchase-intent-survey/` (in the
  `environment/` module) — Dockerfile + the `/app/input` materials, including
  `cases.jsonl` (the 494-case dataset).

## Local smoke

```bash
# reference solution -> verifier (persona injected at /app/input/persona.yaml,
# cases.jsonl + survey.md staged at /app/input/, CASE_ID optional)
bash solution/solve.sh && python3 tests/test_state.py

# or launch through Harbor
uv run harbor run \
  -a persona-claude-code \
  -m "${PERSONABENCH_HARBOR_PERSONA_MODEL:-anthropic/claude-haiku-4-5}" \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/purchase-intent-survey
```
