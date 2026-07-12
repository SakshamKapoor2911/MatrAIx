#!/usr/bin/env python
"""CLI entrypoint for the Starclash simulation.

Loads a single-room ship map (a continuous 2D space with spawn/proximity/
movement parameters) and a crew manifest, deals cards, runs the engine's
tick state machine to completion using the chosen brain, and writes
`game_log.json` + `final_state.json` to the output directory.

--brain choices:
    mock    Deterministic, seeded mock brain (brains.MockArenaBrain). No
            API key or extra dependencies required.
    claude  Real Anthropic Claude-driven brain via structured tool-use
            (brains.ClaudeArenaBrain). Requires ANTHROPIC_API_KEY and the
            `anthropic` package.
    vision  Real vision-driven browser-use brain (vision_brain.
            BrowserVisionBrain): renders each observation as HTML, drives
            it via a real headless Playwright browser, and asks Claude to
            look at screenshots to decide clicks/typing. Requires
            ANTHROPIC_API_KEY plus the `anthropic` and `playwright`
            packages (and `playwright install chromium` having been run).

Example:
    python run_arena.py \\
        --map application/tasks/game-starclash/input/ship_map.yaml \\
        --crew application/tasks/game-starclash/input/crew_manifest.yaml \\
        --brain mock --seed 42 --max-ticks 16 \\
        --out application/tasks/game-starclash/scripts/_sample_output
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

# Ensure this script's own directory is importable regardless of invocation
# style (`python run_arena.py`, `uv run python .../run_arena.py`, etc.).
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import yaml  # noqa: E402

import brains  # noqa: E402
import observations  # noqa: E402
from engine import ArenaEngine, PersonaState  # noqa: E402
from persona_names import random_display_name  # noqa: E402

# A handful of key trait dimensions to keep the game_log.json persona
# summary small (the full persona YAML has ~60 dims and is only needed by
# the brain at decision time, not in the output artifact).
_SUMMARY_DIMENSIONS = (
    "dominant_trait",
    "risk_tolerance",
    "decision_style",
    "values_priority",
    "region",
)


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_personas(crew_manifest: dict, repo_root: str, seed: int) -> List[PersonaState]:
    persona_paths = crew_manifest.get("persona_paths", [])
    personas: List[PersonaState] = []
    for rel_path in persona_paths:
        abs_path = os.path.join(repo_root, rel_path)
        traits = load_yaml(abs_path)
        persona_id = str(traits.get("persona_id", os.path.splitext(os.path.basename(rel_path))[0]))
        personas.append(
            PersonaState(
                id=persona_id,
                display_name=random_display_name(persona_id, seed=seed),
                traits=traits,
                stars=3,
                hand=[],
            )
        )
    return personas


def resolve_room_name(map_data: dict) -> str:
    """Display name of the (sole) physical room, read straight from
    ``room.name`` in ship_map.yaml. There is only ever one room now, so
    unlike the old multi-room map there's no "starting room" indirection
    needed - this name applies for the whole run."""
    room = map_data.get("room", {}) if isinstance(map_data, dict) else {}
    name = room.get("name") if isinstance(room, dict) else None
    return name or "Main Chat Room"


def build_brain(brain_kind: str, seed: int):
    if brain_kind == "mock":
        return brains.MockArenaBrain(seed=seed)

    if brain_kind == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print(
                "ERROR: --brain claude requires the ANTHROPIC_API_KEY environment "
                "variable to be set. Export it and re-run, or use --brain mock.",
                file=sys.stderr,
            )
            sys.exit(1)
        return brains.ClaudeArenaBrain(api_key=api_key)

    if brain_kind == "vision":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print(
                "ERROR: --brain vision requires the ANTHROPIC_API_KEY environment "
                "variable to be set. Export it and re-run, or use --brain mock.",
                file=sys.stderr,
            )
            sys.exit(1)
        # vision_brain is imported lazily, only when --brain vision is
        # actually selected, so that --brain mock/claude runs never require
        # playwright to be installed (mirrors how ClaudeArenaBrain/
        # BrowserVisionBrain each lazily import `anthropic` inside
        # themselves, but one level up: at this CLI level, the whole
        # vision_brain MODULE import is deferred, not just `anthropic`).
        try:
            import vision_brain
        except ImportError as exc:
            print(
                "ERROR: --brain vision requires the 'playwright' package "
                "(e.g. `uv add playwright` and `uv run playwright install "
                "chromium`) and the 'anthropic' package to be installed. "
                f"Import failed: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            return vision_brain.BrowserVisionBrain(api_key=api_key)
        except ImportError as exc:
            print(f"ERROR: --brain vision failed to initialize: {exc}", file=sys.stderr)
            sys.exit(1)

    if brain_kind == "bridge":
        bridge_dir = os.environ.get("ARENA_BRIDGE_DIR")
        if not bridge_dir:
            print(
                "ERROR: --brain bridge requires the ARENA_BRIDGE_DIR environment "
                "variable to be set to a directory an external process will "
                "poll for request_*.json / write response_*.json into.",
                file=sys.stderr,
            )
            sys.exit(1)
        import bridge_brain

        return bridge_brain.FileBridgeBrain(bridge_dir=bridge_dir)

    raise ValueError(f"Unknown brain kind: {brain_kind!r}")


def persona_summary(persona: PersonaState) -> Dict[str, Any]:
    traits = persona.traits or {}
    dims = traits.get("dimensions", traits) if isinstance(traits, dict) else {}
    if not isinstance(dims, dict):
        dims = {}
    summary_dims = {k: dims.get(k) for k in _SUMMARY_DIMENSIONS if k in dims}
    return {
        "id": persona.id,
        "display_name": persona.display_name,
        "traits_summary": summary_dims,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Starclash simulation.")
    parser.add_argument("--map", required=True, help="Path to ship_map.yaml")
    parser.add_argument("--crew", required=True, help="Path to crew_manifest.yaml")
    parser.add_argument("--brain", choices=["mock", "claude", "vision", "bridge"], default="mock")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-ticks", type=int, default=16)
    parser.add_argument("--out", required=True, help="Output directory for game_log.json / final_state.json")
    args = parser.parse_args()

    # repo_root: crew manifest persona_paths are relative to the repo root
    # (e.g. "persona/datasets/bench-dev-sample/persona_0001.yaml"). Walk up
    # from this script's directory to find it, falling back to cwd.
    repo_root = _SCRIPT_DIR
    for _ in range(6):
        candidate = os.path.join(repo_root, "persona", "datasets")
        if os.path.isdir(candidate):
            break
        repo_root = os.path.dirname(repo_root)
    else:
        repo_root = os.getcwd()

    map_data = load_yaml(args.map)
    crew_manifest = load_yaml(args.crew)

    room_name = resolve_room_name(map_data)
    room_data = map_data.get("room", {}) if isinstance(map_data, dict) else {}
    room_width = float(room_data.get("width", 20.0))
    room_height = float(room_data.get("height", 20.0))
    proximity_radius = float(map_data.get("proximity_radius", 3.0))
    max_move_distance = float(map_data.get("max_move_distance", 2.0))
    start_area = map_data.get("start_area") if isinstance(map_data, dict) else None
    hand_size = int(crew_manifest.get("hand_size", 4))
    personas = load_personas(crew_manifest, repo_root, seed=args.seed)

    engine = ArenaEngine(
        personas=personas,
        room_name=room_name,
        max_ticks=args.max_ticks,
        seed=args.seed,
        hand_size=hand_size,
        observation_builder=observations.build_observation,
        room_width=room_width,
        room_height=room_height,
        proximity_radius=proximity_radius,
        max_move_distance=max_move_distance,
        start_area=start_area,
    )

    initial_persona_card_counts = {
        pid: observations._hand_card_counts(engine.personas[pid].hand)
        for pid in engine.persona_order
    }
    spawn_positions = {
        pid: {"x": engine.personas[pid].x, "y": engine.personas[pid].y}
        for pid in engine.persona_order
    }

    brain = build_brain(args.brain, args.seed)

    def brain_fn(persona: PersonaState, observation: dict) -> dict:
        return brain.decide(observation)

    engine.run(brain_fn)

    final = engine.final_state()

    os.makedirs(args.out, exist_ok=True)

    game_log = {
        "seed": args.seed,
        "max_ticks": args.max_ticks,
        "room_name": room_name,
        "hand_size": hand_size,
        "room_width": room_width,
        "room_height": room_height,
        "initial_card_counts": engine.initial_card_counts,
        "initial_persona_card_counts": initial_persona_card_counts,
        "spawn_positions": spawn_positions,
        "personas": [persona_summary(p) for p in personas],
        "events": engine.events,
        "final_state": final["final_state"],
        "termination_reason": final["termination_reason"],
    }

    game_log_path = os.path.join(args.out, "game_log.json")
    final_state_path = os.path.join(args.out, "final_state.json")

    with open(game_log_path, "w", encoding="utf-8") as f:
        json.dump(game_log, f, indent=2)

    final_state_output = {
        "final_state": final["final_state"],
        "termination_reason": final["termination_reason"],
    }
    with open(final_state_path, "w", encoding="utf-8") as f:
        json.dump(final_state_output, f, indent=2)

    # Human-readable summary.
    num_battles = sum(1 for e in engine.events if e.get("type") == "battle_resolved")
    survivors = [p for p in personas if not p.is_eliminated()]
    print("=== Starclash - run summary ===")
    print(f"Room: {room_name}")
    print(f"Seed: {args.seed}  Brain: {args.brain}  Ticks run: {engine.tick}/{args.max_ticks}")
    print(f"Termination reason: {final['termination_reason']}")
    print(f"Battles resolved: {num_battles}")
    if len(survivors) == 1:
        winner = survivors[0]
        print(
            f"Winner: {winner.display_name} ({winner.id}) with {winner.stars} stars, "
            f"at ({winner.x:.1f}, {winner.y:.1f})"
        )
    else:
        print(f"Survivors ({len(survivors)}):")
        for p in sorted(survivors, key=lambda x: -x.stars):
            print(
                f"  - {p.display_name} ({p.id}): {p.stars} stars, {len(p.hand)} cards left, "
                f"at ({p.x:.1f}, {p.y:.1f})"
            )
    eliminated = [p for p in personas if p.is_eliminated()]
    if eliminated:
        print(f"Eliminated: {', '.join(p.display_name for p in eliminated)}")
    print(f"Wrote: {game_log_path}")
    print(f"Wrote: {final_state_path}")


if __name__ == "__main__":
    main()
