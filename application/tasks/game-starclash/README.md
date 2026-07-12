# Starclash

Multi-persona social simulation: several synthetic personas share one continuous 2D room aboard a starship, must physically move within `proximity_radius` to find each other, and can chat publicly, send private messages, or challenge each other to Rock-Paper-Scissors duels for stars. Research purpose: study whether different persona reasoning/trait profiles produce measurably different play styles, and whether that heterogeneity in reward-seeking and reasoning behavior can be turned into useful signal for game designers — success rate aside, do some persona mixes read as more fun, more engaged, or more confused than others from their own reasoning trajectories?

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Brain (text-only smoke) | `ClaudeArenaBrain` (`--brain claude`), needs `ANTHROPIC_API_KEY` |
| Brain (free smoke, no API key) | `MockArenaBrain` (`--brain mock`) |
| Brain (vision / computer-use) | `BrowserVisionBrain` (`--brain vision`), needs `ANTHROPIC_API_KEY` + `uv run playwright install chromium` |
| Brain (external decision-maker, e.g. no API key at all) | `FileBridgeBrain` (`--brain bridge`), needs `ARENA_BRIDGE_DIR` |
| Persona | Repo-root `persona/datasets/bench-dev-sample/` (referenced in `input/crew_manifest*.yaml`; uploaded at Harbor trial start — **not** copied into the task or Docker image; see `application/README.md`) |

Free smoke run, no API key required:

```bash
uv run python application/tasks/game-starclash/scripts/run_arena.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest.yaml \
  --brain mock --seed 42 --max-ticks 16 \
  --out /tmp/arena-smoke
```

Real Claude-driven smoke run (text-only, forced tool-calling — set `ANTHROPIC_API_KEY` first):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
uv run python application/tasks/game-starclash/scripts/run_arena.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest.yaml \
  --brain claude --seed 42 --max-ticks 16 \
  --out jobs/game-starclash-smoke
```

`BrowserVisionBrain` (`--brain vision`) renders each observation as an HTML page, screenshots it, and asks Claude (vision + forced tool-use) to click/type — real browser-use, not a JSON shortcut wearing a screenshot as a costume:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
uv run playwright install chromium   # one-time, if not already installed
uv run python application/tasks/game-starclash/scripts/run_arena.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest.yaml \
  --brain vision --seed 42 --max-ticks 16 \
  --out jobs/game-starclash-vision-smoke
```

`FileBridgeBrain` (`--brain bridge`) delegates every decision to an external process instead of calling an LLM API in-process: it writes each observation to `request_<n>.json` in `ARENA_BRIDGE_DIR` and blocks until a matching `response_<n>.json` appears (falling back to a safe default on timeout or an illegal response). This is how the game can be played by any external decision-maker — a human, a script, or a separate agent process with no `ANTHROPIC_API_KEY` of its own — without the engine needing to know or care what's on the other end:

```bash
export ARENA_BRIDGE_DIR=/tmp/arena_bridge
uv run python application/tasks/game-starclash/scripts/run_arena.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest.yaml \
  --brain bridge --seed 42 --max-ticks 16 \
  --out jobs/game-starclash-bridge-smoke
```

## Running multiple persona-style sessions for comparison

Personas inside a single game session are interacting with (and reacting to) each other, so they are not independent samples — you cannot isolate "how does a meticulous persona play" from one session that also contains careless personas duelling and taunting them. To get comparative data across reasoning styles, run **separate game sessions**, each with a `crew_manifest.yaml` built from a different persona-style mix, then compare aggregate metrics (success/survival rate, rubric scores) **across** sessions rather than within one.

Because independent sessions don't share any state, they can genuinely run in parallel — either as multiple concurrent `run_arena.py` invocations (different `--out`/`--seed`/`--crew` per session), or as separate trials in a Harbor job with `n_concurrent_trials` set.

`persona/datasets/bench-dev-sample/` personas carry ~60 `cog_*` communication-style dimensions per persona (plus a coarser `dimensions.dominant_trait` field). For the "meticulous vs careless" reasoning-style comparison this task was originally framed around, `dimensions.cog_detail_orientation` is the most literal stand-in: its observed values in this 14-persona sample are `"Very high"`, `"High"`, `"Moderate"`, `"Low"`, and `"None"`, so `"Very high"` = meticulous-leaning and `"Low"` = careless-leaning. Two ready-made alternate crew manifests already exist in `input/` built this way:

- `input/crew_manifest_meticulous.yaml` — every persona in the 14-persona sample with `cog_detail_orientation: "Very high"` (there are exactly 4: personas `0042`, `0229`, `0666`, `0712`).
- `input/crew_manifest_careless.yaml` — every persona in the sample with `cog_detail_orientation: "Low"` (also exactly 4: personas `0727`, `0773`, `0855`, `2002`).

