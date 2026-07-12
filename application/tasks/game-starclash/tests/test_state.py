"""Verifier checks for the Starclash task.

Reads the two artifacts written by scripts/run_arena.py (see that file and
scripts/engine.py for the authoritative schema) and asserts real gameplay
invariants - not just "did the file exist" - so a degenerate run (e.g. an
orchestrator where every persona just waits every tick forever, or a single
scripted battle followed by silence) cannot pass.
"""

import json
import math
import os
from pathlib import Path

OUTPUT_DIR = Path(
    os.environ.get("PERSONABENCH_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
GAME_LOG_PATH = OUTPUT_DIR / "game_log.json"
FINAL_STATE_PATH = OUTPUT_DIR / "final_state.json"

# The only two values ArenaEngine.run() ever assigns to termination_reason
# (see scripts/engine.py:run).
VALID_TERMINATION_REASONS = {"max_ticks", "one_survivor"}

# Every persona is constructed with stars=3 (scripts/engine.py PersonaState
# default, also set explicitly in run_arena.py:load_personas) and only
# battle_resolved events ever change stars thereafter. This is the correct
# baseline for a persona with zero battles in the log.
INITIAL_STARS = 3

# Event field names that identify "who chose this action", across every
# event type engine.py's log_event calls actually use. battle_resolved is the
# merger of both combatants' play_card decisions, so it's handled specially
# (persona_a/persona_b) rather than via this generic field list.
_ACTOR_FIELDS = ("persona_id", "sender_id", "challenger_id", "responder_id")

# Event types that represent a persona actively choosing a non-"wait" action,
# used by the degenerate-run check (#6). A persona that only ever "wait"s or
# only appears as a passive recipient/target never shows up here.
_MEANINGFUL_TYPES = {"say", "move", "challenge_issued", "battle_resolved", "challenge_accepted"}


def _load_json(path: Path) -> dict:
    assert path.is_file(), f"Missing expected artifact: {path}"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_game_log() -> dict:
    return _load_json(GAME_LOG_PATH)


def _load_final_state() -> dict:
    return _load_json(FINAL_STATE_PATH)


def _actor_ids(event: dict) -> list:
    """Every persona id that "acted" to produce this event."""
    if event.get("type") == "battle_resolved":
        return [pid for pid in (event.get("persona_a"), event.get("persona_b")) if pid]
    return [event[field] for field in _ACTOR_FIELDS if event.get(field)]


# ---------------------------------------------------------------------------
# 1. Both output files exist and are valid JSON.
# ---------------------------------------------------------------------------


def test_game_log_exists_and_is_valid_json():
    assert GAME_LOG_PATH.is_file(), f"Missing {GAME_LOG_PATH}"
    data = json.loads(GAME_LOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "game_log.json root must be a JSON object"


def test_final_state_file_exists_and_is_valid_json():
    assert FINAL_STATE_PATH.is_file(), f"Missing {FINAL_STATE_PATH}"
    data = json.loads(FINAL_STATE_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "final_state.json root must be a JSON object"


# ---------------------------------------------------------------------------
# 2. Schema sanity.
# ---------------------------------------------------------------------------


def test_game_log_schema():
    game_log = _load_game_log()

    events = game_log.get("events")
    assert isinstance(events, list) and events, "game_log.json 'events' must be a non-empty list"

    personas = game_log.get("personas")
    assert isinstance(personas, list) and personas, "game_log.json 'personas' must be a non-empty list"
    persona_ids = {p.get("id") for p in personas}
    assert all(persona_ids), "every persona summary must have a non-empty 'id'"

    final_state = game_log.get("final_state")
    assert isinstance(final_state, dict) and final_state, (
        "game_log.json 'final_state' must be a non-empty dict keyed by persona id"
    )
    assert set(final_state.keys()) == persona_ids, (
        f"final_state keys {set(final_state.keys())} must match persona roster {persona_ids}"
    )

    termination_reason = game_log.get("termination_reason")
    assert termination_reason in VALID_TERMINATION_REASONS, (
        f"termination_reason {termination_reason!r} must be one of {VALID_TERMINATION_REASONS}"
    )


def test_final_state_file_matches_game_log():
    game_log = _load_game_log()
    final_state_doc = _load_final_state()

    assert final_state_doc.get("final_state") == game_log.get("final_state"), (
        "final_state.json's 'final_state' must match game_log.json's 'final_state' exactly"
    )
    assert final_state_doc.get("termination_reason") == game_log.get("termination_reason"), (
        "final_state.json's termination_reason must match game_log.json's"
    )


# ---------------------------------------------------------------------------
# 3. Star-conservation invariant.
# ---------------------------------------------------------------------------


def test_star_conservation_across_all_battles():
    game_log = _load_game_log()
    battles = [e for e in game_log["events"] if e.get("type") == "battle_resolved"]
    assert battles, "expected at least one battle_resolved event to check conservation on"

    for event in battles:
        stars_before = event.get("stars_before")
        stars_after = event.get("stars_after")
        assert isinstance(stars_before, dict) and isinstance(stars_after, dict), (
            f"battle_resolved event at tick {event.get('tick')} is missing stars_before/stars_after dicts"
        )
        total_before = sum(stars_before.values())
        total_after = sum(stars_after.values())
        assert total_before == total_after, (
            f"star conservation violated at tick {event.get('tick')} "
            f"(persona_a={event.get('persona_a')!r}, persona_b={event.get('persona_b')!r}): "
            f"{total_before} != {total_after} (before={stars_before}, after={stars_after})"
        )


# ---------------------------------------------------------------------------
# 4. No post-elimination action.
# ---------------------------------------------------------------------------


def test_no_persona_acts_after_elimination():
    game_log = _load_game_log()
    events = game_log["events"]

    eliminated: set = set()
    for index, event in enumerate(events):
        for actor in _actor_ids(event):
            assert actor not in eliminated, (
                f"persona {actor!r} appears as an actor in event #{index} "
                f"(tick {event.get('tick')}, type {event.get('type')!r}) after already being "
                f"eliminated (dropped to 0 stars) in an earlier battle_resolved event"
            )
        if event.get("type") == "battle_resolved":
            stars_after = event.get("stars_after", {})
            for pid, stars in stars_after.items():
                if stars <= 0:
                    eliminated.add(pid)


# ---------------------------------------------------------------------------
# 5. At least one battle occurred.
# ---------------------------------------------------------------------------


def test_at_least_one_battle_occurred():
    game_log = _load_game_log()
    battle_count = sum(1 for e in game_log["events"] if e.get("type") == "battle_resolved")
    assert battle_count >= 1, "expected at least one battle_resolved event in the game log"


# ---------------------------------------------------------------------------
# 6. Multiple distinct personas acted meaningfully (anti-degenerate-run check).
# ---------------------------------------------------------------------------


def test_multiple_personas_acted_meaningfully():
    """Catches the "everyone waits / one scripted battle" degenerate run.

    A run where nearly every persona only ever "wait"s, with a single
    battle_resolved event injected to satisfy check #5, must NOT pass overall:
    it fails here because fewer than the required fraction of the roster ever
    took a meaningful (non-wait) action.
    """
    game_log = _load_game_log()
    events = game_log["events"]
    roster_ids = {p["id"] for p in game_log["personas"]}

    meaningful_actors: set = set()
    for event in events:
        if event.get("type") not in _MEANINGFUL_TYPES:
            continue
        meaningful_actors.update(_actor_ids(event))

    roster_size = len(roster_ids)
    threshold = min(roster_size, max(3, math.ceil(0.6 * roster_size)))
    assert len(meaningful_actors) >= threshold, (
        f"only {len(meaningful_actors)} distinct persona(s) ({sorted(meaningful_actors)}) took a "
        f"meaningful (non-wait) action out of a roster of {roster_size}; expected at least "
        f"{threshold} (60% of roster, minimum 3) - this looks like a degenerate/scripted run"
    )


# ---------------------------------------------------------------------------
# 7. final_state consistency with the event log.
# ---------------------------------------------------------------------------


def test_final_state_eliminated_flag_matches_stars():
    final_state = _load_final_state()["final_state"]
    for pid, state in final_state.items():
        stars = state.get("stars")
        eliminated = state.get("eliminated")
        assert eliminated == (stars <= 0), (
            f"persona {pid!r}: eliminated={eliminated!r} inconsistent with stars={stars!r} "
            f"(expected eliminated == (stars <= 0))"
        )


def test_final_state_stars_match_last_battle_or_initial_value():
    """Replay-lite check: since only battle_resolved ever changes stars, each
    persona's final stars must equal the stars_after value from their last
    battle_resolved event in the log (chronological order), or the initial
    star count if they were never in a battle at all."""
    game_log = _load_game_log()
    events = game_log["events"]
    final_state = game_log["final_state"]

    for pid, state in final_state.items():
        last_stars_after = None
        for event in events:
            if event.get("type") != "battle_resolved":
                continue
            if pid not in (event.get("persona_a"), event.get("persona_b")):
                continue
            stars_after = event.get("stars_after", {})
            if pid in stars_after:
                last_stars_after = stars_after[pid]

        expected_stars = last_stars_after if last_stars_after is not None else INITIAL_STARS
        assert state.get("stars") == expected_stars, (
            f"persona {pid!r}: final_state stars={state.get('stars')!r} does not match replay-expected "
            f"stars={expected_stars!r} (from last battle_resolved event, or initial stars if no battles)"
        )
