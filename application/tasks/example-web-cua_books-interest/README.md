# Bookshop browsing (Docker Linux CUA)

Docker **web** CUA task — screenshot-based browsing in a local Linux Xvfb container (no `USE_COMPUTER_API_KEY`).

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json` (materialized from a **done** JSON submission)

```bash
uv sync --extra computer-1
export ANTHROPIC_API_KEY=...
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-web-linux-cua-local.yaml
```

The job sets `cua_submission_profile: book_interest` so Harbor writes `/app/output/book_interest.json` from the agent's final **done** action. The Docker image includes **xfce4-terminal** (`Ctrl+Alt+T`) for optional shell use, but agents should not rely on manual file saving.

## vs other book tasks

| Task | Environment |
|------|-------------|
| **this task** | Docker Linux Xvfb (CUA + submission helper) |
| `books-interest-playwright` | Docker (Playwright DOM) |
| `books-interest-browser-use` | Docker (browser-use) |

OS settings tasks live under `application/tasks/example-computer-use-*`, not here.
