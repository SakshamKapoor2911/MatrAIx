---
name: create-matraix-task
description: >-
  Create MatrAIx Harbor tasks on the Application or Persona bench track. Use when
  scaffolding application product-research tasks (application/tasks/), persona
  validation tasks (persona/tasks/), MatrAIx task metadata, task_catalog.py, or
  when the user asks which track to use. Defers verifier and environment details
  to the create-task skill.
argument-hint: [application|persona-bench] [example-type]
---

# Create MatrAIx task

MatrAIx has **two independent task trees**. Pick one before scaffolding.

| Track | Path | Purpose | Harbor `[task].name` prefix |
|-------|------|---------|----------------------------|
| **Application** | `application/tasks/` | Product / UX simulation | `matraix/application-…` |
| **Persona bench** | `persona/tasks/` | Dimension / profile validation | `matraix/persona-bench-…` or `matraix/persona-bench-dim-{NNN}-…` |

Same folder naming: `example-{type-variants}_{scenario}`. Parallel example names are **not** synced copies.

For verifier design, Docker layout, and `test.sh` patterns, read and follow **`skills/create-task/SKILL.md`**. This skill only covers **MatrAIx track choice, metadata, and scaffolding**.

---

## Step 0 — Choose track

**Application** if the goal is simulating a product scenario (survey, chat, web, desktop) with persona agents.

**Persona bench** if the goal is validating that agent behavior **grounds** on a persona dimension (add `test_grounding.py`, probe env vars, etc.).

When unclear, ask once: *product research or persona dimension validation?*

---

## Shared conventions (both tracks)

1. **Catalog first** — add the folder name to [`src/matraix/task_catalog.py`](../../src/matraix/task_catalog.py) with `type`, `domain`, `tags`. For persona bench tasks tied to one dimension, also set `bench_dim_index`.
2. **Copy, don’t init from scratch** — duplicate the closest `example-*` sibling in the same tree (see tables below). Do **not** use bare `harbor task init` unless the user explicitly wants a greenfield task outside MatrAIx examples.
3. **`task.toml` metadata** — omit `[task].keywords`; set `[metadata]` `type`, `domain`, `tags` to match the catalog entry ([`docs/applications/task-guide.md`](../../docs/applications/task-guide.md)).
4. **Persona at run time** — scenarios live in `instruction.md`; traits live in persona YAML (`persona/datasets/bench-dev-2000/`). Smoke with `-a persona-*` and `--ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml`.
5. **No persona/scripts when authoring** — contributors edit files only; CI validates persona bench `task.toml` vs catalog.

Naming slug: directory `example-survey_my-scenario` → slug `survey-my-scenario` (drop `example-`, `_` → `-`).

Harbor `[task].name` must have exactly one `/` (`matraix/rest`). Use prefixes in the segment after `matraix/`, not nested paths.

- Application: `matraix/application-{slug}` (e.g. `matraix/application-chat-api-support-chatbot`)
- Persona bench (1 dim, 1 task): add `bench_dim_index` in catalog → `matraix/persona-bench-dim-{NNN}-{slug}` (e.g. `matraix/persona-bench-dim-001-survey-product-feedback` for `age_bracket`)
- Persona bench (no dim yet): `matraix/persona-bench-{slug}`

---

## Application track

**Docs:** [`application/tasks/README.md`](../../application/tasks/README.md) · [`docs/applications/task-guide.md`](../../docs/applications/task-guide.md)

### Copy starter

| type | Copy from |
|------|-----------|
| survey | `application/tasks/example-survey_product-feedback` |
| chat (API) | `application/tasks/example-chat-api_support_chatbot` |
| chat (MCP) | `application/tasks/example-chat-mcp_support_chatbot` |
| web | `application/tasks/example-web-playwright_books-interest` |
| desktop / mobile | `application/tasks/example-computer-use-*` |

```bash
cp -R application/tasks/example-survey_product-feedback \
      application/tasks/example-survey_my-scenario
```

### `task.toml`

```toml
[task]
name = "matraix/application-survey-my-scenario"

[metadata]
difficulty = "easy"
type = "survey"       # from catalog
domain = "software"   # from catalog
tags = ["...", "..."] # from catalog — scenario topics only
```

### Smoke

```bash
uv run harbor run \
  -a persona-claude-code \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p application/tasks/example-survey_my-scenario
```

Or use a checked-in job under `configs/jobs/example-job-recipe/` after updating the task path.

### Do not

- Put persona bench-only verifiers (`test_grounding.py`, `MATRAIX_PROBE_*`) here unless the user explicitly wants them on Application tasks.

---

## Persona bench track

**Docs:** [`persona/tasks/README.md`](../../persona/tasks/README.md)

### Copy starter

Persona bench currently ships **survey** examples only. For other interaction types, copy from [`application/tasks/`](../../application/tasks/).

| type | Copy from |
|------|-----------|
| survey | `persona/tasks/example-survey_product-feedback` |

```bash
cp -R persona/tasks/example-survey_product-feedback \
      persona/tasks/example-survey_my-scenario
```

### `task.toml`

```toml
[task]
name = "matraix/persona-bench-dim-001-survey-my-scenario"  # when bench_dim_index = 1 (age_bracket) in catalog
# or: name = "matraix/persona-bench-survey-my-scenario"     # when no bench_dim_index yet

[metadata]
difficulty = "easy"
type = "survey"       # from catalog — same keys as Application
domain = "software"
tags = ["...", "..."]
```

CI: `pytest tests/unit/matraix/test_persona_validation_tasks.py` — catalog and `task.toml` must match.

### Persona-only extras

- Keep or add grounding verifiers under `tests/` (e.g. survey `test_grounding.py`). **`test.sh`**: schema tests are a hard gate; `reward.txt` follows grounding (declined/continued paths). Adhoc smoke without `MATRAIX_PROBE_*` skips grounding and rewards schema pass only.
- **`instruction.md`**: human voice first (like a forwarded ask); minimal JSON/schema footer. Do not say "as your persona" — profile is injected separately. **Do not tell the agent the stimulus may not apply to them** — probe pressure must come from brief/questions/UI only.
- README may note the parallel Application example path (independent code).
- See [`persona/tasks/example-survey_product-feedback/README.md`](../../persona/tasks/example-survey_product-feedback/README.md) for the gold validation template.

### Smoke

```bash
uv run harbor run \
  -a persona-claude-code \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p persona/tasks/example-survey_my-scenario
```

### Dev grounding (after task exists — not part of authoring)

```bash
uv run python persona/scripts/generate_persona_job.py \
  --task persona/tasks/example-survey_my-scenario
```

Then `harbor run` on the job YAML under `configs/jobs/persona-task-grounding-job-recipe/` and `persona/reporting/eval_grounding_job.py`.

---

## Checklist before finishing

```
- [ ] Track chosen (application/ vs persona/tasks/)
- [ ] Catalog entry in task_catalog.py
- [ ] Copied from closest example-* sibling in the same tree
- [ ] task.toml name prefix correct (`application-` vs `persona-bench-` / `persona-bench-dim-{NNN}-`)
- [ ] metadata type / domain / tags match catalog
- [ ] instruction.md + environment/ + tests/ updated for scenario
- [ ] Oracle smoke: harbor run -a oracle -p <task-path>
- [ ] Persona smoke: harbor run with persona-claude-code + persona_0042
- [ ] README.md updated (create-task Step 9)
```
