# PersonaBench Unified Task & Eval Plan

**Status:** Draft for review  
**Last updated:** 2026-06-30  
**Related:** [`user-simulator-chat-design.md`](user-simulator-chat-design.md), [`application/tasks/interface/`](application/tasks/interface/), [`docs/architecture.md`](docs/architecture.md)

---

## 0. Purpose

This plan unifies what we have been designing in architecture discussions:

1. **One contributor contract** for all application task types (`survey`, `chat`, `web`, `cua`, `app-api`).
2. **One execution contract** for batch and UI: Harbor **job → trials** (one trial per persona), not parallel `local | harbor | benchflow` products.
3. **One PersonaEval / Cockpit UX** that builds persona groups, picks model/agent, launches jobs, and scales out trials (distributed workers).
4. **Shared runtime assets** (task image bases, central chat SUT sidecars) so contributors do not copy Dockerfiles per task.
5. **UserSimulator v2** for chat (see [`user-simulator-chat-design.md`](user-simulator-chat-design.md)) as the canonical chat driver, shared by UI and Harbor.

**Reviewers:** use §11 (acceptance criteria) and §12 (non-goals) as the approval checklist.

---

## 1. Executive summary

### 1.1 Problem today

| Pain | Root cause |
|------|------------|
| Contributor edits two trees | `application/tasks/` + `environment/task-environments/` linked only by `[environment].definition` — easy to mispoint or forget |
| Duplicate Dockerfiles | Nearly identical Claude Code / Playwright / Cocoa images per task |
| PersonaEval ≠ Harbor | UI uses `run_store`, built-in task catalogs, `MATRIX_PERSONA_EVAL_RUNTIME`; contributors sign off with `harbor run` + `jobs/` |
| Chat SUT scattered | `recommender-api`, `support-api` live under per-task environments; RecAI / OpenBB / Medical are PersonaEval-only adapters |
| Chat driver split | JSON UserSimulator (local) vs `persona-claude-code` in Docker (Harbor) — different persona injection and artifacts |
| Type confusion | `web` vs `desktop`/`mobile` vs AppWorld; `api` naming collides with HTTP sidecars |

### 1.2 Decision

| Layer | Choice |
|-------|--------|
| **Sign-off authority** | Harbor: `application/tasks/` + `tests/` + `jobs/<job>/<trial>/` + verifier |
| **Task `type` (contributor-facing)** | `survey` · `chat` · `web` · `cua` · `app-api` |
| **Run mode (per job)** | `auto` · `force_docker` · `smoke` |
| **Execution plane (platform)** | `harbor` (default) · `remote` (BenchFlow-compatible HTTP for `app-api`, optional heavy web) |
| **PersonaEval / Cockpit** | **Job launcher + live monitor** over Harbor `jobs/` — not a second artifact store |
| **BenchFlow** | Remote execution plane for `app-api` (and optional cloud web); not a parallel survey/chat implementation |

### 1.3 What we are not doing

- Replacing Harbor with PersonaEval or BenchFlow as the batch platform.
- Using `T0`/`T1`/`T3` in contributor-facing `task.toml` (internal docs may still use execution-profile names).
- Putting module business logic under `apps/` (PersonaEval stays under `application/`; only frontends may move to `apps/persona-eval/` later if desired).

---

## 2. North-star model

### 2.1 One object graph everywhere

```text
PersonaGroup (catalog sample or explicit IDs)
        +
Task (application/tasks/<name>/)
        +
RunConfig (mode, plane, persona_model, agent/driver overrides)
        ↓
Harbor Job (configs/jobs/ or UI-generated job YAML)
        ↓
Trial × N personas   (one trial = one persona × one task attempt)
        ↓
jobs/<job_name>/<trial_name>/
  artifacts/ + verifier result + optional events.jsonl
```

**Contributor** authors **Task**.  
**Researcher / UI** authors **Job** (persona group + task + knobs).  
**Platform** provides **bases**, **SUT registry**, and **workers**.

### 2.2 Three axes (who sets what)

