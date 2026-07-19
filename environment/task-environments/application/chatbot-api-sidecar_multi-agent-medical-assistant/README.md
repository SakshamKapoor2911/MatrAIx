# chatbot-api-sidecar_multi-agent-medical-assistant

Local HTTP sidecar for the [Multi-Agent-Medical-Assistant](https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant) product.

- `multi-agent-medical-assistant` — product SUT (built from a pinned upstream commit)
- `multi-agent-medical-assistant-api` — MatrAIx adapter for this medical chat task:
  `/health`, `/ready`, `/v1/session`, `/v1/messages`, `/v1/conversation`,
  `/v1/upload`, `/v1/validate`

Capabilities are declared on the task (`input/chatbot.yaml`): `text_chat`,
`upload_image`, `validate_output`.

Persona agent runtime: `application/shared-chat-persona`.

First `docker compose up --build` downloads upstream source during image build; requires network and an `OPENAI_API_KEY` for real replies.
