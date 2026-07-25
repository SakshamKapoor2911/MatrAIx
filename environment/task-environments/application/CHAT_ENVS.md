# Chat task environments

## Persona agent (shared)

`shared-chat-persona/` — Harbor main image for all chatbot tasks.

## Local endpoint hosts (per SUT)

Pick the sidecar **by the persona-facing protocol** (`input/chatbot.yaml`
`transport`), not by every internal dependency of the product.

| Directory | Task | Persona-facing protocol |
|-----------|------|-------------------------|
| `chatbot-api-sidecar_recai/` | `chat_recai` | HTTP |
| `chatbot-api-sidecar_openbb/` | `chat_openbb` | HTTP adapter (`finance-chatbot`) over OpenBB MCP (`openbb-mcp`) |
| `chatbot-api-sidecar_acme-support-api/` | `example-chat-api_support_chatbot` | HTTP |
| `chatbot-mcp-sidecar_acme-support/` | `example-chat-mcp_support_chatbot` | MCP |
| `chatbot-api-sidecar_multi-agent-medical-assistant/` | `chat_multi-agent-medical-assistant` | HTTP adapter over product upstream |
| `chatbot-api-sidecar_meal-plan-api/` | `chat_meal-planning-nutrition` | HTTP |

```toml
[environment]
definition = "application/shared-chat-persona"
local_compose = "application/chatbot-api-sidecar_recai"  # omit for external URLs
```

`chatbot-api-sidecar_openbb` is an API sidecar because the eval talks
`/v1/messages`; OpenBB itself is the MCP data layer behind the adapter, not a
`chatbot-mcp-sidecar_*` (those are for MCP surfaces the persona calls directly).