| Axis | Field | Who sets it | Question answered |
|------|--------|-------------|-------------------|
| **A — Type** | `[metadata].type` | Task contributor | What interaction protocol is this? |
| **B — Mode** | `execution.mode` on job | Runner / UI / CI | How “real” is this run? |
| **C — Plane** | `execution.plane` on job or deployment | Platform (default `harbor`) | Where does compute run? |

**Type** lives in task protocol docs and `task.toml`.  
**Mode** and **plane** live on **job recipes** and PersonaEval launch forms — not in every task folder.

#### Type → default driver (axis A)

| `type` | Control surface | Default agent / driver | Default plane |
|--------|-----------------|------------------------|---------------|
| `survey` | Structured questionnaire | `json_survey` (host) or `persona-claude-code` if `force_docker` | `harbor` |
| `chat` | Multi-turn chat API | `user_sim` (UserSim v2) + `ChatSessionPort` → SUT sidecar | `harbor` |
| `web` | Browser DOM / automation | `persona-openhands-sdk` \| `persona-browser-use` \| `persona-cocoa` (per task) | `harbor` |
| `cua` | OS GUI (screenshot loop) | `persona-computer-1` | `harbor` |
| `app-api` | Multi-app programmatic API | AppWorld-style agent (future); today `remote` stub | `remote` |

Suggested agents are also documented in task `instruction.md` (`**Suggested agent:** ...`), matching the Persona agents table.

#### Mode (axis B)

| Mode | Behavior |
|------|----------|
| `auto` | Use type defaults; survey/chat use lightweight drivers when Harbor supports them; web/cua use real containers |
| `force_docker` | Run `persona-claude-code` (or type-appropriate container agent) even for survey/chat — parity / sign-off |
| `smoke` | Stubs / W0 web / compat mocks — UI dev and CI wiring only; **not** benchmark sign-off |

#### Plane (axis C)

| Plane | Behavior |
|-------|----------|
| `harbor` | Local or cluster Harbor schedules trials, writes `jobs/`, runs verifiers |
| `remote` | HTTP worker (`POST /v1/runs`) for `app-api`; preserves artifact shapes; verifier alignment required for sign-off |

Deprecate **`MATRIX_PERSONA_EVAL_RUNTIME=local|harbor|benchflow`** as the primary fork. Replace with **job-level `mode` + `plane`** and shared drivers inside Harbor / PersonaEval launch layer.

### 2.3 Web fidelity (orthogonal to type)

For `web` / some `cua` tasks only:

| Label | Meaning | Sign-off? |
|-------|---------|-----------|
| W0 | LLM-imagined steps / mock screenshots | No |
| W1 | Real browser + DOM | Yes |
| W2 | Screenshot CUA loop | Yes |

`smoke` mode implies W0 for web. `auto` uses task-declared fidelity (default W1/W2 for real web tasks).

---

## 3. Task contributor model

### 3.1 What lives in `application/tasks/<name>/`

| Asset | Purpose |
|-------|---------|
| `instruction.md` | Agent-facing task (and optional `USER` block or `user_scenario.yaml` for chat) |
| `user_scenario.yaml` | Chat only: hidden user goal, progressive disclosure (see UserSim design) |
| `task.toml` | `type`, `domain`, tags, `[environment]` pointers, verifier/agent timeouts |
| `tests/` | Objective verifier — **authority for pass/fail** |
| `solution/` | Oracle / reference |
| `fixtures/` | Task-specific inputs copied into container (`survey_questions.md`, `order_context.md`, …) |

Contributor **primary workspace** is this folder. Verifier and scenario stay colocated.

### 3.2 Shared runtime assets (not per-task copies)

```text
environment/task-bases/              # Few Docker / compose templates
  survey-claude/
  chat-claude-sidecar/
  web-playwright/
  web-browser-use/
  web-cocoa/
  cua-linux-desktop/

environment/chat-suts/               # Central registry of chatbots under test (SUT)
  recommender-api/
  support-api/
  openbb-mcp/                        # future
  medical-assistant/                 # future

environment/task-environments/application/<task-name>/   # Thin overlay (generated or scaffolded)
  Dockerfile          # FROM task-base + COPY fixtures
  docker-compose.yaml # wires main + sut service
```

