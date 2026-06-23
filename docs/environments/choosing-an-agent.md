# Choosing a Persona Agent and Model

Every run specifies the agent, model, persona, and task on the command line.

## Parameters

| Flag | Meaning | Example |
|------|---------|---------|
| `-a` | Persona agent | `persona-claude-code` |
| `-m` | LLM | `anthropic/claude-sonnet-4-6` |
| `-p` | Task scenario | `application/tasks/example-survey_product-feedback` |
| `--ak persona_path` | Persona YAML (**which profile**) | `persona/datasets/bench-dev-2000/persona_0042.yaml` |

## Persona agents

| CLI name | Application | Typical use | Example task |
|----------|-------------|-------------|----------------|
| `persona-claude-code` | survey<br>chat | Forms, surveys, multi-turn chat, API/MCP sidecars | [product-feedback](../../application/tasks/example-survey_product-feedback)<br>[acme-support-api](../../application/tasks/example-chat-api_support_chatbot)<br>[acme-support-mcp](../../application/tasks/example-chat-mcp_support_chatbot) |
| `persona-gemini-cli` | survey<br>chat | Same as `persona-claude-code`; Google Gemini CLI backend | [product-feedback](../../application/tasks/example-survey_product-feedback)<br>[acme-support-api](../../application/tasks/example-chat-api_support_chatbot)<br>[acme-support-mcp](../../application/tasks/example-chat-mcp_support_chatbot) |
| `persona-codex` | survey<br>chat | Same as `persona-claude-code`; OpenAI Codex CLI backend | [product-feedback](../../application/tasks/example-survey_product-feedback)<br>[acme-support-api](../../application/tasks/example-chat-api_support_chatbot)<br>[acme-support-mcp](../../application/tasks/example-chat-mcp_support_chatbot) |
| `persona-openhands-sdk` | web | Python Playwright in the terminal (DOM selectors); fast, CI-friendly | [books-interest-playwright](../../application/tasks/example-web-playwright_books-interest) |
| `persona-browser-use` | web | browser-use agent loop over Chromium | [books-interest-browser-use](../../application/tasks/example-web-browser-use_books-interest) |
| `persona-cocoa` | web | browser + shell + files in one container | [books-interest-cocoa](../../application/tasks/example-web-cocoa_books-interest) |
| `persona-computer-1` | web<br>computer-use | Screenshot CUA; auto-routes to use.computer (macOS/iOS) or Docker Linux | **computer-use:** [macos-notification-preferences](../../application/tasks/example-computer-use-macos_notification-preferences)<br>[ios-notification-preferences](../../application/tasks/example-computer-use-ios_notification-preferences)<br>[linux-notification-preferences](../../application/tasks/example-computer-use-linux_notification-preferences)<br>**web:** [books-interest-linux-cua](../../application/tasks/example-web-cua_books-interest) |

Live-web details: [web-interaction.md](../applications/web-interaction.md).

### Web modes at a glance

| Mode | Agent | How the agent sees the page | Strengths | Trade-offs |
|------|-------|----------------------------|-----------|------------|
| **Playwright** | `persona-openhands-sdk` | Terminal agent **writes & runs Python**; reads the page via Playwright **DOM API** (`locator`, `goto`, …). No built-in screenshot loop. | Cheapest Docker web mode; repeatable | Agent must write working scripts |
| **browser-use** | `persona-browser-use` | Dedicated browser loop: each step the model gets **page structure (DOM)** and picks click/type/scroll tools. Screenshots are **optional**, not every turn. | Purpose-built web agent | Slower than a good hand-written script |
| **Cocoa** | `persona-cocoa` | Same browser as above (**DOM tools first**), plus optional `browser_screenshot`, and **shell + files** in one container. | All-in-one digital agent in Docker | Heavier base image |
| **CUA** | `persona-computer-1` | **Screenshot every turn** of a real remote desktop, then mouse/keyboard — closest to “looking at the screen”. | Highest human fidelity | Slowest; `USE_COMPUTER_API_KEY` + LLM cost |

## Environment variables (host)

Persona agents read API keys from the **host** shell (or job `agents[].env`). Names differ by agent:

| Agent | Required on host | Notes |
|-------|------------------|-------|
| `persona-claude-code` | `ANTHROPIC_API_KEY` | Anthropic models |
| `persona-gemini-cli` | `GEMINI_API_KEY` | Google models, e.g. `google/gemini-2.5-pro` |
| `persona-codex` | `OPENAI_API_KEY` | OpenAI models, e.g. `openai/gpt-4o` |
| `persona-openhands-sdk` | **`LLM_API_KEY`** | Not the provider-native name. Map before run, e.g. `export LLM_API_KEY="$ANTHROPIC_API_KEY"` or `"$GEMINI_API_KEY"` or `"$OPENAI_API_KEY"` (match `-m`). |
| `persona-browser-use` | `ANTHROPIC_API_KEY` or `LLM_API_KEY` | OpenAI models: `OPENAI_API_KEY`. |
| `persona-cocoa` | `ANTHROPIC_API_KEY` or `LLM_API_KEY` | Task image must be AIO Sandbox-based. |
| `persona-computer-1` | `USE_COMPUTER_API_KEY` + `ANTHROPIC_API_KEY` | use.computer (macOS/iOS). Docker Linux CUA needs only `ANTHROPIC_API_KEY`. Install: `uv sync --extra use-computer --extra computer-1`. |

Job YAML can pass keys per agent, e.g. `agents[].env.LLM_API_KEY: ${ANTHROPIC_API_KEY}`.

### Setting API keys

Export in your shell before running (e.g. in `~/.zshrc` or the current terminal):

```bash
export ANTHROPIC_API_KEY=sk-...
export GEMINI_API_KEY=...
export OPENAI_API_KEY=sk-...

# persona-openhands-sdk (pick one to match -m)
export LLM_API_KEY="$ANTHROPIC_API_KEY"
# export LLM_API_KEY="$GEMINI_API_KEY"
# export LLM_API_KEY="$OPENAI_API_KEY"

export USE_COMPUTER_API_KEY=...  # persona-computer-1
```

Variable names per agent: see [`.env.example`](../../.env.example). Optional: [direnv](https://direnv.net/) with a gitignored `.envrc`.

## Examples

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p application/tasks/example-chat-mcp_support_chatbot
```

```bash
uv run harbor run \
  -a persona-browser-use \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p application/tasks/example-web-browser-use_books-interest
```

Batch runs: [configs/jobs/README.md](../../configs/jobs/README.md).

## For task authors

Add **Suggested setup (non-binding)** in `application/.../README.md` (or `persona/tasks/.../README.md`); do not hard-require an agent.

## Related

- [applications/README.md](../applications/README.md)
- [configs/jobs/README.md](../../configs/jobs/README.md)
- [web-interaction.md](../applications/web-interaction.md)
