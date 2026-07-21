# MIT OpenCourseWare course choice (Playwright)

MatrAIx **Playwright** web task on the live public MIT OpenCourseWare site. The
persona searches or browses the course catalog, inspects at least three course
pages, and selects the course they would most want to study next.

- Start URL: https://ocw.mit.edu/search/
- Output: `/app/output/course_choice.json`
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
  -p application/tasks/web-mit-ocw-course-choice
```

Oracle (live Playwright browsing; needs outbound network):

```bash
uv run harbor run \
  -p application/tasks/web-mit-ocw-course-choice \
  -a oracle
```

The verifier checks MIT OCW URL structure and internal consistency across the
submitted course metadata, and requires at least three distinct candidates.
Persona alignment is reported separately from objective task completion; there
is no single globally correct course.
