# Quote choice (Playwright)

PersonaBench **Playwright** web task on a live public site. Chromium is driven
through the **Playwright Python API** (DOM automation), and the persona picks a
quote they would most want to save or share.

- URL: https://quotes.toscrape.com/
- Output: `/app/output/quote_choice.json`

See [Application Tasks](../README.md) for contribution guidance.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-openhands-sdk` |
| Environment | `docker` (Playwright image, `network_mode = "public"`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-web-playwright_quote-choice
```

Oracle (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p application/tasks/example-web-playwright_quote-choice -a oracle
```

## Example family

| Mode | Task path | Concept |
|------|-----------|---------|
| **this task** | `example-web-playwright_quote-choice` | Quote choice |
| browser-use | `example-web-browser-use_laptop-choice` | Laptop shortlist |
| CocoaAgent | `example-web-cocoa_plan-choice` | Pricing-plan choice |
| CUA | `example-web-cua_bookshop-choice` | Bookshop choice |
