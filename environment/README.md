# Environment Module

This module owns execution infrastructure.

Planned layout:

```text
environment/
  runtime/     Job and trial execution code.
  agents/      Persona-conditioned agents and model wrappers.
  jobs/        Job recipe schemas and reusable templates.
  viewer/      Result inspection UI.
  adapters/    Optional external benchmark adapters.
```

Persona agent implementations live here because they are runtime mechanisms.
Persona schemas and datasets live in `persona/`.
