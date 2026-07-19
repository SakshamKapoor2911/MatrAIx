# Application task structure

A Playground application task is a Harbor task folder under `application/tasks/`.
Copy the closest `example-*` task for your form (survey, chat, web, computer-use)
into `application/tasks/<your-task-name>/`, then edit these parts.

## Folder layout

```text
application/tasks/example-survey_product-feedback/
├── task.toml           # Harbor config (timeouts, metadata, artifacts paths)
├── instruction.md      # What the agent should do (scenario + output format)
├── input/              # Task-owned content (survey, chat, web docs)
│   ├── context.md
│   ├── questionnaire.yaml    # survey (askRationale / askConfidence)
│   ├── self_report_schema.yaml  # chatbot / web / os-app (under input/)
│   └── chatbot.yaml          # chat (under input/)
├── tests/              # Verifier — runs after the agent; scores output / trajectory
│   ├── test.sh
│   └── test_*.py       # optional helpers
├── reporting.json      # Batch reporting policy (contextRules, judge directives)
├── persona_strategy.json  # target cohort + Playground sampling defaults
├── solution/           # optional — reference solution for CI smoke
└── README.md           # notes for your team (smoke commands, suggested agent)
```

**Runtime build contexts** live separately under
`environment/task-environments/application/` — not inside the task folder.
Harbor resolves `[environment].definition` in `task.toml` to a folder there.

Survey tasks reuse `shared-survey-form`; web agent stacks reuse `shared-web-*`
with optional `web-sidecar_<sut>` via `[environment].local_compose` for
task-hosted sites; chat tasks reuse `shared-chat-persona` with optional
`chatbot-api-sidecar_*` / `chatbot-mcp-sidecar_*` the same way (or an external URL in `chatbot.yaml`).
macOS/iOS os-app tasks reuse `shared-os-app-mac-ios` (use.computer stub, no
Docker); Linux desktop computer-use keeps `shared-os-app-linux`. Create a
task-specific environment only when the agent image itself is genuinely new.

Do **not** create `application/tasks/<your-task>/environment/` for surveys.
Harbor treats a task-local `environment/` as the full runtime, which shadows the
shared survey runtime instead of extending it.

## The files

### `task.toml`

Harbor reads this for **timeouts**, **CPU/memory**, **metadata** (`type`, `domain`,
`tags`), and **which paths to collect** after a run:

```toml
artifacts = ["/app/output"]
```

Survey/chat/web Docker tasks usually declare `/app/output`. Computer-use tasks
may use paths under `/tmp/matraix-.../` — follow the nearest
`example-computer-use-*` task.

Live-web tasks also need:

```toml
[environment]
network_mode = "public"

[agent]
network_mode = "public"
```

### `instruction.md`

The **scenario**: what product or surface the agent sees, what to produce, and
where to write it (`/app/output/...`).

Persona traits do **not** go here — they come from `persona_path` at run time.

Agent names, Playground labels, and operator setup hints do **not** belong here
either. Put those in the task `README.md` under **Suggested setup (non-binding)**.

### `input/`

Task-owned materials the agent reads:

- **Survey:** `context.md`, `questionnaire.yaml` (`askRationale` / `askConfidence`)
- **Chat:** `context.md`, `protocol.md`, `chatbot.yaml`, `self_report_schema.yaml`
  (all under `input/`)
- **Web / OS-app:** `context.md` (optional), `self_report_schema.yaml` under
  `input/`; prefer trace/state verification (optional submission schema inline
  in `instruction.md`)

These files are copied or mounted into `/app/input/` by the shared runtime.

### `tests/`

Scripts Harbor runs **after** the agent finishes:

- **`test.sh`** — entry point; often calls pytest and writes `reward` to
  `/logs/verifier/reward.txt`.
- **`test_*.py`** — check submission JSON/schema, and optionally **trajectory**
  fields (logs under `/logs/agent/`, artifacts, conversation transcripts).

Design tests around what you need to **score** and what you want in **reports**
later. Verifier extracts structured facts into `verifier/structured_output.json`;
reporting semantics belong in `reporting.json`.

### `reporting.json`

Each task should define batch reporting policy here (even if minimal):

```json
{
  "schemaVersion": "1.0",
  "contextRules": []
}
```

See [tasks/README.md](tasks/README.md) and the task specs under
[task-spec/](task-spec/).

### `persona_strategy.json`

Target cohort and Playground sampling defaults (mode, `dimensionFilters`
and/or `cohortId`, optional `sampleSize`). Other fields may use defaults.
The checked-in `bench-dev-sample` pool is only ~200 personas — narrow filters
often undershoot it. Prefer generating a local strategy pool first.

Until the production persona dataset ships, these synthetic pools are how we
**validate task design** and the **persona reporting / analysis** the task
needs — not a final population substitute.

```bash
uv run python persona/scripts/generate_dev_personas.py \
  --strategy application/tasks/<your-task-name>/persona_strategy.json
```

