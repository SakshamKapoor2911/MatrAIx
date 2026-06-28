# Application Module

This module owns scenarios where personas are used to evaluate products,
workflows, assistants, and research questions.

Current layout:

```text
application/
  persona_eval/ PersonaEval app, API, simulator, and frontend workbench.
  reporting/   Application result summaries.
  scripts/     Application job generation helpers.
  tasks/       Runnable survey, chat, web, and product tasks.
```

Applications should depend on persona inputs by reference. They should not copy
large persona datasets into application folders.

Related runtime and recipe surfaces live outside this module:

- `configs/jobs/application-task-job-recipe/` contains curated multi-persona
  application job fixtures.
- `configs/jobs/example-job-recipe/` contains local smoke recipes for the
  example application tasks.
- `environment/runtime/harbor/` and `environment/agents/personabench/agents/`
  own execution and agent wiring.

## Scenario Handoff Template

Use this format when proposing a new runnable application scenario. The goal is
to make the task concrete enough that the environment/runtime side can execute
it without guessing at product state, tools, or metrics.

```text
Scenario name:
Task type:                # survey / chatbot / web / app / social-sim
Domain / vertical:
Product or system under test:
Task specification:       # what happens in the episode and what must be done
Environment needs:        # surface, tools, initial state, data, credentials
Persona inputs:           # referenced cohort or dimensions, not copied data
User goal and context:    # motivation, prior knowledge, constraints
Metrics:                  # task success, fidelity, friction, safety, etc.
Outputs:                  # trajectory, telemetry, reports, artifacts
```

Example:

```text
Scenario name: Retail order-support refund handling
Task type: chatbot
Domain / vertical: Commerce & Retail / order support
Product or system under test: retail order-support chatbot
Task specification: simulated shoppers request a return or refund over
  multi-turn chat; the bot must handle each request under the return policy.
Environment needs: chat API connector, orders fixture, return policy document,
  and deterministic task start state.
Persona inputs: price sensitivity, age, shopping habits, tech savviness.
User goal and context: ordered earbuds arrived late and the user wants a refund.
Metrics: persona adherence, turns to resolution, frustration, policy compliance.
Outputs: conversation trajectory and per-metric score report.
```

For broader domain inspiration, see
[`docs/research/application-domain-benchmark-catalog.md`](../docs/research/application-domain-benchmark-catalog.md).

## Current Imported Scope

The clean import currently includes:

- `tasks/`: survey, chat, web, and computer-use example tasks
- `scripts/`: application job generation helpers
- `reporting/`: placeholder aggregation surface for application batch reports
- `persona_eval/`: PersonaEval app/API/frontend plus survey, chatbot, and web
  evaluation helpers

Keep new application contributions scoped to application-owned task, script,
reporting, or PersonaEval folders. Do not add repo-root scripts, copy persona
datasets into application folders, or commit generated job outputs.
