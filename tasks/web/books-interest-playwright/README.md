# Bookshop browsing (Playwright)

MatrAIx **Playwright** web task on a live public site. Chromium is driven through the **Playwright Python API** (DOM automation), not screenshot-based CUA.

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json`

See [web-interaction.md](../../docs/applications/web-interaction.md) for Playwright vs CUA.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-openhands-sdk` |
| Environment | `docker` (Playwright image, `network_mode = "public"`) |
| Persona | `personas/examples/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/web/books-interest-playwright
```

Oracle (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p tasks/web/books-interest-playwright -a oracle
```

## CUA alternative

For screenshot-based browsing, use `tasks/web/books-interest-cua/` with `persona-computer-1` and `-e use-computer`.
