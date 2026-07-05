# Calendar + reminder handoff (macOS)

PersonaBench **macOS** computer-use task: turn a short scheduling brief into a
two-artifact cross-app handoff, with one calendar event line and one reminder
line.

Requires the **use-computer** environment (remote macOS desktop sandbox), not Docker.

Uses **`persona-computer-1`** → use.computer **`AnthropicCUAAgent`** (native screenshot/mouse API, not Docker Xvfb).

```bash
uv sync --extra use-computer --extra computer-1
export USE_COMPUTER_API_KEY=...
export ANTHROPIC_API_KEY=...
```

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-computer-1` |
| Environment | `use-computer` (default `platform: macos`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-computer-use-macos_calendar-reminder-handoff \
  -e use-computer
```

The curated local job recipe is
`configs/jobs/example-job-recipe/appSim-example-computer-use-macos-local.yaml`.

Oracle check (no LLM; writes the artifact files directly):

```bash
uv run harbor run -p application/tasks/example-computer-use-macos_calendar-reminder-handoff -a oracle -e use-computer
```

## Output path

Submissions are written inside the sandbox to:

- `/tmp/personabench-macos-calendar-reminder-handoff/handoff.txt`
- `/tmp/personabench-macos-calendar-reminder-handoff/plan.json`

Harbor downloads that directory after the trial (`artifacts` in `task.toml`). On
the host:

`jobs/<job>/<trial>/artifacts/tmp/personabench-macos-calendar-reminder-handoff/`

Check `artifacts/manifest.json` in the trial directory if a file is missing (`status: ok` vs `failed`).

The verifier checks:

- `handoff.txt` matches the expected two-line format
- `plan.json` contains the expected calendar title, reminder title, and location
