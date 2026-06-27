# Application Module

This module owns scenarios where personas are used to evaluate products,
workflows, assistants, and research questions.

Current layout:

```text
application/
  persona_eval/ Reusable PersonaEval survey/backend helpers.
  tasks/       Runnable survey, chat, web, and product tasks.
  metrics/     Application-side scoring and evaluation logic.
  cohorts/     Persona cohort specifications used by scenarios.
  reporting/   Application result summaries.
```

Applications should depend on persona inputs by reference. They should not copy
large persona datasets into application folders.

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

## Imported from MatrAIx

The first application import brings in example task definitions and reporting
stubs only:

- `tasks/`: survey, chat, web, and computer-use example tasks
- `scripts/`: application job generation helpers
- `reporting/`: placeholder aggregation surface for application batch reports
- `persona_eval/`: PersonaEval survey types and curated built-in survey
  instruments

Agents, curated job recipes, and runtime wiring are imported in later PRs. Until
then, keep new contributions scoped to task folders and avoid adding repo-root
scripts or generated job outputs.
