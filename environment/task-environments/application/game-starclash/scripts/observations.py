"""Observation + legal action menu construction for the Starclash
RPS Crew task.

`build_observation` is the single entry point the engine calls (via the
`observation_builder` hook on `ArenaEngine`) once per eligible persona per
sub-step. It must never leak information the persona shouldn't have -
notably:

  - other personas' hands are always private (nearby_occupants excludes hand)
  - the opponent's submitted battle card in sub-step 1 is never included,
    even if it already exists in engine state by the time this observation
    is built (see engine.py: all sub-step-1 observations are built before
    any brain call is made, precisely to make this structurally impossible)
  - the market_signal is a coarse bucket, never raw counts, and is withheld
    entirely below a minimum sample size

There is only one physical room now (a continuous 2D space); "visibility"
is entirely proximity-based - two personas must be within
`engine.proximity_radius` of each other to see/chat-with/challenge each
other. This replaces the old "same room_id" adjacency-graph scoping.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Kept in sync with engine.CARD_TYPES; duplicated here (not imported) so this
# module has no hard dependency on engine.py's internals beyond the
# PersonaState/PersonaLifeState types it needs for read-only inspection.
from engine import ArenaEngine, PersonaLifeState, PersonaState, CARD_TYPES

MIN_TRADERS_FOR_MARKET_SIGNAL = 4
INSUFFICIENT_DATA_MESSAGE = "insufficient data (too few active traders)"


def _market_signal(engine: "ArenaEngine") -> str:
    qualifying_hands: List[List[str]] = [
        p.hand
        for p in engine.personas.values()
        if not p.is_eliminated() and len(p.hand) > 0
    ]
    if len(qualifying_hands) < MIN_TRADERS_FOR_MARKET_SIGNAL:
        return INSUFFICIENT_DATA_MESSAGE

    counts = {card_type: 0 for card_type in CARD_TYPES}
    for hand in qualifying_hands:
        for card in hand:
            if card in counts:
                counts[card] += 1

    max_count = max(counts.values())
    min_count = min(counts.values())
    if max_count - min_count <= 1:
        return "balanced"

    # Plurality type (ties among the max broken by CARD_TYPES order, which
    # is deterministic and doesn't leak anything beyond "one of these").
    plurality_type = max(CARD_TYPES, key=lambda t: counts[t])
    return f"{plurality_type}-heavy"


def _hand_card_counts(hand: List[str]) -> Dict[str, int]:
    counts = {card_type: 0 for card_type in CARD_TYPES}
    for card in hand:
        if card in counts:
            counts[card] += 1
    return counts


def _arena_card_counts(engine: "ArenaEngine") -> Dict[str, int]:
    """Arena-wide Rock/Paper/Scissors still in play (public info)."""
    counts = {card_type: 0 for card_type in CARD_TYPES}
    for persona in engine.personas.values():
        if persona.is_eliminated():
            continue
        for card in persona.hand:
            if card in counts:
                counts[card] += 1
    return counts


def _arena_roster(engine: "ArenaEngine", persona: "PersonaState") -> List[Dict[str, Any]]:
    """Every persona in the match — public map + scoreboard data.

    Positions (x, y) are public so the agent HUD can draw the full crew on
    the room viewscreen (not only proximity-scoped neighbors). Interaction
    rights (challenge / private message / chat overhear) still come only
    from nearby_occupants + action_menu; far pilots appear dimmed and are
    not challengeable until you walk into range.
    """
    roster = []
    for pid in engine.persona_order:
        other = engine.personas[pid]
        name = other.display_name or pid
        is_self = pid == persona.id
        nearby = (
            (not is_self)
            and (not other.is_eliminated())
            and engine._within_proximity(other, persona)
        )
        roster.append(
            {
                "id": pid,
                "display_name": name,
                "short_name": name.split()[0] if name else pid,
                "stars": other.stars,
                "eliminated": other.is_eliminated(),
                "is_self": is_self,
                "x": other.x,
                "y": other.y,
                "nearby": nearby,
            }
        )
    return roster


def _nearby_occupants(engine: "ArenaEngine", persona: "PersonaState") -> List[Dict[str, Any]]:
    """Other non-eliminated personas within `proximity_radius` of this
    persona's current (x, y) position. There is only one physical room now,
    so proximity - not room-id equality - is the entire visibility
    mechanism: a persona literally cannot perceive anyone outside this
    list. Includes each nearby persona's position so this persona can
    reason about movement/positioning relative to them."""
    occupants = []
    for pid in engine.persona_order:
        if pid == persona.id:
            continue
        other = engine.personas[pid]
        if other.is_eliminated():
            continue
        if not engine._within_proximity(other, persona):
            continue
        occupants.append(
            {
                "id": other.id,
                "display_name": other.display_name,
                "stars": other.stars,
                "x": other.x,
                "y": other.y,
            }
        )
    return occupants


def _recent_chat(engine: "ArenaEngine", persona: "PersonaState") -> List[Dict[str, Any]]:
    """Last ~5 PUBLIC chat messages said by personas CURRENTLY within
    proximity_radius of this persona (position-based visibility, evaluated
    live at observation-build time - not historical "were they in radius
    when they said it"). This is a deliberate simplification: tracking
    radius-at-time-of-message would need a whole extra bookkeeping
    dimension (recording speaker position per message and re-checking
    against this persona's position at every past tick); scoping by
    CURRENT proximity of the speaker is simpler and still captures "you can
    only overhear people near you right now."
    """
    nearby_ids = {
        pid
        for pid in engine.persona_order
        if pid != persona.id
        and not engine.personas[pid].is_eliminated()
        and engine._within_proximity(engine.personas[pid], persona)
    }
    nearby_messages = [msg for msg in engine.chat_log if msg.persona_id in nearby_ids or msg.persona_id == persona.id]
    return [
        {"persona_id": msg.persona_id, "text": msg.text, "tick": msg.tick}
        for msg in nearby_messages[-5:]
    ]


def _private_chat_with_me(engine: "ArenaEngine", persona: "PersonaState", sub_step: int) -> List[Dict[str, Any]]:
    """Private messages this persona was party to (sender or target) -
    strictly filtered so a persona can never see private messages exchanged
    between two OTHER personas.

    - sub_step 1/2 (has a pending_partner_id): only messages exchanged
      between this persona and that specific partner (last ~5).
    - sub_step 3 (FREE, no forced partner): last ~3 private messages this
      persona was party to with ANY partner, tagged with who it was with.
    """
    mine = [
        msg
        for msg in engine.private_chat_log
        if msg.sender_id == persona.id or msg.target_id == persona.id
    ]

    partner_id = persona.pending_partner_id
    if sub_step in (1, 2) and partner_id:
        with_partner = [
            msg
            for msg in mine
            if (msg.sender_id == partner_id or msg.target_id == partner_id)
        ]
        return [
            {
                "sender_id": msg.sender_id,
                "target_id": msg.target_id,
                "text": msg.text,
                "tick": msg.tick,
            }
            for msg in with_partner[-5:]
        ]

    # sub_step 3 (or no partner): last ~3 messages with any partner, tagged.
    recent = mine[-3:]
    result = []
    for msg in recent:
        other_id = msg.target_id if msg.sender_id == persona.id else msg.sender_id
        result.append(
            {
                "sender_id": msg.sender_id,
                "target_id": msg.target_id,
                "text": msg.text,
                "tick": msg.tick,
                "with_id": other_id,
            }
        )
    return result


def _build_action_menu(engine: "ArenaEngine", persona: "PersonaState", sub_step: int) -> Dict[str, Any]:
    """Return the legal action menu (and any accompanying legal parameter
    lists) for `persona` at this sub-step. Shape:
        {"actions": [...], **extra}
    """
    if sub_step == 1:
        menu = {"actions": ["play_card"], "available_cards": list(persona.hand)}
        # Piggyback private_message target restricted to the current battle
        # opponent only.
        opponent_id = persona.pending_partner_id
        menu["private_message_targets"] = [opponent_id] if opponent_id else []
        return menu

    if sub_step == 2:
        menu = {"actions": ["accept", "decline"]}
        # Piggyback private_message target restricted to the challenger only.
        challenger_id = persona.pending_partner_id
        menu["private_message_targets"] = [challenger_id] if challenger_id else []
        return menu

    # sub_step == 3: free actions. Nearby others are proximity-scoped (this
    # persona's only-visibility mechanism now that there is one room).
    nearby_others = engine._nearby_target_ids(persona)

    # Challenges are proximity-scoped: only personas within proximity_radius
    # are challengeable at all.
    challengeable_targets: List[str] = []
    if len(persona.hand) > 0:
        for pid in nearby_others:
            other = engine.personas[pid]
            if other.state != PersonaLifeState.FREE:
                continue
            if persona.decline_cooldowns.get(pid, 0) > 0:
                continue
            challengeable_targets.append(pid)

    # "move" is always available - a persona can always try to walk
    # somewhere in the room (there's no adjacency gate anymore).
    movable_bounds = {
        "max_distance": engine.max_move_distance,
        "room_width": engine.room_width,
        "room_height": engine.room_height,
    }

    actions = ["say", "wait", "move"]
    if challengeable_targets:
        actions.append("challenge")
    if nearby_others:
        actions.append("private_message")

    return {
        "actions": actions,
        "challengeable_targets": challengeable_targets,
        "movable_bounds": movable_bounds,
        "private_message_targets": nearby_others,
    }


def build_observation(engine: "ArenaEngine", persona: "PersonaState", sub_step: int) -> dict:
    """Build the full observation dict for `persona` at the given sub_step.

    sub_step: 1 (battle card submission), 2 (challenge response), or
    3 (free action).
    """
    menu = _build_action_menu(engine, persona, sub_step)

    observation: Dict[str, Any] = {
        "self": {
            "id": persona.id,
            "display_name": persona.display_name,
            "stars": persona.stars,
            "hand": list(persona.hand),
            "traits": persona.traits,
            "x": persona.x,
            "y": persona.y,
        },
        "current_room": {
            "name": engine.room_name,
        },
        "room_bounds": {
            "width": engine.room_width,
            "height": engine.room_height,
            "proximity_radius": engine.proximity_radius,
            "max_move_distance": engine.max_move_distance,
        },
        "nearby_occupants": _nearby_occupants(engine, persona),
        "arena_roster": _arena_roster(engine, persona),
        "arena_card_counts": _arena_card_counts(engine),
        "recent_chat": _recent_chat(engine, persona),
        "private_chat_with_me": _private_chat_with_me(engine, persona, sub_step),
        "market_signal": _market_signal(engine),
        "tick": engine.tick,
        "max_ticks": engine.max_ticks,
        "action_menu": menu,
    }

    if sub_step == 2:
        challenger_id = persona.pending_partner_id
        challenger = engine.personas.get(challenger_id) if challenger_id else None
        observation["pending_challenge_from"] = (
            {"id": challenger.id, "display_name": challenger.display_name}
            if challenger is not None
            else None
        )
    else:
        observation["pending_challenge_from"] = None

    if sub_step == 1:
        opponent_id = persona.pending_partner_id
        opponent = engine.personas.get(opponent_id) if opponent_id else None
        # Deliberately omit the opponent's card - do not read it from engine
        # state under any circumstance, even though at the point these
        # observations are built (before any sub-step-1 brain call has run)
        # no submission exists yet anyway. This comment + the omission below
        # is the leakage-prevention contract for this field.
        observation["battle_opponent"] = (
            {"id": opponent.id, "display_name": opponent.display_name}
            if opponent is not None
            else None
        )
    else:
        observation["battle_opponent"] = None

    return observation
