# Acme support chat (MCP)

MatrAIx chat task with a **mock Acme support bot** exposed as an MCP sidecar. The persona agent must use MCP tools (`send_message`, `get_conversation_history`) for a multi-turn conversation, then save the transcript to `/app/output/transcript.json`.

Requires **Docker Compose** (local `docker` environment). Not supported on cloud providers yet.

## Smoke run

**No API key** — validates Docker + verifier:

```bash
uv run harbor run -p application/tasks/example-chat-mcp_support_chatbot -a oracle
```

**Full run** — Playground UI or terminal auto mode: [Application Quickstart](../../QUICKSTART.md).

## Layout

```
application/tasks/example-chat-mcp_support_chatbot/
├── input/
│   ├── chatbot.yaml
│   ├── instruction.md
│   ├── context.md
│   └── self_report_schema.yaml
└── ...

environment/
├── Dockerfile
├── docker-compose.yaml      # support-bot sidecar
└── support-bot/
    ├── Dockerfile
    └── server.py            # FastMCP tools
```
