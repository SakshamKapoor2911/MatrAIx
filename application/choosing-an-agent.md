# Choosing a Persona Agent and Model

Every run specifies the agent, model, persona, and task on the command line (or
via PersonaEval Cockpit / `generate_application_job.py`, which pin the same
fields in the job YAML).

## Parameters

| Flag | Meaning | Example |
|------|---------|---------|
| `-a` | Persona agent | `persona-claude-code` |
| `-m` | LLM | `anthropic/claude-sonnet-4-6` |
| `-p` | Task scenario | `application/tasks/example-survey_product-feedback` |
| `--ak persona_path` | Persona YAML (**which profile**) | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

Default smoke persona: **`persona_0042`** in `persona/datasets/bench-dev-sample/`.

## Persona agents

| CLI name | Application | Typical use | Example task |
|----------|-------------|-------------|----------------|
| `persona-claude-code` | survey<br>chat | Forms, surveys, multi-turn chat, API/MCP sidecars | [product-feedback](tasks/example-survey_product-feedback)<br>[acme-support-api](tasks/example-chat-api_support_chatbot)<br>[acme-support-mcp](tasks/example-chat-mcp_support_chatbot)<br>[recommender-agent_chat_api](tasks/recommender-agent_chat_api) |
| `persona-gemini-cli` | survey<br>chat | Same as `persona-claude-code`; Google Gemini CLI backend | [product-feedback](tasks/example-survey_product-feedback)<br>[acme-support-api](tasks/example-chat-api_support_chatbot) |
| `persona-codex` | survey<br>chat | Same as `persona-claude-code`; OpenAI Codex CLI backend | [product-feedback](tasks/example-survey_product-feedback)<br>[acme-support-api](tasks/example-chat-api_support_chatbot) |
| `persona-openhands-sdk` | web | Python Playwright in the terminal (DOM selectors); fast, CI-friendly | [quote-choice-playwright](tasks/example-web-playwright_quote-choice) |
| `persona-browser-use` | web | browser-use agent loop over Chromium | [laptop-choice-browser-use](tasks/example-web-browser-use_laptop-choice) |
| `persona-cocoa` | web | browser + shell + files in one container | [plan-choice-cocoa](tasks/example-web-cocoa_plan-choice) |
| `persona-computer-1` | web<br>computer-use | Screenshot CUA; auto-routes to use.computer (macOS/iOS) or Docker Linux | **computer-use:** [macos-notification-preferences](tasks/example-computer-use-macos_notification-preferences)<br>[ios-notification-preferences](tasks/example-computer-use-ios_notification-preferences)<br>[linux-notification-preferences](tasks/example-computer-use-linux_notification-preferences)<br>**web:** [bookshop-choice-cua](tasks/example-web-cua_bookshop-choice) |

Live-web details: [web-interaction.md](web-interaction.md).

The PersonaEval Cockpit selects the web agent driver per task in the UI — that
metadata is for operators, not for `instruction.md`.

### Web modes at a glance

| Mode | Agent | How the agent sees the page | Strengths | Trade-offs |
|------|-------|----------------------------|-----------|------------|
| **Playwright** | `persona-openhands-sdk` | Terminal agent **writes & runs Python**; reads the page via Playwright **DOM API** (`locator`, `goto`, …). No built-in screenshot loop. | Cheapest Docker web mode; repeatable | Agent must write working scripts |
| **browser-use** | `persona-browser-use` | Dedicated browser loop: each step the model gets **page structure (DOM)** and picks click/type/scroll tools. Screenshots are **optional**, not every turn. | Purpose-built web agent | Slower than a good hand-written script |
| **Cocoa** | `persona-cocoa` | Same browser as above (**DOM tools first**), plus optional `browser_screenshot`, and **shell + files** in one container. | All-in-one digital agent in Docker | Heavier base image |
| **CUA** | `persona-computer-1` | **Screenshot every turn** of a real remote desktop, then mouse/keyboard — closest to “looking at the screen”. | Highest human fidelity | Slowest; higher LLM cost |

## Environment variables (host)

Persona agents read API keys from the **host** shell (or job `agents[].env`). Names
differ by agent:

| Agent | Required on host | Notes |
|-------|------------------|-------|
| `persona-claude-code` | `ANTHROPIC_API_KEY` | Anthropic models |
| `persona-gemini-cli` | `GEMINI_API_KEY` | Google models, e.g. `google/gemini-2.5-pro` |
| `persona-codex` | `OPENAI_API_KEY` | OpenAI models, e.g. `openai/gpt-4o` |
| `persona-openhands-sdk` | **`LLM_API_KEY`** | Not the provider-native name. Map before run, e.g. `export LLM_API_KEY="$ANTHROPIC_API_KEY"` (match `-m`). |
| `persona-browser-use` | `ANTHROPIC_API_KEY` or `LLM_API_KEY` | OpenAI models: `OPENAI_API_KEY`. |
| `persona-cocoa` | `ANTHROPIC_API_KEY` or `LLM_API_KEY` | Task image must be AIO Sandbox-based. |
| `persona-computer-1` | `ANTHROPIC_API_KEY` | Docker Linux web CUA and linux computer-use. **use.computer** (macOS/iOS) also needs `USE_COMPUTER_API_KEY`. Install extras: `uv sync --extra use-computer --extra computer-1`. |

Chat tasks may also need `OPENAI_API_KEY` and `MATRIX_CHATBOT_*` exports — the
job generator prints them.

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

export USE_COMPUTER_API_KEY=...  # persona-computer-1 on use.computer (macOS/iOS)
```

Variable names per agent: see [`.env.example`](../.env.example).

## Examples

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-chat-mcp_support_chatbot
```

```bash
uv run harbor run \
  -a persona-browser-use \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-web-browser-use_laptop-choice
```

Auto mode (matches PersonaEval Cockpit):

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --persona-ids 0042
# Run the printed harbor command + exports
```

Batch runs: [QUICKSTART.md §7](QUICKSTART.md#7-batch--sample-many-personas-job),
[../configs/jobs/README.md](../configs/jobs/README.md).

## For task authors

Add **Suggested setup (non-binding)** in `application/tasks/.../README.md`; do
not hard-require an agent in `task.toml` or `instruction.md`.

The Cockpit web agent selector and this doc are for **operators**. The simulated
user prompt in `instruction.md` should never mention which Harbor agent runs the
task.

## Related

- [QUICKSTART.md](QUICKSTART.md)
- [task-guide.md](task-guide.md)
- [web-interaction.md](web-interaction.md)
- [../configs/jobs/README.md](../configs/jobs/README.md)
