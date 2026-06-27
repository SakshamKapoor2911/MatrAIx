# Web / Computer-Use Application Tasks

Web tasks let the simulated user operate an application through a browser or a
computer-use runtime.

## Contract

- Task instruction: define the website, realistic user goal, and submission schema.
- Interaction protocol: browser or computer-use actions, ending with an explicit done action.
- Task-specific environment: a hosted web application sidecar plus a
  browser-capable main container.
- Stop conditions: max steps, explicit done action, verifier timeout, or task failure.
- Artifacts: browser trajectory, final application result JSON, objective
  result, and persona self-report.
- Evaluation contract: schema validation, optional application-state verifier,
  and persona self-report.

## Canonical Task

`application/tasks/example-web-playwright_books-interest`

The bookshop web task is intentionally small and self-hosted so it validates the
task-specific host pattern before introducing heavier web application services.
