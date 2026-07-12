"""Gymnasium-compatible wrapper around `ArenaEngine` for the Starclash
RPS Crew task.

This is an ADDITIVE access pattern alongside the existing `run_arena.py` CLI
loop and the browser/vision rendering path (both of those stay exactly as
they are) - it lets a single RL-style policy or scripted agent drive ONE
designated "ego" persona through the standard Gymnasium `reset()`/`step()`
contract, while every other persona ("NPCs") is driven automatically by a
supplied `ArenaBrain` (typically `MockArenaBrain`), exactly as they would be
in a normal `run_arena.py` run.

Design notes
------------

1. Tick-pausing approach (engine.py is READ-ONLY - not edited here):
   `engine.py` exposes exactly one public entry point that drives multiple
   ticks, `ArenaEngine.run(brain_fn)`, which loops `run_tick(brain_fn)` until
   `is_done()`. `run_tick` itself is NOT decomposed into anything finer than
   "one full tick (all 3 sub-steps)" - the three `_run_substep_*` methods are
   private, and each one internally loops over ALL eligible personas for
   that sub-step (building observations up front, then calling `brain_fn`
   for each, then applying results) with no hook to pause between one
   persona's brain call and the next. So there is no clean "step one
   (tick, sub_step, persona) unit at a time" seam to call from outside
   without either reimplementing engine internals (which would duplicate -
   and risk drifting from - the real state machine) or reaching into
   private methods (fragile, and exactly the kind of engine-internals
   coupling the task says to avoid).

   Given that, this module uses the thread + queue handoff the task
   describes as the safe fallback: `ArenaEngine.run(brain_fn)` runs on a
   background daemon thread. The `brain_fn` passed to it is
   `StarclashEnv._brain_fn`, which:
     - for the ego persona: puts the observation on `_obs_queue` and BLOCKS
       on `_action_queue.get()` until `step()` (running on the main thread)
       supplies an action, then returns it to the engine unmodified.
     - for every other persona: delegates directly to `npc_brain.decide()`,
       exactly like `run_arena.py`'s own `brain_fn`.
   `step()` pushes the caller's action onto `_action_queue` (unblocking the
   engine thread) and then blocks on `_obs_queue.get()` for whatever comes
   next: either the ego's next pending observation, or a "done" sentinel
   once `engine.run()` has returned. Because the handoff is a strict
   ping-pong (exactly one of the two threads is ever running engine logic
   at a time), there is no data race on `ArenaEngine` state - the main
   thread only reads engine state while the background thread is parked in
   `_action_queue.get()`.

2. `observation_space` / `action_space`: both are set to `gym.spaces.Dict({})`
   (a Dict space with no declared keys) rather than any flattened
   `Box`/`Discrete` encoding. The real observation (nested trait profiles,
   variable-length hands/nearby-occupant lists, a legal action menu whose
   shape changes by sub-step) and action (a small tagged-union-style dict
   whose required keys depend on `action_menu["actions"]`) are both
   intentionally heterogeneous, structured, and variable-shape - flattening
   them into fixed-width numeric vectors would either lose information
   (hands/occupant lists get truncated/padded) or require inventing an
   encoding nothing else in this codebase uses, purely to satisfy
   `gym.spaces` strictness. Since this task's research goal is studying LLM
   reasoning trajectories over rich structured state (not training a
   flat-vector RL policy), `Dict({})` is used as a documented, honest
   placeholder: the *actual* contract is "whatever `observations.py`'s
   `build_observation` returns" for observations, and "whatever
   `brains.ArenaBrain.decide` is documented to return" for actions. This
   mirrors an increasingly common pattern for LLM-agent Gym environments.

3. Reward (computed from real engine state, not guessed field names): the
   only field that changes as a direct result of gameplay outcomes for a
   persona is `PersonaState.stars` (mutated exclusively in
   `ArenaEngine._resolve_battle`, +1 for the winner / -1 for the loser,
   clamped at 0, no change on a tie). Each `step()` call's reward is:
       reward = ego.stars (now) - ego.stars (as of the previous ego decision)
   which naturally realizes "+1 per star gained / -1 per star lost since the
   last ego turn" without needing to inspect `battle_resolved` events
   directly (though those events are what *cause* the delta). On the final
   step of an episode this delta is further adjusted by a terminal bonus:
   +5 if the ego persona is the sole survivor (`len(active_personas) == 1`
   and it's the ego), -5 if the ego persona was eliminated
   (`PersonaState.is_eliminated()`), 0 otherwise (e.g. game truncated at
   `max_ticks` with multiple survivors including ego - no terminal bonus in
   that ambiguous case).

4. `terminated` vs `truncated`: `ArenaEngine.run()` sets
   `self.termination_reason` to `"one_survivor"` (if
   `len(active_personas()) <= 1` when the loop stops) or `"max_ticks"`
   (otherwise). This wrapper maps:
       - `terminated=True`  if the ego persona is eliminated, OR
                             `termination_reason == "one_survivor"`
         (covers both "ego is the survivor" and "ego lost, someone else is
         the survivor" - either way the ego's own episode is definitively
         over).
       - `truncated=True`   if NOT terminated and
                             `termination_reason == "max_ticks"`
         (ego is still alive, game hit the tick cap without a natural end).
   Ego-eliminated is checked first so that "ego died early, but the OTHER
   personas fought on until max_ticks" is correctly reported as
   `terminated=True` for the ego (its episode ended when it died), not
   `truncated=True`.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
from typing import Any

import gymnasium as gym

# Ensure this script's own directory is importable regardless of invocation
# style, matching run_arena.py's own bootstrap.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import yaml  # noqa: E402

import observations  # noqa: E402
from brains import ArenaBrain, MockArenaBrain  # noqa: E402
from engine import ArenaEngine, PersonaState  # noqa: E402


def _resolve_repo_root(start_dir: str) -> str:
    """Walk up from `start_dir` looking for `persona/datasets`, matching
    run_arena.py's own repo-root resolution (crew manifest persona_paths are
    relative to the repo root)."""
    repo_root = start_dir
    for _ in range(6):
        candidate = os.path.join(repo_root, "persona", "datasets")
        if os.path.isdir(candidate):
            return repo_root
        repo_root = os.path.dirname(repo_root)
    return os.getcwd()


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class StarclashEnv(gym.Env):
    """Gymnasium-compatible wrapper around ArenaEngine, controlling ONE
    designated persona per episode (the "ego" persona) while all OTHER
    personas are driven by a supplied ArenaBrain (e.g. MockArenaBrain) as
    NPCs/background agents. This lets a single RL-style policy or scripted
    agent be plugged in for one persona while the rest of the game runs
    exactly as it does today.

    See module docstring for the tick-pausing, observation/action space, and
    reward design rationale.
    """

    def __init__(
        self,
        map_path: str,
        crew_path: str,
        ego_persona_id: str,
        npc_brain: "ArenaBrain",
        seed: int = 42,
        max_ticks: int = 20,
    ) -> None:
        super().__init__()
        self.map_path = map_path
        self.crew_path = crew_path
        self.ego_persona_id = ego_persona_id
        self.npc_brain = npc_brain
        self.seed_value = seed
        self.max_ticks = max_ticks

        # Intentionally permissive placeholder spaces - see module docstring
        # design note 2. The real, authoritative contract for observations
        # is `observations.build_observation`'s return shape, and for
        # actions is `brains.ArenaBrain.decide`'s documented return shape.
        self.observation_space = gym.spaces.Dict({})
        self.action_space = gym.spaces.Dict({})

        self.engine: ArenaEngine | None = None
        self._thread: threading.Thread | None = None
        self._obs_queue: queue.Queue = queue.Queue()
        self._action_queue: queue.Queue = queue.Queue()
        self._last_observation: dict | None = None
        self._last_stars: int = 0
        self._done: bool = True  # no active episode until reset() is called
        self._thread_exception: BaseException | None = None

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _build_engine(self, seed: int) -> ArenaEngine:
        map_data = _load_yaml(self.map_path)
        crew_manifest = _load_yaml(self.crew_path)
        repo_root = _resolve_repo_root(_SCRIPT_DIR)

        room = map_data.get("room", {}) if isinstance(map_data, dict) else {}
        room_name = room.get("name") or "Main Chat Room"
        room_width = float(room.get("width", 20.0))
        room_height = float(room.get("height", 20.0))
        proximity_radius = float(map_data.get("proximity_radius", 3.0))
        max_move_distance = float(map_data.get("max_move_distance", 2.0))
        start_area = map_data.get("start_area") if isinstance(map_data, dict) else None
        hand_size = int(crew_manifest.get("hand_size", 4))

        personas: list[PersonaState] = []
        for rel_path in crew_manifest.get("persona_paths", []):
            abs_path = os.path.join(repo_root, rel_path)
            traits = _load_yaml(abs_path)
            persona_id = str(
                traits.get("persona_id", os.path.splitext(os.path.basename(rel_path))[0])
            )
            from persona_names import random_display_name

            personas.append(
                PersonaState(
                    id=persona_id,
                    display_name=random_display_name(persona_id, seed=seed),
                    traits=traits,
                    stars=3,
                    hand=[],
                )
            )

        if self.ego_persona_id not in {p.id for p in personas}:
            raise ValueError(
                f"ego_persona_id {self.ego_persona_id!r} not found among crew "
                f"manifest persona ids: {[p.id for p in personas]}"
            )

        return ArenaEngine(
            personas=personas,
            room_name=room_name,
            max_ticks=self.max_ticks,
            seed=seed,
            hand_size=hand_size,
            observation_builder=observations.build_observation,
            room_width=room_width,
            room_height=room_height,
            proximity_radius=proximity_radius,
            max_move_distance=max_move_distance,
            start_area=start_area,
        )

    # ------------------------------------------------------------------
    # Thread/queue plumbing - see module docstring design note 1.
    # ------------------------------------------------------------------

    def _brain_fn(self, persona: PersonaState, observation: dict) -> dict:
        if persona.id == self.ego_persona_id:
            self._obs_queue.put(("ego_turn", observation))
            action = self._action_queue.get()
            return action
        return self.npc_brain.decide(observation)

    def _run_engine_thread(self) -> None:
        try:
            self.engine.run(self._brain_fn)
        except BaseException as exc:  # noqa: BLE001 - deliberately broad
            # Surface the failure to the main thread instead of silently
            # hanging it; step()/reset() re-raise this after the queue
            # handoff completes.
            self._thread_exception = exc
        finally:
            # Always signal completion, even if engine.run() raised, so a
            # caller blocked on _obs_queue.get() can never hang forever.
            self._obs_queue.put(("done", None))

    def _shutdown_previous_episode(self) -> None:
        """Best-effort drain of a still-running background thread from a
        prior episode that was abandoned before reaching termination (e.g.
        the caller invoked reset()/close() again without exhausting the
        previous episode). Feeds harmless 'wait' actions - which the engine
        always tolerates as a defensive fallback in every sub-step - until
        the engine thread reports done. Bounded so this can never hang
        forever even if something is wrong."""
        if self._thread is None or not self._thread.is_alive():
            return
        max_iterations = self.max_ticks * 4 + 16
        for _ in range(max_iterations):
            if not self._thread.is_alive():
                break
            try:
                kind, _payload = self._obs_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if kind == "done":
                break
            self._action_queue.put({"action": "wait"})
        self._thread.join(timeout=5.0)

    def _synthetic_terminal_observation(self) -> dict:
        """Build a fresh observation reflecting current (possibly terminal,
        possibly eliminated) ego state, for use as the observation returned
        alongside a terminated/truncated step. sub_step=3 is used
        unconditionally since it's the only sub-step whose menu-building
        doesn't assume an active pending_partner_id."""
        ego = self.engine.personas[self.ego_persona_id]
        try:
            return observations.build_observation(self.engine, ego, 3)
        except Exception:
            # Should not happen (build_observation is a pure function of
            # engine + persona + sub_step regardless of persona state), but
            # never let a reporting-only fallback crash the caller.
            return {
                "self": {"id": ego.id, "stars": ego.stars},
                "action_menu": {"actions": ["wait"]},
            }

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------

    def reset(
        self, *, seed: int | None = None, options: dict | None = None
    ) -> tuple[dict, dict]:
        super().reset(seed=seed)
        self._shutdown_previous_episode()

        effective_seed = seed if seed is not None else self.seed_value
        self.engine = self._build_engine(effective_seed)
        self._obs_queue = queue.Queue()
        self._action_queue = queue.Queue()
        self._done = False
        self._thread_exception = None

        ego = self.engine.personas[self.ego_persona_id]
        self._last_stars = ego.stars

        self._thread = threading.Thread(target=self._run_engine_thread, daemon=True)
        self._thread.start()

        kind, payload = self._obs_queue.get()
        if kind == "done":
            # Degenerate case (e.g. a crew of size 1, or an already-decided
            # game): the episode ended before the ego ever got a turn.
            # Surface a terminal-looking observation rather than crashing.
            self._thread.join(timeout=5.0)
            self._done = True
            if self._thread_exception is not None:
                raise self._thread_exception
            observation = self._synthetic_terminal_observation()
            self._last_observation = observation
            return observation, {"termination_reason": self.engine.termination_reason}

        self._last_observation = payload
        return payload, {}

    def step(self, action: dict) -> tuple[dict, float, bool, bool, dict]:
        if self.engine is None or self._thread is None:
            raise RuntimeError("step() called before reset().")
        if self._done:
            raise RuntimeError("step() called after episode ended; call reset() first.")

        self._action_queue.put(action)
        kind, payload = self._obs_queue.get()

        ego = self.engine.personas[self.ego_persona_id]
        new_stars = ego.stars
        reward = float(new_stars - self._last_stars)
        self._last_stars = new_stars

        if kind == "ego_turn":
            self._last_observation = payload
            return payload, reward, False, False, {}

        # kind == "done": the background engine thread has fully finished
        # (ArenaEngine.run() returned and set termination_reason).
        self._thread.join(timeout=5.0)
        self._done = True
        if self._thread_exception is not None:
            raise self._thread_exception

        reason = self.engine.termination_reason
        active = self.engine.active_personas()
        eliminated = ego.is_eliminated()
        sole_survivor = len(active) == 1 and active[0].id == self.ego_persona_id

        if eliminated:
            reward -= 5.0
        elif sole_survivor:
            reward += 5.0

        terminated = eliminated or reason == "one_survivor"
        truncated = (not terminated) and reason == "max_ticks"

        observation = self._synthetic_terminal_observation()
        self._last_observation = observation
        info = {
            "termination_reason": reason,
            "final_state": self.engine.final_state()["final_state"],
        }
        return observation, reward, terminated, truncated, info

    def render(self) -> str:
        """Reuse render_observation.render_observation_html if that module
        exists (lazy import - it may not exist yet / may be built by a
        concurrent process). Falls back to a simple text repr otherwise."""
        if self._last_observation is None:
            return ""
        try:
            from render_observation import render_observation_html
        except ImportError:
            return self._text_repr(self._last_observation)
        try:
            return render_observation_html(self._last_observation)
        except Exception:
            return self._text_repr(self._last_observation)

    @staticmethod
    def _text_repr(observation: dict) -> str:
        self_state = observation.get("self", {})
        menu = observation.get("action_menu", {})
        return (
            f"tick={observation.get('tick')} persona={self_state.get('id')} "
            f"stars={self_state.get('stars')} "
            f"pos=({self_state.get('x')}, {self_state.get('y')}) "
            f"legal_actions={menu.get('actions')}"
        )

    def close(self) -> None:
        self._shutdown_previous_episode()


