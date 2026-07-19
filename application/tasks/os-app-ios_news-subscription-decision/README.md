# News+ subscription decision (iOS)

MatrAIx **mobile** computer-use task: open the **News+ subscription**
screen on an iPhone 17 simulator, browse the **full offer**, return to the top
to re-check **features and pricing**, then convert only by tapping
**Get Started** (or end without tapping if declining).

Requires **`use-computer`** with **`platform: ios`**, not Docker. The News app
and a News+ offer screen with **Get Started** must be available on the reserved
mini.

Uses **`persona-computer-1`** → use.computer **`IOSAgent`**. The instruction is
written for the persona; MatrAIx materializes the submitted JSON to
`decision.json` on the simulator host for scoring.

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
| Agent kwargs | `max_steps: 45`, `recording_enabled: false` (job config) |

```bash
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/os-app-ios_news-subscription-decision \
  -e use-computer \
  --ek platform=ios
```

Oracle check (writes the submission file directly; no LLM):

```bash
uv run harbor run \
  -p application/tasks/os-app-ios_news-subscription-decision \
  -a oracle \
  -e use-computer \
  --ek platform=ios
```

## Output path

Host path after trial:

`jobs/<job>/<trial>/artifacts/app/output/decision.json`

The verifier checks that the submission includes:

- `browsed_full_offer: true` and `reviewed_features_and_pricing: true`
- boolean `clicked_get_started` (true only after tapping **Get Started**)
- non-empty `price_seen`, `highlights_noticed`, and `reason`

Conversion reporting treats `clicked_get_started=true` as `subscribe` and
`false` as `decline`.
