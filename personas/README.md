# Personas

YAML persona definitions for `persona-*` Harbor agents.

## Layout

```
personas/
├── examples/          # Profile YAML (which persona to simulate)
└── templates/       # Jinja2 templates (how to format persona + task)
```

## Two knobs

| Argument | Required | Meaning |
|----------|----------|---------|
| `persona_path` | **Yes** | **Which profile** — e.g. `personas/examples/persona_0042.yaml` |
| `persona_template_path` | No | **Which template** — override default `.md.j2`; defaults below |

Task scenario text comes from the Harbor task `instruction.md` (not from persona files).

**Schema v0** — flat `display_name` / `summary` / `system_prompt` (legacy minimal profiles).

**Schema v1** — nested domains (`demographics`, `psychology`, …). See `personas/examples/persona_0042.yaml`. No `system_prompt`; who the person is lives in domains, what they do lives in the task.

## Default templates

| Agent | Template | v1 behavior |
|-------|----------|-------------|
| `persona-claude-code` | `persona_system.md.j2` | Renders ## Demographics, ## Psychology, … |
| `persona-openhands-sdk`, `persona-computer-1` | `persona_instruction.md.j2` | Domains + task instruction |

Shared macros: `personas/templates/persona_macros.md.j2`.

## Usage

```bash
harbor run \
  -a persona-claude-code \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/chat/<scenario>
```

Optional custom template:

```bash
harbor run \
  -a persona-openhands-sdk \
  --ak persona_path=personas/examples/persona_0042.yaml \
  --ak persona_template_path=personas/templates/my_format.md.j2 \
  -p tasks/web/<scenario>
```

Schema reference: `docs/personas/`.
