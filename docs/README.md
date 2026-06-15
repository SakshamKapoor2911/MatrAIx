# MatrAIx documentation

This directory (`docs/`) holds **MatrAIx team documentation** (Markdown only).

> **Do not confuse with repo-root assets:**  
> - `docs/applications/` = **Application team docs** (how to author tasks)  
> - `/tasks/` (repo root) = **executable simulation tasks**  
> Likewise: `docs/personas/` is documentation; `/personas/` is YAML data.

## Overview

- [Contributing](./contributing.md)

## Three teams

| Team | Docs | Team PLAN | Repo assets (root) |
|------|------|-----------|-------------------|
| Persona | [personas/](./personas/) | [PLAN.md](./personas/PLAN.md) | `personas/` |
| Application | [applications/](./applications/) | [PLAN.md](./applications/PLAN.md) | `tasks/{survey,chat,web,computer-use}/` |
| Environment | [environments/](./environments/) — incl. [choosing an agent](./environments/choosing-an-agent.md) | [PLAN.md](./environments/PLAN.md) | `configs/jobs/`, `src/matraix/`, `src/harbor/` |

## Run cheat sheet

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/chat/<scenario>
```

```bash
harbor run -c configs/jobs/persona-debug-local.yaml
```

## Future

Public website: `apps/matraix-web/` (content migrated from this directory as MDX).