Both rosters use every persona in the sample that genuinely carries the target value — the sample doesn't yet have 5+ personas at either extreme, so these manifests run with 4 personas each rather than padding with personas that don't actually match. The default `input/crew_manifest.yaml` (personas `0001`, `0052`, `0229`, `0666`, `0042`) already serves as a reasonable "mixed" roster for comparison: its `cog_detail_orientation` values are `None`, `Moderate`, `Very high`, `Very high`, `Very high` — skewed toward meticulous but not uniform, so it's a usable (if imperfect) mixed baseline without needing a third new file.

Run all three side by side:

```bash
uv run python application/tasks/game-starclash/scripts/run_arena.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest_meticulous.yaml \
  --brain mock --seed 42 --max-ticks 20 \
  --out /tmp/arena_meticulous_run &

uv run python application/tasks/game-starclash/scripts/run_arena.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest_careless.yaml \
  --brain mock --seed 42 --max-ticks 20 \
  --out /tmp/arena_careless_run &

uv run python application/tasks/game-starclash/scripts/run_arena.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest.yaml \
  --brain mock --seed 42 --max-ticks 20 \
  --out /tmp/arena_mixed_run &

wait
```

Compare `outcome_status`/success-rate and rubric scores (see `reporting.json`) across the resulting `/tmp/arena_meticulous_run/` vs `/tmp/arena_careless_run/` vs `/tmp/arena_mixed_run/` (`final_state.json` for the scoreboard, `game_log.json` for full reasoning trajectories) to see how detail-orientation composition shifts survival outcomes and reasoning-trajectory tone.

`cog_detail_orientation` is just one of ~60 `cog_*` dimensions available per persona (see any file under `persona/datasets/bench-dev-sample/persona_*.yaml`) — the same filter-and-build-a-manifest approach works for any other dimension (e.g. `cog_risk_framing`, `cog_assertiveness`, `cog_patience`) to study a different persona-style research question.

### Persona loading (repo convention)

Per [`application/README.md`](../../README.md) and [`environment/README.md`](../../../environment/README.md):

- Persona YAML lives under **repo-root** `persona/datasets/bench-dev-sample/`.
- `input/crew_manifest*.yaml` lists `persona_paths` pointing at those files.
- **Do not** copy persona YAML into `application/tasks/game-starclash/persona/` or the Docker image.
- **Harbor trials** upload crew personas into `/app/persona/...` at agent setup (`harbor.utils.crew_personas`), the multi-file analogue of the single `persona_path` upload to `/app/input/persona.yaml` used by survey/chat tasks.
- **Local runs** from the MatrAIx repo root resolve the same paths via `run_arena.py` directory walk-up.

## Output

Each run writes:

- `/app/output/game_log.json` — full event log (moves, chat, private messages, challenges, battle resolutions, and any persona `reasoning` text attached to a decision), plus a persona trait summary and final state.
- `/app/output/final_state.json` — just the final scoreboard (stars, eliminated flag, final hand size, position per persona) and the termination reason.

To watch a run visually, render `game_log.json` into a self-contained, read-only replay page — an event/moment scrubber, live scoreboard, comms ticker, and room view of every persona's position and duels:

```bash
uv run python -c "
import sys, json
sys.path.insert(0, 'application/tasks/game-starclash/scripts')
from render_observation import render_spectator_html

with open('/path/to/game_log.json') as f:
    game_log = json.load(f)

with open('replay.html', 'w', encoding='utf-8') as f:
    f.write(render_spectator_html(game_log))
"
```

Then open `replay.html` in any browser — no server or network access needed.

### Live watch (no API key)

Step through a match tick-by-tick and auto-refresh a spectator page while it runs:

```bash
uv run python application/tasks/game-starclash/scripts/run_arena_live.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest_meticulous.yaml \
  --brain mock --seed 42 --max-ticks 16 \
  --delay 1.2 --serve 8765
```

Open `http://127.0.0.1:8765/spectator_live.html` — the page refreshes during play, then stops when the match ends.

For the external-decision pattern (same file handshake an out-of-process pilot would use, still no API key), use `--brain bridge`. `run_arena_live.py` spawns `bridge_responder.py`, which answers each `request_<n>.json` with `MockArenaBrain` decisions:

```bash
uv run python application/tasks/game-starclash/scripts/run_arena_live.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest_meticulous.yaml \
  --brain bridge --seed 42 --max-ticks 12 \
  --delay 1.5 --serve 8765
```

### Real computer-use without an in-process API key

`--brain mock` and `--brain bridge` are **not** computer-use — they never open Chromium or click the HUD.

**Computer-use paths:**

| Mode | Who clicks the UI | In-process API key |
|------|-------------------|-------------------|
| `--brain vision` | `BrowserVisionBrain` (Playwright + vision model in-process) | `ANTHROPIC_API_KEY` (Claude today) |
| `--brain cua` | `bridge_cua_responder.py` (Playwright) + **external pilot(s)** | None |

