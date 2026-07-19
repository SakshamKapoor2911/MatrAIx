# Personalized Meal Planning & Nutrition Assistant

PersonaBench application task for an AI nutrition and meal-planning chatbot exposed through a REST chat API. The persona agent acts as a simulated user seeking personalized meal plans, has a multi-turn conversation with the sidecar, and saves the resulting transcript and feedback artifacts.

## Domain

Healthcare & Commerce & Retail — evaluates safety, personalization, dietary accuracy, and adherence support.

## Contract

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Sidecar health check |
| `POST` | `/v1/session` | Create a meal planning session |
| `POST` | `/v1/messages` | Send one user message and receive one assistant reply |
| `GET` | `/v1/conversation?sessionId=...` | Fetch the full transcript |
| `GET` | `/v1/recommendations?sessionId=...` | Fetch meal plan recommendations accumulated across turns |

## Expected Artifacts

The persona agent writes:

- `/app/output/transcript.json`
- optionally `/app/output/user_feedback.json`

The verifier checks artifact shape, multi-turn coverage, session consistency, and nutrition-specific quality signals.

Canonical contributor-facing docs:

- `application/tasks/meal-planning-nutrition_chatbot/instruction.md`
- `application/tasks/meal-planning-nutrition_chatbot/input/context.md`
- `application/tasks/meal-planning-nutrition_chatbot/input/protocol.md`
- `application/tasks/meal-planning-nutrition_chatbot/input/chatbot.yaml`
- `application/tasks/meal-planning-nutrition_chatbot/input/self_report_schema.yaml`

## Smoke run

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/meal-planning-nutrition_chatbot \
  --execution-mode auto \
  --persona-ids 0042

export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export MATRIX_CHATBOT_TASK_PATH="application/tasks/meal-planning-nutrition_chatbot"
uv run harbor run -c configs/jobs/application-task-job-recipe/meal-planning-nutrition-chatbot-auto-n1.yaml
```

See [Application Quickstart](../../QUICKSTART.md) for the UI path.
