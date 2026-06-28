# Bookshop browsing (Playwright)

PersonaBench **Playwright** web task on a live public site. Chromium is driven through the **Playwright Python API** (DOM automation), not screenshot-based CUA.

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json`

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
  -p application/tasks/example-web-playwright_books-interest
```

Oracle (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p application/tasks/example-web-playwright_books-interest -a oracle
```

## CUA alternative

For screenshot-based browsing, use `application/tasks/example-web-cua_books-interest/` with `persona-computer-1` (Docker).
