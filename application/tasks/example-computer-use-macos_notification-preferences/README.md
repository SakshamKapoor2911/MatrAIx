# Notification preferences (macOS)

PersonaBench **macOS** computer-use task: the persona opens real **System Settings → Notifications**, reviews an app, and writes a structured JSON preference to disk.

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
  -p application/tasks/example-computer-use-macos_notification-preferences \
  -e use-computer
```

The curated local job recipe is
`configs/jobs/example-job-recipe/appSim-example-computer-use-macos-local.yaml`.

Oracle check (no LLM; writes the decision file directly):

```bash
uv run harbor run -p application/tasks/example-computer-use-macos_notification-preferences -a oracle -e use-computer
```

## Output path

Submissions are written inside the sandbox to:

`/tmp/personabench-macos-notification-preferences/decision.json`

Harbor downloads that directory after the trial (`artifacts` in `task.toml`). On the host:

`jobs/<job>/<trial>/artifacts/tmp/personabench-macos-notification-preferences/decision.json`

Check `artifacts/manifest.json` in the trial directory if a file is missing (`status: ok` vs `failed`).

## vs iOS `ios-notification-preferences`

| | this task | iOS |
|--|-----------|-----|
| Platform | macOS (`use-computer`, default) | iOS Simulator (`platform: ios`) |
| Settings UI | System Settings → Notifications | Settings app → Notifications |
| Output dir | `/tmp/personabench-macos-notification-preferences/` | `/tmp/personabench-ios-notification-preferences/` |
