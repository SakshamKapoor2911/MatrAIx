# Recommender agent chat API

MatrAIx application task for a recommender agent exposed through a REST chat API.
The Harbor persona agent acts as the simulated user. The application sidecar
(`rec-agent-api`) runs the existing RecBot / RecAI recommender and exposes a
small synchronous API for multi-turn recommendation conversations.

## Contract

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Sidecar health check |
| `POST` | `/v1/session` | Create a recommendation session |
| `POST` | `/v1/messages` | Send one user message and receive one assistant reply |
| `GET` | `/v1/conversation?sessionId=...` | Fetch the full transcript |
| `GET` | `/v1/recommendations?sessionId=...` | Fetch recommended item ids accumulated across turns |

## Expected artifacts

The persona agent writes:

- `/app/output/transcript.json`
- `/app/output/recommendation_result.json`
- optionally `/app/output/user_feedback.json`

The verifier checks artifact shape, multi-turn coverage, and recommendation
grounding.

## Local smoke

After the Harbor runtime is installed:

```bash
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
harbor run \
  -a persona-claude-code \
  -m "${MATRIX_HARBOR_PERSONA_MODEL:-anthropic/claude-haiku-4-5}" \
  --ak persona_path=/path/to/persona.yaml \
  -p application/tasks/recommender-agent_chat_api
```

The first sidecar build installs the real RecAI runtime and downloads the
ready-to-run resource bundle, so it can be slow.