# ----------------------------------------------------------------------
# Sample episode / smoke test
# ----------------------------------------------------------------------


def _discover_first_persona_id(crew_path: str, repo_root: str) -> str:
    crew_manifest = _load_yaml(crew_path)
    rel_path = crew_manifest["persona_paths"][0]
    abs_path = os.path.join(repo_root, rel_path)
    traits = _load_yaml(abs_path)
    return str(traits.get("persona_id", os.path.splitext(os.path.basename(rel_path))[0]))


def _trivial_action(observation: dict) -> dict:
    """Always 'wait' if legal, else the first legal action in the menu,
    filled in with the minimum params needed to be legal (this is NOT a
    real policy - just enough to drive a smoke-test episode forward)."""
    menu = observation.get("action_menu", {})
    actions = list(menu.get("actions", []))
    if "wait" in actions:
        return {"action": "wait"}

    action = actions[0] if actions else "wait"
    if action == "play_card":
        available = menu.get("available_cards") or observation.get("self", {}).get("hand") or []
        card = available[0] if available else "Rock"
        return {"action": "play_card", "card": card}
    if action == "challenge":
        targets = menu.get("challengeable_targets") or []
        if targets:
            return {"action": "challenge", "target_id": targets[0]}
        return {"action": "wait"}
    return {"action": action}


