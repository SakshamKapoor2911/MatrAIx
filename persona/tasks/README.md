# Persona bench tasks

Each `example-*` directory here is a **real task** you can copy as your starting point.

Persona bench tasks live separately from `application/tasks/`; they validate
persona grounding rather than generic application behavior.

## New task

**1. Copy the survey starter** (persona bench currently ships one example task type):

```bash
cp -R persona/tasks/example-survey_product-feedback persona/tasks/example-survey_my-scenario
```

For chat, web, and computer-use scenarios, start from [`application/tasks/`](../../application/tasks/) instead.

**2. Edit `grounding.toml`** — `probe_dimension` + `confounders` for job sampling (see gold template).

**3. Register metadata** in [`src/personabench/task_catalog.py`](../../src/personabench/task_catalog.py)
(`type`, `domain`, `tags`; `bench_dim_index` / `bench_dim_id` for Harbor naming).

**4. Edit `task.toml`** in the new folder:

- `[task].name` → from catalog helpers:
  - with `bench_dim_index`: `personabench/persona-bench-dim-{NNN}-{slug}`
  - otherwise: `personabench/persona-bench-{slug}`
  (slug = folder name minus `example-`, with `_` → `-`)
- `[metadata]` → same `type`, `domain`, `tags` as the catalog entry

**5. Replace** `instruction.md`, `environment/`, `tests/` for your scenario.

CI (`test_persona_validation_tasks.py`) fails if catalog, `task.toml`, and `grounding.toml` disagree.
No scripts to run.

**6. Smoke**

```bash
uv run harbor run \
  -a persona-claude-code \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
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

1. **One probe dimension per task** — declare in **`grounding.toml`**; set matching `bench_dim_index` in [`task_catalog.py`](../../src/personabench/task_catalog.py) for Harbor naming.
2. **Probe pressure** — the stimulus should invite a generic "average user" answer. Grounded agents answer from their profile; ungrounded agents leak counterfactual cues.
3. **Human instruction** — write like someone forwarding a real request. Persona lives in YAML; don't say "as your persona" or paste agent setup into `instruction.md`. **Never warn the agent about the probe trap** — traps belong in the stimulus only.
4. **MCQ + checkpoints** — prefer `choice_id` options and verifier lookup tables over open-text regex. Support **multiple valid paths** (e.g. decline with low relevance vs full form).
5. **Trial verifier** — `test_state.py` is a hard gate (invalid output → reward 0). `test_grounding.py` scores behavior and drives `reward.txt`; it also writes `/logs/verifier/grounding.json` with rationale.
6. **Job rollup** — `persona/reporting/eval_grounding_job.py` only aggregates trial `grounding.json` files.

**Gold template:** [`example-survey_product-feedback`](example-survey_product-feedback/README.md) — probes **`economic_motivation`** (dim-047) via neutral ClearQueue MCQ spending forks; default controlled-probe cohort on anchor persona.
