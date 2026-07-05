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
- optionally `/app/output/user_feedback.json`

The verifier checks artifact shape, multi-turn coverage, session consistency,
and conversation quality signals.

Canonical contributor-facing docs:

- `application/tasks/recommender-agent_chat_api/instruction.md`
- `application/tasks/recommender-agent_chat_api/input/context.md`
- `application/tasks/recommender-agent_chat_api/input/protocol.md`
- `application/tasks/recommender-agent_chat_api/input/chatbot.yaml`
- `application/tasks/recommender-agent_chat_api/input/self_report_schema.yaml`

## Smoke run

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/recommender-agent_chat_api \
  --execution-mode auto \
  --persona-ids 0042

export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export MATRIX_CHATBOT_TASK_PATH="application/tasks/recommender-agent_chat_api"
uv run harbor run -c configs/jobs/application-task-job-recipe/recommender-agent-chat-api-auto-n1.yaml
```

See [Application Quickstart](../../QUICKSTART.md) for the UI path.

## Native RecAI stack (full PersonaEval preflight)

The lightweight `server.py` sidecar is enough for Harbor smoke runs. PersonaEval's
**Catalog**, **Recommendation engine**, and **RecAI resources** checks need the
real Microsoft InteRecAgent checkout plus the `all_resources` bundles.

From the recommender API root:

```bash
cd environment/task-environments/application/shared-chat-api-recommender/recommender-api
pip install gdown pandas pyarrow   # one-time
./scripts/setup_recai_native.sh
```

This sparse-clones [microsoft/RecAI](https://github.com/microsoft/RecAI) into
`recai/InteRecAgent/`, downloads `all_resources.zip` (~1–2 GB), and writes
`data/catalogs/*.parquet`. Restart the PersonaEval backend afterward.

Flags: `--engine-only`, `--skip-download`, `--skip-parquets` (see
`scripts/setup_recai_resources.py --help`).