def _run_demo() -> None:
    task_dir = os.path.dirname(_SCRIPT_DIR)
    map_path = os.path.join(task_dir, "input", "ship_map.yaml")
    crew_path = os.path.join(task_dir, "input", "crew_manifest.yaml")
    repo_root = _resolve_repo_root(_SCRIPT_DIR)
    ego_persona_id = _discover_first_persona_id(crew_path, repo_root)

    npc_brain = MockArenaBrain(seed=7)
    env = StarclashEnv(
        map_path=map_path,
        crew_path=crew_path,
        ego_persona_id=ego_persona_id,
        npc_brain=npc_brain,
        seed=42,
        max_ticks=20,
    )

    observation, info = env.reset()
    print(f"[reset] ego={ego_persona_id} tick={observation.get('tick')} info={info}")

    total_reward = 0.0
    terminated = False
    truncated = False
    step_count = 0
    final_info: dict[str, Any] = {}

    while not (terminated or truncated):
        action = _trivial_action(observation)
        observation, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        step_count += 1
        final_info = info
        print(
            f"[step {step_count}] action={action} reward={reward:+.1f} "
            f"terminated={terminated} truncated={truncated} "
            f"ego_stars={observation.get('self', {}).get('stars')}"
        )

    print("=== Episode finished ===")
    print(f"Total steps: {step_count}  Total reward: {total_reward:+.1f}")
    print(f"Termination reason: {final_info.get('termination_reason')}")
    print(f"Final state: {final_info.get('final_state')}")
    print(env.render())
    env.close()


if __name__ == "__main__":
    _run_demo()
