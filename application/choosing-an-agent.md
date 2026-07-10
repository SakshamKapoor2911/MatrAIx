# Choosing a Persona Agent and Model

Every run specifies the agent, model, persona, and task on the command line (or
via Playground / `generate_application_job.py`, which pin the same
fields in the job YAML).

## Parameters

| Flag | Meaning | Example |
|------|---------|---------|
| `-a` | Persona agent | `persona-claude-code` |
| `-m` | Persona LLM (simulated user) | `anthropic/claude-sonnet-4-6` |
| `-p` | Task scenario | `application/tasks/example-survey_product-feedback` |
| `--ak persona_path` | Persona YAML (**which profile**) | `persona/datasets/bench-dev-sample/persona_0042.yaml` |
| `--model-name` | Same as `-m`, on `generate_application_job.py` | `openai/gpt-4o-mini` |

Default smoke persona: **`persona_0042`** in `persona/datasets/bench-dev-sample/`.

## Persona model (`-m` / `--model-name`)

The **persona LLM** is the model that plays the simulated user. It is separate
from chat **SUT** backends (`MATRIX_CHATBOT_ENGINE`, sidecar APIs, etc.).

All persona agents — including auto host-native survey/chat — resolve the model
the same way:

1. Harbor job `agents[].model_name` or CLI `-m` / `--model-name` (**wins**)
2. `MATRIX_CHATBOT_PERSONA_MODEL` (chat auto only, when no YAML model)
3. `MATRIX_PERSONA_MODEL` or `MATRIX_HARBOR_PERSONA_MODEL`
4. Default: `anthropic/claude-haiku-4-5`

Web/CUA agents (`persona-browser-use`, `persona-computer-1`, …) and auto agents
(`persona-json-survey`, `persona-user-sim`) all honor the YAML `model_name`.
CLI wrapper agents (`persona-claude-code`, …) pass `-m` through to the same field.

Supported persona models in Playground include Anthropic (`anthropic/claude-*`),
OpenAI (`openai/gpt-4o*`), and DashScope OpenAI-compatible models
(`dashscope/qwen3.6-plus-2026-04-02`, `dashscope/qwen3.7-max`,
`dashscope/deepseek-v4-pro`, …). Set `DASHSCOPE_API_KEY` (and optional
`DASHSCOPE_API_BASE`) when using `dashscope/*` — the same `-m` value applies to
auto survey/chat and Docker web/CUA agents. CLI harness agents
(`persona-claude-code`, `persona-gemini-cli`, `persona-codex`) stay
vendor-locked. Other LiteLLM-compatible ids may work if the matching API key is
set.

## Persona agents

| CLI name | Application | Typical use | Example task |
|----------|-------------|-------------|----------------|
| `persona-json-survey` | survey | **Auto mode (recommended):** one-shot JSON survey on the host; no Docker | [product-feedback](tasks/example-survey_product-feedback) |
| `persona-user-sim` | chat | **Auto mode (recommended):** multi-turn user simulator + task sidecar on the host | [recommender-agent_chat_api](tasks/recommender-agent_chat_api)<br>[acme-support-api](tasks/example-chat-api_support_chatbot) |
| `persona-claude-code` | survey<br>chat | CLI agent in Docker; forms, surveys, multi-turn chat, API/MCP sidecars | [product-feedback](tasks/example-survey_product-feedback)<br>[acme-support-api](tasks/example-chat-api_support_chatbot)<br>[acme-support-mcp](tasks/example-chat-mcp_support_chatbot)<br>[recommender-agent_chat_api](tasks/recommender-agent_chat_api) |
| `persona-gemini-cli` | survey<br>chat | Same as `persona-claude-code`; Google Gemini CLI backend | [product-feedback](tasks/example-survey_product-feedback)<br>[acme-support-api](tasks/example-chat-api_support_chatbot) |
| `persona-codex` | survey<br>chat | Same as `persona-claude-code`; OpenAI Codex CLI backend | [product-feedback](tasks/example-survey_product-feedback)<br>[acme-support-api](tasks/example-chat-api_support_chatbot) |
| `persona-openhands-sdk` | web | Python Playwright in the terminal (DOM selectors); fast, CI-friendly | [quote-choice-playwright](tasks/example-web-playwright_quote-choice) |
| `persona-browser-use` | web | browser-use agent loop over Chromium | [laptop-choice-browser-use](tasks/example-web-browser-use_laptop-choice) |
| `persona-cocoa` | web | browser + shell + files in one container | [plan-choice-cocoa](tasks/example-web-cocoa_plan-choice) |
| `persona-computer-1` | web<br>computer-use | Screenshot CUA; auto-routes to use.computer (macOS/iOS) or Docker Linux | **computer-use:** [macos-calendar-reminder-handoff](tasks/example-computer-use-macos_calendar-reminder-handoff)<br>[ios-photo-access-review](tasks/example-computer-use-ios_photo-access-review)<br>[linux-note-to-csv](tasks/example-computer-use-linux_note-to-csv)<br>**web:** [bookshop-choice-cua](tasks/example-web-cua_bookshop-choice) |