> **How this was tested:** No `ANTHROPIC_API_KEY` was available during development, so computer-use was exercised via `--brain cua` with **external pilots** (separate agent processes watching the bridge directory and writing click primitives). Any vision-capable external agent works — the repo ships `persona_cua_pilot.py` and `run_4agent_cua_play.py` for this; the author personally used Grok for early smoke runs, but nothing in the bridge contract is vendor-specific.

With `--headed`, `bridge_cua_responder.py` opens **real Chromium** (by default one cockpit window per persona, up to four in a 2×2 grid). The external pilot reads screenshots / `TASK.md` and writes JSON; Playwright executes the clicks.

**External-pilot flow (`--brain cua`):**

1. Start the live match (spawns Playwright CUA responder + spectator):

```bash
uv run python application/tasks/game-starclash/scripts/run_arena_live.py \
  --map application/tasks/game-starclash/input/ship_map.yaml \
  --crew application/tasks/game-starclash/input/crew_manifest_meticulous.yaml \
  --brain cua --headed --seed 42 --max-ticks 8 \
  --delay 2.0 --serve 8765 \
  --out application/tasks/game-starclash/scripts/_sample_output/cua_live
```

2. Open spectator: `http://127.0.0.1:8765/spectator_live.html`

3. Run external pilot(s) against the bridge directory (or launch separate Task/subagent processes) with a prompt like:

> Watch `<out>/bridge/cua_*/TASK.md`. For each new `cua_<n>/` folder: study `screenshot.png` (and `page.html` if helpful), decide one legal action, write `../primitives_<n>.json` with click steps (`click_at`, `type_text`, `done`). The CUA responder executes real clicks in Chromium.

Bridge dir default: `<out>/bridge/` (e.g. `.../cua_live/bridge/`).

Each `cua_<n>/` bundle contains `page.html`, `screenshot.png`, `observation.json`, and `TASK.md` with legal actions for that persona's turn.

**In-process CUA** (when you do have an API key): `--brain vision` on `run_arena.py` / `run_arena_live.py` — same Playwright HUD, vision model drives clicks inside the runner.

### 4-persona CUA play (one pilot + one Chromium window per persona)

Orchestrates the real CUA bridge (Playwright screenshots + click primitives) with **four built-in pilots** (`persona_cua_pilot.py`, one thread per meticulous persona) until every hand is empty. **By default this opens four headed Chromium cockpits** in a 2×2 grid so you can watch each persona navigate, challenge, accept, and pick cards live. No in-process LLM API key required.

```bash
# From the MatrAIx monorepo root (personas resolve via walk-up to persona/datasets)
uv run python application/tasks/game-starclash/scripts/run_4agent_cua_play.py \
  --max-ticks 48 --serve 8765 \
  --out application/tasks/game-starclash/scripts/_sample_output/cua_4agent_play
```

- Spectator: `http://127.0.0.1:8765/spectator_live.html`
- Four live cockpits: one Chromium window per persona (titles `Starclash · 0042`, etc.)
- Headless CI / smoke: add `--no-headed`
- Single shared browser: add `--single-window`
- Each turn still writes `bridge/cua_<n>/{page.html,screenshot.png,TASK.md,observation.json}`

What you should see during a healthy run:

1. Agents **move toward** each other on the bordered **room deck**
2. When in proximity, **DUEL** arms and challenges issue
3. Challenge modal: **Accept / Decline**
4. Pokemon-style duel stage: click **Rock / Paper / Scissors**
5. Spectator scoreboard updates as stars transfer

### Agent HUD notes

- **Full ship room** is shown; room `(x,y)` maps onto the floor region inside that art.
- **All players** appear on the map (far pilots are dimmed; only nearby are challengeable). Color rings identify each pilot.
- **Hotbar** always shows SAY / MOVE / DUEL / DM / WAIT — illegal actions are dimmed, not missing.
- **Duel phase** uses the original top-down sprite, VS face-off, and painted RPS cards.
- **UI auto-scales** (agent design 1024×768, spectator 1280×720) to fit the window.
- Dense status (e.g. market signal) stays in `observation.json` / `TASK.md` so the click surface stays simple for computer-use.

### Indie polish agent loop

To keep raising visual quality iteratively:

1. Skill: ask your agent to **“run the game-starclash polish loop”** (skill `game-starclash-polish`).
2. Capture harness:

```bash
python application/tasks/game-starclash/scripts/polish_loop.py capture \
  --out application/tasks/game-starclash/scripts/_sample_output/polish_loop
```

3. Critique `shots/*.png`, apply ≤3 fixes, re-capture, update `REPORT.md`.

Exit when Structure + Agent + Spectator checklist items pass and ≥3/4 Indie juice items pass (see skill + `REPORT.md`).

