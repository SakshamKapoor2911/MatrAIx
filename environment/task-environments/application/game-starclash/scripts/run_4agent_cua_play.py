#!/usr/bin/env python
"""Run a 4-persona CUA match with one pilot process per persona.

Orchestrates (in one OS process tree kept alive until the match ends):

  1. FileBridgeBrain engine loop (same as run_arena_live --brain cua)
  2. bridge_cua_responder (Playwright screens + real click execution)
  3. Four persona_cua_pilot threads (one screen / persona)

Stops when the engine terminates OR every active persona has spent all
cards (hand empty), whichever comes first after at least one battle.

Example (from repo root)::

    python application/tasks/game-starclash/scripts/run_4agent_cua_play.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import observations  # noqa: E402
from engine import ArenaEngine, PersonaState  # noqa: E402
from persona_cua_pilot import run_pilot  # noqa: E402
from render_observation import _sync_preview_assets, render_spectator_html  # noqa: E402
from run_arena import build_brain, load_personas, load_yaml, persona_summary, resolve_room_name  # noqa: E402


def _all_hands_empty(engine: ArenaEngine) -> bool:
    active = [p for p in engine.personas.values() if not p.is_eliminated()]
    if not active:
        return True
    return all(len(p.hand) == 0 for p in active)


def _current_final_state(engine: ArenaEngine) -> Dict[str, Any]:
    return {
        pid: {
            "stars": engine.personas[pid].stars,
            "eliminated": engine.personas[pid].is_eliminated(),
            "final_hand_size": len(engine.personas[pid].hand),
            "x": engine.personas[pid].x,
            "y": engine.personas[pid].y,
        }
        for pid in engine.persona_order
    }


def _write_live(
    out_dir: str,
    game_log: dict,
    *,
    refresh_sec: float,
    live: bool,
) -> None:
    os.makedirs(out_dir, exist_ok=True)
    assets_prefix = _sync_preview_assets(out_dir)
    with open(os.path.join(out_dir, "game_log.json"), "w", encoding="utf-8") as fh:
        json.dump(game_log, fh, indent=2)
    html = render_spectator_html(
        game_log, inline_assets=False, asset_rel_prefix=assets_prefix
    )
    if live and refresh_sec > 0:
        tag = f'  <meta http-equiv="refresh" content="{refresh_sec}">\n'
        html = html.replace("</head>", tag + "</head>", 1)
    with open(os.path.join(out_dir, "spectator_live.html"), "w", encoding="utf-8") as fh:
        fh.write(html)


def main() -> None:
    parser = argparse.ArgumentParser(description="4-agent CUA Starclash play session.")
    parser.add_argument(
        "--map",
        default=os.path.join(_SCRIPT_DIR, "..", "input", "ship_map.yaml"),
    )
    parser.add_argument(
        "--crew",
        default=os.path.join(_SCRIPT_DIR, "..", "input", "crew_manifest_meticulous.yaml"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-ticks", type=int, default=48)
    parser.add_argument(
        "--out",
        default=os.path.join(_SCRIPT_DIR, "_sample_output", "cua_4agent_play"),
    )
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--serve", type=int, default=8765)
    parser.add_argument(
        "--headed",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show 4 Chromium cockpit windows (default: on). Use --no-headed for headless.",
    )
    parser.add_argument(
        "--single-window",
        action="store_true",
        help="One Chromium window for all personas instead of one-per-persona.",
    )
    parser.add_argument("--cua-timeout", type=float, default=45.0)
    parser.add_argument(
        "--response-only",
        action="store_true",
        help="Pilots write response JSON only (no click primitives).",
    )
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out)
    bridge_dir = os.path.join(out_dir, "bridge")
    os.makedirs(bridge_dir, exist_ok=True)
    # Clean prior bridge traffic
    for name in os.listdir(bridge_dir):
        path = os.path.join(bridge_dir, name)
        try:
            if os.path.isdir(path):
                import shutil

                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError:
            pass

    repo_root = _SCRIPT_DIR
    for _ in range(6):
        if os.path.isdir(os.path.join(repo_root, "persona", "datasets")):
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
    personas: List[PersonaState] = load_personas(crew_manifest, repo_root, seed=args.seed)

    if len(personas) != 4:
        print(f"[warn] expected 4 personas, got {len(personas)}", flush=True)

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

    os.environ["ARENA_BRIDGE_DIR"] = bridge_dir

    # --- CUA responder subprocess (one headed window per persona by default) ---
    cua_cmd = [
        sys.executable,
        os.path.join(_SCRIPT_DIR, "bridge_cua_responder.py"),
        "--bridge-dir",
        bridge_dir,
        "--timeout",
        str(args.cua_timeout),
    ]
    if args.headed:
        cua_cmd.append("--headed")
    if args.single_window:
        cua_cmd.append("--single-window")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    cua_proc = subprocess.Popen(cua_cmd, env=env, cwd=_SCRIPT_DIR)
    print(
        f"[orch] CUA responder pid={cua_proc.pid} headed={args.headed} "
        f"multi_window={args.headed and not args.single_window}",
        flush=True,
    )

    # --- 4 persona pilot threads ---
    pilot_threads: List[threading.Thread] = []
    stop_idle = 99999.0  # keep flying until orchestrator exits

    def _start_pilot(persona_id: str, seed: int) -> threading.Thread:
        def _target() -> None:
            try:
                run_pilot(
                    bridge_dir,
                    persona_id,
                    seed=seed,
                    poll_interval=0.12,
                    prefer_primitives=not args.response_only,
                    idle_exit_sec=stop_idle,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[orch] pilot {persona_id} crashed: {exc}", flush=True)

        t = threading.Thread(target=_target, name=f"pilot-{persona_id}", daemon=True)
        t.start()
        return t

    for idx, persona in enumerate(personas):
        pilot_threads.append(_start_pilot(persona.id, args.seed + 10 + idx))
        print(f"[orch] pilot thread for persona {persona.id} ({persona.display_name})", flush=True)

    brain = build_brain("bridge", args.seed)

    def brain_fn(persona: PersonaState, observation: dict) -> dict:
        return brain.decide(observation)

    httpd = None
    if args.serve:
        from run_arena_live import _start_static_server

        os.makedirs(out_dir, exist_ok=True)
        httpd = _start_static_server(out_dir, args.serve)
        print(f"[orch] spectator http://127.0.0.1:{args.serve}/spectator_live.html", flush=True)

    def snapshot(*, in_progress: bool, reason: Optional[str] = None) -> dict:
        if in_progress:
            termination = None
        else:
            termination = reason or (
                "one_survivor"
                if len(engine.active_personas()) <= 1
                else ("all_cards_spent" if _all_hands_empty(engine) else "max_ticks")
            )
        return {
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
            "final_state": _current_final_state(engine),
            "termination_reason": termination,
            "live_tick": engine.tick,
        }

    stop_reason: Optional[str] = None
    try:
        while not engine.is_done():
            engine.run_tick(brain_fn)
            hands = {
                pid: len(engine.personas[pid].hand) for pid in engine.persona_order
            }
            battles = sum(1 for e in engine.events if e.get("type") == "battle_resolved")
            print(
                f"[orch] tick {engine.tick}/{args.max_ticks} "
                f"battles={battles} hands={hands} survivors={len(engine.active_personas())}",
                flush=True,
            )
            _write_live(out_dir, snapshot(in_progress=True), refresh_sec=1.0, live=True)

            if battles > 0 and _all_hands_empty(engine):
                stop_reason = "all_cards_spent"
                print("[orch] all cards spent — stopping", flush=True)
                break

            if args.delay > 0:
                time.sleep(args.delay)

        final = snapshot(in_progress=False, reason=stop_reason)
        _write_live(out_dir, final, refresh_sec=1.0, live=False)
        with open(os.path.join(out_dir, "final_state.json"), "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "final_state": final["final_state"],
                    "termination_reason": final["termination_reason"],
                },
                fh,
                indent=2,
            )

        battles = sum(1 for e in engine.events if e.get("type") == "battle_resolved")
        print("=== 4-agent CUA play complete ===", flush=True)
        print(f"Ticks: {engine.tick}  Battles: {battles}", flush=True)
        print(f"Termination: {final['termination_reason']}", flush=True)
        print(f"Final hands: { {pid: s['final_hand_size'] for pid, s in final['final_state'].items()} }", flush=True)
        print(f"Artifacts: {out_dir}", flush=True)
    finally:
        if hasattr(brain, "close"):
            try:
                brain.close()
            except Exception:
                pass
        if cua_proc.poll() is None:
            cua_proc.terminate()
            try:
                cua_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cua_proc.kill()
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                pass


if __name__ == "__main__":
    main()
