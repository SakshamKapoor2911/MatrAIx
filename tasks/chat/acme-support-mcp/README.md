# Acme support chat (MCP)

MatrAIx chat task with a **mock Acme support bot** exposed as an MCP sidecar. The persona agent must use MCP tools (`send_message`, `get_conversation_history`) for a multi-turn conversation, then save the transcript to `/app/output/transcript.json`.

Requires **Docker Compose** (local `docker` environment). Not supported on cloud providers yet.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-claude-code` |
| Environment | `docker` (default) |
| Persona | `personas/examples/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/chat/acme-support-mcp
```

Oracle check (no API key):

```bash
uv run harbor run -p tasks/chat/acme-support-mcp -a oracle
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
