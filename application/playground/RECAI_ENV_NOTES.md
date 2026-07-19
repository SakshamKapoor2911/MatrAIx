# RecAI Environment Notes

This file is kept as a compatibility note for the historical Playground RecAI
integration from MatrAIx PR #127.

Clean `main` does not currently vendor the full RecAI / InteRecAgent checkout or
the large model/resource bundle. The clean recommender task in
`application/tasks/chat_recai/` provides the REST contract used
for smoke runs, but it is not the full native RecAI runtime.

## If Native RecAI Is Restored Later

Restore it as a focused runtime PR rather than mixing it into a UI import. That
PR should:

- Place task-owned runtime code under
  `environment/task-environments/application/chatbot-api-sidecar_recai/recommender-api/`.
- Keep large resources out of git and document their Hugging Face or external
  artifact locations.
- Provide a setup script in the task directory if resources must be materialized
  locally.
- Add smoke tests for the task-local API contract and at least one real
  recommendation turn.

The historical native stack used Python 3.9 because `unirec==0.0.1a4` depended
on older Torch wheels. Do not assume the repository root `.venv` is the correct
environment for that runtime.
