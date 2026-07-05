# Photo access review (iOS)

PersonaBench **mobile** computer-use task: open **Settings → Privacy & Security → Photos** on an iPhone 17 simulator, review one app, and submit a structured privacy decision.

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
  -p application/tasks/example-computer-use-ios_photo-access-review \
  -e use-computer \
  --ek platform=ios
```

Oracle check (writes the submission file directly; no LLM):

```bash
uv run harbor run \
  -p application/tasks/example-computer-use-ios_photo-access-review \
  -a oracle \
  -e use-computer \
  --ek platform=ios
```

## Output path

Host path after trial:

`jobs/<job>/<trial>/artifacts/tmp/personabench-ios-photo-access-review/decision.json`

The verifier checks that the submission includes:

- a non-empty `app_reviewed`
- a valid `photo_access_level`
- a non-trivial free-text `reason`
