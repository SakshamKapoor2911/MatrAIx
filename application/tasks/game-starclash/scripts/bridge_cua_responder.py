#!/usr/bin/env python
"""Computer-use bridge responder for FileBridgeBrain (real Playwright clicks).

Watches ``ARENA_BRIDGE_DIR`` for ``request_<n>.json``. For each request:

  1. Renders the observation as interactive HTML (same page agents see).
  2. Loads it in a **real** Chromium session via Playwright.
  3. Saves ``cua_<n>/page.html``, ``cua_<n>/screenshot.png``, and
     ``cua_<n>/TASK.md`` so an external pilot can inspect
     the UI.
  4. Waits for either:
       - ``primitives_<n>.json`` — click/type steps to execute in the live
         browser (subagent does vision; this process does real CUA); OR
       - ``response_<n>.json`` — a finished legal action dict (subagent
         decided without this executor).
  5. After primitives, executes clicks/typing in Playwright, reads
     ``window.__lastAction``, writes ``response_<n>.json``.

When ``--headed`` and multiple personas take turns, opens **one Chromium
window per persona** (2x2 grid) so you can watch four cockpits live.

Pair with ``run_arena_live.py --brain cua`` (or ``run_4agent_cua_play.py``)
and launch external pilot(s) to process ``cua_*`` folders.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from render_observation import render_observation_html  # noqa: E402

_NAV_TIMEOUT_MS = 5_000
_ACTION_TIMEOUT_MS = 3_000
_SCREENSHOT_TIMEOUT_MS = 5_000
_VIEWPORT = {"width": 1024, "height": 768}
_WINDOW_W = 1040
_WINDOW_H = 820

_TASK_TEMPLATE = """# Arena computer-use decision #{seq}

Persona: **{persona_id}** ({display_name})

## System prompt (rules for the pilot)

You are piloting this persona in Starclash. The HTML HUD is your
**only** controller — decide by **looking and clicking**, not by inventing JSON.

**Goal:** spend your Rock/Paper/Scissors cards in duels, earn stars, survive.
Cards only leave your hand when a duel resolves. Walk close to others (inside
the amber proximity ring) before you can challenge or private-message them.
Everyone is drawn on the **room deck** (bordered square); **far** pilots are
dimmed — click MOVE then the deck, or click glowing targets after DUEL.

**UI map (click targets):**
- Bottom hotbar: SAY / MOVE / DUEL / DM / WAIT (large buttons)
- Room deck: click empty floor to MOVE (after arming MOVE or when MOVE is free);
  click a **glowing** pilot after arming DUEL to challenge
- Duel screen (Pokemon-style): big Rock / Paper / Scissors cards — click one
- Challenge modal: ACCEPT or DECLINE
- Composers: type then Send (SAY / DM)

**Hidden from UI (use observation.json if needed):** market_signal, full
traits, legal parameter lists. Prefer the screenshot + legal actions below.

## Your job

1. Open ``screenshot.png`` (and ``page.html`` if needed).
2. Perform **one** legal action for this persona.
3. Write either:
   - ``../primitives_{seq}.json`` — Playwright click/type steps (preferred), or
   - ``../response_{seq}.json`` — finished action dict.

## Legal actions (from observation)

```json
{action_menu_json}
```

## Primitive step schema

```json
{{
  "steps": [
    {{"type": "click_at", "x": 512, "y": 400}},
    {{"type": "type_text", "text": "your message"}},
    {{"type": "done"}}
  ]
}}
```

Viewport is typically 1024x768. Call ``done`` after the UI records the action.

## Direct response schema (alternative)

```json
{{"action": "wait"}}
{{"action": "move", "target_x": 10.0, "target_y": 5.0}}
{{"action": "say", "text": "..."}}
{{"action": "challenge", "target_id": "..."}}
{{"action": "play_card", "card": "Rock"}}
{{"action": "accept"}}
{{"action": "decline"}}
```