`generate_application_job.py --execution-mode auto` picks `persona-json-survey` or
`persona-user-sim` from the task type. Use `--agent-name` to override, or
`--execution-mode force_docker` for the CLI agents above.

Live-web details: [web-interaction.md](web-interaction.md).

The Playground selects the web agent driver per task in the UI — that
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
| `persona-json-survey` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `DASHSCOPE_API_KEY` | Match `-m` / YAML `model_name`. Auto host-native survey. |
| `persona-user-sim` | Persona: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `DASHSCOPE_API_KEY`; often `OPENAI_API_KEY` for SUT | Persona model via `-m`; chat sidecar engine via `MATRIX_CHATBOT_ENGINE` (default `gpt-4o-mini`). |
| `persona-claude-code` | `ANTHROPIC_API_KEY` | Anthropic models |
| `persona-gemini-cli` | `GEMINI_API_KEY` | Google models, e.g. `google/gemini-2.5-pro` |
| `persona-codex` | `OPENAI_API_KEY` | OpenAI models, e.g. `openai/gpt-4o` |
| `persona-openhands-sdk` | **`LLM_API_KEY`** (or `DASHSCOPE_API_KEY` when `-m` is `dashscope/*`) | Not the provider-native name for Anthropic/OpenAI. Map before run, e.g. `export LLM_API_KEY="$ANTHROPIC_API_KEY"` (match `-m`). DashScope models auto-map `DASHSCOPE_API_KEY` → `LLM_API_KEY`. |
| `persona-browser-use` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, or `LLM_API_KEY` | DashScope: set `DASHSCOPE_API_KEY` (+ optional `DASHSCOPE_API_BASE`). |
| `persona-cocoa` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, or `LLM_API_KEY` | Task image must be AIO Sandbox-based. |
| `persona-computer-1` | `ANTHROPIC_API_KEY` or `DASHSCOPE_API_KEY` | Docker Linux web CUA and linux computer-use. **use.computer** (macOS/iOS) also needs `USE_COMPUTER_API_KEY`. Install extras: `uv sync --extra use-computer --extra computer-1`. |

Chat tasks may also need `OPENAI_API_KEY` and `MATRIX_CHATBOT_*` exports — the
job generator prints them. Optional global persona default:
`export MATRIX_PERSONA_MODEL=anthropic/claude-sonnet-4-6` (overridden when the job
YAML sets `model_name`).

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

Variable names per agent: see the export blocks in [choosing-an-agent.md](choosing-an-agent.md).

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

Auto mode (matches Playground; `persona-json-survey` / `persona-user-sim`):

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --model-name anthropic/claude-sonnet-4-6 \
  --persona-ids 0042
# Run the printed harbor command + exports
```

The generated YAML includes `agents[].model_name`; edit it or pass `--model-name`
on regenerate to swap the persona LLM.

Batch runs: [QUICKSTART.md §7](QUICKSTART.md#7-batch--sample-many-personas-job),
[../configs/jobs/README.md](../configs/jobs/README.md).

## For task authors

Add **Suggested setup (non-binding)** in `application/tasks/.../README.md`; do
not hard-require an agent in `task.toml` or `instruction.md`.

The Playground web agent selector and this doc are for **operators**. The simulated
user prompt in `instruction.md` should never mention which Harbor agent runs the
task.

## Related

- [QUICKSTART.md](QUICKSTART.md)
- [task-guide.md](task-guide.md)
- [web-interaction.md](web-interaction.md)
- [../configs/jobs/README.md](../configs/jobs/README.md)