Playground auto top-ups `_generated/` when coverage fails; see
[Ensuring pool coverage](task-spec/authoring-bundle.md#ensuring-pool-coverage).

## Conventions

| Path in container | Purpose |
|-------------------|---------|
| `/app/input/` | Task materials (from task `input/` via shared runtime) |
| `/app/output/` | Agent submission (collected to host `jobs/.../artifacts/`) |
| `/logs/agent/` | Agent trajectory / CLI logs |

## Examples — what to copy

| Form | Copy from |
|------|-----------|
| survey | `application/tasks/example-survey_product-feedback/` |
| chat (REST) | `application/tasks/example-chat-api_support_chatbot/` |
| chat (MCP) | `application/tasks/example-chat-mcp_support_chatbot/` |
| chat (recommender / real SUT samples) | `application/tasks/chat_recai/` (also `chat_openbb`, `chat_multi-agent-medical-assistant`) |
| web (Playwright) | `application/tasks/example-web-playwright_quote-choice/` |
| web (browser-use) | `application/tasks/example-web-browser-use_laptop-choice/` |
| web (Cocoa) | `application/tasks/example-web-cocoa_plan-choice/` |
| web (CUA) | `application/tasks/example-web-cua_bookshop-choice/` |
| computer-use | `application/tasks/example-computer-use-macos_calendar-reminder-handoff/` (macOS / iOS / Linux) |

Agent choice depends on the form — [choosing-an-agent.md](choosing-an-agent.md).
Web stack details — [web-interaction.md](web-interaction.md).

## Reference scenarios

| Form | Path | Suggested agent |
|------|------|-----------------|
| survey | `application/tasks/example-survey_product-feedback/` | `persona-claude-code` |
| chat (API) | `application/tasks/example-chat-api_support_chatbot/` | `persona-claude-code` |
| chat (MCP) | `application/tasks/example-chat-mcp_support_chatbot/` | `persona-claude-code` |
| chat (recommender) | `application/tasks/chat_recai/` | `persona-claude-code` |
| chat (OpenBB / HTTP over MCP data) | `application/tasks/chat_openbb/` | `persona-claude-code` |
| chat (medical) | `application/tasks/chat_multi-agent-medical-assistant/` | `persona-claude-code` |
| web (Playwright) | `application/tasks/example-web-playwright_quote-choice/` | `persona-openhands-sdk` |
| web (browser-use) | `application/tasks/example-web-browser-use_laptop-choice/` | `persona-browser-use` |
| web (Cocoa) | `application/tasks/example-web-cocoa_plan-choice/` | `persona-cocoa` |
| web (CUA) | `application/tasks/example-web-cua_bookshop-choice/` | `persona-computer-1` (Docker Linux) |
| computer-use (macOS) | `application/tasks/example-computer-use-macos_calendar-reminder-handoff/` | `persona-computer-1` |
| computer-use (iOS) | `application/tasks/example-computer-use-ios_photo-access-review/` | `persona-computer-1` |
| computer-use (Linux) | `application/tasks/example-computer-use-linux_note-to-csv/` | `persona-computer-1` |

Real application survey tasks (`survey_*`) follow the same layout as the reference
example; only **`example-survey_product-feedback`** is the copy-from reference.
Real application chatbot tasks (`chat_*`) follow the same layout as
`example-chat-*`; name the folder after the SUT and pick
`chatbot-api-sidecar_*` vs `chatbot-mcp-sidecar_*` from the persona-facing
protocol (see [tasks/README.md](tasks/README.md)).

## Playground registration

Tasks appear in the Playground only when indexed. After scaffolding,
add an entry to:

`application/playground/backend/service/playground_task_registry.py`

```python
"<your-task-folder>": PlaygroundTaskEntry(application_type="survey"),  # or chatbot / web / os-app
```

**Web tasks** also need `site_name`, `site_url`, `output_artifact`, and
`submission_profile` (copy fields from the nearest `example-web-*` entry).

**Survey tasks** also need a questionnaire id mapping in
`packages/playground/src/playground/survey_task_content.py`:

```python
SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID = {
    ...
    "<questionnaire_id>": "<your-task-folder>",
}
```

The questionnaire id must match `input/questionnaire.yaml` → `id`.

Restart the Playground backend after registry changes.

## Job recipes

| Config path | Use |
|-------------|-----|
| [`configs/jobs/example-job-recipe/`](../configs/jobs/example-job-recipe/) | Hand-written smoke jobs (`appSim-*`, 1 persona) |
| [`configs/jobs/application-task-job-recipe/`](../configs/jobs/application-task-job-recipe/) | Multi-persona runs from `generate_application_job.py` or Playground |

**Smoke** (checked-in YAML):

```bash
# Harbor hello-world (no API key)
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml

# Application survey (needs ANTHROPIC_API_KEY)
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml

# Web examples (see example-job-recipe/README.md for the full list)
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-web-playwright-local.yaml
```

Full list: [`configs/jobs/README.md`](../configs/jobs/README.md).

**Multi-persona batch:** [QUICKSTART.md §7](QUICKSTART.md#7-batch--sample-many-personas-job).

## Related

- [QUICKSTART.md](QUICKSTART.md) — install through Playground play
- [web-interaction.md](web-interaction.md) — live-web modes
- [choosing-an-agent.md](choosing-an-agent.md) — agents and API keys
- [task-spec/](task-spec/) — shared metric and artifact contracts
