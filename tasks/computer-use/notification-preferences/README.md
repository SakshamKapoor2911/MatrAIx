# Notification preferences (desktop)

MatrAIx **computer-use** task: the persona opens real **System Settings → Notifications**, reviews an app, and writes a structured JSON preference to disk.

Requires the **use-computer** environment (remote macOS/Ubuntu desktop sandbox), not Docker.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-computer-1` |
| Environment | `use-computer` |
| Persona | `personas/examples/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/computer-use/notification-preferences \
  -e use-computer
```

Oracle check (no LLM; writes the decision file directly):

```bash
uv run harbor run -p tasks/computer-use/notification-preferences -a oracle -e use-computer
```

## Output path

use-computer sandboxes do not use `/app/`. Submissions go to:

`/tmp/matraix-notification-preferences/decision.json`

## vs `settings-smoke`

| | smoke | this task |
|--|-------|-----------|
| Goal | prove desktop agent works | realistic onboarding scenario |
| Output | fixed text token | JSON with app name + persona reason |
| Settings depth | open Notifications once | review a specific app's notification style |
