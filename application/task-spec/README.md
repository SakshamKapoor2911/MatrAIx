# Application Task Spec

This directory defines the shared **application task spec** used by survey,
chatbot, web/computer-use, and OS/app tasks. Runnable task folders stay in
`application/tasks/<task-name>/`; this `task-spec/` directory is the
cross-protocol index, authoring standard, and evaluation contract.

> Formerly `application/tasks/interface/`. The runtime **protocol surface** and
> per-type **contracts** (artifact, evaluation, metrics) live in the sections below.

## Common Contract

Each application task defines these parts:

- Task instruction: what the simulated user is trying to accomplish.
- Interaction protocol: survey answers, chat turns, browser/computer-use actions,
  or native OS/app interaction flows.
- Task-specific environment: survey form, chatbot API sidecar, hosted web app, or
  OS/app state and artifacts.
- Stop conditions: max turns, max steps, explicit done action, or task failure.
- Artifacts: trajectory, application result, task outputs, logs, and optional browser traces.
- Evaluation contract: objective verifier when available, plus persona
  self-report after interaction.

## Authoring Bundle

Each runnable task lives under `application/tasks/<task-name>/` and always
includes `instruction.md`, `task.toml`, `tests/`, and `reporting.json`.
Supplementary files differ by application type:

### Survey

```text
instruction.md                 # short scenario; points to output_schema
input/
  context.md                   # product concept (optional)
  questionnaire.yaml           # structured questions
  output_schema.md             # survey_result.json contract
```

### Chatbot

