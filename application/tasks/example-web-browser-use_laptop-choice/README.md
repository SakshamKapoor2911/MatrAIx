# Laptop shortlist (browser-use)

MatrAIx **browser-use** web task on a live public site. Chromium is driven
by the [browser-use](https://github.com/browser-use/browser-use) agent loop
(DOM + optional vision) while the persona compares laptops and picks one they
would realistically consider.

- URL: https://webscraper.io/test-sites/e-commerce/static/computers/laptops
- Output: `/app/output/laptop_choice.json`

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
  -p application/tasks/example-web-browser-use_laptop-choice \
  --env-file .env
```

Oracle (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p application/tasks/example-web-browser-use_laptop-choice -a oracle
```

## Alternatives

| Mode | Task | Agent |
|------|------|-------|
| Playwright scripts | `example-web-playwright_quote-choice` | `persona-openhands-sdk` |
| Cocoa + AIO Sandbox | `example-web-cocoa_plan-choice` | `persona-cocoa` |
| CUA screenshots | `example-web-cua_bookshop-choice` | `persona-computer-1` (Docker) |
