# Bookshop browsing (CocoaAgent)

MatrAIx **CocoaAgent** web task on a live public site. The Harbor task container is an [AIO Sandbox](https://github.com/agent-infra/sandbox) image; [CocoaAgent](https://github.com/cocoabench/cocoa-agent) connects to `localhost:8080` (no nested Docker).

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json`

See [web-interaction.md](../../docs/applications/web-interaction.md).

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-cocoa` |
| Environment | `docker` (`network_mode = "public"`) |
| Persona | `personas/examples/persona_0042.yaml` |
| API key | `ANTHROPIC_API_KEY` or `LLM_API_KEY` |

```bash
uv run harbor run -c configs/jobs/persona-cocoa-local.yaml --env-file .env
```

Oracle (Playwright fetch inside task image; needs outbound network):

```bash
uv run harbor run -p tasks/web/books-interest-cocoa -a oracle
```

## Requirements

- Docker on the host (standard Harbor `-e docker`)
- Outbound network for the in-container browser
- Larger image than Playwright-only tasks (`agent-infra/sandbox` base)

## Alternatives

| Mode | Task | Agent |
|------|------|-------|
| browser-use loop | `books-interest-browser-use` | `persona-browser-use` |
| Playwright scripts | `books-interest-playwright` | `persona-openhands-sdk` |
| CUA screenshots | `books-interest-cua` | `persona-computer-1` + `use-computer` |
