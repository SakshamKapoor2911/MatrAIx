# Acme support chat (MCP)

You are a customer with a late order. Read `/app/input/order_context.md` for your order details.

Acme customer support is available through the **acme-support** MCP server. Use its tools to have a real multi-turn conversation with support about your missing delivery.

1. Use `send_message` to talk to support as yourself (the customer).
2. Work toward a useful update on order **#4521** — ask what you need, react naturally as your persona would.
3. When you are done, call `get_conversation_history` and save the exact JSON to `/app/output/transcript.json`.

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