#### When to add a central SUT vs keep local

| Put under `environment/chat-suts/<bot>/` | Keep next to task |
|------------------------------------------|-------------------|
| Product-line bot reused across scenarios (RecAI, OpenBB, Medical) | One-off demo bot tied to a single scenario |
| Stable HTTP chat contract | Sidecar encodes scenario-specific state only |

#### `task.toml` environment section (target shape)

```toml
[metadata]
type = "chat"          # survey | chat | web | cua | app-api
domain = "commerce-retail"

[environment]
base = "chat-claude-sidecar"
sut = "chat-suts/support-api"       # chat only; omit for survey/web/cua
definition = "application/<name>"   # thin overlay path (scaffolded)
# fixtures copied from application/tasks/<name>/fixtures/ at build
```

Migrate existing `desktop` / `mobile` → `type = "cua"` with `tags = ["platform:ios"]` etc.

### 3.3 Contributor workflow (unified)

```bash
# 1. Scaffold task + thin environment + optional new SUT
scripts/scaffold_application_task.sh \
  --name my-support-chat \
  --type chat \
  --base chat-claude-sidecar \
  --sut chat-suts/support-api   # or --new-sut

# 2. Edit application/tasks/my-support-chat/{instruction,tests,fixtures,user_scenario.yaml}

# 3. Sign-off locally
uv run harbor run -c configs/jobs/<recipe>.yaml

# 4. Optional smoke in UI (mode=smoke) — same task path once UI reads task registry
```

CI guards: `definition` exists, `base` valid, `sut` ref resolvable, fixtures present.

---

## 4. Chat: UserSimulator + central SUTs

Implement per [`user-simulator-chat-design.md`](user-simulator-chat-design.md).

### 4.1 Roles

| Component | Owner | Notes |
|-----------|-------|-------|
| **UserSimSession** | `persona_eval/user_sim/` (shared library) | Persona Jinja + `user_scenario.yaml` + tools + `messages[]` |
| **ChatSessionPort** | Protocol in `application/tasks/interface/chatbot/` | Adapters per SUT |
| **SUT sidecar** | `environment/chat-suts/<name>/` | HTTP (or in-process RecAI adapter for dev) |
| **Objective verifier** | `application/tasks/.../tests/` | Unchanged |
| **Persona self-report** | UserSim post-loop artifact | Does not gate objective pass/fail |

### 4.2 PersonaEval `applicationId` → registry entry

Deprecate hardcoded three-app UI list as the source of truth. Target:

```yaml
# configs/chat-suts.yaml or application/persona_eval/data/chat_registry.yaml
- id: recai
  sut: in_process/recai          # or chat-suts/recommender-api for smoke
  default_task: recommender-agent_chat_api
- id: finance_openbb
  sut: chat-suts/openbb-mcp
  default_task: ...
- id: medical_assistant
  sut: chat-suts/medical-assistant
  default_task: ...
```

UI picks **registry id** → resolves **task + sut** → launches **Harbor job**.

### 4.3 Harbor chat execution profile

- **Default (`auto`):** T1-style — host or service trial runs `UserSimSession` loop; sidecar in compose; per-trial `sessionId`; no `persona-claude-code` container for the user role.
- **`force_docker`:** Existing path — `persona-claude-code` in container talking to sidecar (parity).
- Remove `_RUN_LOCK` for Harbor path; use `n_concurrent_trials` + isolated sessions.

---

## 5. PersonaEval / Cockpit UI

### 5.1 Role

PersonaEval is the **application module workbench** (`application/persona_eval/`):

- Public demo and future marketing surfaces.
- **Same job abstraction as CLI** for researchers and contributors smoke-testing tasks.

It is **not** the canonical artifact root (`jobs/` is).

### 5.2 Unified launch flow (target UX)

