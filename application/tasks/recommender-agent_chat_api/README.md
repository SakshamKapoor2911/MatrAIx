# Recommender Agent Chat API

PersonaBench application task for a recommender agent exposed through a REST
chat API. The persona agent acts as a simulated user, has a multi-turn
conversation with the sidecar, and saves the resulting transcript and
recommendation artifacts.

This is the clean-task import of the MatrAIx recommender chat task. The full
historical recommendation evaluation app and generated catalog/persona fixtures
remain outside `main`; this task includes a small local sidecar that implements
the same HTTP contract for smoke runs.

## Contract

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Sidecar health check |
| `POST` | `/v1/session` | Create a recommendation session |
| `POST` | `/v1/messages` | Send one user message and receive one assistant reply |
| `GET` | `/v1/conversation?sessionId=...` | Fetch the full transcript |
| `GET` | `/v1/recommendations?sessionId=...` | Fetch recommended item ids accumulated across turns |

## Expected Artifacts

The persona agent writes:

- `/app/output/transcript.json`
- `/app/output/recommendation_result.json`
- optionally `/app/output/user_feedback.json`

The verifier checks artifact shape, multi-turn coverage, session consistency,
and recommendation grounding.

## Suggested Setup

| Field | Value |
|---|---|
| Agent | `persona-claude-code` |
| Environment | `docker` |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/recommender-agent_chat_api
```

The task-local sidecar is intentionally lightweight. A production RecAI or
catalog-backed recommender can replace `environment/recommender-api/` later as a
separate application tooling PR.