Bridge directory: ``{bridge_dir}``
"""


def _list_request_seqs(bridge_dir: str) -> List[int]:
    seqs: List[int] = []
    for path in glob.glob(os.path.join(bridge_dir, "request_*.json")):
        base = os.path.basename(path)
        try:
            seqs.append(int(base.replace("request_", "").replace(".json", "")))
        except ValueError:
            continue
    return sorted(seqs)


def _load_request(bridge_dir: str, seq: int) -> Optional[dict]:
    """Load request JSON, tolerating partial writes from the engine process."""
    path = os.path.join(bridge_dir, f"request_{seq}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        if not text.strip():
            return None
        return json.loads(text)
    except (OSError, json.JSONDecodeError):
        # Writer still flushing — try again on the next poll.
        return None


def _write_cua_bundle(
    bridge_dir: str,
    seq: int,
    observation: dict,
    html: str,
    screenshot_bytes: bytes,
) -> str:
    cua_dir = os.path.join(bridge_dir, f"cua_{seq}")
    os.makedirs(cua_dir, exist_ok=True)

    with open(os.path.join(cua_dir, "page.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    with open(os.path.join(cua_dir, "screenshot.png"), "wb") as fh:
        fh.write(screenshot_bytes)
    with open(os.path.join(cua_dir, "observation.json"), "w", encoding="utf-8") as fh:
        json.dump(observation, fh, indent=2)

    self_info = observation.get("self", {}) or {}
    menu = observation.get("action_menu", {}) or {}
    task_md = _TASK_TEMPLATE.format(
        seq=seq,
        persona_id=self_info.get("id", "?"),
        display_name=self_info.get("display_name", "?"),
        action_menu_json=json.dumps(menu, indent=2),
        bridge_dir=os.path.abspath(bridge_dir),
    )
    with open(os.path.join(cua_dir, "TASK.md"), "w", encoding="utf-8") as fh:
        fh.write(task_md)

    return cua_dir


def _execute_primitives(page: Any, steps: List[dict]) -> Optional[dict]:
    for step in steps:
        kind = step.get("type")
        if kind == "done":
            break
        if kind == "click_at":
            x, y = step.get("x"), step.get("y")
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                page.mouse.click(float(x), float(y))
                time.sleep(0.05)
            continue
        if kind == "type_text":
            text = step.get("text")
            if isinstance(text, str):
                page.keyboard.type(text)
            continue
    try:
        return page.evaluate("() => window.__lastAction")
    except Exception:
        return None


def _write_response(bridge_dir: str, seq: int, decision: dict) -> None:
    response_path = os.path.join(bridge_dir, f"response_{seq}.json")
    # Pilot may already have written the authoritative response; keep it.
    if os.path.isfile(response_path):
        return
    tmp_path = response_path + f".tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(decision, fh, indent=2)
    try:
        os.replace(tmp_path, response_path)
    except OSError:
        if os.path.isfile(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        if not os.path.isfile(response_path):
            raise


def _read_json_file(path: str) -> Optional[dict]:
    """Read a JSON file, returning None if missing, empty, locked, or partial."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        if not text.strip():
            return None
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except (OSError, PermissionError, json.JSONDecodeError):
        return None


def _wait_for_subagent_files(
    bridge_dir: str,
    seq: int,
    deadline: float,
    poll_interval_sec: float,
) -> tuple[Optional[str], Optional[dict]]:
    """Return ('primitives', dict) or ('response', dict) or (None, None).

    Prefer click primitives when present so the Playwright path runs real
    mouse input; fall back to a finished response dict when clicks are
    unavailable or fail later. Tolerates Windows file-lock races while a
    pilot is still writing ``.tmp`` -> final path.
    """
    response_path = os.path.join(bridge_dir, f"response_{seq}.json")
    primitives_path = os.path.join(bridge_dir, f"primitives_{seq}.json")

    while time.monotonic() < deadline:
        prims = _read_json_file(primitives_path)
        if prims is not None:
            return "primitives", prims
        resp = _read_json_file(response_path)
        if resp is not None:
            return "response", resp
        time.sleep(poll_interval_sec)

    prims = _read_json_file(primitives_path)
    if prims is not None:
        return "primitives", prims
    resp = _read_json_file(response_path)
    if resp is not None:
        return "response", resp
    return None, None


