# Chatbot Task Generator

Generate verified chatbot tasks from a single CSV row. Designed for the 350-task
scaling effort.

## How it works

1. **Fill in a row** in `chatbot_domains.csv` (or your own CSV)
2. **Run the generator** -- it creates a complete `application/tasks/<name>/` directory
3. **Verify** -- run the task's verifier
4. **Ship** -- the generated task is fully compatible with the task-spec baseline

No per-task server.py, Dockerfile, or Docker Compose changes needed.
All system-prompt-simulated chatbots use the shared persona runtime
(`shared-chat-persona/`) and a per-task sidecar compose profile
(`local_compose`).

## Quickstart

```bash
# Generate all tasks from the demo CSV
uv run python application/scripts/chatbot_task_generator/generate.py \
  --csv application/scripts/chatbot_task_generator/chatbot_domains.csv

# Generate a single task
uv run python application/scripts/chatbot_task_generator/generate.py \
  --csv application/scripts/chatbot_task_generator/chatbot_domains.csv \
  --task-name education-ai-tutoring_chatbot

# Preview without writing
uv run python application/scripts/chatbot_task_generator/generate.py \
  --csv application/scripts/chatbot_task_generator/chatbot_domains.csv \
  --dry-run
```

## CSV schema

| Column | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Directory name (e.g., `education-ai-tutoring_chatbot`) |
| `domain` | Yes | Domain category (e.g., `education`, `legal`, `telecom`) |
| `difficulty` | No | `easy`, `medium`, or `hard` (default: `medium`) |
| `tags` | No | Comma-separated tags (default: `"generated"`) |
| `full_name` | No | Fully qualified task name (auto-generated if blank) |
| `application_id` | No | Sidecar app ID (auto-generated if blank) |
| `application_context` | No | Sidecar app context (auto-generated if blank) |
| `task_title` | No | Display title (auto-generated if blank) |
| `summarized_goal` | Yes | Brief persona-facing goal |
| `persona_background_header` | No | Context section header (auto-generated if blank) |
| `persona_background` | Yes | Full persona scenario description |
| `task_goal_label` | Yes | Goal text for the verifier's structured output |
| `greeting` | Yes | Chatbot's first message |
| `fallback` | Yes | Chatbot's response when no rules match |
| `bot_name` | No | Display name for the chatbot assistant |
| `rules` | No | Newline-separated JSON objects (one per line): `{"pattern": "...", "response": "...", "priority": 0}`. Priority defaults to 0 if omitted. Injected into `knowledge_base.json`. |

## What gets generated

```
application/tasks/<name>/
├── task.toml                # Metadata + environment definition
├── instruction.md           # Persona-facing prompt
├── reporting.json           # Aggregation/reporting policy
├── input/
│   ├── chatbot.yaml         # Sidecar connection config
│   ├── context.md           # Domain background for the persona
│   ├── protocol.md          # REST API contract
│   ├── self_report_schema.yaml  # Persona feedback schema
│   └── knowledge_base.json  # Domain-specific rules + responses
├── solution/solve.sh        # Reference solution
└── tests/
    ├── test.sh              # Entry-point script
    ├── test_state.py        # Verifier (schema validation + structured output)
    └── verifier_env.sh      # Path resolution helper
```

## Architecture

All generated tasks share one persona runtime environment and reference a
per-task sidecar compose profile:

```
environment/task-environments/application/shared-chat-persona/
└── Dockerfile               # ubuntu:24.04 + Claude Code

environment/task-environments/application/chatbot-api-sidecar_<name>/
└── ...                       # Per-task sidecar (referenced via local_compose)
```

The sidecar is **rule-based and domain-agnostic**. It reads `knowledge_base.json`
from the task's `input/` directory at runtime and uses the patterns there to
respond. No code changes needed between domains.

## Adding a new chatbot domain

1. Add a row to the CSV
2. Optionally add rules to `knowledge_base.json` if you want the chatbot to have
   specific responses (the empty `rules: []` array means only greeting + fallback
   are used)
3. Run the generator
4. Verify: `uv run pytest application/tasks/<name>/tests/test_state.py -q`

## Demo domains included

The `chatbot_domains.csv` includes 6 approved chatbot proposals:

- **Education** -- AI Tutoring (concept-mastery adaptation)
- **Legal** -- Tenant Rights (jurisdiction-aware legal info)
- **Travel** -- Trip Change/Cancellation (bundled itinerary management)
- **Real Estate** -- Rental Eligibility (applicant pre-screening)
- **Telecom** -- Bill Dispute & Plan Change (billing + proration)
- **Insurance** -- Claim Filing (coverage estimation + evidence guidance)
