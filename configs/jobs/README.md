# MatrAIx job configs

Harbor Job YAML under `configs/jobs/`. Run with `harbor run -c configs/jobs/<subdir>/<file>.yaml`.

## Layout

| Directory | Purpose |
|-----------|---------|
| [`example-job-recipe/`](example-job-recipe/) | Hand-written **smoke / demo** jobs (checked in; `appSim-*`, `harbor-smoke-local`) |
| [`persona-task-grounding-job-recipe/`](persona-task-grounding-job-recipe/) | **Generated** persona bench jobs (`persona/scripts/generate_persona_job.py`) — **gitignored** |
| [`application-task-job-recipe/`](application-task-job-recipe/) | **Generated** application multi-persona jobs — **gitignored**; see [getting-started.md](../../docs/applications/getting-started.md#7-batch--sample-many-personas-job) |

## Example smoke jobs

| File | Purpose |
|------|---------|
| `example-job-recipe/appSim-example-debug-local.yaml` | Quick local run: survey + chat |
| `example-job-recipe/harbor-smoke-local.yaml` | Harbor hello-world smoke (no API key) |
| `example-job-recipe/appSim-example-survey-local.yaml` | Survey task smoke |
| `example-job-recipe/appSim-example-chat-local.yaml` | Chat task smoke |
| `example-job-recipe/appSim-example-web-playwright-local.yaml` | Web via `persona-openhands-sdk` |
| `example-job-recipe/appSim-example-web-browser-use-local.yaml` | Web via `persona-browser-use` |
| `example-job-recipe/appSim-example-web-cocoa-local.yaml` | Web via `persona-cocoa` |
| `example-job-recipe/appSim-example-web-linux-cua-local.yaml` | Docker Linux web CUA |
| `example-job-recipe/appSim-example-computer-use-linux-local.yaml` | Linux desktop notifications |
| `example-job-recipe/appSim-example-computer-use-macos-local.yaml` | macOS desktop |
| `example-job-recipe/appSim-example-computer-use-ios-local.yaml` | iOS Simulator |

## Persona grounding recipes

Generated locally via `persona/scripts/generate_persona_job.py` → `configs/jobs/persona-task-grounding-job-recipe/` (gitignored). See [`persona/README.md`](../../persona/README.md).

## Environment variables

- `ANTHROPIC_API_KEY` — Claude-family persona agents
- `LLM_API_KEY` — `persona-openhands-sdk` (Playwright web)
- `USE_COMPUTER_API_KEY` — `persona-computer-1` with `-e use-computer` (macOS / iOS)
- Docker Linux CUA needs `ANTHROPIC_API_KEY` + `uv sync --extra computer-1`
- `DAYTONA_API_KEY` — when `environment.type: daytona`

See [`.env.example`](../../.env.example) and [choosing-an-agent.md](../../docs/environments/choosing-an-agent.md).

## Run

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-debug-local.yaml
```

Computer-use: `persona-computer-1` auto-routes — see `example-job-recipe/appSim-example-computer-use-*` and `example-job-recipe/appSim-example-web-linux-cua-local.yaml`.
