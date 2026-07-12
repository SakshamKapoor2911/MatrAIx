"""Real vision-driven browser-use brain for the Starclash task.

Unlike `MockArenaBrain`/`ClaudeArenaBrain` (brains.py), which turn an
observation dict directly into structured JSON via forced tool-use,
`BrowserVisionBrain` renders the observation as an actual HTML page, loads
it in a real (headless by default) browser via Playwright, screenshots it,
asks Claude to look at the screenshot and decide where to click/type, and
executes that click/type via Playwright. The resulting action is read back
from `window.__lastAction` (a JS global the rendered page sets from its own
click handlers) rather than being invented by the model directly - this is
what makes it "real" browser-use rather than a JSON API shortcut wearing a
screenshot as a costume.

Design notes (see task-level discussion for the full tradeoff writeup):

  - One Playwright browser + one persistent browsing context is launched
    lazily on first use and reused for the lifetime of this brain instance
    (launching a fresh browser per `decide()` call would be wasteful across
    a run that may call `decide()` hundreds of times).
  - Each `decide()` call reuses a single Page and calls `page.set_content`
    to inject the freshly rendered HTML directly (no temp files, no
    `file://` URLs, no network) - matching render_observation_html's
    "self-contained, no external assets" contract.
  - Rather than wiring up Anthropic's `computer` beta tool (built for
    general desktop/browser control - mouse move, keypress-by-keypress
    typing, scrolling, etc.), this brain uses a small bounded loop of
    ordinary forced tool-use with a tiny custom primitive set:
    click_at(x, y), type_text(text), done(). This UI is a small, known,
    constrained set of controls (a handful of buttons/inputs/a canvas),
    not a general desktop - the bounded custom-primitive loop is simpler to
    implement correctly, easier to keep legality-safe, and just as capable
    for this task's action space as the heavier computer-use beta tool
    would be.
  - After the loop ends, `window.__lastAction` is read back and validated
    against `observation["action_menu"]` using the same fallback shape as
    `ClaudeArenaBrain._fallback` (duplicated here rather than refactored
    into a shared helper - see `_fallback` docstring below for why).
"""

from __future__ import annotations

import base64
import random
from typing import Any, Dict, List, Optional

from brains import ArenaBrain
from render_observation import render_observation_html

CARD_TYPES = ("Rock", "Paper", "Scissors")

# Bounded step loop: screenshot -> ask model for one primitive -> execute ->
# re-screenshot -> repeat. Kept small because each step is a real model call
# plus a real browser round-trip; a compound action (e.g. type text then
# click submit) needs at most a couple of steps, so 4 is generous headroom
# without letting one hung/looping persona-tick stall the whole engine.
_MAX_STEPS = 4

# Per-call Playwright timeouts, in milliseconds. Every wait/screenshot/click
# is bounded so a single stuck browser interaction can't hang the engine's
# synchronous per-persona `decide()` call indefinitely.
_NAV_TIMEOUT_MS = 5_000
_ACTION_TIMEOUT_MS = 3_000
_SCREENSHOT_TIMEOUT_MS = 5_000

# Viewport used for the persistent context. Fixed and known so that pixel
# coordinates the model reports against the screenshot map 1:1 onto
# page-space coordinates Playwright can click.
_VIEWPORT = {"width": 1024, "height": 768}


