# Bookshop browsing (CUA)

MatrAIx **CUA** web task on a live public site. The persona uses **screenshot-based computer-use** (navigate / click / scroll) in a real desktop browser — not Playwright DOM automation.

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json` (same path as Playwright; on macOS use-computer, materializes under `/Users/lume/output/`)

Requires **`USE_COMPUTER_API_KEY`** and `-e use-computer`.

See [web-interaction.md](../../docs/applications/web-interaction.md) for Playwright vs CUA.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-computer-1` |
| Environment | `use-computer` |
| Persona | `personas/examples/persona_0042.yaml` |

```bash
export USE_COMPUTER_API_KEY=...
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/web/books-interest-cua \
  -e use-computer
```

Oracle (writes submission file; still needs use-computer sandbox):

```bash
uv run harbor run -p tasks/web/books-interest-cua -a oracle -e use-computer
```

## Playwright alternative

For DOM automation in Docker (no use.computer account), use `tasks/web/books-interest-playwright/` with `persona-openhands-sdk`.