```text
1. Select task(s)        — from registry: application/tasks + curated PersonaEval catalog
2. Build persona group   — explicit IDs | sample N from catalog | saved cohort YAML
3. Configure run
     - type implied by task
     - mode: auto | smoke | force_docker
     - persona model (user sim / survey JSON model)
     - agent override (web/cua: persona-* from table)
     - plane: harbor | remote (app-api only by default)
4. Launch job            — POST /api/jobs → spawns harbor run (local or dispatcher)
5. Monitor trials        — poll jobs/<job>/ trials; SSE tail events.jsonl
6. Compare / export      — reuse viewer components where possible
```

### 5.3 Distributed execution

| Tier | Mechanism |
|------|-----------|
| **Phase 1** | Single machine: `harbor run -c job.yaml` subprocess from PersonaEval API |
| **Phase 2** | Job queue + worker pool: workers pull trial specs, run `harbor trial`, report back to shared `jobs_dir` (NFS/S3 sync) |
| **Phase 3** | Remote plane: `app-api` and optional web trials via BenchFlow-compatible `/v1/runs`; job coordinator merges artifacts into same `jobs/` layout |

UI shows **job progress = trials completed / N** regardless of where trials execute.

### 5.4 Contributor vs visitor

| User | Path |
|------|------|
| **Visitor / demo** | Curated tasks, `mode=smoke` or small persona sample |
| **Contributor** | `harbor run` sign-off + UI `mode=auto` on their task once registered |
| **Researcher** | Persona group sampling, batch jobs, compare trials |

### 5.5 Runs & history — **decided: attach to Harbor `jobs/`**

**Decision (review):** PersonaEval does **not** grow a parallel persistence layer. Launch, monitor, list, and export run history by reading **Harbor `jobs/<job>/<trial>/`** (reuse `environment/runtime/harbor/viewer` APIs / `apps/viewer` types where possible). Customize debrief UX later; do not block on a perfect mapper on day one.

| Today (`run_store`) | Target (Harbor jobs) |
|---------------------|----------------------|
| Flat `{run_id}.json` under `data/cache/.../persona_eval_runs/` | Tree: `jobs/<job_name>/<trial_name>/` |
| `GET /api/persona-eval/runs` scans cache | List jobs/trials from `jobs_dir` (or viewer API) |
| Run-centric debrief (`surveyResult`, `questionnaire`, …) | Trial-centric: `artifacts/`, `result.json`, verifier — **thin adapter** to existing UI shapes as follow-up |
| One-off eval from Cockpit | Batch-native: 500 personas = 1 job × 500 trials |

**Migration notes:**

- **Phase 3 first slice:** `POST /api/jobs` → `harbor run` → poll trial status from `jobs/`; Runs page lists trials, not `run_store` records.
- **`run_store`:** deprecate for sign-off and history; may remain temporarily behind `mode=smoke` only until Harbor path covers demo flows.
- **Customization deferred:** per-type debrief tiles, self-report vs verifier display, Run Compare — iterate after jobs wiring works.
- **Consolidate paths:** PersonaEval Harbor integrations today write to `data/cache/.../harbor_*_eval/`; target is repo-standard `jobs_dir` from job YAML.

---

## 6. Harbor execution profiles (internal)

Contributor sees **type + suggested agent**. Platform implements profiles:

| Profile | Types | Container? | Driver |
|---------|-------|------------|--------|
| `json_survey` | survey | No agent container | `complete_json` + persona Jinja; verifier on host |
| `user_sim_chat` | chat | Sidecar only (+ thin main optional) | UserSim v2 + `ChatSessionPort` |
| `docker_agent` | survey/chat/web/cua | Yes | `persona-*` per agent table |
| `remote_worker` | app-api | Remote | HTTP worker; artifact ingest |

Implement `json_survey` and `user_sim_chat` as **Harbor trial modes** (new environment/trial hooks), not as PersonaEval-only shortcuts.

---

## 7. BenchFlow / remote plane

