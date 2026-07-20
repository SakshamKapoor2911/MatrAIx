# Notion plan comparison (Playwright)

MatrAIx **Playwright** web task on the live public Notion pricing page. The
persona compares all four standard workspace plans in monthly billing mode and
selects the one that best fits their realistic personal or work context.

- Start URL: https://www.notion.com/pricing
- Output: `/app/output/notion_plan_comparison.json`
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
  -p application/tasks/web-notion-plan-comparison
```

Oracle (live Playwright browsing; needs outbound network):

```bash
uv run harbor run \
  -p application/tasks/web-notion-plan-comparison \
  -a oracle
```

The verifier checks the four canonical plan identities, monthly billing mode,
the canonical source URL, and internal consistency between the selected plan
and the complete comparison. Persona alignment is reported separately from
objective task completion; there is no single globally correct plan.

## Known limitations

Notion can change plan prices, audience descriptions, or feature tables
without notice. Agents must read those values from the rendered live page. In
accordance with the live-web contract, the verifier validates the submission
schema and internal consistency rather than making a second network request to
compare the artifact against a mutable page.
