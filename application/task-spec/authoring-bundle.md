# Authoring bundle

Per-type file layouts for tasks under `application/tasks/<task-name>/`.
Part of [README.md](README.md) **Step 2**. Per-type **diagrams** are in each
type README ([survey](survey/README.md), [chatbot](chatbot/README.md),
[web](web/README.md), [os-app](os-app/README.md)).

Each runnable task lives under `application/tasks/<task-name>/` and always
includes `instruction.md`, `task.toml`, `tests/`, and `reporting.json`.
Supplementary files differ by application type:

### Survey

```text
instruction.md                 # short scenario; points to output_schema
reporting.json                 # batch aggregation policy (contextRules)
input/
  context.md                   # product concept (optional)
  questionnaire.yaml           # structured questions
  output_schema.md             # survey_result.json contract
```

### Chatbot

```text
instruction.md                 # conversation goal
reporting.json                 # batch aggregation policy (contextRules)
input/
  context.md                   # application background (optional)
  protocol.md                  # chat API / MCP contract (optional)
  chatbot.yaml                 # runtime connection metadata
  self_report_schema.yaml      # user_feedback.json
```

Platform-managed harness artifacts (`transcript.json`,
`application_result.json`) are documented in
[`chatbot/eval_artifacts.md`](chatbot/eval_artifacts.md), not in per-task files.

### Web / OS-app

```text
instruction.md                 # task goal, steps, inline task-result JSON schema
reporting.json                 # batch aggregation policy (contextRules)
input/
  context.md                   # scenario / product background (optional)
  self_report_schema.yaml      # user_feedback.json (optional)
```

Web and OS/app tasks do **not** use `input/output_schema.md`. The submission
shape (for example `quote_choice.json` or `decision.json`) is written directly
in `instruction.md`, and the verifier enforces it. Persona self-report uses the
same `input/self_report_schema.yaml` convention as chatbot tasks.

### Quick reference

| Concern | survey | chatbot | web / os-app |
|---|---|---|---|
| Scenario | `instruction.md` | `instruction.md` | `instruction.md` |
| Background context | `input/context.md` | `input/context.md` | `input/context.md` (optional) |
| Task result JSON | `input/output_schema.md` | platform-managed | inline in `instruction.md` |
| Persona self-report | — | `input/self_report_schema.yaml` | `input/self_report_schema.yaml` |
| Batch reporting policy | `reporting.json` | `reporting.json` | `reporting.json` |
| Structured questions | `input/questionnaire.yaml` | — | — |
| Transport / runtime | — | `input/protocol.md`, `input/chatbot.yaml` | shared environment |

