# Notification preferences (iOS)

PersonaBench **mobile** computer-use task: open **Settings → Notifications** on an iPhone 17 simulator (use.computer, iOS 26.4), review one app, and submit a JSON decision.

Requires **`use-computer`** with **`platform: ios`**, not Docker.

Uses **`persona-computer-1`** → use.computer **`IOSAgent`**. The instruction is written for the persona; PersonaBench materializes the submitted JSON to `decision.json` on the simulator host for scoring.

```bash
uv sync --extra use-computer --extra computer-1
export USE_COMPUTER_API_KEY=...
export ANTHROPIC_API_KEY=...
```

## Simulator pin (match your use.computer mini)

| Field | Default in `task.toml` |
|-------|-------------------------|
| Device | `iPhone-17` |
| Runtime | `iOS-26-4` |

Change `[ios]` in `task.toml` if your reserved mini uses different simulator runtimes.

## Suggested setup

| Field | Value |
|-------|-------|
| Agent | `persona-computer-1` |
| Environment | `use-computer` + `platform: ios` |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |
| Agent kwargs | `max_steps: 35`, `recording_enabled: false` (job config) |

```bash
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-computer-use-ios_notification-preferences \
  -e use-computer \
  --ek platform=ios
```

Oracle check (writes `decision.json` on the host via shell; no LLM):

```bash
uv run harbor run \
  -p application/tasks/example-computer-use-ios_notification-preferences \
  -a oracle \
  -e use-computer \
  --ek platform=ios
```

## Submission (persona CUA)

The agent hands in JSON as described in `instruction.md`. `persona-computer-1` writes that to `/tmp/personabench-ios-notification-preferences/decision.json` on the Mac host before the verifier runs.

## Output path

Host path after trial:

`jobs/<job>/<trial>/artifacts/tmp/personabench-ios-notification-preferences/decision.json`

## vs macOS `macos-notification-preferences`

| | macOS | this task |
|--|-------|-----------|
| Platform | macOS desktop | iPhone 17 simulator |
| Settings UI | System Settings → Notifications | Settings → search Notifications |
| Submit | Terminal + shell heredoc | `done` tool JSON → host file |
| Step budget | Anthropic CUA (no 50-step cap) | `max_steps` default 50; job uses 35 |