- **Scope:** `app-api` default; optional offload for heavy web at scale.
- **Contract:** MatrAIx `/v1/runs` payload (persona, task, prompts) → artifacts (`trace.json`, `appworld_result.json`, …).
- **Not in scope:** Parallel BenchFlow implementations for survey/chat/web drivers.
- **Compat server:** `smoke` + local dev only.

---

## 8. Repository layout (target)

```text
application/
  tasks/                          # Scenarios + verifiers + fixtures (all types)
  tasks/interface/                # Protocol docs; five types
  persona_eval/                   # API + frontend + UserSim library

environment/
  task-bases/                     # NEW: shared image templates
  chat-suts/                      # NEW: central SUT sidecars
  task-environments/application/  # Thin per-task overlays (scaffolded)
  runtime/harbor/                 # Job/trial/verifier + native trial hooks
  agents/personabench/agents/     # persona-* agents
  integrations/persona_eval/      # Launch adapters (shrink over time)

configs/jobs/                     # Job recipes: persona list + task + mode + plane

apps/viewer/                      # Post-hoc job browser (unchanged)
apps/persona-eval/                # OPTIONAL later: move frontend only
```

---

## 9. Migration phases

### Phase 0 — Docs & guards (1–2 weeks)

- [ ] Adopt five `type` values in `application/tasks/README.md` and `interface/`
- [ ] Document axes A/B/C in this plan; mark `desktop`/`mobile` deprecated → `cua`
- [ ] `scripts/scaffold_application_task.sh` + CI check `environment.definition`
- [ ] Fix import shims (`backend.service.*` → `environment.integrations.*`) or direct imports — **done:** `deps.py` imports canonical modules; backend shims are thin re-exports

### Phase 1 — Runtime assets (2–3 weeks)

- [ ] Create `environment/task-bases/` from existing example Dockerfiles (4–6 bases)
- [ ] Extract `environment/chat-suts/{recommender-api,support-api}` from task-environments
- [ ] Thin overlays for 2–3 reference tasks
- [ ] `fixtures/` under `application/tasks/` for survey/chat examples

### Phase 2 — UserSim v2 + chat registry (3–4 weeks)

Per [`user-simulator-chat-design.md`](user-simulator-chat-design.md) Phase 1–2:

- [ ] `UserSimSession`, `ChatSessionPort`, `user_scenario.yaml` on one chat task
- [ ] `chat-suts` registry YAML; wire PersonaEval `applicationId` to registry
- [ ] Feature flag `MATRIX_USER_SIM_V2=1` → default on

### Phase 3 — Unified job launch in UI (4–6 weeks)

- [ ] PersonaEval API: `POST /api/jobs` → generate job YAML → `harbor run` (standard `jobs_dir`) — **started:** `POST /api/harbor/jobs` + list/get
- [ ] Persona group builder (sample N, save cohort) — uses `bench-dev-sample` + `dimension_categories.json` (§10.3)
- [ ] **Runs / monitor:** list jobs and trials from `jobs/` (viewer API); **no new `run_store` writes** for sign-off paths (§5.5)
- [ ] Minimal trial detail API (status + artifact paths); rich debrief mapping **deferred**
- [ ] Deprecate `run_store` for history (optional smoke-only shim until demo paths migrate)

### Phase 4 — Harbor native trials (6–10 weeks)

- [ ] `json_survey` profile: no agent container, host verifier
- [ ] `user_sim_chat` profile: sidecar + UserSim on trial worker
- [ ] `n_concurrent_trials` ≥ 4 chat without cross-talk
- [ ] Remove duplicate `local_*` / `harbor_*` PersonaEval runners where Harbor subsumes

### Phase 5 — Distributed + remote (ongoing)

- [ ] Trial worker queue + shared `jobs_dir`
- [ ] `app-api` remote plane production path
- [ ] UI shows distributed trial placement (optional)

---

## 10. Persona sampling & job recipes

### 10.1 Job YAML shape (illustrative)

