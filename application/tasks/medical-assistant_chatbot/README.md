# Medical Assistant chatbot

Canonical PersonaBench chatbot task for a medical-information assistant exposed through the PersonaEval chat runtime.

This task is task-backed: contributor-facing prompt docs live under `input/`, while runtime connection metadata lives in `input/chatbot.yaml`.

The repository does not currently vendor a startable local medical sidecar for this task. Run it by pointing the task at an already-available upstream endpoint via `CHATBOT_UPSTREAM_MEDICAL` or `MEDICAL_CHATBOT_URL`.
