# Acme support chat (REST API)

PersonaBench chat task with a **mock Acme support bot** exposed as a REST API compose sidecar. The persona agent must call HTTP endpoints (`POST /v1/messages`, `GET /v1/conversation`) for a multi-turn conversation, then save the transcript to `/app/output/transcript.json`.

Requires **Docker Compose** (local `docker` environment). Not supported on cloud providers yet.

For the MCP variant, see [`example-chat-mcp_support_chatbot`](../example-chat-mcp_support_chatbot/).

## Smoke run

**No API key** — validates Docker + verifier:

```bash
uv run harbor run -p application/tasks/example-chat-api_support_chatbot -a oracle
```

**Full run** — Playground UI or terminal auto mode: [Application Quickstart](../../QUICKSTART.md).

## Layout

```
application/tasks/example-chat-api_support_chatbot/
├── input/
│   ├── chatbot.yaml
│   ├── instruction.md
│   ├── context.md
│   └── self_report_schema.yaml
└── ...

environment/
├── Dockerfile
├── docker-compose.yaml      # support-api sidecar
└── support-api/
    ├── Dockerfile
    └── server.py            # Flask REST endpoints
```
