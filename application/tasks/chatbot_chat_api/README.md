# Chatbot Application API

MatrAIx application task for a chatbot exposed through a REST chat API. The
task environment runs a deterministic controller that asks the persona model for
the next natural user turn, sends that turn to the `chatbot-api` sidecar, tracks
termination, and asks the persona model for a post-interaction self-report.

## Contract

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Sidecar health check and available applications |
| `POST` | `/v1/session` | Create an application chat session |
| `POST` | `/v1/messages` | Send one user message and receive one assistant reply |
| `GET` | `/v1/conversation?sessionId=...&applicationId=...` | Fetch the full transcript |
| `GET` | `/v1/application-result?sessionId=...&applicationId=...` | Fetch grounded application items accumulated across turns |

## Expected Artifacts

The task controller writes:

- `/app/output/transcript.json`
- `/app/output/application_result.json`
- `/app/output/persona_self_report.json`
- `/app/output/evaluation_result.json`
- `/app/output/user_feedback.json`
- `/app/output/run_metadata.json`

The verifier checks artifact shape, multi-turn coverage, grounding, and the
persona self-report schema. The frontend continues to read `user_feedback.json`
as the compatibility questionnaire artifact.

## Local Smoke

After the Harbor runtime is available on the branch:

```bash
export OPENAI_API_KEY=...
uv run harbor run \
  -a persona-claude-code \
  -m "${MATRIX_HARBOR_PERSONA_MODEL:-anthropic/claude-haiku-4-5}" \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p application/tasks/chatbot_chat_api
```

The first sidecar build can be slow because application adapters may install or
warm their own resources.
