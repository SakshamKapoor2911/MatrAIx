# Chatbot Application Tasks

Chatbot tasks let the simulated user interact with an application exposed
through a chat API.

## Contract

- Task instruction: describe the chatbot application and the user's goal context.
- Interaction protocol: multi-turn user and assistant messages through the task controller.
- Task-specific environment: a chatbot API sidecar and any application-specific resources.
- Stop conditions: max turns, persona done signal, terminal chatbot state, or task failure.
- Artifacts: transcript, application result, persona self-report, and evaluation result.
- Evaluation contract: artifact validation, optional objective checks, and persona self-report.

## Canonical Task

`application/tasks/recommender-agent_chat_api`

The recommender task hosts a small REST sidecar that follows the same contract
as heavier chatbot applications: session creation, message exchange,
conversation export, and final recommendation export.
