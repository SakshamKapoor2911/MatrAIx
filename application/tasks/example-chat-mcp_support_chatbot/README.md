# Acme support chat (MCP)

PersonaBench chat task with a **mock Acme support bot** exposed as an MCP sidecar. The persona agent must use MCP tools (`send_message`, `get_conversation_history`) for a multi-turn conversation, then save the transcript to `/app/output/transcript.json`.

Requires **Docker Compose** (local `docker` environment). Not supported on cloud providers yet.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-claude-code` |
| Environment | `docker` (default) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-chat-mcp_support_chatbot
```

Oracle check (no API key):

```bash
uv run harbor run -p application/tasks/example-chat-mcp_support_chatbot -a oracle
```

## Layout

```
environment/
├── Dockerfile
├── docker-compose.yaml      # support-bot sidecar
├── order_context.md         # → /app/input/
└── support-bot/
    ├── Dockerfile
    └── server.py            # FastMCP tools
```
