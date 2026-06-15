# Choosing a Persona Agent and Model

Every run specifies the agent, model, persona, and task on the command line.

## Parameters

| Flag | Meaning | Example |
|------|---------|---------|
| `-a` | Persona agent | `persona-claude-code` |
| `-m` | LLM | `anthropic/claude-sonnet-4-20250514` |
| `-p` | Task scenario | `tasks/survey/product-feedback` |
| `--ak persona_path` | Persona YAML (**which profile**) | `personas/examples/persona_0042.yaml` |
| `--ak persona_template_path` | Jinja template override (**optional**) | `personas/templates/persona_instruction.md.j2` |

## Tier 1 persona agents

| CLI name | Typical use |
|----------|-------------|
| `persona-claude-code` | survey / chat / lightweight API |
| `persona-computer-1` | desktop computer-use; web (CUA) |
| `persona-openhands-sdk` | web (Playwright scripts) |
| `persona-browser-use` | web (browser-use agent loop) |
| `persona-cocoa` | web (CocoaAgent + AIO Sandbox) |

Live-web modes: [web-interaction.md](../applications/web-interaction.md).

## Environment variables (host)

Persona agents read API keys from the **host** shell (or job `agents[].env`). Names differ by agent:

| Agent | Required on host | Notes |
|-------|------------------|-------|
| `persona-claude-code` | `ANTHROPIC_API_KEY` | Anthropic models |
| `persona-openhands-sdk` | **`LLM_API_KEY`** | Not `ANTHROPIC_API_KEY`. With Anthropic, `export LLM_API_KEY="$ANTHROPIC_API_KEY"`. Optional: `LLM_BASE_URL` for proxies. |
| `persona-browser-use` | `ANTHROPIC_API_KEY` or `LLM_API_KEY` | OpenAI models: `OPENAI_API_KEY`. Optional: `LLM_BASE_URL`. |
| `persona-cocoa` | `ANTHROPIC_API_KEY` or `LLM_API_KEY` | Task image must be AIO Sandbox-based. Job: `configs/jobs/persona-cocoa-local.yaml`. |
| `persona-computer-1` | `USE_COMPUTER_API_KEY` | Plus `-e use-computer` |

Job YAML can pass keys per agent, e.g. `agents[].env.LLM_API_KEY: ${ANTHROPIC_API_KEY}`.

### Setting API keys

Export in your shell before running (e.g. in `~/.zshrc` or the current terminal):

```bash
export ANTHROPIC_API_KEY=sk-...
export LLM_API_KEY=...           # persona-openhands-sdk
export USE_COMPUTER_API_KEY=...  # persona-computer-1
```

Variable names per agent: see [`.env.example`](../../.env.example). Optional: [direnv](https://direnv.net/) with a gitignored `.envrc`.

## Examples

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/chat/acme-support-mcp
```

```bash
uv run harbor run \
  -a persona-browser-use \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/web/books-interest-browser-use
```

Batch runs (several tasks, one YAML): [configs/jobs/README.md](../../configs/jobs/README.md).

## For task authors

Add **Suggested setup (non-binding)** in `tasks/.../README.md`; do not hard-require an agent.

## Related

- [applications/README.md](../applications/README.md)
- [configs/jobs/README.md](../../configs/jobs/README.md)
