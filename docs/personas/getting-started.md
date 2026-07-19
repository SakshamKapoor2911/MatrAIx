# Persona team — grounding evaluation

> **Layer 3** in the Persona pipeline — after [data curation](../../persona/curation/existing_data/README.md)
> and [schema / dimension graph](../../persona/schema/README.md). Index:
> [docs/personas/README.md](./README.md).

> Working draft — prefer [Application QUICKSTART](../../application/QUICKSTART.md) for stable smoke runs.

A step-by-step path from zero to your first **persona grounding** job. No prior Harbor experience required.

**What you are doing (vs Application):** Application tasks simulate *what users would do* in a product scenario. **Persona bench** asks: *given a full persona profile (~1,300 dimensions), does the agent's behavior in this task actually reflect the **probe dimension** we care about?* You build a **controlled cohort** (probe varies, confounders restricted, everything else controlled), run them through a **discriminative task**, and score **grounding**.

**Time:** ~45–90 minutes the first time (Docker image build + grounding job).

---

## Methodology: three roles for dimensions

Every persona carries **1,300+ dimensions** ([`persona/schema/dimensions.json`](../../persona/schema/dimensions.json)). For one bench task you split them into three roles — same layout as the diagram below.

![Persona grounding: dimensions → cohort → task](../assets/persona-grounding-flow.png)

| Zone | Role in this task | Generation / sampling |
|------|-------------------|------------------------|
| **Probe dimension** | The trait you are **testing**. Must **cover all values** in the cohort (e.g. four `economic_motivation` postures). | **Stratify:** N personas per probe value (`--sample-size-per-value-group`). |
| **Confounders** | Dims that would **collide** with your MCQ axes if left free (income shifts price questions, age shifts subscription appetite, …). | **Restrict per task:** fixed values in **`grounding.toml`** → **filter** the pool so only matching personas enter the job. They must **not** explain away probe effects. |
| **Control variables** | All **other** dimensions — rich profile context, not manipulated for this experiment. | **Sampled naturally** from the pool; task design should not make them decisive. |

```text
1,300+ dims
  ├─ probe (varies, full coverage)     → stratify N per value
  ├─ confounders (task-specific)       → filter to catalog fixed values
  └─ control (everything else)         → ride along in YAML, held stable by cohort design
        ↓
  Persona cohort (bench-dev-2000 filtered)
        ↓
  Persona bench task → behavior checkpoints → grounding score
```

**Persona group** = many full profiles that differ on **probe only** (within confounder constraints). Produced by `generate_persona_job.py` or topped up via `generate_dev_personas.py --stratum-min`.

**Legacy shortcut:** `--controlled-probe` clones one anchor and swaps only the probe field — debugging only, not the default production path.

---

## Task design: verify grounding, not “run a survey”

Once the cohort enters the task, **questions / behavior checkpoints** must **verify** the probe dimension — not merely collect opinions.

| Principle | What it means |
|-----------|----------------|
| **Sufficient** | Each checkpoint gives a grounded agent a **fair chance** to express the probe; a generic user could answer without the profile. |
| **Necessary** | After confounders are restricted, the **best** explanation for the oracle-expected choice is the probe value. |
| **Discriminative** | Each probe value → **distinct** expected behavior. Use **bijective MCQ** (`choice_id` ↔ probe value per axis). |

**Task layers (bottom of diagram):**

1. **Neutral stimulus** — product brief + form; **no probe leak** in `instruction.md`.
2. **Behavior checkpoints** — q0…qN forks where options separate probe postures.
3. **Grounding verifier** — `test_grounding.py` oracle (hidden from agent) → `grounding.json` + per-value alignment.

**Anti-patterns:** probe hints in instructions, forks where two postures pick the same option, confounders left free on price-sensitive questions.

---

## Artifacts map

| Layer | Artifact | Notes |
|-------|----------|-------|
| **Catalog** | `src/playground_core/task_catalog.py` | `bench_dim_index`, `type`, `domain`, `tags` (Harbor naming + CI) |
| **Grounding spec** | `persona/tasks/<task>/grounding.toml` | `probe_dimension`, `confounders` (+ rationale, `affects_questions`) |
| **Stimulus** | `environment/*.md`, `instruction.md` | Neutral product/scenario copy; human tone; **no oracle** |
| **Agent input** | `persona_path` YAML | Full profile; never pasted into `instruction.md` |
| **Output** | `/app/output/` | Structured JSON with `choice_id` per question |
| **Trial verifier** | `tests/test_state.py` | Schema gate — invalid → reward 0 |
| **Grounding scorer** | `tests/test_grounding.py` | Oracle whitelist → `reward.txt` + `grounding.json` |
| **Job rollup** | `persona/reporting/eval_grounding_job.py` | Aggregates trials after a grounding job |

**Gold template:** [`persona/tasks/example-survey_product-feedback`](../../persona/tasks/example-survey_product-feedback/) — probes **`economic_motivation`** (dim 47) via ClearQueue pricing MCQs; confounders `socioeconomic_band` + `age_bracket` fixed in catalog.

---

## What you need

