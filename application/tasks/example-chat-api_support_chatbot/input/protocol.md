# Support chat API protocol

Acme customer support is available through a **REST API** on the compose sidecar
`support-api` (reachable from this container as `http://support-api:8000`). Use
`curl` or a short script to have a real multi-turn conversation with support about
your missing delivery.

## Endpoints

| Method | Path | Body | Response |
|--------|------|------|----------|
| `POST` | `/v1/messages` | `{"message": "<your text>"}` | `{"reply": "<support reply>"}` |
| `GET` | `/v1/conversation` | — | `{"messages": [{"role": "customer"|"support", "content": "..."}, ...]}` |

1. `POST` to `/v1/messages` at least twice as yourself (the customer).
2. Work toward a useful update on order **#4521**.
3. Continue until you can judge whether support gave you a useful resolution path.
