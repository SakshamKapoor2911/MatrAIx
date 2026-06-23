# Acme support chat (REST API)

You are a customer with a late order. Read `/app/input/order_context.md` for your order details.

Acme customer support is available through a **REST API** on the compose sidecar `support-api` (reachable from this container as `http://support-api:8000`). Use `curl` or a short script to have a real multi-turn conversation with support about your missing delivery.

**Endpoints**

| Method | Path | Body | Response |
|--------|------|------|----------|
| `POST` | `/v1/messages` | `{"message": "<your text>"}` | `{"reply": "<support reply>"}` |
| `GET` | `/v1/conversation` | — | `{"messages": [{"role": "customer"|"support", "content": "..."}, ...]}` |

1. `POST` to `/v1/messages` at least twice as yourself (the customer).
2. Work toward a useful update on order **#4521** — ask what you need, react naturally as your persona would.
3. When you are done, `GET` `/v1/conversation` and save the exact JSON to `/app/output/transcript.json`.

The transcript file must be valid JSON with this shape:

```json
{
  "messages": [
    {"role": "customer", "content": "<string>"},
    {"role": "support", "content": "<string>"}
  ]
}
```

Have at least **two** back-and-forth exchanges (four or more messages total). Do not promise refunds or replacements you cannot verify.