```yaml
job_name: my-study-2026-06-30
jobs_dir: jobs
n_concurrent_trials: 4

execution:
  mode: auto          # auto | force_docker | smoke
  plane: harbor       # harbor | remote

personas:
  source: catalog
  sample: 32
  seed: 42
  # or explicit: [persona/datasets/.../persona_0042.yaml, ...]

persona_model: anthropic/claude-haiku-4-5

tasks:
  - path: application/tasks/recommender-agent_chat_api
    # chat: sut override optional if not in task.toml
    agent: persona-claude-code   # only if force_docker or type requires

agents: []   # populated by resolver from task type + overrides
```

PersonaEval UI is a **form over this schema**.

### 10.2 Cohort files

Save reusable persona groups under `persona/datasets/cohorts/` or `configs/cohorts/` (TBD) for paper reproducibility.

### 10.3 Dev persona catalog (`bench-dev-sample`) — **implemented, pending UI wiring**

**Goal:** One checked-in dev persona pool for Harbor smoke, docs, and PersonaEval persona-group builder — without exposing 1300+ flat dimensions in the UI.

#### Dataset shape (v2 YAML, persona version `1.0`)

| Field | Value |
|-------|-------|
| Path | `persona/datasets/bench-dev-sample/` |
| Count | **500** (`persona_0001.yaml` … `persona_0500.yaml`) |
| Smoke fixture | `persona_0042.yaml` (unchanged ID for task READMEs / recipes) |
| Schema | `persona_id`, `version`, `source`, `dimensions` (82 fields) |
| `version` | `1.0` |
| `source` | Random per persona from PersonaEval catalog provenance: `Nemotron` · `OASIS` · `PersonaHub` · `PRIMEX` |
| Dimensions | Catalog index 1–47 (core) + all `cog_*` communication dims — same dev profile as before |

Regenerate:

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --count 500 \
  --seed 42 \
  --out persona/datasets/bench-dev-sample \
  --smoke-id 0042 \
  --version 1.0 \
  --manifest-name bench-dev-sample \
  --manifest-description "Dev persona pool for docs, smoke tests, and PersonaEval UI."
```

`manifest.json` includes `dimension_categories` pointer, `source_counts`, and full persona index.

#### Dimension UI hierarchy (`persona/schema/dimension_categories.json`)

Flat `dimensions.json` (1339 dims) stays the **catalog authority**. A separate mapping file drives **grouped pickers** in PersonaEval:

```text
dimension_categories.json
  topLevelGroups[]           # 11 groups (demographic, linguistic, expertise, …)
  devProfile.groups[]        # 82-field bench-dev profile only
    - id, label
    - dimensionIds[]         # ordered subset for nested UI
  categoryIndex[]            # full catalog: dimensions.json category → groupId
  personaSources[]           # Nemotron | OASIS | PersonaHub | PRIMEX