| Requirement | Why |
|-------------|-----|
| **[Docker](https://docs.docker.com/get-docker/)** | Persona bench runs in the same Harbor containers as Application tasks |
| **uv** | Python + `harbor` CLI — [Application getting started §2](../../application/QUICKSTART.md#2-install-uv-clone-and-sync) if you have not set up the repo yet |
| **Anthropic API key** | `persona-claude-code` for the examples below |

---

## Harbor vocabulary (Persona bench)

| Term | In this guide |
|------|----------------|
| **Persona bench task** | Harbor task under `persona/tasks/` with catalog `grounding` block — e.g. `example-survey_product-feedback` |
| **Probe** | One dimension (`dimensions.economic_motivation`) whose values you expect to change behavior |
| **Confounder** | Dimension fixed in catalog so it does not explain away probe effects |
| **Trial** | One persona + one task → `grounding.json` |
| **Grounding job** | Many trials, stratified on probe — YAML from `generate_persona_job.py` |
| **Alignment rate** | Share of MCQ answers matching the oracle for that persona's probe value |

Application open-text survey (no grounding oracle): [`application/tasks/example-survey_product-feedback`](../../application/tasks/example-survey_product-feedback/).

---

## 1. Smoke — one persona, one bench task

Assumes repo cloned and `uv venv --python 3.12 && uv pip install -e .` done ([Application §1–2](../../application/QUICKSTART.md)).

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p persona/tasks/example-survey_product-feedback
```

First run builds the Docker image (several minutes).

**Success:** command finishes; trial output under `jobs/`; verifier writes `grounding.json` in trial logs.

**Inspect grounding:**

```bash
# Find latest trial folder, then:
cat jobs/*/example-survey_product-feedback__*/verifier/grounding.json | head -40
```

---

## 2. Read the gold template

Before authoring, walk through:

1. **Catalog** — `grounding.toml` probe + confounders; `bench_dim_index` in [`task_catalog.py`](../../src/playground_core/task_catalog.py) for naming
2. **Stimulus** — neutral brief + MCQ in `environment/survey_questions.md`
3. **Oracle** — value → `choice_id` matrix in `tests/test_grounding.py` (**never** in `instruction.md`)
4. **Task README** — [`persona/tasks/example-survey_product-feedback/README.md`](../../persona/tasks/example-survey_product-feedback/README.md)

Ask for each question: *If I swap only the probe value, does the expected answer change? If two values share the same best option, the fork is not discriminative enough.*

---

## 3. Generate a grounding job

The job generator reads catalog confounders, **filters** the persona pool, **stratifies** on the probe dimension, and writes YAML under `configs/jobs/persona-task-grounding-job-recipe/` (gitignored except the checked-in `playground-*-pg2` example).

```bash
uv run python persona/scripts/generate_persona_job.py \
  --task persona/tasks/example-survey_product-feedback \
  --sample-size-per-value-group 2 \
  --seed 42
```

Generator output (default slug, no `playground-` prefix):

| File | Purpose |
|------|---------|
| `configs/jobs/persona-task-grounding-job-recipe/example-survey-product-feedback-economic-motivation-pg2.yaml` | 8 trials (2 personas × 4 probe values) |
| `...economic-motivation-pg2.meta.json` | Cohort spec for `eval_grounding_job.py` |

The YAML header lists persona IDs and run commands. **Shortcut:** checked-in recipe `playground-example-survey-product-feedback-economic-motivation-pg2.yaml` (same task / pg2 design).

| Flag | Effect |
|------|--------|
| `--sample-size-per-value-group N` | N personas **per probe value** (default stratify mode) |
| `--controlled-probe` | One anchor persona; only probe field varies |
| `--no-stratify` | Random sample without per-value balance |
| `--stratify dimensions.foo` | Override stratify fields (advanced) |

If the pool lacks cells, top up with:

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --task persona/tasks/example-survey_product-feedback \
  --stratum-min 2
```

---

## 4. Run the job and evaluate

**Checked-in recipe** (`seed 42`, `--sample-size-per-value-group 2`):

```bash
uv run harbor run -c configs/jobs/persona-task-grounding-job-recipe/playground-example-survey-product-feedback-economic-motivation-pg2.yaml

uv run python persona/reporting/eval_grounding_job.py jobs/playground-example-survey-product-feedback-economic-motivation-pg2 \
  --meta configs/jobs/persona-task-grounding-job-recipe/playground-example-survey-product-feedback-economic-motivation-pg2.meta.json
```

**After §3 generate** — use paths from your YAML header (`job_name` usually matches the slug):

```bash
# uv run harbor run -c configs/jobs/persona-task-grounding-job-recipe/example-survey-product-feedback-economic-motivation-pg2.yaml
#
# uv run python persona/reporting/eval_grounding_job.py jobs/example-survey-product-feedback-economic-motivation-pg2 \
#   --meta configs/jobs/persona-task-grounding-job-recipe/example-survey-product-feedback-economic-motivation-pg2.meta.json
```

**Success:** per-value-group alignment rates; failures point to weak forks, agent drift, or persona YAML inconsistency.

**View trajectories:** `uv run harbor view jobs/playground-example-survey-product-feedback-economic-motivation-pg2 --build`

---

## 5. Authoring checklist (new bench task)

1. Pick **one** probe dimension from [`persona/schema/dimensions.json`](../../persona/schema/dimensions.json) → `bench_dim_index` + `bench_dim_id` in catalog; **`probe_dimension` in `grounding.toml`**.
2. List **confounders** in `grounding.toml` with fixed values + `affects_questions` rationale.
3. Design **neutral stimulus** + **4×N bijective forks** (see gold template q0–q6 table).
4. Implement oracle in `test_grounding.py`; keep `test_state.py` as schema-only gate.
5. Smoke single persona, then grounding job with `--sample-size-per-value-group 2`.
6. If a value group clusters near chance, **redesign the fork** — do not tune the oracle to fit bad questions.

Copy workflow: [`persona/tasks/README.md`](../../persona/tasks/README.md)

---

## Next steps

| Topic | Doc |
|-------|-----|
| Persona schema & datasets | [README.md](./README.md) |
| Team plan & research | [persona/README.md](../../persona/README.md) |
| Application simulations (product metrics) | [QUICKSTART.md](../../application/QUICKSTART.md) |
| Agents & API keys | [choosing-an-agent.md](../../application/choosing-an-agent.md) |