```text
instruction.md                 # conversation goal
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
instruction.md                 # scenario + inline task-result JSON schema
input/
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
| Background context | `input/context.md` | `input/context.md` | usually in `instruction.md` |
| Task result JSON | `input/output_schema.md` | platform-managed | inline in `instruction.md` |
| Persona self-report | — | `input/self_report_schema.yaml` | `input/self_report_schema.yaml` |
| Structured questions | `input/questionnaire.yaml` | — | — |
| Transport / runtime | — | `input/protocol.md`, `input/chatbot.yaml` | shared environment |

Keep transport details and API tables out of `instruction.md` when they belong in
`input/protocol.md` (chatbot). Survey tasks should keep the response contract in
`input/output_schema.md` and reference it from a short `instruction.md`.

## Interface Folders

| Interface | Folder | Canonical task |
|---|---|---|
| Survey | `survey/` | `application/tasks/example-survey_product-feedback` |
| Chatbot | `chatbot/` | `application/tasks/recommender-agent_chat_api` |
| Browser / computer-use | `web/` | `application/tasks/example-web-playwright_quote-choice` |
| OS / app | `os-app/` | `application/tasks/example-computer-use-ios_notification-preferences` |

For browser, computer-use, and native app tasks, use the folders this way:

- `web/` is the web-task contract. It covers browser/computer-use protocol,
  web-specific metrics, and browser-specific persona decision reporting.
- `os-app/` is the native app / cross-app contract. It covers desktop/mobile
  app metrics, side effects, and persona-aware app behavior.

For persona-sensitive chatbot tasks, the `chatbot/` folder defines the matching
conversation outcome and feedback contract. Use these shared contracts before
inventing task-specific reporting keys from scratch.

## Choosing `web` vs `os-app`

Use `web/` when the benchmark target is primarily one website or web product:

- the core task is search, browse, compare, filter, fill, submit, cart, checkout,
  booking, or account management on web pages
- the main observable errors are wrong page navigation, broken form filling,
  search/filter misuse, or live-site brittleness
- success is mainly judged from web-visible state or a site-backed submission

Use `os-app/` when the benchmark target is primarily native app operation or a
workflow that spans apps and local artifacts:

- the core task is settings changes, file transforms, local document edits,
  email/calendar/file-manager workflows, or mobile/desktop app operation
- the main observable errors are wrong edits, destructive side effects, broken
  cross-app handoff, or task completion with the wrong artifact
- success is mainly judged from local app state, exported files, or cross-app
  side effects

If a task starts in a browser but the real benchmark target is a broader
operating workflow, prefer `os-app/`. If the browser is the product under test,
prefer `web/`.

## Shared Core For `web` And `os-app`

`web/` and `os-app/` should remain separate scenario contracts, but they should
reuse one shared core so that verifier outputs and reporting stay comparable.
Across all interactive task families, they should also reuse one shared
subjective feedback channel whenever the task collects post-run self-report.

For a machine-readable companion to this section, see
`shared_core_metric_contract.example.json`.

### Shared Core Contexts

Both `web` and `os-app` should reuse these context types with the same names
and semantics:

1. `task_outcome`
   Required. The benchmark-facing result for the whole task.
2. `goal_component`
   Recommended. One context per major required subgoal or assertion group.
3. `side_effects`
   Recommended. Unexpected edits, destructive changes, duplicates, privacy
   leaks, or other collateral damage.
4. `execution_profile`
   Recommended. Runtime and operating-shape diagnostics.
5. `infeasibility`
   Optional but strongly recommended when some tasks are intentionally blocked,
   unsupported, or impossible.
6. `user_feedback`
   Recommended whenever the task collects post-run self-report.
7. `persona_alignment`
   Recommended when persona alignment is part of the evaluation target.
8. `persona_constraint`
   Recommended when the task has explicit or inferable persona constraints.

Scenario-specific contexts such as `web_interaction`, `web_artifact`,
`decision`, or `decision_process` should layer on top of this shared core, not
replace it.

### Shared Core Facet Keys

These facet keys should stay identical across `web` and `os-app` so that
reporting code can aggregate them without task-family-specific branching.

For `task_outcome`:

- `outcome_status`
- `goal_completion_ratio`
- `goal_completion_bucket`
- `verifier_mode`
- `primary_failure_reason`
- `outcome_explanation`
- `completion_evidence`

For `goal_component`:

- `goal_component_key`
- `goal_component_label`
- `goal_component_status`
- `goal_component_weight`
- `goal_component_required`
- `goal_component_evidence`

For `side_effects`:

- `collateral_damage_present`
- `blocking_side_effect_present`
- `damage_severity`
- `damage_type_primary`
- `unsafe_action_present`
- `side_effect_notes`

For `execution_profile`:

- `task_archetype`
- `used_gui_primary`
- `used_terminal_or_script`
- `apps_touched_count`
- `step_count`
- `wall_clock_seconds`
- `recovery_count`

For `infeasibility`:

- `infeasible_expected`
- `agent_declared_infeasible`
- `infeasibility_reason_match`
- `declared_before_side_effects`
- `infeasibility_notes`

For `user_feedback`:

- `overall_experience_rating`
- `feedback_reason`
- `need_constraint_satisfaction`
- `personal_preference_satisfaction`
- `trust_level`
- `effort_rating`
- `clarity_of_next_step`

For persona-aware tasks:

- `persona_alignment_status`
- `persona_alignment_score`
- `persona_preference_axis_primary`
- `persona_signal_source`
- `persona_alignment_explanation`
- `persona_constraint_key`
- `persona_constraint_type`
- `persona_constraint_priority`
- `persona_constraint_status`
- `persona_constraint_evidence`

### Shared Core Rules

- Keep the shared context names and facet keys exactly as written.
- Do not rename shared fields to fit one task family; add task-specific fields
  behind a `task_` prefix or in scenario-specific contexts instead.
- Keep `user_feedback` as the shared post-run subjective channel across
  interactive tasks. Family-specific process contexts may add richer slices, but
  they should not replace the shared feedback context.
- Keep binary success outcome-based. Do not derive success from action-sequence
  matching.
- Use the same shared enums for common fields whenever possible so batch reports
  can compare `web` and `os-app` runs directly.

## Shared Subjective Channel For Interactive Tasks

When an interactive task asks the persona for post-run subjective feedback, use
the same shared mechanism across `chatbot`, `web`, and `os-app`:

- write the raw artifact to `user_feedback.json`
- define task-owned questions in `input/self_report_schema.yaml`
- map the feedback into a `user_feedback` context in
  `verifier/structured_output.json`

The shared `user_feedback` context is the default reporting home for subjective
signals such as satisfaction, effort, trust, or clarity. Family-specific
contexts can still add narrower slices when that improves analysis:

- chatbot may additionally emphasize conversation-only signals such as whether
  clarification questions were useful or whether the user felt understood
- web may optionally add an `experience` context for web-specific friction or UI
  journey analysis
- os-app may additionally surface persona alignment or archetype-specific
  summaries when local workflow tradeoffs matter

Recommended shared `user_feedback` facets:

- `overall_experience_rating`
- `feedback_reason`
- `need_constraint_satisfaction`
- `personal_preference_satisfaction`
- `trust_level`
- `effort_rating`
- `clarity_of_next_step`

Task families can extend this shared feedback contract with extra `task_*`
fields or family-specific fields when needed, but `user_feedback` should remain
the common subjective reporting entry point.

Across application tasks, prefer `shared-*` environment folders when the runtime
is reusable across multiple tasks. Reserve task-named environment folders for
truly task-specific app hosts or sidecar topologies.

## Stable Runtime Boundary

The persona agent interacts through the protocol surface only. For survey tasks
that surface is the survey instrument and output schema. For chatbot tasks it is
the task controller's chat loop. For web tasks it is the browser/computer-use
runtime. For OS/app tasks it is the exposed desktop/mobile/browser operating
surface plus task-owned artifacts. Internal APIs, databases, or service health
checks are reserved for task setup, reset, and verifier logic.
