# Bookshop browsing (browser-use)

MatrAIx **browser-use** web task on a live public site. Chromium is driven by the [browser-use](https://github.com/browser-use/browser-use) agent loop (DOM + optional vision), not terminal Playwright scripts or CUA screenshots.

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json`

See [web-interaction.md](../../docs/applications/web-interaction.md).

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-browser-use` |
| Environment | `docker` (`network_mode = "public"`) |
| Persona | `personas/examples/persona_0042.yaml` |
| API key | `ANTHROPIC_API_KEY` or `LLM_API_KEY` |

```bash
uv run harbor run \
  -a persona-browser-use \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/web/books-interest-browser-use \
  --env-file .env
```

Oracle (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p tasks/web/books-interest-browser-use -a oracle
```

## Alternatives

| Mode | Task | Agent |
|------|------|-------|
| Playwright scripts | `books-interest-playwright` | `persona-openhands-sdk` |
| Cocoa + AIO Sandbox | `books-interest-cocoa` | `persona-cocoa` |
| CUA screenshots | `books-interest-cua` | `persona-computer-1` + `use-computer` |
