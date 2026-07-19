# Examples

This directory contains small runnable Harbor examples that support local smoke
testing and contributor onboarding.

Import policy:

- Keep examples small and directly runnable from this repository.
- Do not commit generated example job outputs.
- Do not import the full MatrAIx example zoo without a specific runtime or
  contributor workflow that needs it.
- Prefer module-local examples under `persona/`, `application/`, or
  `environment/` when the example belongs to one business module.

Current examples:

- `tasks/hello-world/`: minimal Docker task used by
  `configs/jobs/example-job-recipe/harbor-smoke-local.yaml`.