class BrowserVisionBrain(ArenaBrain):
    """Real vision-driven browser-use brain: renders the observation as an
    HTML page, loads it in a persistent per-persona Playwright browser
    context, screenshots it, asks Claude (vision + forced tool-use) to
    decide where to click/type, executes that via Playwright, and reads
    back window.__lastAction as the resulting action dict.

    Both `playwright` and `anthropic` are imported lazily (inside
    `__init__`), never at module import time, so importing this module (or
    using MockArenaBrain/ClaudeArenaBrain elsewhere) never requires either
    heavier dependency to be installed.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", headless: bool = True) -> None:
        try:
            import anthropic  # noqa: F401  (imported lazily, kept as attribute below)
        except ImportError as exc:  # pragma: no cover - exercised only with --brain vision
            raise ImportError(
                "The 'anthropic' package is required for BrowserVisionBrain. "
                "Install it (e.g. `uv add anthropic` or `pip install anthropic`) "
                "or run with --brain mock instead."
            ) from exc

        try:
            import playwright.sync_api  # noqa: F401  (imported lazily, kept as attribute below)
        except ImportError as exc:  # pragma: no cover - exercised only with --brain vision
            raise ImportError(
                "The 'playwright' package is required for BrowserVisionBrain. "
                "Install it (e.g. `uv add playwright`) and then run "
                "`uv run playwright install chromium` once to fetch the browser "
                "binary, or run with --brain mock/claude instead."
            ) from exc

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.headless = headless

        self._sync_playwright_cm = playwright.sync_api.sync_playwright
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    # -- lazy browser lifecycle ---------------------------------------

    def _ensure_browser(self) -> None:
        """Lazily launch the ONE persistent Playwright browser + context +
        page on first use, reused across every subsequent `decide()` call
        for this brain instance's lifetime. Safe to call repeatedly."""
        if self._page is not None:
            return
        self._playwright = self._sync_playwright_cm().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(viewport=_VIEWPORT)
        self._context.set_default_timeout(_ACTION_TIMEOUT_MS)
        self._page = self._context.new_page()

    def close(self) -> None:
        """Release the Playwright browser/context. Must be safe to call
        even if setup partially failed (e.g. never launched, or launch
        raised partway through)."""
        try:
            if self._page is not None:
                self._page.close()
        except Exception:
            pass
        try:
            if self._context is not None:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright is not None:
                self._playwright.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    # -- public API ---------------------------------------------------

    def decide(self, observation: dict) -> dict:
        menu = observation.get("action_menu", {})
        actions: List[str] = list(menu.get("actions", []))
        if not actions:
            return {"action": "wait"}

        try:
            decision = self._run_vision_loop(observation)
        except Exception:
            # Any Playwright/SDK/timeout failure anywhere in the loop ->
            # fall back defensively below, exactly as ClaudeArenaBrain does.
            decision = None

        return self._sanitize_decision(decision, observation, menu)

    # -- browser-driven step loop ---------------------------------------

    def _run_vision_loop(self, observation: dict) -> Optional[dict]:
        self._ensure_browser()
        page = self._page

        html = render_observation_html(observation)
        page.set_content(html, timeout=_NAV_TIMEOUT_MS)

        step_history: List[Dict[str, Any]] = []
        for _step in range(_MAX_STEPS):
            screenshot_bytes = page.screenshot(timeout=_SCREENSHOT_TIMEOUT_MS)
            primitive = self._ask_vision_model(screenshot_bytes, step_history)
            step_history.append(primitive)

            kind = primitive.get("type")
            if kind == "done":
                break
            if kind == "click_at":
                x = primitive.get("x")
                y = primitive.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    # page.mouse.click is a raw synthetic-input dispatch, not
                    # an auto-waiting action - it has no `timeout` parameter
                    # because it doesn't wait on anything (it fires and
                    # returns immediately). The context-level default
                    # timeout set in `_ensure_browser` still bounds every
                    # OTHER Playwright call in this loop that does wait
                    # (set_content, screenshot, evaluate, locator lookups).
                    page.mouse.click(float(x), float(y))
                continue
            if kind == "type_text":
                text = primitive.get("text")
                if isinstance(text, str):
                    # Types into whatever element currently has focus (the
                    # model is expected to have already clicked the target
                    # input in a prior step); this mirrors how a human
                    # would tab/click into a field, then type. Also a raw
                    # synthetic-input dispatch with no `timeout` parameter,
                    # for the same reason as page.mouse.click above.
                    page.keyboard.type(text)
                continue
            # Unknown/malformed primitive: stop the loop early rather than
            # looping uselessly for the remaining step budget.
            break

        return page.evaluate("() => window.__lastAction")

    # -- model call (isolated so tests can monkeypatch/override it) -----

    def _ask_vision_model(
        self, screenshot_bytes: bytes, step_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Ask Claude for exactly ONE primitive action given the current
        screenshot and the primitives already taken this decide() call.
        Isolated into its own method (rather than inlined in
        `_run_vision_loop`) specifically so it can be monkeypatched/
        overridden in a test subclass without needing a real API key or
        network access.
        """
        tool = {
            "name": "act",
            "description": (
                "Perform exactly one primitive UI action toward completing your "
                "turn: click at a pixel coordinate, type text into the "
                "currently focused input, or signal that your action is "
                "already complete."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["click_at", "type_text", "done"],
                    },
                    "x": {
                        "type": "number",
                        "description": "Pixel x coordinate. Required when type is 'click_at'.",
                    },
                    "y": {
                        "type": "number",
                        "description": "Pixel y coordinate. Required when type is 'click_at'.",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type. Required when type is 'type_text'.",
                    },
                },
                "required": ["type"],
            },
        }

        image_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
        history_note = (
            f"Primitives already performed this turn (oldest first): {step_history}"
            if step_history
            else "No primitives performed yet this turn."
        )
        response = self._client.messages.create(
            model=self.model,
            max_tokens=512,
            system=(
                "You are looking at a screenshot of a small game UI. Decide the "
                "single next primitive action needed to complete one legal game "
                "action (e.g. click a button, click a point on a map/canvas, or "
                "type into a text field then click its submit button). Call "
                "'done' once you've already clicked whatever finalizes the "
                "action (the page will record the result itself - you do not "
                "need to report what happened, only drive the clicks/typing)."
            ),
            tools=[tool],
            tool_choice={"type": "tool", "name": "act"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": history_note},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                    ],
                }
            ],
        )
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "act":
                return dict(block.input)
        return {"type": "done"}

    # -- defensive sanitization (duplicated from ClaudeArenaBrain._fallback
    # / _sanitize_decision on purpose - see docstring below) -------------

    def _sanitize_decision(self, decision: Optional[dict], observation: dict, menu: dict) -> dict:
        """Validate `decision` (the read-back window.__lastAction) against
        observation["action_menu"], exactly the same way
        ClaudeArenaBrain._sanitize_decision does. This normally shouldn't
        need to reject anything, since the rendered page only ever exposes
        legal controls - but the vision loop could time out, click nothing,
        click something dead, or the model could call `done()` before ever
        producing a window.__lastAction, so this stays just as defensive as
        the JSON-brain path.
        """
        actions: List[str] = list(menu.get("actions", []))
        if not isinstance(decision, dict) or decision.get("action") not in actions:
            return self._fallback(observation, menu)

        action = decision["action"]
        piggyback = decision.get("private_message")

        if action == "play_card":
            available = menu.get("available_cards") or observation["self"]["hand"]
            card = decision.get("card")
            if card not in available:
                card = random.choice(list(available)) if available else random.choice(list(CARD_TYPES))
            result: Dict[str, Any] = {"action": "play_card", "card": card}
            if piggyback is not None:
                result["private_message"] = piggyback
            return result

        if action == "challenge":
            targets = menu.get("challengeable_targets", [])
            target_id = decision.get("target_id")
            if target_id not in targets:
                return self._fallback(observation, menu)
            result = {"action": "challenge", "target_id": target_id}
            if piggyback is not None:
                result["private_message"] = piggyback
            return result

        if action == "say":
            text = decision.get("text")
            if not isinstance(text, str) or not text.strip():
                text = "..."
            return {"action": "say", "text": text}

        if action == "move":
            target_x = decision.get("target_x")
            target_y = decision.get("target_y")
            if not isinstance(target_x, (int, float)) or not isinstance(target_y, (int, float)):
                return self._fallback(observation, menu)
            return {"action": "move", "target_x": float(target_x), "target_y": float(target_y)}

        if action == "private_message":
            pm_targets = menu.get("private_message_targets", [])
            pm = decision.get("private_message")
            target_id = pm.get("target_id") if isinstance(pm, dict) else None
            text = pm.get("text") if isinstance(pm, dict) else None
            if target_id not in pm_targets:
                return self._fallback(observation, menu)
            if not isinstance(text, str) or not text.strip():
                text = "..."
            return {"action": "private_message", "private_message": {"target_id": target_id, "text": text}}

        # accept / decline / wait carry no extra required params, but may
        # still carry a piggybacked private_message.
        result = {"action": action}
        if piggyback is not None:
            result["private_message"] = piggyback
        return result

    def _fallback(self, observation: dict, menu: dict) -> dict:
        """Same fallback preference order as ClaudeArenaBrain._fallback:
        prefer "wait", else "decline", else a random legal card, else the
        first legal menu action. Deliberately duplicated rather than
        imported/shared - factoring this into a free function in brains.py
        would touch the already-tested ClaudeArenaBrain module for the sake
        of a ~10-line method; duplication here is the safer choice.
        """
        actions: List[str] = list(menu.get("actions", []))
        if "wait" in actions:
            return {"action": "wait"}
        if "decline" in actions:
            return {"action": "decline"}
        if "play_card" in actions:
            available = menu.get("available_cards") or observation["self"]["hand"]
            card = random.choice(list(available)) if available else random.choice(list(CARD_TYPES))
            return {"action": "play_card", "card": card}
        return {"action": actions[0]} if actions else {"action": "wait"}
