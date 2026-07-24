# Allrecipes recipe choice (Playwright)

MatrAIx **Playwright** web task on the live public Allrecipes site. The persona
searches or browses the recipe catalog, inspects at least three recipe pages,
and selects the recipe they would most realistically prepare for an upcoming
meal.

- Start URL: https://www.allrecipes.com/
- Output: `/app/output/recipe_choice.json`
- Authentication: none
- External side effects: none

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
  -p application/tasks/web-allrecipes-recipe-choice
```

Oracle (live Playwright browsing; needs outbound network):

```bash
uv run harbor run \
  -p application/tasks/web-allrecipes-recipe-choice \
  -a oracle
```

The verifier checks Allrecipes recipe URL structure and internal consistency
across the submitted recipe metadata, and requires at least three distinct
candidates. Persona alignment is reported separately from objective task
completion; there is no single globally correct recipe.

## Known limitations

Allrecipes may return a generic server-error page to Chromium contexts that use
Playwright's default automated-browser user agent. The checked-in oracle uses a
normal desktop-browser user agent and isolated contexts for the search and
recipe pages. The task remains live-site-only and does not use a cached page or
an API substitute.
