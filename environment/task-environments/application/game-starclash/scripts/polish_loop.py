#!/usr/bin/env python
"""Capture harness for the Starclash indie polish agent loop.

Usage (from task root)::

    python scripts/polish_loop.py capture --out scripts/_sample_output/polish_loop
    python scripts/polish_loop.py init-report --out scripts/_sample_output/polish_loop

See ~/.grok/skills/game-starclash-polish/SKILL.md for the full agent loop.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from render_observation import (  # noqa: E402
    _asset_data_uri,
    render_observation_html,
    render_spectator_html,
)

# Clear asset cache so re-captures pick up new art
try:
    _asset_data_uri.cache_clear()
except Exception:
    pass


def _find_sample_game() -> Tuple[Path, Path]:
    """Return (game_log.json, bridge_dir) preferring latest live runs."""
    sample = _SCRIPT_DIR / "_sample_output"
    candidates = [
        sample / "cua_live_watch",
        sample / "cua_live_qa",
        sample / "cua_4agent_play",
        sample / "verify_mock",
    ]
    for root in candidates:
        log = root / "game_log.json"
        bridge = root / "bridge"
        if log.is_file():
            return log, bridge
    raise FileNotFoundError(
        "No sample game_log.json found under scripts/_sample_output/. "
        "Run a mock or CUA match first."
    )


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _pick_observations(bridge: Path) -> Dict[str, dict]:
    """Pick free / battle / challenge observations from CUA bridge if present."""
    picked: Dict[str, dict] = {}
    if not bridge.is_dir():
        return picked

    def seq_key(name: str) -> int:
        try:
            return int(name.replace("cua_", ""))
        except ValueError:
            return 10**9

    for name in sorted(os.listdir(bridge), key=seq_key):
        obs_path = bridge / name / "observation.json"
        if not obs_path.is_file():
            continue
        obs = _load_json(obs_path)
        acts = (obs.get("action_menu") or {}).get("actions") or []
        if "play_card" in acts and "battle" not in picked:
            picked["battle"] = obs
        elif "accept" in acts and "decline" in acts and "challenge" not in picked:
            picked["challenge"] = obs
        elif "move" in acts and "free" not in picked:
            picked["free"] = obs
        if len(picked) >= 3:
            break
    return picked


def _synthetic_free_from_log(game_log: dict) -> dict:
    """Build a minimal free-action observation from game_log for preview."""
    personas = game_log.get("personas") or []
    spawn = game_log.get("spawn_positions") or {}
    final = game_log.get("final_state") or {}
    roster = []
    self_id = personas[0]["id"] if personas else "0042"
    for p in personas:
        pid = p["id"]
        st = final.get(pid) or {}
        pos = spawn.get(pid) or {"x": 10.0, "y": 10.0}
        roster.append(
            {
                "id": pid,
                "display_name": p.get("display_name", pid),
                "short_name": (p.get("display_name") or pid).split()[0],
                "stars": st.get("stars", 3),
                "x": st.get("x", pos.get("x", 10.0)),
                "y": st.get("y", pos.get("y", 10.0)),
                "eliminated": st.get("eliminated", False),
                "is_self": pid == self_id,
                "nearby": pid != self_id,
            }
        )
    self_row = next(r for r in roster if r["is_self"])
    return {
        "self": {
            "id": self_id,
            "display_name": self_row["display_name"],
            "stars": self_row["stars"],
            "hand": ["Rock", "Paper", "Scissors", "Paper"],
            "x": self_row["x"],
            "y": self_row["y"],
            "traits": {},
        },
        "current_room": {"name": game_log.get("room_name", "Main Chat Room")},
        "room_bounds": {
            "width": game_log.get("room_width", 20.0),
            "height": game_log.get("room_height", 20.0),
            "proximity_radius": 3.0,
            "max_move_distance": 2.0,
        },
        "nearby_occupants": [r for r in roster if not r["is_self"] and r.get("nearby")],
        "arena_roster": roster,
        "arena_card_counts": game_log.get("initial_card_counts")
        or {"Rock": 6, "Paper": 5, "Scissors": 5},
        "recent_chat": [],
        "private_chat_with_me": [],
        "tick": 0,
        "max_ticks": game_log.get("max_ticks", 48),
        "action_menu": {
            "actions": ["say", "wait", "move", "challenge", "private_message"],
            "challengeable_targets": [
                r["id"] for r in roster if not r["is_self"] and not r["eliminated"]
            ],
            "private_message_targets": [
                r["id"] for r in roster if not r["is_self"] and not r["eliminated"]
            ],
            "movable_bounds": {
                "max_distance": 2.0,
                "room_width": game_log.get("room_width", 20.0),
                "room_height": game_log.get("room_height", 20.0),
            },
        },
    }


def capture(out_dir: Path) -> Path:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    shots = out_dir / "shots"
    shots.mkdir(exist_ok=True)

    log_path, bridge = _find_sample_game()
    game_log = _load_json(log_path)
    picked = _pick_observations(bridge)
    if "free" not in picked:
        picked["free"] = _synthetic_free_from_log(game_log)

    # HTML pages
    pages: List[Tuple[str, str, int, int]] = []
    for key in ("free", "battle", "challenge"):
        if key not in picked:
            continue
        html = render_observation_html(picked[key], inline_assets=True)
        path = out_dir / f"agent_{key}.html"
        path.write_text(html, encoding="utf-8")
        pages.append((f"agent_{key}", str(path), 1024, 768))

    spec_html = render_spectator_html(game_log, inline_assets=True)
    spec_path = out_dir / "spectator.html"
    spec_path.write_text(spec_html, encoding="utf-8")
    pages.append(("spectator", str(spec_path), 1280, 720))
    # scale stress
    if "free" in picked:
        pages.append(("agent_free_800", str(out_dir / "agent_free.html"), 800, 600))
        pages.append(("agent_free_1920", str(out_dir / "agent_free.html"), 1920, 1080))
    pages.append(("spectator_900", str(spec_path), 900, 600))

    manifest: List[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, html_path, w, h in pages:
            page = browser.new_page(viewport={"width": w, "height": h})
            uri = "file:///" + os.path.abspath(html_path).replace("\\", "/")
            page.goto(uri)
            page.wait_for_timeout(750)
            if name.startswith("spectator"):
                try:
                    page.evaluate(
                        """() => {
                          const r = document.querySelector('input[type=range]');
                          if (r) {
                            r.value = Math.min(28, r.max || 28);
                            r.dispatchEvent(new Event('input'));
                            r.dispatchEvent(new Event('change'));
                          }
                        }"""
                    )
                    page.wait_for_timeout(400)
                except Exception:
                    pass
            scale = page.evaluate(
                "() => getComputedStyle(document.documentElement)"
                ".getPropertyValue('--ui-scale').trim()"
            )
            png = shots / f"{name}.png"
            page.screenshot(path=str(png))
            page.close()
            manifest.append(
                {
                    "name": name,
                    "viewport": f"{w}x{h}",
                    "scale": scale,
                    "path": str(png.relative_to(out_dir)).replace("\\", "/"),
                }
            )
            print(f"[capture] {name} {w}x{h} scale={scale} -> {png.name}", flush=True)
        browser.close()

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[capture] wrote {len(manifest)} shots under {shots}", flush=True)
    return out_dir


REPORT_TEMPLATE = """# Starclash — Polish Loop Report

