# FinAI / OpenBB chatbot

Canonical MatrAIx chatbot task for a financial-research assistant exposed through the Playground chat runtime.

Product under test: **OpenBB** (MCP data layer) + MatrAIx finance chat adapter — ported from [PR #86](https://github.com/MatrAIx-ai/MatrAIx/pull/86).

Local endpoint:

`environment/task-environments/application/chatbot-api-sidecar_openbb`

- Adapter service: `finance-chatbot` (host port `8901`)
- Upstream SUT: `openbb-mcp` on the compose network

Requires `OPENAI_API_KEY` for agent turns. Override endpoints with
`CHATBOT_UPSTREAM_FINANCE` / `FINANCE_CHATBOT_URL` when pointing at an external deploy.
