# Bookshop browsing (CocoaAgent)

PersonaBench **CocoaAgent** web task on a live public site. The Harbor task container is an [AIO Sandbox](https://github.com/agent-infra/sandbox) image; [CocoaAgent](https://github.com/cocoabench/cocoa-agent) connects to `localhost:8080` (no nested Docker).

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json`

See [Application Tasks](../README.md) for contribution guidance.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-cocoa` |
| Environment | `docker` (`network_mode = "public"`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |
| API key | `ANTHROPIC_API_KEY` or `LLM_API_KEY` |

```bash
uv run harbor run \
  -a persona-cocoa \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-web-cocoa_books-interest \
  --env-file .env
```

Oracle (Playwright fetch inside task image; needs outbound network):

```bash
uv run harbor run -p application/tasks/example-web-cocoa_books-interest -a oracle
```

## Requirements

- Docker on the host (standard Harbor `-e docker`)
- Outbound network for the in-container browser
- Larger image than Playwright-only tasks (`agent-infra/sandbox` base)
- **Apple Silicon:** base image is **linux/amd64 only**; Dockerfile pins `--platform=linux/amd64`, and `environment/docker-compose.yaml` starts the real AIO Sandbox entrypoint (Harbor's default `sleep infinity` would leave `:8080` down).

## Alternatives

| Mode | Task | Agent |
|------|------|-------|
| browser-use loop | `books-interest-browser-use` | `persona-browser-use` |
| Playwright scripts | `books-interest-playwright` | `persona-openhands-sdk` |
| CUA screenshots | `books-interest-linux-cua` | `persona-computer-1` (Docker) |