```

**UI rule:** render `devProfile.groups` as collapsible sections; filter persona `dimensions` by `dimensionIds`. Do **not** list all 1339 dims in the persona picker. Full catalog grouping is for future “extend profile” flows.

#### Relationship to PersonaEval `data/personas/`

| Pool | Role | Schema |
|------|------|--------|
| `persona/datasets/bench-dev-sample/` | Harbor jobs, smoke, dev sampling | v2 `dimensions` map (82 fields) |
| `application/persona_eval/data/personas/` | Legacy PersonaEval catalog (Nemotron/OASIS/…) | v1 nested domains (`demographics`, `psychology`, …) |

**Target (Phase 3):** PersonaEval persona-group builder reads **`bench-dev-sample` + `dimension_categories.json`** for attribute filters and sampling; `source` field aligns provenance labels with the eval catalog. Unify or migrate PersonaEval YAMLs later — not blocking Harbor sign-off.

#### Generator changes (done)

- `src/personabench/persona_generator.py`: `version` default `1.0`, random `source`, manifest metadata
- `persona/scripts/generate_dev_personas.py`: `--version`, `--sources`, `--manifest-name`
- Consistency rules unchanged (`persona_consistency.py`)

#### Pending (PersonaEval UI — for review)

- [ ] API: expose `dimension_categories.json` + manifest summary (`count`, `source_counts`, `smoke_persona_id`)
- [ ] Persona group builder: hierarchical dimension filters via `devProfile.groups`
- [ ] Optional filter by `source` (provenance chip)
- [ ] Sample N from `bench-dev-sample` in job launch form (§5.2 step 2)

---

## 11. Acceptance criteria

- [ ] Contributor can scaffold **any** of the five types with one script; CI catches missing environment overlay.
- [ ] At least **two** chat tasks share one `chat-suts` entry without duplicating server code.
- [ ] PersonaEval launches a **Harbor job** with **≥4 personas** and shows per-trial status from `jobs/`.
- [ ] UserSim v2 drives at least one chat task; artifacts match `interface/chatbot` contract.
- [ ] Survey `auto` path runs verifier without per-trial `persona-claude-code` container (when Phase 4 lands).
- [ ] `smoke` mode documented as non-sign-off; web smoke labeled W0.
- [ ] `app-api` tasks declare `plane: remote` default; compat mock only for smoke.
- [ ] No new feature depends on `MATRIX_PERSONA_EVAL_RUNTIME` triad as primary control.
- [ ] PersonaEval persona picker uses `dimension_categories.json` groups (not flat 1339-dim list); `bench-dev-sample` is default dev pool.

---

## 12. Explicit non-goals

1. PersonaEval / BenchFlow as second benchmark platform or canonical `jobs/` replacement.
2. Contributor-facing `T0`/`T1`/`T3` labels in `task.toml`.
3. Auto-generating verifiers or visual task designer in UI.
4. Multi-user playground in Phase 1–3 (reserved in UserSim design only).
5. Bulk WebArena / AppWorld adapters in this plan (separate adapter PRs).
6. Moving PersonaEval backend into `apps/` (frontend-only move optional).

---

## 13. Open decisions

| # | Question | Lean |
|---|----------|------|
| 1 | Cohort storage path | `persona/datasets/cohorts/` |
| 2 | `run_store` fate | **Decided:** Harbor `jobs/` for launch + history (§5.5); `run_store` deprecated; UI customization later |
| 3 | RecAI in-process vs sidecar | In-process dev; `chat-suts` for Harbor parity |
| 4 | Frontend location | Keep in `application/persona_eval/frontend` until Phase 3 |
| 5 | `app-api` verifier on remote runs | Require ingest + host verifier before sign-off |

---

## 14. References

- [`user-simulator-chat-design.md`](user-simulator-chat-design.md)
- [`application/tasks/interface/`](application/tasks/interface/)
- [`application/persona_eval/UNIFIED_RUNTIME.md`](application/persona_eval/UNIFIED_RUNTIME.md) (to be updated when runtime triad is deprecated)
- [`docs/architecture.md`](docs/architecture.md)
- [`environment/adapters/README.md`](environment/adapters/README.md) (external benchmarks → Harbor tasks)
- Persona agents table (survey/chat → `persona-claude-code`; web → openhands/browser-use/cocoa; cua → `persona-computer-1`)
- [`persona/datasets/bench-dev-sample/SOURCE_README.md`](persona/datasets/bench-dev-sample/SOURCE_README.md)
- [`persona/schema/dimension_categories.json`](persona/schema/dimension_categories.json)

---

## 15. Summary diagram

```text
                    ┌──────────────────────────────────────┐
                    │  PersonaEval UI / CLI / CI           │
                    │  persona group + task + mode + plane │
                    └───────────────────┬──────────────────┘
                                        │ Harbor Job
                    ┌───────────────────▼──────────────────┐
                    │  Trial × persona                       │
                    │  driver resolved from task.type        │
                    └───────────────────┬──────────────────┘
          ┌─────────────────────────────┼─────────────────────────────┐
          ▼                             ▼                             ▼
   json_survey                    user_sim_chat                  docker_agent
   (survey)                       (chat + chat-suts)            (web/cua/force_docker)
          │                             │                             │
          └─────────────────────────────┴─────────────────────────────┘
                                        ▼
                              jobs/.../artifacts + tests/
```

**Contributor writes tasks. Everyone else runs jobs.**
