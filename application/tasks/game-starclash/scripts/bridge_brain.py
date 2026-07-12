"""File-based bridge brain for the Starclash task.

`FileBridgeBrain` is an `ArenaBrain` that delegates every decision to an
EXTERNAL process via a simple file-based request/response handshake,
instead of calling an LLM API in-process. This is what lets a
human/orchestrator (or any other out-of-process decision-maker with no
`ANTHROPIC_API_KEY` and no direct Anthropic API access, but with filesystem
read/write access) "play" a persona: the engine and `ArenaBrain` interface
never know or care what's actually deciding on the other end of the bridge
directory.

Handshake, per `decide(observation)` call:
  1. Write `observation` (plus a fresh, monotonically-incrementing request
     id) to `<bridge_dir>/request_<seq>.json`.
  2. Poll (sleeping `poll_interval_sec` between checks) for
     `<bridge_dir>/response_<seq>.json` to appear, bounded by
     `timeout_sec` total.
  3. Read the response dict once found, run it through the SAME
     legality/sanitization contract `ClaudeArenaBrain._sanitize_decision`
     already enforces (so a fallible external responder - e.g. a small/
     fast LLM or a careless human - can never hand the engine an illegal
     action), then delete both the request and response file so
     `bridge_dir` never accumulates stale files across a long session.
  4. On timeout, delete the (now-stale) request file too, then fall back
     to the same safe default `ClaudeArenaBrain._fallback` uses.

The incrementing `seq` counter (instance attribute, starts at 0) is what
makes a slow/late response for an old request unable to be mistaken for
the current one: each request/response pair is keyed by its own unique
sequence number, and only the response file matching the CURRENT seq is
ever read.

Sanitization is duplicated here (not imported) rather than refactored into
a shared free function on `ClaudeArenaBrain` - same call `vision_brain.py`
already made for `BrowserVisionBrain._sanitize_decision`/`_fallback` (see
its module docstring / `_fallback` docstring): factoring ~80 lines out of
the already-tested `ClaudeArenaBrain` for the sake of one more caller isn't
worth the risk of touching that tested class, so this brain follows the
same established precedent instead of reinventing it from scratch.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional

from brains import CARD_TYPES, ArenaBrain


class FileBridgeBrain(ArenaBrain):
    """An ArenaBrain that delegates each decision to an external process via
    a simple file-based request/response handshake, instead of calling an
    LLM API directly. On decide(observation), it:
      1. Writes observation (plus a fresh unique request id) to
         <bridge_dir>/request_<n>.json
      2. Polls (sleeping briefly between checks) for
         <bridge_dir>/response_<n>.json to appear
      3. Reads and returns the response dict once found, deleting the
         exchanged files
      4. Times out after `timeout_sec` (default generous, e.g. 300s per
         decision, since a human-or-subagent-driven external process may be
         slow) and falls back to a safe default action, mirroring
         ClaudeArenaBrain._fallback's philosophy.
    """

    def __init__(self, bridge_dir: str, timeout_sec: float = 300.0, poll_interval_sec: float = 1.0) -> None:
        self.bridge_dir = bridge_dir
        self.timeout_sec = timeout_sec
        self.poll_interval_sec = poll_interval_sec
        self._next_seq = 0
        os.makedirs(self.bridge_dir, exist_ok=True)

    # -- public API ---------------------------------------------------

    def decide(self, observation: dict) -> dict:
        menu = observation.get("action_menu", {})
        seq = self._next_seq
        self._next_seq += 1

        request_path = self._request_path(seq)
        response_path = self._response_path(seq)

        request_payload = {"request_id": seq, "observation": observation}
        with open(request_path, "w", encoding="utf-8") as f:
            json.dump(request_payload, f, indent=2)

        persona_id = observation.get("self", {}).get("id", "?")
        print(
            f"[bridge] waiting for external decision on request_{seq}.json "
            f"(persona {persona_id})...",
            file=sys.stderr,
        )

        decision = self._await_response(response_path, seq)

        # Whether we got a real response or gave up, the request file is no
        # longer needed - clean it up either way so bridge_dir never
        # accumulates stale files across a long game session.
        self._safe_remove(request_path)

        if decision is None:
            return self._fallback(observation, menu)

        return self._sanitize_decision(decision, observation, menu)

    # -- polling --------------------------------------------------------

    def _await_response(self, response_path: str, seq: int) -> Optional[dict]:
        deadline = time.monotonic() + self.timeout_sec
        while time.monotonic() < deadline:
            if os.path.exists(response_path):
                decision = self._read_response(response_path)
                self._safe_remove(response_path)
                return decision
            time.sleep(self.poll_interval_sec)

        # One last check in case the response landed between the final
        # sleep and the deadline check above.
        if os.path.exists(response_path):
            decision = self._read_response(response_path)
            self._safe_remove(response_path)
            return decision

        print(f"[bridge] timed out waiting for response_{seq}.json - falling back.", file=sys.stderr)
        return None

    @staticmethod
    def _read_response(response_path: str) -> Optional[dict]:
        try:
            with open(response_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _safe_remove(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass

    # -- file naming ------------------------------------------------------

    def _request_path(self, seq: int) -> str:
        return os.path.join(self.bridge_dir, f"request_{seq}.json")

    def _response_path(self, seq: int) -> str:
        return os.path.join(self.bridge_dir, f"response_{seq}.json")

    # -- defensive sanitization (duplicated from ClaudeArenaBrain on
    # purpose - see module docstring for why) ---------------------------

    def _sanitize_decision(self, decision: Optional[dict], observation: dict, menu: dict) -> dict:
        actions: List[str] = list(menu.get("actions", []))
        if not isinstance(decision, dict) or decision.get("action") not in actions:
            return self._fallback(observation, menu)

        action = decision["action"]
        piggyback = decision.get("private_message")

        raw_reasoning = decision.get("reasoning")
        reasoning = raw_reasoning if isinstance(raw_reasoning, str) and raw_reasoning.strip() else None

        if action == "play_card":
            available = menu.get("available_cards") or observation["self"]["hand"]
            card = decision.get("card")
            if card not in available:
                card = random.choice(list(available)) if available else random.choice(list(CARD_TYPES))
            result: Dict[str, Any] = {"action": "play_card", "card": card}
            if piggyback is not None:
                result["private_message"] = piggyback
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        if action == "challenge":
            targets = menu.get("challengeable_targets", [])
            target_id = decision.get("target_id")
            if target_id not in targets:
                return self._fallback(observation, menu)
            result = {"action": "challenge", "target_id": target_id}
            if piggyback is not None:
                result["private_message"] = piggyback
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        if action == "say":
            text = decision.get("text")
            if not isinstance(text, str) or not text.strip():
                text = "..."
            result = {"action": "say", "text": text}
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        if action == "move":
            target_x = decision.get("target_x")
            target_y = decision.get("target_y")
            if not isinstance(target_x, (int, float)) or not isinstance(target_y, (int, float)):
                return self._fallback(observation, menu)
            result = {"action": "move", "target_x": float(target_x), "target_y": float(target_y)}
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        if action == "private_message":
            pm_targets = menu.get("private_message_targets", [])
            pm = decision.get("private_message")
            target_id = pm.get("target_id") if isinstance(pm, dict) else None
            text = pm.get("text") if isinstance(pm, dict) else None
            if target_id not in pm_targets:
                return self._fallback(observation, menu)
            if not isinstance(text, str) or not text.strip():
                text = "..."
            result = {"action": "private_message", "private_message": {"target_id": target_id, "text": text}}
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        # accept / decline / wait carry no extra required params, but may
        # still carry a piggybacked private_message and/or reasoning.
        result = {"action": action}
        if piggyback is not None:
            result["private_message"] = piggyback
        if reasoning is not None:
            result["reasoning"] = reasoning
        return result

    def _fallback(self, observation: dict, menu: dict) -> dict:
        """Same fallback preference order as ClaudeArenaBrain._fallback:
        prefer "wait", else "decline", else a random legal card, else the
        first legal menu action."""
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


if __name__ == "__main__":
    # Throwaway end-to-end verification harness (not production code) -
    # proves the file handshake mechanism itself works correctly using a
    # SCRIPTED FAKE responder (a background thread), not a real LLM/
    # subagent. That integration is a separate, later step.
    import shutil
    import tempfile
    import threading

    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if _SCRIPT_DIR not in sys.path:
        sys.path.insert(0, _SCRIPT_DIR)

    import brains as _brains
    import observations as _observations
    from engine import ArenaEngine, PersonaLifeState, PersonaState

    _PASS: List[str] = []
    _FAIL: List[str] = []

    def _check(label: str, condition: bool, detail: str = "") -> None:
        if condition:
            _PASS.append(label)
            print(f"[PASS] {label}")
        else:
            _FAIL.append(label)
            print(f"[FAIL] {label} {detail}")

    # -- Step 1: build a REAL observation from a REAL engine run -----------
    repo_root = _SCRIPT_DIR
    for _ in range(6):
        candidate = os.path.join(repo_root, "persona", "datasets", "bench-dev-sample")
        if os.path.isdir(candidate):
            break
        repo_root = os.path.dirname(repo_root)
    persona_dir = os.path.join(repo_root, "persona", "datasets", "bench-dev-sample")

    import yaml

    def _load_persona(persona_id: str) -> PersonaState:
        path = os.path.join(persona_dir, f"persona_{persona_id}.yaml")
        with open(path, "r", encoding="utf-8") as fh:
            traits = yaml.safe_load(fh)
        from persona_names import random_display_name

        return PersonaState(
            id=persona_id,
            display_name=random_display_name(persona_id, seed=11),
            traits=traits,
            stars=3,
            hand=[],
        )

    personas = [_load_persona(pid) for pid in ("0001", "0042", "0052", "0229")]

    engine = ArenaEngine(
        personas=personas,
        max_ticks=3,
        seed=11,
        observation_builder=_observations.build_observation,
        room_width=20.0,
        room_height=20.0,
        proximity_radius=3.0,
        max_move_distance=2.0,
    )
    mock_brain = _brains.MockArenaBrain(seed=11)
    engine.run_tick(lambda persona, obs: mock_brain.decide(obs))

    real_persona = engine.personas[engine.persona_order[0]]
    # Sub-step 3 (FREE) observations are the richest ("say"/"move"/"wait"
    # always present) - force this persona into FREE regardless of what
    # tick 1 actually left it in, for a representative observation.
    real_persona.state = PersonaLifeState.FREE
    real_observation = _observations.build_observation(engine, real_persona, sub_step=3)
    _check(
        "built a real observation dict from a real ArenaEngine + MockArenaBrain run",
        isinstance(real_observation, dict) and "action_menu" in real_observation,
    )

    bridge_dir = tempfile.mkdtemp(prefix="bridge_brain_verify_")

    def _first_legal_action(observation: dict) -> dict:
        menu = observation.get("action_menu", {})
        actions = list(menu.get("actions", []))
        if "wait" in actions:
            return {"action": "wait"}
        return {"action": actions[0]} if actions else {"action": "wait"}

    def _fake_responder(bridge_dir: str, seq: int, delay_sec: float, illegal: bool = False) -> None:
        """Simulates the external responder: watches for request_<seq>.json,
        waits `delay_sec` (proving the polling loop actually polls), then
        writes back a response derived from the request's OWN observation
        (a "dumb but correct" responder - proving the round-trip carries
        real data both ways, not hardcoded on both ends)."""
        request_path = os.path.join(bridge_dir, f"request_{seq}.json")
        response_path = os.path.join(bridge_dir, f"response_{seq}.json")
        deadline = time.monotonic() + 10.0
        while not os.path.exists(request_path) and time.monotonic() < deadline:
            time.sleep(0.05)
        if not os.path.exists(request_path):
            return
        with open(request_path, "r", encoding="utf-8") as fh:
            request_payload = json.load(fh)
        time.sleep(delay_sec)
        if illegal:
            # Deliberately illegal: a challenge target that does not exist.
            action: Dict[str, Any] = {"action": "challenge", "target_id": "no-such-persona-9999"}
        else:
            action = _first_legal_action(request_payload["observation"])
        tmp_path = response_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(action, fh)
        os.replace(tmp_path, response_path)

    # -- Scenario A: real round-trip ---------------------------------------
    responder_thread = threading.Thread(
        target=_fake_responder, args=(bridge_dir, 0, 0.5), kwargs={"illegal": False}, daemon=True
    )
    responder_thread.start()

    brain = FileBridgeBrain(bridge_dir=bridge_dir, timeout_sec=10.0, poll_interval_sec=0.1)
    start = time.monotonic()
    decision_a = brain.decide(real_observation)
    elapsed_a = time.monotonic() - start
    responder_thread.join(timeout=5.0)

    legal_actions = list(real_observation.get("action_menu", {}).get("actions", []))
    _check(
        "round-trip: decide() blocked until the fake responder's file appeared "
        f"(elapsed={elapsed_a:.2f}s, expected >= ~0.5s)",
        elapsed_a >= 0.4,
        detail=f"(elapsed={elapsed_a:.2f}s)",
    )
    _check(
        "round-trip: decide() returned the exact legal action the fake responder wrote",
        decision_a == _first_legal_action(real_observation) and decision_a.get("action") in legal_actions,
        detail=f"(decision_a={decision_a!r})",
    )
    _check(
        "round-trip: request/response files were cleaned up after a successful exchange",
        not os.path.exists(os.path.join(bridge_dir, "request_0.json"))
        and not os.path.exists(os.path.join(bridge_dir, "response_0.json")),
    )

    # -- Scenario B: timeout + fallback (no responder running) -------------
    # Uses a fresh brain instance with a short timeout_sec, per the spec
    # ("call decide() again with a very short timeout_sec ... and no
    # responder running this time") - a dedicated instance keeps its own
    # seq counter (starting at 0 again) independent of `brain` above, so
    # request_0.json/response_0.json here refer unambiguously to THIS
    # instance's exchange, not scenario A's (already cleaned up) files.
    short_brain = FileBridgeBrain(bridge_dir=bridge_dir, timeout_sec=1.0, poll_interval_sec=0.1)
    start = time.monotonic()
    decision_b = short_brain.decide(real_observation)
    elapsed_b = time.monotonic() - start
    _check(
        f"timeout (short_brain, timeout_sec=1.0): returned within bounds, did not hang "
        f"(elapsed={elapsed_b:.2f}s, expected ~1s)",
        1.0 <= elapsed_b < 3.0,
        detail=f"(elapsed={elapsed_b:.2f}s)",
    )
    _check(
        "timeout: decide() fell back to a legal action instead of hanging/crashing",
        decision_b.get("action") in legal_actions,
        detail=f"(decision_b={decision_b!r})",
    )
    _check(
        "timeout: the stale request file was cleaned up before falling back",
        not os.path.exists(os.path.join(bridge_dir, "request_0.json")),
    )

    # -- Scenario C: illegal-response rejection -----------------------------
    # Continues on `brain` (from scenario A), whose internal counter is now
    # at seq 1 (scenario A consumed seq 0).
    responder_thread_c = threading.Thread(
        target=_fake_responder, args=(bridge_dir, 1, 0.3), kwargs={"illegal": True}, daemon=True
    )
    responder_thread_c.start()
    decision_c = brain.decide(real_observation)
    responder_thread_c.join(timeout=5.0)
    _check(
        "illegal-response: fake responder wrote an illegal challenge target, "
        "FileBridgeBrain rejected it and fell back to a legal action",
        decision_c.get("action") in legal_actions and decision_c.get("action") != "challenge",
        detail=f"(decision_c={decision_c!r})",
    )
    _check(
        "illegal-response: request/response files were still cleaned up",
        not os.path.exists(os.path.join(bridge_dir, "request_1.json"))
        and not os.path.exists(os.path.join(bridge_dir, "response_1.json")),
    )

    shutil.rmtree(bridge_dir, ignore_errors=True)

    print()
    print("=== FileBridgeBrain verification summary ===")
    print(f"PASS: {len(_PASS)}  FAIL: {len(_FAIL)}")
    print()
    print(f"Scenario A (real round-trip) returned: {decision_a!r}")
    print(f"Scenario B (timeout, no responder) fell back to: {decision_b!r}")
    print(f"Scenario C (illegal response) fell back to: {decision_c!r}")
    if _FAIL:
        print()
        print("Failed checks:")
        for label in _FAIL:
            print(f"  - {label}")
        sys.exit(1)
    print()
    print("All checks passed.")
