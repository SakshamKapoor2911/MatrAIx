# Bookshop browsing (browser-use)

PersonaBench **browser-use** web task on a live public site. Chromium is driven by the [browser-use](https://github.com/browser-use/browser-use) agent loop (DOM + optional vision), not terminal Playwright scripts or CUA screenshots.

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json`

See [Application Tasks](../README.md) for contribution guidance.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-browser-use` |
| Environment | `docker` (`network_mode = "public"`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |
| API key | `ANTHROPIC_API_KEY` or `LLM_API_KEY` |

```bash
uv run harbor run \
  -a persona-browser-use \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-web-browser-use_books-interest \
  --env-file .env
```

Oracle (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p application/tasks/example-web-browser-use_books-interest -a oracle
```

## Alternatives

| Mode | Task | Agent |
|------|------|-------|
| Playwright scripts | `books-interest-playwright` | `persona-openhands-sdk` |
| Cocoa + AIO Sandbox | `books-interest-cocoa` | `persona-cocoa` |
| CUA screenshots | `books-interest-linux-cua` | `persona-computer-1` (Docker) |
