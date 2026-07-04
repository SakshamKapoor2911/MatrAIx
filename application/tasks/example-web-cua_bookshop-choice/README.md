# Bookshop choice (Docker Linux CUA)

Docker **web** CUA task for a persona-sensitive book decision. The agent browses
the public catalog in a local Linux Xvfb container and submits a structured
choice with a final **done** action.

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json` (materialized from a **done** JSON submission)

```bash
uv sync --extra computer-1
export ANTHROPIC_API_KEY=...
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  --ak cua_submission_profile=book_interest \
  -p application/tasks/example-web-cua_bookshop-choice
```

`cua_submission_profile=book_interest` tells the runtime to write
`/app/output/book_interest.json` from the agent's final **done** action. The
Docker image includes **xfce4-terminal** (`Ctrl+Alt+T`) for optional shell use,
but agents should not rely on manual file saving.

## Example family

| Task | Environment |
|------|-------------|
| **this task** | Docker Linux Xvfb (CUA + submission helper) |
| `example-web-playwright_quote-choice` | Quote choice on `quotes.toscrape.com` |
| `example-web-browser-use_laptop-choice` | Laptop shortlist on `webscraper.io` |
| `example-web-cocoa_plan-choice` | Pricing-plan choice on PythonAnywhere |

OS settings tasks live under `application/tasks/example-computer-use-*`, not here.
