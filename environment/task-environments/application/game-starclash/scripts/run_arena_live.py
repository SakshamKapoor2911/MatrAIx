#!/usr/bin/env python
"""Step the arena tick-by-tick and refresh a live spectator page.

Brain modes:
  mock    In-process MockArenaBrain (no API key, not computer-use).
  bridge  External mock responder (file handshake, not computer-use).
  cua     Real Playwright computer-use via ``bridge_cua_responder.py``;
          external pilot(s) write ``primitives_<n>.json`` or
          ``response_<n>.json`` into the bridge dir (no in-process API key).
  vision  In-process ``BrowserVisionBrain`` (Playwright + Claude vision;
          needs ``ANTHROPIC_API_KEY``).

Example (4 meticulous personas, watch in browser):
    python run_arena_live.py \\
        --map ../input/ship_map.yaml \\
        --crew ../input/crew_manifest_meticulous.yaml \\
        --brain mock --seed 42 --max-ticks 16 \\
        --delay 1.2 --serve 8765

Open http://127.0.0.1:8765/spectator_live.html — the page auto-refreshes while
the match is in progress, then stops refreshing when the run completes.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import observations  # noqa: E402
from engine import ArenaEngine, PersonaState  # noqa: E402
from render_observation import _sync_preview_assets, render_spectator_html  # noqa: E402
from run_arena import build_brain, load_personas, load_yaml, persona_summary, resolve_room_name  # noqa: E402


def _inject_live_refresh(html: str, refresh_sec: float, *, live: bool) -> str:
    if not live or refresh_sec <= 0:
        return html
    tag = f'  <meta http-equiv="refresh" content="{refresh_sec}">\n'
    marker = "</head>"
    if marker in html:
        return html.replace(marker, tag + marker, 1)
    return tag + html


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


def _write_live_artifacts(
    out_dir: str,
    game_log: dict,
    *,
    refresh_sec: float,
    live: bool,
) -> None:
    os.makedirs(out_dir, exist_ok=True)
    assets_prefix = _sync_preview_assets(out_dir)
    spectator_path = os.path.join(out_dir, "spectator_live.html")
    game_log_path = os.path.join(out_dir, "game_log.json")

    with open(game_log_path, "w", encoding="utf-8") as fh:
        json.dump(game_log, fh, indent=2)

    html = render_spectator_html(
        game_log,
        inline_assets=False,
        asset_rel_prefix=assets_prefix,
    )
    html = _inject_live_refresh(html, refresh_sec, live=live)
    with open(spectator_path, "w", encoding="utf-8") as fh:
        fh.write(html)


def _start_static_server(directory: str, port: int) -> http.server.HTTPServer:
    class _QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    httpd = http.server.HTTPServer(("127.0.0.1", port), _QuietHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def _spawn_bridge_responder(bridge_dir: str, seed: int) -> subprocess.Popen:
    responder = os.path.join(_SCRIPT_DIR, "bridge_responder.py")
    env = os.environ.copy()
    env["ARENA_BRIDGE_DIR"] = bridge_dir
    return subprocess.Popen(
        [sys.executable, responder, "--bridge-dir", bridge_dir, "--seed", str(seed)],
        env=env,
    )


def _spawn_cua_responder(bridge_dir: str, *, headed: bool, timeout: float) -> subprocess.Popen:
    responder = os.path.join(_SCRIPT_DIR, "bridge_cua_responder.py")
    env = os.environ.copy()
    env["ARENA_BRIDGE_DIR"] = bridge_dir
    cmd = [
        sys.executable,
        responder,
        "--bridge-dir",
        bridge_dir,
        "--timeout",
        str(timeout),
    ]
    if headed:
        cmd.append("--headed")
    return subprocess.Popen(cmd, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run arena with live spectator refresh.")
    parser.add_argument("--map", required=True)
    parser.add_argument("--crew", required=True)
    parser.add_argument(
        "--brain",
        choices=["mock", "bridge", "cua", "vision"],
        default="mock",
        help="mock/bridge=fast smoke; cua=real Playwright + external subagents; vision=Claude CUA",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-ticks", type=int, default=16)
    parser.add_argument("--out", default=os.path.join(_SCRIPT_DIR, "_sample_output", "live_run"))
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between ticks")
    parser.add_argument("--refresh", type=float, default=1.0, help="Spectator HTML auto-refresh interval")
    parser.add_argument("--serve", type=int, default=0, help="Serve --out on this port (e.g. 8765)")
    parser.add_argument(
        "--bridge-dir",
        default=None,
        help="Bridge directory for --brain bridge|cua (default: <out>/bridge)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show Chromium during --brain cua (watch real clicks)",
    )
    parser.add_argument(
        "--cua-timeout",
        type=float,
        default=300.0,
        help="Seconds bridge_cua_responder waits per subagent decision",
    )
    args = parser.parse_args()

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
    personas: List[PersonaState] = load_personas(crew_manifest, repo_root, seed=args.seed)

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

    bridge_proc: subprocess.Popen | None = None
    bridge_dir = args.bridge_dir or os.path.join(args.out, "bridge")
    engine_brain_kind = args.brain
    if args.brain in ("bridge", "cua"):
        os.makedirs(bridge_dir, exist_ok=True)
        os.environ["ARENA_BRIDGE_DIR"] = bridge_dir
        engine_brain_kind = "bridge"
        if args.brain == "bridge":
            bridge_proc = _spawn_bridge_responder(bridge_dir, args.seed)
            print(f"[live] mock bridge responder pid={bridge_proc.pid} dir={bridge_dir}")
        else:
            bridge_proc = _spawn_cua_responder(
                bridge_dir, headed=args.headed, timeout=args.cua_timeout
            )
            print(
                f"[live] CUA bridge responder pid={bridge_proc.pid} dir={bridge_dir} "
                f"headed={args.headed} — launch external pilot(s) to process cua_*/TASK.md"
            )

    brain: Any = None
    brain = build_brain(engine_brain_kind, args.seed)

    def brain_fn(persona: PersonaState, observation: dict) -> dict:
        return brain.decide(observation)

    httpd: http.server.HTTPServer | None = None
    if args.serve:
        os.makedirs(args.out, exist_ok=True)
        httpd = _start_static_server(args.out, args.serve)
        print(f"[live] spectator: http://127.0.0.1:{args.serve}/spectator_live.html")

    def snapshot(*, in_progress: bool) -> dict:
        termination = None if in_progress else (
            "one_survivor" if len(engine.active_personas()) <= 1 else "max_ticks"
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

    try:
        while not engine.is_done():
            engine.run_tick(brain_fn)
            _write_live_artifacts(
                args.out,
                snapshot(in_progress=True),
                refresh_sec=args.refresh,
                live=True,
            )
            print(
                f"[live] tick {engine.tick}/{args.max_ticks} "
                f"events={len(engine.events)} survivors={len(engine.active_personas())}",
                flush=True,
            )
            if args.delay > 0:
                time.sleep(args.delay)

        final_log = snapshot(in_progress=False)
        _write_live_artifacts(
            args.out,
            final_log,
            refresh_sec=args.refresh,
            live=False,
        )

        final_state_path = os.path.join(args.out, "final_state.json")
        with open(final_state_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "final_state": final_log["final_state"],
                    "termination_reason": final_log["termination_reason"],
                },
                fh,
                indent=2,
            )

        num_battles = sum(1 for e in engine.events if e.get("type") == "battle_resolved")
        print("=== Live run complete ===")
        print(f"Ticks: {engine.tick}/{args.max_ticks}  Battles: {num_battles}")
        print(f"Termination: {final_log['termination_reason']}")
        print(f"Artifacts: {args.out}")
        if args.serve:
            print(f"Replay: http://127.0.0.1:{args.serve}/spectator_live.html")
    finally:
        if brain is not None and hasattr(brain, "close"):
            try:
                brain.close()
            except Exception:
                pass
        if bridge_proc is not None:
            bridge_proc.terminate()
            try:
                bridge_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                bridge_proc.kill()
        if httpd is not None:
            httpd.shutdown()


if __name__ == "__main__":
    main()