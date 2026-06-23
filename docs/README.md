# MatrAIx documentation

This directory (`docs/`) holds **MatrAIx team documentation** (Markdown only).

> **Do not confuse with repo-root assets:**  
> - `docs/applications/` = **Application team docs** (how to author tasks)  
> - `/application/` (repo root) = **application-oriented simulation tasks**  
> - `/persona/tasks/` = **persona validation tasks** (dimension grounding probes)  
> Likewise: `docs/personas/` is documentation; `/persona/` is YAML data + validation entry.

## Overview

- [Contributing](./contributing.md)

## Three teams

| Team | Docs | Team PLAN | Repo assets (root) |
|------|------|-----------|-------------------|
| Persona | [personas/](./personas/) | [PLAN.md](./personas/PLAN.md) | `persona/` |
| Application | [applications/](./applications/) | [PLAN.md](./applications/PLAN.md) | `application/tasks/{survey,chat,web,computer-use}/` |
| Environment | [environments/](./environments/) — incl. [choosing an agent](./environments/choosing-an-agent.md) | [PLAN.md](./environments/PLAN.md) | `configs/jobs/`, `src/matraix/`, `src/harbor/` |

## Run cheat sheet

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p application/tasks/example-chat-<scenario>
```

```bash
harbor run -c configs/jobs/example-job-recipe/appSim-example-debug-local.yaml
```

## Future

Public website: `apps/matraix-web/` (content migrated from this directory as MDX).
