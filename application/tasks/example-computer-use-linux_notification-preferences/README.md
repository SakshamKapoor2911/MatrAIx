# Notification preferences (Linux)

PersonaBench **Linux desktop** computer-use task: the persona opens **XFCE Settings → Notifications** (Notify OSD) in a Docker Xvfb desktop and writes a JSON preference to disk.

Requires **`persona-computer-1`** with default **Docker** environment (Harbor `Computer1`). No `USE_COMPUTER_API_KEY`.

```bash
uv sync --extra computer-1
export ANTHROPIC_API_KEY=...
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-computer-use-linux_notification-preferences
```

Oracle:

```bash
uv run harbor run -p application/tasks/example-computer-use-linux_notification-preferences -a oracle
```

## Output

`/tmp/personabench-linux-notification-preferences/decision.json`

## vs macOS / iOS

| | Linux (this) | macOS | iOS |
|--|--------------|-------|-----|
| Environment | Docker Xvfb | use.computer | use.computer + `platform: ios` |
| Settings UI | XFCE Settings → Notify OSD | System Settings → Notifications | Settings → Notifications |

Web browsing CUA (books.toscrape.com) lives under `application/tasks/example-web-cua_*`, not here.
