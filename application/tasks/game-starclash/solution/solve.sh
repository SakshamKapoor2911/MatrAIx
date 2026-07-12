#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 /app/scripts/stage_crew_personas.py --crew /app/input/crew_manifest.yaml

# Oracle for the Starclash task: run the deterministic,
# no-API-key MockArenaBrain against the task's own ship map + crew roster
# and write game_log.json / final_state.json to /app/output. Seed 42 with
# --max-ticks 20 is a known-good combination (6 battles resolved before the
# tick budget runs out, confirmed by re-running run_arena.py directly), so
# this oracle run is fully deterministic and reproducibly produces at least
# one battle_resolved event.
python3 /app/scripts/run_arena.py \
  --map /app/input/ship_map.yaml \
  --crew /app/input/crew_manifest.yaml \
  --brain mock \
  --seed 42 \
  --max-ticks 20 \
  --out /app/output
