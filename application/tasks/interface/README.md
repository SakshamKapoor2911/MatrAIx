# Application Task Interface

This directory defines the shared application task interface used by survey,
chatbot, and web/computer-use tasks. Runnable task folders stay in
`application/tasks/<task-name>/`; this interface directory is the
cross-protocol index and contract.

## Common Contract

Each application task defines these parts:

- Task instruction: what the simulated user is trying to accomplish.
- Interaction protocol: survey answers, chat turns, or browser/computer-use actions.
- Task-specific environment: survey form, chatbot API sidecar, or hosted web app.
- Stop conditions: max turns, max steps, explicit done action, or task failure.
- Artifacts: trajectory, application result, task outputs, logs, and optional browser traces.
- Evaluation contract: objective verifier when available, plus persona
  self-report after interaction.

## Protocol Folders

| Protocol | Folder | Canonical task |
|---|---|---|
| Survey | `survey/` | `application/tasks/persona-survey` |
| Chatbot | `chatbot/` | `application/tasks/recommender-agent_chat_api` |
| Web / computer-use | `web/` | `application/tasks/example-web-playwright_books-interest` |

## Stable Runtime Boundary

The persona agent interacts through the protocol surface only. For survey tasks
that surface is the survey instrument and output schema. For chatbot tasks it is
the task controller's chat loop. For web tasks it is the browser/computer-use
runtime. Internal APIs, databases, or service health checks are reserved for
task setup, reset, and verifier logic.
