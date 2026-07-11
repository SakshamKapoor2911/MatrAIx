# FinAI / OpenBB chatbot

Canonical PersonaBench chatbot task for a financial-research assistant exposed through the Playground chat runtime.

This task is task-backed: contributor-facing prompt docs live under `input/`, while runtime connection metadata lives in `input/chatbot.yaml`.

The repository does not currently vendor a startable local OpenBB sidecar for this task. Run it by pointing the task at an already-available upstream endpoint via `CHATBOT_UPSTREAM_FINANCE` or `FINANCE_CHATBOT_URL`.
