# Application task structure

A MatrAIx application task is a Harbor task folder under `application/tasks/`. Copy the closest `example-*` task for your form (survey, chat, web, computer-use) into `application/tasks/<your-task-name>/`, then edit these parts.

## Folder layout

```text
application/tasks/example-survey_product-feedback/
├── task.toml           # Harbor config (timeouts, metadata, artifacts paths)
├── instruction.md      # What the agent should do (scenario + output format)
├── environment/        # Docker image + task input files
│   ├── Dockerfile
│   ├── docker-compose.yaml   # optional — chat/web sidecars
│   └── …                     # files copied into /app/input/
├── tests/              # Verifier — runs after the agent; scores output / trajectory
│   ├── test.sh
│   └── test_*.py       # optional helpers
├── solution/           # optional — reference solution for CI smoke
└── README.md           # notes for your team
```

## The files

### `task.toml`

Harbor reads this for **timeouts**, **CPU/memory**, **metadata** (`type`, `domain`, `tags`), and **which paths to collect** after a run:

```toml
artifacts = ["/app/output"]
```

Survey/chat/web Docker tasks usually declare `/app/output`. Computer-use tasks may use paths under `/tmp/matraix-.../` — follow the nearest `example-computer-use-*` task.

### `instruction.md`

The **scenario**: what product or surface the agent sees, what to produce, and where to write it (`/app/output/...`).

Persona traits do **not** go here — they come from `persona_path` at run time.

### `environment/`

- **`Dockerfile`** — base image, extra dependencies, `COPY` assets into `/app/input/`, create `/app/output/`.
- **Input files** — briefs, mock pages, survey questions, etc. (anything the agent reads but does not edit).
- **`docker-compose.yaml`** — only when the task needs a **sidecar** (mock chatbot API, MCP server, …).

Check whether your scenario needs packages beyond the example Dockerfile (browsers, compose services, …).

### `tests/`

Scripts Harbor runs **after** the agent finishes:

- **`test.sh`** — entry point; often calls pytest and writes `reward` to `/logs/verifier/reward.txt`.
- **`test_*.py`** — check submission JSON/schema, and optionally **trajectory** fields (logs under `/logs/agent/`, artifacts, conversation transcripts).

Design tests around what you need to **score** and what you want in **reports** later.

## Conventions

| Path in container | Purpose |
|-------------------|---------|
| `/app/input/` | Task materials (seeded from `environment/`) |
| `/app/output/` | Agent submission (collected to host `jobs/.../artifacts/`) |
| `/logs/agent/` | Agent trajectory / CLI logs |

## Examples

| Form | Copy from |
|------|-----------|
| survey | `application/tasks/example-survey_product-feedback/` |
| chat (REST) | `application/tasks/example-chat-api_support_chatbot/` |
| chat (MCP) | `application/tasks/example-chat-mcp_support_chatbot/` |
| web | `application/tasks/example-web-playwright_books-interest/` (also `browser-use`, `cocoa`, `cua` — see [web-interaction.md](./web-interaction.md)) |
| computer-use | `application/tasks/example-computer-use-macos_notification-preferences/` (macOS / iOS / Linux) |

Agent choice depends on the form — [choosing-an-agent.md](../environments/choosing-an-agent.md).

## Reference scenarios

| Form | Path | Suggested agent |
|------|------|-----------------|
| survey | `application/tasks/example-survey_product-feedback/` | `persona-claude-code` |
| chat (API) | `application/tasks/example-chat-api_support_chatbot/` | `persona-claude-code` |
| chat (MCP) | `application/tasks/example-chat-mcp_support_chatbot/` | `persona-claude-code` |
| web (Playwright) | `application/tasks/example-web-playwright_books-interest/` | `persona-openhands-sdk` |
| web (browser-use) | `application/tasks/example-web-browser-use_books-interest/` | `persona-browser-use` |
| web (Cocoa) | `application/tasks/example-web-cocoa_books-interest/` | `persona-cocoa` |
| web (CUA) | `application/tasks/example-web-cua_books-interest/` | `persona-computer-1` |
| computer-use (macOS) | `application/tasks/example-computer-use-macos_notification-preferences/` | `persona-computer-1` |
| computer-use (iOS) | `application/tasks/example-computer-use-ios_notification-preferences/` | `persona-computer-1` |
| computer-use (Linux) | `application/tasks/example-computer-use-linux_notification-preferences/` | `persona-computer-1` |

## Job recipes

| Config path | Use |
|-------------|-----|
| [`configs/jobs/example-job-recipe/`](../../configs/jobs/example-job-recipe/) | Hand-written smoke jobs (`appSim-*`, 1 persona) |
| [`configs/jobs/application-task-job-recipe/`](../../configs/jobs/application-task-job-recipe/) | Generated multi-persona application runs (gitignored; see [getting-started §7](./getting-started.md#7-batch--sample-many-personas-job)) |

**Smoke** (no script — checked-in YAML):

```bash
# Harbor hello-world (no API key)
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml

# Application survey (needs ANTHROPIC_API_KEY)
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

Full list: [`configs/jobs/README.md`](../../configs/jobs/README.md).

**Multi-persona batch** (random sample, stratify, run the generated YAML): [getting-started.md §7](./getting-started.md#7-batch--sample-many-personas-job).