Target: **polished indie game** (agent cockpit + spectator).

## Checklist

Score each: `pass` / `fail` / `n/a`

### Structure
- [ ] Full room art (corridors + floor)
- [ ] Agents on floor tiles (not void/corridors only)
- [ ] Auto-scale (800×600 + 1920×1080)
- [ ] No clipped HUD at design resolution

### Agent free play
- [ ] Hotbar complete; illegal actions disabled
- [ ] Crew / cards / comms aligned
- [ ] Phase banner short
- [ ] Empty comms intentional

### Agent battle
- [ ] Original top-down sprite
- [ ] Clear YOU vs Opponent plates
- [ ] Large RPS cards
- [ ] Banner not a text wall

### Agent challenge
- [ ] Focused Accept/Decline modal
- [ ] Original sprite avatar
- [ ] Note uses display name

### Spectator
- [ ] Full room + scrubber
- [ ] Side panels matched
- [ ] Labels OK when clustered (or mitigated)
- [ ] Comms readable

### Indie juice
- [ ] Distinct persona colors on map
- [ ] Tasteful micro-motion
- [ ] Cards feel like game items
- [ ] No debug strings

## Iterations

### Iteration 0 — baseline
- Date:
- Shots: `shots/`
- Failures:
- Plan (max 3):
- Result:

## Exit
- Structure/Agent/Spectator all pass?
- ≥3/4 Indie juice pass?
- Known limitations:
"""


def init_report(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "REPORT.md"
    if not report.exists():
        report.write_text(REPORT_TEMPLATE, encoding="utf-8")
        print(f"[report] created {report}", flush=True)
    else:
        print(f"[report] already exists {report}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Starclash polish loop harness")
    sub = parser.add_subparsers(dest="cmd", required=True)
    cap = sub.add_parser("capture", help="Render HTML + Playwright screenshots")
    cap.add_argument(
        "--out",
        default=str(_SCRIPT_DIR / "_sample_output" / "polish_loop"),
    )
    init = sub.add_parser("init-report", help="Write REPORT.md template")
    init.add_argument(
        "--out",
        default=str(_SCRIPT_DIR / "_sample_output" / "polish_loop"),
    )
    args = parser.parse_args()
    out = Path(args.out)
    if args.cmd == "capture":
        init_report(out)
        capture(out)
    elif args.cmd == "init-report":
        init_report(out)


if __name__ == "__main__":
    main()
