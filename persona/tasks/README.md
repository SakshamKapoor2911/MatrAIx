# Persona bench tasks

Each `example-*` directory here is a **real task** you can copy as your starting point.

For the full workflow (Persona bench vs Application), see
[`skills/create-matraix-task/SKILL.md`](../../skills/create-matraix-task/SKILL.md).

## New task

**1. Copy the survey starter** (persona bench currently ships one example task type):

```bash
cp -R persona/tasks/example-survey_product-feedback persona/tasks/example-survey_my-scenario
```

For chat, web, and computer-use scenarios, start from [`application/tasks/`](../../application/tasks/) instead.

**2. Register metadata** in [`src/matraix/task_catalog.py`](../../src/matraix/task_catalog.py)
(`type`, `domain`, `tags`; optional `bench_dim_index` for 1-dim-1-task names).

**3. Edit `task.toml`** in the new folder:

- `[task].name` → from catalog helpers:
  - with `bench_dim_index`: `matraix/persona-bench-dim-{NNN}-{slug}`
  - otherwise: `matraix/persona-bench-{slug}`
  (slug = folder name minus `example-`, with `_` → `-`)
- `[metadata]` → same `type`, `domain`, `tags` as the catalog entry

**4. Replace** `instruction.md`, `environment/`, `tests/` for your scenario.

CI (`test_persona_validation_tasks.py`) fails if catalog and `task.toml` disagree.
No scripts to run.

**5. Smoke**

```bash
uv run harbor run \
  -a persona-claude-code \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p persona/tasks/example-survey_my-scenario
```

## Dev grounding (run time, not task authoring)

```bash
uv run python persona/scripts/generate_persona_job.py \
  --task persona/tasks/example-survey_my-scenario
```

Then `harbor run` + `persona/reporting/eval_grounding_job.py` — see [`../README.md`](../README.md).

## vs `application/tasks/`

Parallel examples may share folder names; they are independent copies, not synced.

## Docker (`persona-claude-code` tasks)

[`_docker/install-claude-code.sh`](_docker/install-claude-code.sh) pre-bakes Claude Code + `uv` into the image. Copy it into `environment/` when authoring survey tasks (see `example-survey_product-feedback`).

## Validation scenario design (persona bench)

Persona bench tasks focus on **survey-style grounding probes** today. What changes vs application tasks is the **scenario** and **instruction tone**:

1. **One probe dimension per task** — `bench_dim_index` in [`task_catalog.py`](../../src/matraix/task_catalog.py) matches [`persona/dimensions.json`](../../dimensions.json). Grounding jobs use `dimensions.<id>` (e.g. `dimensions.age_bracket`).
2. **Probe pressure** — the stimulus should invite a generic "average user" answer. Grounded agents answer from their profile; ungrounded agents leak counterfactual cues.
3. **Human instruction** — write like someone forwarding a real request. Persona lives in YAML; don't say "as your persona" or paste agent setup into `instruction.md`. **Never warn the agent about the probe trap** — traps belong in the stimulus only.
4. **MCQ + checkpoints** — prefer `choice_id` options and verifier lookup tables over open-text regex. Support **multiple valid paths** (e.g. decline with low relevance vs full form).
5. **Trial verifier** — `test_state.py` is a hard gate (invalid output → reward 0). `test_grounding.py` scores behavior and drives `reward.txt`; it also writes `/logs/verifier/grounding.json` with rationale.
6. **Job rollup** — `persona/reporting/eval_grounding_job.py` only aggregates trial `grounding.json` files.

**Gold template:** [`example-survey_product-feedback`](example-survey_product-feedback/README.md) — probes **`economic_motivation`** (dim-047) via neutral ClearQueue MCQ spending forks; default controlled-probe cohort on anchor persona.

