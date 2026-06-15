# MatrAIx job configs

Harbor Job YAML templates for `harbor run -c configs/jobs/<file>.yaml`.

## How this differs from code paths

| Path | Contents |
|------|----------|
| **`configs/jobs/`** (this directory) | Orchestration: agents, personas, tasks, concurrency, docker/daytona |
| `src/harbor/environments/` | Python environment provider implementations |
| `tasks/*/environment/` | Per-task container definitions |

## Files

| File | Purpose |
|------|---------|
| `persona-debug-local.yaml` | Quick local run: survey + chat with `persona-claude-code` |
| `persona-browser-use-local.yaml` | Live web via `persona-browser-use` |
| `persona-cocoa-local.yaml` | Live web via `persona-cocoa` (AIO Sandbox image) |
| `persona-cua-local.yaml` | Live web / desktop via `persona-computer-1` + `use-computer` |

Planned (Phase 3): `persona-sweep-daytona.yaml`

## Environment variables

- `ANTHROPIC_API_KEY` — Claude-family persona agents
- `LLM_API_KEY` — `persona-openhands-sdk` (Playwright web)
- `USE_COMPUTER_API_KEY` — `persona-computer-1` with `-e use-computer`
- `DAYTONA_API_KEY` — when `environment.type: daytona`

Set these in your shell (see [`.env.example`](../../.env.example) and [choosing-an-agent.md](../../docs/environments/choosing-an-agent.md)).

## Run

```bash
uv run harbor run -c configs/jobs/persona-debug-local.yaml
```

Computer-use scenarios need `-e use-computer` — see `persona-cua-local.yaml` or `tasks/computer-use/notification-preferences/`.
