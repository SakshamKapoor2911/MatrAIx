#!/usr/bin/env python
"""One-persona computer-use pilot for the CUA bridge.

Watches ``ARENA_BRIDGE_DIR/cua_<n>/`` folders. When a bundle belongs to
``--persona-id``, decides a legal action and writes either:

  * ``primitives_<n>.json`` — click coordinates for Playwright CUA, or
  * ``response_<n>.json`` — finished action dict (fallback).

Policy is social-then-duel: agents chat / approach before challenging so
matches look like a multiplayer room, not instant combat spam.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

_VIEWPORT_W = 1024
_VIEWPORT_H = 768

# Floor UV within nebula_backdrop (full room art is shown; coords map here).
_FLOOR_UV = (0.10, 0.14, 0.90, 0.86)

_HOTBAR_Y = 720
_HOTBAR = {
    "say": (360, _HOTBAR_Y),
    "move": (455, _HOTBAR_Y),
    "challenge": (550, _HOTBAR_Y),
    "duel": (550, _HOTBAR_Y),
    "private_message": (645, _HOTBAR_Y),
    "dm": (645, _HOTBAR_Y),
    "wait": (740, _HOTBAR_Y),
}
_ACCEPT_XY = (430, 400)
_DECLINE_XY = (594, 400)
_CARD_Y = 640
_CARD_XS = {
    "Rock": 360,
    "Paper": 512,
    "Scissors": 664,
}

_CHAT_LINES = [
    "Anyone up for a friendly match?",
    "Hey crew — cards are warm.",
    "Nice flying. Want a duel?",
    "I'll trade a star if you can beat me.",
    "Let's settle this with Rock Paper Scissors.",
    "Who's brave enough?",
    "Come closer if you dare.",
    "Good luck out there.",
]


def _list_cua_seqs(bridge_dir: str) -> List[int]:
    seqs: List[int] = []
    for path in glob.glob(os.path.join(bridge_dir, "cua_*")):
        base = os.path.basename(path)
        if not base.startswith("cua_"):
            continue
        try:
            seqs.append(int(base.replace("cua_", "")))
        except ValueError:
            continue
    return sorted(seqs)


def _load_json(path: str) -> Optional[dict]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError, PermissionError):
        return None


def _write_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def _room_art_rect(vw: int = _VIEWPORT_W, vh: int = _VIEWPORT_H) -> Tuple[float, float, float, float]:
    """Contain-fit of 1280x720 room art into the viewport."""
    src_w, src_h = 1280.0, 720.0
    scale = min(vw / src_w, vh / src_h)
    dw, dh = src_w * scale, src_h * scale
    return (vw - dw) / 2, (vh - dh) / 2, dw, dh


def _play_field(viewport_w: int = _VIEWPORT_W, viewport_h: int = _VIEWPORT_H) -> Tuple[float, float, float]:
    """Floor square inside full room art — matches render_observation.playField."""
    ax, ay, aw, ah = _room_art_rect(viewport_w, viewport_h)
    u0, v0, u1, v1 = _FLOOR_UV
    fx = ax + aw * u0
    fy = ay + ah * v0
    fw = aw * (u1 - u0)
    fh = ah * (v1 - v0)
    size = min(fw, fh)
    ox = fx + (fw - size) / 2
    oy = fy + (fh - size) / 2
    return size, ox, oy


def _room_to_canvas(x: float, y: float, room_w: float, room_h: float) -> Tuple[int, int]:
    size, ox, oy = _play_field()
    inset = max(8.0, size * 0.03)
    usable = size - inset * 2
    px = ox + inset + (x / max(room_w, 1e-6)) * usable
    py = oy + inset + (y / max(room_h, 1e-6)) * usable
    return int(px), int(py)


def _decide(observation: dict, rng: random.Random, memory: Dict[str, Any]) -> dict:
    """Social-then-duel policy: chat / approach, then challenge and play cards."""
    menu = observation.get("action_menu", {}) or {}
    actions: List[str] = list(menu.get("actions") or [])
    self_state = observation.get("self", {}) or {}
    tick = int(observation.get("tick", memory.get("last_tick", 0)) or 0)
    memory["last_tick"] = tick

    if "play_card" in actions:
        available = list(menu.get("available_cards") or self_state.get("hand") or ["Rock"])
        # Mild mix: sometimes counter market if present, else random.
        raw_market = observation.get("market_signal")
        if isinstance(raw_market, dict):
            market = raw_market.get("leaning") or raw_market.get("signal")
        elif isinstance(raw_market, str):
            market = raw_market
        else:
            market = None
        market_s = str(market or "")
        if "Rock" in market_s and "Paper" in available and rng.random() < 0.55:
            card = "Paper"
        elif "Paper" in market_s and "Scissors" in available and rng.random() < 0.55:
            card = "Scissors"
        elif "Scissors" in market_s and "Rock" in available and rng.random() < 0.55:
            card = "Rock"
        else:
            card = rng.choice(available)
        return {
            "action": "play_card",
            "card": card,
            "reasoning": f"Playing {card} in the duel.",
        }

    if "accept" in actions and "decline" in actions:
        hand = list(self_state.get("hand") or [])
        # Accept most challenges when holding cards; occasional decline for flavor.
        if hand and rng.random() < 0.88:
            return {"action": "accept", "reasoning": "Accepting the challenge."}
        return {"action": "decline", "reasoning": "Not this time." if hand else "No cards left."}

    targets = list(menu.get("challengeable_targets") or [])
    nearby_ids = [
        str(r.get("id"))
        for r in (observation.get("arena_roster") or [])
        if r.get("nearby") and not r.get("is_self") and not r.get("eliminated")
    ]

    # Chat when near others before (or instead of) immediately duelling.
    if "say" in actions and nearby_ids:
        last_chat = int(memory.get("last_chat_tick", -99))
        if tick - last_chat >= 2 and rng.random() < 0.45:
            memory["last_chat_tick"] = tick
            return {
                "action": "say",
                "text": rng.choice(_CHAT_LINES),
                "reasoning": "Banter with nearby crew before fighting.",
            }

    if "private_message" in actions:
        pm_targets = list(menu.get("private_message_targets") or nearby_ids)
        if pm_targets and rng.random() < 0.12:
            tid = rng.choice(pm_targets)
            return {
                "action": "private_message",
                "target_id": tid,
                "text": rng.choice(["Ready when you are.", "Good luck.", "Let's trade stars."]),
                "reasoning": f"Private note to {tid}.",
            }

    if "challenge" in actions and targets and self_state.get("hand"):
        # Prefer challenging someone we already chatted near; otherwise still duel.
        last_chat = int(memory.get("last_chat_tick", -99))
        if tick - last_chat < 1 and rng.random() < 0.35:
            # Just spoke — wait a beat.
            if "wait" in actions:
                return {"action": "wait", "reasoning": "Pause after talking."}
        target_id = rng.choice(targets)
        return {
            "action": "challenge",
            "target_id": target_id,
            "reasoning": f"Challenging {target_id} to a duel.",
        }

    if "move" in actions:
        me_x = float(self_state.get("x", 10.0))
        me_y = float(self_state.get("y", 10.0))
        bounds = menu.get("movable_bounds") or {}
        max_d = float(bounds.get("max_distance", 2.0))
        room_w = float(bounds.get("room_width", 20.0))
        room_h = float(bounds.get("room_height", 20.0))

        best = None
        best_dist = 1e9
        for row in observation.get("arena_roster") or []:
            if row.get("is_self") or row.get("eliminated"):
                continue
            if row.get("x") is None or row.get("y") is None:
                continue
            dx = float(row["x"]) - me_x
            dy = float(row["y"]) - me_y
            dist = math.hypot(dx, dy)
            if dist < best_dist and dist > 0.05:
                best_dist = dist
                best = (dx, dy, row.get("id"))

        if best is not None:
            dx, dy, tid = best
            length = math.hypot(dx, dy) or 1.0
            step = min(max_d, length)
            tx = min(max(me_x + (dx / length) * step, 0.0), room_w)
            ty = min(max(me_y + (dy / length) * step, 0.0), room_h)
            return {
                "action": "move",
                "target_x": tx,
                "target_y": ty,
                "reasoning": f"Walking toward {tid} to talk or duel.",
            }

        angle = rng.uniform(0, 2 * math.pi)
        step = max_d * 0.8
        tx = min(max(me_x + step * math.cos(angle), 0.0), room_w)
        ty = min(max(me_y + step * math.sin(angle), 0.0), room_h)
        return {"action": "move", "target_x": tx, "target_y": ty, "reasoning": "Exploring the room."}

    if "say" in actions and rng.random() < 0.2:
        return {
            "action": "say",
            "text": rng.choice(_CHAT_LINES),
            "reasoning": "Public chat while searching.",
        }

    if "wait" in actions:
        return {"action": "wait", "reasoning": "Holding position."}

    if actions:
        return {"action": actions[0], "reasoning": "Fallback legal action."}
    return {"action": "wait", "reasoning": "No legal actions listed."}


def _card_click_xy(observation: dict, card: str) -> Tuple[int, int]:
    hand = list((observation.get("self") or {}).get("hand") or [])
    if not hand:
        return 512, _CARD_Y
    try:
        idx = hand.index(card)
    except ValueError:
        idx = 0
    n = len(hand)
    spacing = 124
    total_w = spacing * max(n - 1, 0)
    start_x = 512 - total_w / 2
    x = int(start_x + idx * spacing)
    return x, _CARD_Y


def _decision_to_primitives(decision: dict, observation: dict) -> Optional[dict]:
    action = decision.get("action")
    steps: List[Dict[str, Any]] = []

    if action == "play_card":
        card = str(decision.get("card", "Rock"))
        x, y = _card_click_xy(observation, card)
        steps.append({"type": "click_at", "x": x, "y": y})
        steps.append({"type": "done"})
        return {"steps": steps}

    if action == "accept":
        steps.append({"type": "click_at", "x": _ACCEPT_XY[0], "y": _ACCEPT_XY[1]})
        steps.append({"type": "done"})
        return {"steps": steps}

    if action == "decline":
        steps.append({"type": "click_at", "x": _DECLINE_XY[0], "y": _DECLINE_XY[1]})
        steps.append({"type": "done"})
        return {"steps": steps}

    if action == "wait":
        x, y = _HOTBAR["wait"]
        steps.append({"type": "click_at", "x": x, "y": y})
        steps.append({"type": "done"})
        return {"steps": steps}

    if action == "say":
        x, y = _HOTBAR["say"]
        steps.append({"type": "click_at", "x": x, "y": y})
        steps.append({"type": "type_text", "text": str(decision.get("text") or "...")})
        steps.append({"type": "click_at", "x": 620, "y": 640})
        steps.append({"type": "done"})
        return {"steps": steps}

    if action == "private_message":
        x, y = _HOTBAR["dm"]
        steps.append({"type": "click_at", "x": x, "y": y})
        # Pick first chip area approx then type
        steps.append({"type": "click_at", "x": 420, "y": 560})
        steps.append({"type": "type_text", "text": str(decision.get("text") or "hey")})
        steps.append({"type": "click_at", "x": 620, "y": 640})
        steps.append({"type": "done"})
        return {"steps": steps}

    if action == "move":
        x, y = _HOTBAR["move"]
        steps.append({"type": "click_at", "x": x, "y": y})
        bounds = (observation.get("action_menu") or {}).get("movable_bounds") or {}
        room_w = float(bounds.get("room_width", 20.0))
        room_h = float(bounds.get("room_height", 20.0))
        tx = float(decision.get("target_x", 10.0))
        ty = float(decision.get("target_y", 10.0))
        cx, cy = _room_to_canvas(tx, ty, room_w, room_h)
        steps.append({"type": "click_at", "x": cx, "y": cy})
        steps.append({"type": "done"})
        return {"steps": steps}

    if action == "challenge":
        x, y = _HOTBAR["duel"]
        steps.append({"type": "click_at", "x": x, "y": y})
        target_id = decision.get("target_id")
        room = observation.get("room_bounds") or {}
        room_w = float(room.get("width", 20.0))
        room_h = float(room.get("height", 20.0))
        for row in observation.get("arena_roster") or []:
            if row.get("id") == target_id and row.get("x") is not None:
                cx, cy = _room_to_canvas(float(row["x"]), float(row["y"]), room_w, room_h)
                steps.append({"type": "click_at", "x": cx, "y": cy})
                steps.append({"type": "done"})
                return {"steps": steps}
        return None

    return None


def run_pilot(
    bridge_dir: str,
    persona_id: str,
    *,
    seed: int,
    poll_interval: float,
    prefer_primitives: bool,
    idle_exit_sec: float,
) -> None:
    rng = random.Random(seed)
    handled: Set[int] = set()
    memory: Dict[str, Any] = {}
    last_activity = time.monotonic()
    print(
        f"[pilot {persona_id}] watching {os.path.abspath(bridge_dir)} "
        f"(primitives={prefer_primitives})",
        flush=True,
    )

    while True:
        found = False
        for seq in _list_cua_seqs(bridge_dir):
            if seq in handled:
                continue
            cua_dir = os.path.join(bridge_dir, f"cua_{seq}")
            obs_path = os.path.join(cua_dir, "observation.json")
            task_path = os.path.join(cua_dir, "TASK.md")
            if not os.path.isfile(obs_path):
                continue
            if not os.path.isfile(os.path.join(cua_dir, "screenshot.png")):
                continue
            if not os.path.isfile(task_path):
                continue

            response_path = os.path.join(bridge_dir, f"response_{seq}.json")
            primitives_path = os.path.join(bridge_dir, f"primitives_{seq}.json")
            if os.path.isfile(response_path) or os.path.isfile(primitives_path):
                handled.add(seq)
                continue

            observation = _load_json(obs_path)
            if not observation:
                continue
            self_id = str((observation.get("self") or {}).get("id", ""))
            if self_id != str(persona_id):
                continue

            found = True
            last_activity = time.monotonic()
            decision = _decide(observation, rng, memory)
            print(
                f"[pilot {persona_id}] seq={seq} action={decision.get('action')} "
                f"detail={ {k: v for k, v in decision.items() if k != 'reasoning'} }",
                flush=True,
            )

            if prefer_primitives:
                prims = _decision_to_primitives(decision, observation)
                if prims is not None:
                    _write_json(primitives_path, prims)
                    for _ in range(160):
                        if os.path.isfile(response_path):
                            break
                        time.sleep(0.05)
            if not os.path.isfile(response_path):
                _write_json(response_path, decision)
            handled.add(seq)

        if not found:
            if idle_exit_sec > 0 and (time.monotonic() - last_activity) > idle_exit_sec:
                if handled:
                    print(
                        f"[pilot {persona_id}] idle timeout — exiting ({len(handled)} turns)",
                        flush=True,
                    )
                    return
            time.sleep(poll_interval)
        else:
            time.sleep(0.05)


def main() -> None:
    parser = argparse.ArgumentParser(description="Single-persona CUA pilot for Starclash.")
    parser.add_argument("--persona-id", required=True)
    parser.add_argument("--bridge-dir", default=os.environ.get("ARENA_BRIDGE_DIR"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--poll-interval", type=float, default=0.15)
    parser.add_argument("--prefer-primitives", action="store_true", default=True)
    parser.add_argument("--response-only", action="store_true")
    parser.add_argument("--idle-exit-sec", type=float, default=90.0)
    args = parser.parse_args()

    if not args.bridge_dir:
        print("ERROR: set ARENA_BRIDGE_DIR or pass --bridge-dir", file=sys.stderr)
        sys.exit(1)

    run_pilot(
        args.bridge_dir,
        args.persona_id,
        seed=args.seed,
        poll_interval=args.poll_interval,
        prefer_primitives=not args.response_only,
        idle_exit_sec=args.idle_exit_sec,
    )


if __name__ == "__main__":
    main()
