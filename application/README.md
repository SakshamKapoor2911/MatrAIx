# Application Module

This module owns scenarios where personas are used to evaluate products,
workflows, assistants, and research questions.

Planned layout:

```text
application/
  tasks/       Runnable survey, chat, web, and product tasks.
  metrics/     Application-side scoring and evaluation logic.
  cohorts/     Persona cohort specifications used by scenarios.
  reporting/   Application result summaries.
```

Applications should depend on persona inputs by reference. They should not copy
large persona datasets into application folders.
