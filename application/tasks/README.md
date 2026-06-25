# Application tasks

Harbor tasks for **application product research**. Owned by the **Application team**.

The shared protocol index lives in
[`application_interface/`](application_interface/). It groups the current task
family into survey, chatbot, and web/computer-use application protocols without
moving existing Harbor task paths.

## Naming

- Task directories live under `application/tasks/<task-name>/`.
- Use an interaction-specific prefix when it helps discovery, such as
  `chatbot_`, `survey_`, or `web-`.

## New Task

Create a task directory with a Harbor-compatible `task.toml`, `instruction.md`,
`environment/`, and `tests/`. Keep task-specific prompts, sidecars, and verifier
logic in the task directory so the PersonaEval backend can load the task through
the shared task interface.

## Metadata

| Field | Meaning |
|-------|---------|
| **type** | Interaction form (`survey`, `chat`, `web`, `desktop`, `mobile`, …) |
| **domain** | Vertical: `software` · `finance` · `healthcare` · `commerce-retail` |
| **tags** | Task-specific labels for filtering and documentation |

## Current application protocols

| Protocol | Canonical runnable task |
| --- | --- |
| Survey | `survey_form` |
| Chatbot | `chatbot_chat_api` |
| Web / computer-use | `web-ecommerce-platform_product-discovery` |

The PersonaEval backend discovers runnable task types through
`applications/persona_eval/backend/service/task_catalog.py`.
