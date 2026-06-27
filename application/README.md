# Application Module

This module owns scenarios where personas are used to evaluate products,
workflows, assistants, and research questions.

Current layout:

```text
application/
  tasks/       Runnable survey, chat, web, and product tasks.
  metrics/     Application-side scoring and evaluation logic.
  cohorts/     Persona cohort specifications used by scenarios.
  reporting/   Application result summaries.
```

Applications should depend on persona inputs by reference. They should not copy
large persona datasets into application folders.

## Imported from MatrAIx

The first application import brings in example task definitions and reporting
stubs only:

- `tasks/`: survey, chat, web, and computer-use example tasks
- `scripts/`: application job generation helpers
- `reporting/`: placeholder aggregation surface for application batch reports

Agents, curated job recipes, and runtime wiring are imported in later PRs. Until
then, keep new contributions scoped to task folders and avoid adding repo-root
scripts or generated job outputs.
