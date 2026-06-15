# AGENTS.md — MatrAIx

> **Implementation plan:** [`docs/plan.md`](docs/plan.md)  
> **Changelog:** [`CHANGELOG.md`](CHANGELOG.md)

## Project overview

**MatrAIx** is a persona-driven agent simulation platform ("Simulate before reality"). Simulations run through the `harbor` CLI — tasks, trials, jobs, environments, and the results viewer.

Three teams:

| Team | Assets (repo root) | Docs |
|------|-------------------|------|
| Persona | `personas/` | `docs/personas/` |
| Application | `tasks/{survey,chat,web,computer-use}/` | `docs/applications/` |
| Environment | `configs/jobs/`, `src/matraix/`, `src/harbor/` | `docs/environments/` |

**CLI convention:** persona runs use `-a persona-<agent>` (e.g. `persona-claude-code`) with `--ak persona_path=personas/...`. No `matraix-persona` facade; no automatic task→agent mapping (see [`docs/environments/choosing-an-agent.md`](docs/environments/choosing-an-agent.md)).

**Documentation language:** MatrAIx docs and READMEs are **English**.

## Development

```bash
uv sync
uv run harbor --help
uv run pytest          # unit tests
uv run ruff check .
uv run ty check
```

## Repository structure

```
src/matraix/          # MatrAIx core (persona agents, …)
src/harbor/           # agent execution runtime
personas/             # Persona YAML
tasks/                # MatrAIx simulation tasks
configs/jobs/         # Job YAML
packages/rewardkit/   # Verifier toolkit
apps/viewer/          # harbor view
docs/                 # Team Markdown docs
reporting/            # Batch report placeholder
adapters/             # Dataset import reference (not CI parity)
examples/tasks/       # Hello-world examples
```

**Do not add** root `environments/` (conflicts with `src/harbor/environments/`) or `docs/matraix/` (flat `docs/` only).

## Runtime (`src/harbor/`)

The execution runtime provides agents, environments, CLI, metrics, and the viewer. Key paths:

- `src/harbor/agents/` — agent implementations and factory
- `src/harbor/environments/` — docker, daytona, modal, …
- `src/harbor/cli/` — Typer CLI (`harbor run`, `harbor view`, …)
- `packages/rewardkit/` — LLM judge / structured verifier criteria

Runtime API reference: https://harborframework.com/docs

## MatrAIx conventions

- **Tasks:** `task.toml`, `instruction.md`, `environment/`, `tests/`. Application docs: `docs/applications/`.
- **Jobs:** `harbor run -c configs/jobs/<file>.yaml`
- **Persona agents:** `src/matraix/agents/persona/` registered as `-a persona-claude-code`, `persona-computer-1`, `persona-openhands-sdk` with `--ak persona_path=...`
- **Skills:** `skills/create-task`, `skills/rewardkit`; `skills/create-adapter` → import-dataset workflow

## Legal

Apache 2.0 — see `LICENSE` and `NOTICE`. MatrAIx is an independent project; do not imply official Harbor project affiliation.