def _cleanup_aux(bridge_dir: str, seq: int) -> None:
    for name in (f"primitives_{seq}.json",):
        path = os.path.join(bridge_dir, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def _window_slot(slot: int) -> Tuple[int, int]:
    """2x2 grid positions for up to 4 live cockpits."""
    col = slot % 2
    row = slot // 2
    return col * _WINDOW_W, row * _WINDOW_H


class CuaBridgeResponder:
    """One Playwright cockpit window per persona (when headed)."""

    def __init__(
        self,
        bridge_dir: str,
        *,
        headed: bool,
        timeout_sec: float,
        poll_interval_sec: float,
        multi_window: bool = True,
    ) -> None:
        self.bridge_dir = bridge_dir
        self.headed = headed
        self.timeout_sec = timeout_sec
        self.poll_interval_sec = poll_interval_sec
        self.multi_window = multi_window and headed
        self._handled: Set[int] = set()
        self._playwright = None
        # Shared single-window mode
        self._browser = None
        self._context = None
        self._page = None
        # Multi-window: persona_id -> (browser, context, page, slot)
        self._cockpits: Dict[str, Dict[str, Any]] = {}
        self._next_slot = 0

    def _ensure_playwright(self) -> None:
        if self._playwright is not None:
            return
        import playwright.sync_api

        self._playwright = playwright.sync_api.sync_playwright().start()

    def _ensure_shared_page(self) -> Any:
        self._ensure_playwright()
        if self._page is not None:
            return self._page
        launch_args: List[str] = []
        if self.headed:
            launch_args = [f"--window-size={_WINDOW_W},{_WINDOW_H}", "--window-position=40,40"]
        self._browser = self._playwright.chromium.launch(
            headless=not self.headed,
            args=launch_args,
        )
        self._context = self._browser.new_context(viewport=_VIEWPORT)
        self._context.set_default_timeout(_ACTION_TIMEOUT_MS)
        self._page = self._context.new_page()
        return self._page

    def _page_for_persona(self, persona_id: str) -> Any:
        """Return a Playwright page for this persona (dedicated window if multi)."""
        if not self.multi_window:
            return self._ensure_shared_page()

        if persona_id in self._cockpits:
            return self._cockpits[persona_id]["page"]

        self._ensure_playwright()
        slot = self._next_slot
        self._next_slot += 1
        wx, wy = _window_slot(slot)
        launch_args = [
            f"--window-size={_WINDOW_W},{_WINDOW_H}",
            f"--window-position={wx},{wy}",
        ]
        browser = self._playwright.chromium.launch(
            headless=False,
            args=launch_args,
        )
        context = browser.new_context(viewport=_VIEWPORT)
        context.set_default_timeout(_ACTION_TIMEOUT_MS)
        page = context.new_page()
        # Title badge so each window is identifiable in the taskbar.
        try:
            page.evaluate(
                """(pid) => { document.title = 'Starclash · ' + pid; }""",
                persona_id,
            )
        except Exception:
            pass
        self._cockpits[persona_id] = {
            "browser": browser,
            "context": context,
            "page": page,
            "slot": slot,
        }
        print(
            f"[cua] opened cockpit window for persona {persona_id} "
            f"(slot={slot}, pos={wx},{wy})",
            flush=True,
        )
        return page

    def close(self) -> None:
        for pid, pack in list(self._cockpits.items()):
            for key in ("page", "context", "browser"):
                obj = pack.get(key)
                if obj is None:
                    continue
                try:
                    if key == "browser":
                        obj.close()
                    else:
                        obj.close()
                except Exception:
                    pass
            self._cockpits.pop(pid, None)

        for attr in ("_page", "_context", "_browser", "_playwright"):
            obj = getattr(self, attr, None)
            if obj is None:
                continue
            try:
                if attr == "_playwright":
                    obj.stop()
                else:
                    obj.close()
            except Exception:
                pass
            setattr(self, attr, None)

    def process_seq(self, seq: int) -> bool:
        if seq in self._handled:
            return False
        response_path = os.path.join(self.bridge_dir, f"response_{seq}.json")
        if os.path.isfile(response_path):
            self._handled.add(seq)
            return False

        payload = _load_request(self.bridge_dir, seq)
        if payload is None:
            return False

        observation = payload.get("observation", {})
        persona_id = str((observation.get("self") or {}).get("id", "?"))
        page = self._page_for_persona(persona_id)

        html = render_observation_html(observation)
        page.set_content(html, timeout=_NAV_TIMEOUT_MS)
        try:
            page.evaluate(
                """(title) => { document.title = title; }""",
                f"Starclash · {persona_id}",
            )
        except Exception:
            pass
        # Let deck art / sprites settle one frame before screenshot.
        try:
            page.wait_for_timeout(120)
        except Exception:
            pass
        screenshot_bytes = page.screenshot(timeout=_SCREENSHOT_TIMEOUT_MS)

        cua_dir = _write_cua_bundle(self.bridge_dir, seq, observation, html, screenshot_bytes)
        print(
            f"[cua] cua_{seq}/ ready for persona {persona_id} "
            f"(headed={self.headed}, multi={self.multi_window}) "
            f"— waiting for primitives_{seq}.json or response_{seq}.json",
            flush=True,
        )

        deadline = time.monotonic() + self.timeout_sec
        kind, data = _wait_for_subagent_files(
            self.bridge_dir, seq, deadline, self.poll_interval_sec
        )

        if kind == "response" and isinstance(data, dict):
            print(f"[cua] subagent wrote response_{seq}.json directly", flush=True)
            self._handled.add(seq)
            _cleanup_aux(self.bridge_dir, seq)
            return True

        if kind == "primitives" and isinstance(data, dict):
            steps = data.get("steps", [])
            if not isinstance(steps, list):
                steps = []
            # Re-load page so click targets match the screenshot the pilot saw.
            page.set_content(html, timeout=_NAV_TIMEOUT_MS)
            try:
                page.wait_for_timeout(80)
            except Exception:
                pass
            decision = _execute_primitives(page, steps)
            if isinstance(decision, dict) and decision.get("action"):
                try:
                    _write_response(self.bridge_dir, seq, decision)
                except OSError as exc:
                    print(f"[cua] response write race on seq={seq}: {exc}", flush=True)
                if not os.path.isfile(os.path.join(self.bridge_dir, f"response_{seq}.json")):
                    _write_response(self.bridge_dir, seq, decision)
                print(
                    f"[cua] executed {len(steps)} primitive(s) -> response_{seq}.json "
                    f"action={decision.get('action')}",
                    flush=True,
                )
                self._handled.add(seq)
                _cleanup_aux(self.bridge_dir, seq)
                return True
            print(f"[cua] primitives_{seq}.json did not yield window.__lastAction", flush=True)
            if os.path.isfile(os.path.join(self.bridge_dir, f"response_{seq}.json")):
                print(f"[cua] falling back to response_{seq}.json after failed clicks", flush=True)
                self._handled.add(seq)
                _cleanup_aux(self.bridge_dir, seq)
                return True

        if os.path.isfile(os.path.join(self.bridge_dir, f"response_{seq}.json")):
            print(f"[cua] using late response_{seq}.json", flush=True)
            self._handled.add(seq)
            _cleanup_aux(self.bridge_dir, seq)
            return True

        print(f"[cua] timed out waiting for subagent on seq={seq}", flush=True)
        self._handled.add(seq)
        return False

    def run_loop(self) -> None:
        os.makedirs(self.bridge_dir, exist_ok=True)
        print(
            f"[cua] watching {os.path.abspath(self.bridge_dir)} "
            f"(headed={self.headed}, multi_window={self.multi_window}, "
            f"timeout={self.timeout_sec}s per decision)",
            flush=True,
        )
        try:
            while True:
                for seq in _list_request_seqs(self.bridge_dir):
                    if seq not in self._handled:
                        self.process_seq(seq)
                time.sleep(self.poll_interval_sec)
        finally:
            self.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Playwright CUA bridge responder for arena subagents.")
    parser.add_argument("--bridge-dir", default=os.environ.get("ARENA_BRIDGE_DIR"))
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show Chromium window(s) so you can watch real clicks",
    )
    parser.add_argument(
        "--single-window",
        action="store_true",
        help="Use one shared Chromium window instead of one-per-persona",
    )
    parser.add_argument("--timeout", type=float, default=300.0, help="Seconds to wait per decision")
    parser.add_argument("--poll-interval", type=float, default=0.1)
    args = parser.parse_args()

    if not args.bridge_dir:
        print("ERROR: set ARENA_BRIDGE_DIR or pass --bridge-dir", file=sys.stderr)
        sys.exit(1)

    responder = CuaBridgeResponder(
        args.bridge_dir,
        headed=args.headed,
        timeout_sec=args.timeout,
        poll_interval_sec=args.poll_interval,
        multi_window=not args.single_window,
    )
    try:
        responder.run_loop()
    except KeyboardInterrupt:
        print("\n[cua] stopped", flush=True)
    finally:
        responder.close()


if __name__ == "__main__":
    main()
