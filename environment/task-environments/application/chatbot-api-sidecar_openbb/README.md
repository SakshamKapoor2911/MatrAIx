# chatbot-api-sidecar_openbb

Local HTTP sidecar for the OpenBB-powered financial research chatbot from
[PR #86](https://github.com/MatrAIx-ai/MatrAIx/pull/86) (`app/chatbot-general`).

- `openbb-mcp` — product data layer ([OpenBB](https://github.com/OpenBB-finance/OpenBB) MCP server)
- `finance-chatbot` — MatrAIx adapter (`/health`, `/ready`, `/v1/session`,
  `/v1/messages`, `/v1/conversation`, `/v1/recommendations`) using the OpenAI
  Agents SDK against OpenBB MCP tools. Structured instruments are exposed as
  `groundedItems` (task `structuredExposure` selector).

Persona agent runtime: `application/shared-chat-persona`.
Task: `application/tasks/chat_openbb`.

First `docker compose up --build` pulls OpenBB packages and needs network plus
an `OPENAI_API_KEY` for real agent turns (`/ready` checks for that key).
