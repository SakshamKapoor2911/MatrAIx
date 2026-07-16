# Chat API protocol

The chatbot is available through a **REST API** on the compose sidecar
`real-estate-moving-services-chatbot` (reachable from this container as `http://real-estate-moving-services-chatbot:8000`).
Use `curl` or a short script to have a multi-turn conversation.

## Endpoints

| Method | Path | Body | Response |
|--------|------|------|----------|
| `POST` | `/v1/messages` | `{"message": "<your text>"}` | `{"reply": "<chatbot reply>"}` |
| `GET` | `/v1/conversation` | -- | `{"messages": [{"role": "customer"|"assistant", "content": "..."}, ...]}` |

1. `POST` to `/v1/messages` at least twice.
2. Work toward the goal described in `context.md`.
3. Continue until you can judge whether the chatbot was helpful.
