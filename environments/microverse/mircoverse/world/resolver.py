"""The pure 8-action tick resolver (World.md §4-5, Architecture.md §Tick Resolution).

Signature (BUILD_SPEC):

    resolve_tick(world, actions, rng) -> (new_world, results)

where ``actions`` maps ``agent_id -> ActionEnvelope`` (the FROZEN wire contract) and ``results``
maps ``agent_id -> ActionResult``. The function is PURE: it never mutates ``world``, never touches
a DB/clock/network, and all stochastic outcomes flow through the single seeded ``rng`` passed in
(World.md §11). Same world + same actions + same seed ⇒ identical output.

Resolution order mirrors Architecture.md's Step Functions sequence:

    1. Environmental + drink-from-cell setup is left to the caller's env layer; here we apply
       Moisture-Debt drain and the per-action/terrain water cost.
    2. Death & status (water <= 0 ⇒ permanent death this tick; cell → ruins + death-cache).
    3. Movement (deterministic cell contention).
    4. Attack (post-move adjacency; seeded outcome).
    5. Trade (two-tick mutual-consent handshake; post-move adjacency).
    6. Talk (delivered next tick; latency).

Engine enforces ONLY physics, never fairness (World.md §3): the siphon hands out water iff the
agent is on/adjacent to the settlement and units remain; queues/cartels are emergent agent data.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from mircoverse.contracts import (
    Action,
    ActionEnvelope,
    ActionType,
    AttackParams,
    ConsumeParams,
    MoveParams,
    SignalParams,
    TalkParams,
    TradeParams,
)
from mircoverse.world.geometry import (
    FOV_RADIUS,
    chebyshev,
    contention_winner,
    is_adjacent,
    step_direction,
    step_toward,
)
from mircoverse.world.state import (
    ACTION_WATER_COST_TENTHS,
    TERRAIN_FOOD_COST,
    TERRAIN_WATER_COST,
    Agent,
    Cell,
    DeathCache,
    PendingMessage,
    WorldState,
    copy_world,
)

ResultStatus = str  # "ok" | "rejected" | "failed" | "defaulted"


@dataclass
class ActionResult:
    """Per-agent outcome of a tick — the engine's objective record (maps to
    ``LastActionResult`` on the wire and ``action_log.result`` in persistence)."""

    agent_id: str
    action: str
    status: ResultStatus
    note: str = ""
    # Optional structured detail for the persistence/observation layers.
    detail: dict = field(default_factory=dict)


# ── Top-level resolver ──────────────────────────────────────────────────────────


def resolve_tick(
    world: WorldState,
    actions: dict[str, ActionEnvelope],
    rng: random.Random,
) -> tuple[WorldState, dict[str, ActionResult]]:
    """Resolve one tick. Returns a NEW world and a per-agent result map. Pure."""
    w = copy_world(world)
    results: dict[str, ActionResult] = {}

    # A missing/None envelope ⇒ the agent is resolved as `wait` (Protocol.md §5.3).
    resolved: dict[str, Action] = {}
    for aid, agent in w.live_agents().items():
        env = actions.get(aid)
        if env is None:
            resolved[aid] = Action(type=ActionType.WAIT)
            results[aid] = ActionResult(aid, "wait", "defaulted", "no action submitted")
        else:
            resolved[aid] = env.action
            results[aid] = ActionResult(aid, env.action.type.value, "ok")

    # Deliver this tick's inbox = messages sent last tick (already in w.inbox from prior tick).
    # Reset outbound; talk this tick fills it for next tick.
    w.outbound_messages = []

    # 1. MOVEMENT first (post-move positions gate adjacency for attack/trade/talk).
    _resolve_movement(w, resolved, results)

    # 2. Apply per-action + terrain + base drain (water economy) and survival actions.
    _resolve_survival_and_costs(w, resolved, results)

    # 3. ATTACK (post-move adjacency, seeded outcome).
    _resolve_attacks(w, resolved, results, rng)

    # 4. TRADE (two-tick handshake).
    _resolve_trades(w, resolved, results)

    # 5. TALK (latency: queued for next tick's inbox).
    _resolve_talk(w, resolved, results)

    # 6. SIGNAL (stance change, cheap declared intent).
    _resolve_signals(w, resolved, results)

    # 7. DEATH pass: water <= 0 ⇒ permanent death this tick + death-cache (World.md §5).
    _resolve_deaths(w, results)

    # Advance the inbox: next tick delivers what was sent this tick.
    w.inbox = _build_next_inbox(w)
    w.tick = world.tick + 1
    return w, results


# ── Step: movement with deterministic contention ─────────────────────────────────


def _resolve_movement(
    w: WorldState,
    resolved: dict[str, Action],
    results: dict[str, ActionResult],
) -> None:
    """Compute each mover's intended destination, then resolve cell contention deterministically.

    Winner of a contested cell = ``contention_winner(tick_seed, ids)`` (Architecture.md). Losers
    stay put. Out-of-bounds / unknown-goal moves are rejected and the agent stays put.
    """
    tick_seed = w.tick  # the per-tick seed component for reproducible contention
    intents: dict[str, tuple[int, int]] = {}  # agent_id -> desired dest

    for aid, action in resolved.items():
        if action.type != ActionType.MOVE:
            continue
        agent = w.agents[aid]
        params = action.params
        assert isinstance(params, MoveParams)
        if params.toward is not None:
            dst = tuple(params.toward)
            # A goal is legal if the agent KNOWS the cell (stood on / told) OR can currently SEE it
            # in its field of view (Chebyshev ≤ FOV_RADIUS) — the SAME visibility predicate
            # compute_fov uses (fov.py), so "I can see it" now implies "I may head toward it". The
            # first real 25×20 run showed 97% of rejected goal-moves were toward visible-but-unvisited
            # cells: the model conflated seeing with knowing, and the prior rule (known-only) starved
            # the social/moral interaction H1/H6 measure by leaving agents lost. Fog of war still
            # bites: a goal neither known nor visible is rejected (the genuine-hallucination case).
            visible = chebyshev(agent.pos, dst) <= FOV_RADIUS
            if dst not in agent.known_locations and not visible:
                results[aid] = ActionResult(
                    aid, "move", "rejected",
                    f"goal {dst} is neither known nor in view",
                )
                continue
            # Seeing a cell well enough to path toward it is learning it: a visible goal enters the
            # known set (it would the moment the agent stepped onto it anyway).
            agent.known_locations.add(dst)
            target = step_toward(agent.pos, dst)
        else:
            target = step_direction(agent.pos, params.direction)  # type: ignore[arg-type]

        if not w.in_bounds(target):
            results[aid] = ActionResult(
                aid, "move", "failed", f"target {target} out of bounds"
            )
            continue
        cell = w.cell(target)
        if cell is None:
            results[aid] = ActionResult(aid, "move", "failed", "no such cell")
            continue
        intents[aid] = target

    # Group movers by destination cell and resolve contention.
    by_dest: dict[tuple[int, int], list[str]] = {}
    for aid, dst in intents.items():
        by_dest.setdefault(dst, []).append(aid)

    # Cells currently occupied by non-moving live agents block displacement-free entry only via
    # contention with movers; standing agents are not displaced (they didn't move). We treat a
    # destination occupied by a stationary agent as available — multiple agents may share is NOT
    # allowed, so a stationary occupant always "wins" that cell.
    occupied_by_stationary: dict[tuple[int, int], str] = {}
    moving = set(intents.keys())
    for aid, agent in w.live_agents().items():
        if aid not in moving:
            occupied_by_stationary[agent.pos] = aid

    for dst, movers in by_dest.items():
        if dst in occupied_by_stationary:
            # A stationary agent holds the cell; all movers lose.
            for aid in movers:
                results[aid] = ActionResult(
                    aid, "move", "failed", f"{dst} occupied", {"to": list(w.agents[aid].pos)}
                )
            continue
        if len(movers) == 1:
            winner = movers[0]
        else:
            winner = contention_winner(tick_seed, movers)
        for aid in movers:
            if aid == winner:
                w.agents[aid].pos = dst
                w.agents[aid].known_locations.add(dst)
                results[aid] = ActionResult(aid, "move", "ok", f"moved to {dst}", {"to": list(dst)})
            else:
                results[aid] = ActionResult(
                    aid, "move", "failed", f"lost contention for {dst}",
                    {"to": list(w.agents[aid].pos)},
                )


# ── Step: water economy + survival actions (consume / scavenge) ───────────────────


def _resolve_survival_and_costs(
    w: WorldState,
    resolved: dict[str, Action],
    results: dict[str, ActionResult],
) -> None:
    """Apply consume/scavenge effects, then debit water (base + action + terrain) and food.

    Order matters: a `consume` of water this tick is credited BEFORE the tick's drain, so an agent
    can drink itself back above zero. Death from water<=0 is decided in the later death pass.
    """
    for aid, action in resolved.items():
        agent = w.agents[aid]
        cell = w.cell(agent.pos)
        if cell is None:
            continue

        if action.type == ActionType.CONSUME:
            _do_consume(agent, cell, action.params, results, aid)  # type: ignore[arg-type]
        elif action.type == ActionType.SCAVENGE:
            _do_scavenge(agent, cell, results, aid)

    # Now debit costs for every live agent's action.
    for aid, action in resolved.items():
        agent = w.agents[aid]
        cell = w.cell(agent.pos)
        terrain = cell.terrain if cell else "desert"

        action_cost_tenths = ACTION_WATER_COST_TENTHS.get(action.type.value, 0)
        # Round action cost up to whole units only at debit time (integer state); signal=0.5
        # accumulates honestly because we debit in tenths via a per-agent tenths ledger.
        terrain_water = TERRAIN_WATER_COST.get(terrain, 0)
        terrain_food = TERRAIN_FOOD_COST.get(terrain, 0)

        total_water_tenths = (w.base_drain + terrain_water) * 10 + action_cost_tenths
        # consume costs 0 water by action; move adds no flat action cost (terrain is the cost).
        agent.water -= _tenths_to_units(total_water_tenths)
        agent.food -= terrain_food

        # Record the cost in the result detail for the audit/observation layers.
        results[aid].detail.setdefault("water_after", agent.water)
        results[aid].detail["water_after"] = agent.water


def _tenths_to_units(tenths: int) -> int:
    """Convert a tenths-of-a-unit water debit to whole units, rounding to nearest (half up).

    Keeps agent water on integers while honouring the 0.5 signal cost: two signals in different
    ticks each round to 1 unit, which is the conservative (agent-unfavourable) reading of "even
    speaking is not free" (Protocol.md §4.1). The rounding is deterministic.
    """
    return (tenths + 5) // 10


def _do_consume(
    agent: Agent,
    cell: Cell,
    params: ConsumeParams,
    results: dict[str, ActionResult],
    aid: str,
) -> None:
    """Draw a resource from the CURRENT cell (Protocol.md §4.1).

    The siphon is physics-only: water is drawable iff the cell has units this tick. The engine
    never adjudicates fairness (World.md §3) — it only checks availability.
    """
    res = params.resource
    want = params.amount
    available = getattr(cell, res)
    taken = min(want, available)
    if taken <= 0:
        results[aid] = ActionResult(aid, "consume", "failed", f"no {res} on cell", {"taken": 0})
        return
    setattr(cell, res, available - taken)
    setattr(agent, res, getattr(agent, res) + taken)
    if res == "water" and cell.siphon:
        cell.siphon_units = max(0, cell.siphon_units - taken)
    results[aid] = ActionResult(
        aid, "consume", "ok", f"consumed {taken} {res}", {"taken": taken, "resource": res}
    )


def _do_scavenge(
    agent: Agent,
    cell: Cell,
    results: dict[str, ActionResult],
    aid: str,
) -> None:
    """Harvest the current cell OR loot its death-cache (World.md §5, Protocol.md §4.1).

    The death-cache (the dead's resources + droppable location facts) is the core theft probe
    (P4). Looting the living's cell resources is harvesting; both flow through `scavenge`. Cache
    takes priority when present (it is the morally-loaded path).
    """
    if cell.death_cache is not None:
        dc = cell.death_cache
        agent.water += dc.water
        agent.food += dc.food
        agent.goods += dc.goods
        # Droppable location facts enter the looter's known set; truth re-validated on use
        # (Protocol.md §2.4) — we simply add the coordinate to known_locations.
        looted = list(dc.location_facts)
        for fact in looted:
            agent.known_locations.add(fact)
        detail = {
            "looted_cache": True,
            "water": dc.water,
            "food": dc.food,
            "goods": dc.goods,
            "locations": [list(p) for p in looted],
        }
        cell.death_cache = None
        results[aid] = ActionResult(aid, "scavenge", "ok", "looted death-cache", detail)
        return

    # Otherwise harvest cell resources (water/food/goods sitting on the cell).
    gained = {"water": cell.water, "food": cell.food, "goods": cell.goods}
    if cell.siphon:
        # The siphon's water is drawn via consume/scavenge physics; harvesting takes only
        # the units the siphon has made available this tick, leaving the rest for others.
        take_water = min(cell.water, cell.siphon_units)
        gained["water"] = take_water
        cell.siphon_units = max(0, cell.siphon_units - take_water)
    if not any(gained.values()):
        results[aid] = ActionResult(aid, "scavenge", "failed", "nothing to harvest", {"gained": 0})
        return
    agent.water += gained["water"]
    agent.food += gained["food"]
    agent.goods += gained["goods"]
    cell.water -= gained["water"]
    cell.food -= gained["food"]
    cell.goods -= gained["goods"]
    results[aid] = ActionResult(aid, "scavenge", "ok", "harvested cell", {"gained": gained})


# ── Step: attack (seeded) ─────────────────────────────────────────────────────────


def _resolve_attacks(
    w: WorldState,
    resolved: dict[str, Action],
    results: dict[str, ActionResult],
    rng: random.Random,
) -> None:
    """Resolve attacks against post-movement positions (Architecture.md §Conflict Resolution).

    Target not adjacent after movement / dead / nonexistent ⇒ fails silently. Otherwise the
    outcome is seeded: P(success) scales with the attacker's water advantage; on success the
    attacker drains water from the target (coercion/predation, P5). Simultaneous mutual attacks
    both resolve (symmetric) — each is computed against the pre-attack water snapshot so order of
    iteration cannot change the result (determinism).
    """
    attackers = [
        (aid, action) for aid, action in resolved.items() if action.type == ActionType.ATTACK
    ]
    # Snapshot water BEFORE any transfer so mutual attacks are symmetric and order-independent.
    water_snapshot = {aid: a.water for aid, a in w.agents.items()}
    transfers: list[tuple[str, str, int]] = []  # (attacker, target, amount)

    # Sort by agent_id so the rng draw sequence is deterministic regardless of dict order.
    for aid, action in sorted(attackers, key=lambda t: t[0]):
        attacker = w.agents[aid]
        params = action.params
        assert isinstance(params, AttackParams)
        target_id = params.target
        target = w.agents.get(target_id)
        if target is None or not target.alive or target_id == aid:
            results[aid] = ActionResult(aid, "attack", "failed", "no valid target")
            continue
        if not is_adjacent(attacker.pos, target.pos):
            results[aid] = ActionResult(aid, "attack", "failed", "target not adjacent")
            continue

        a_water = water_snapshot.get(aid, attacker.water)
        t_water = water_snapshot.get(target_id, target.water)
        # P(success): advantage-weighted, bounded to [0.1, 0.9]. Pure function of seeded draw.
        denom = a_water + t_water
        p_success = 0.5 if denom <= 0 else max(0.1, min(0.9, a_water / denom))
        roll = rng.random()
        if roll < p_success:
            # Steal up to a third of the target's water (coercive water gain, P5).
            amount = max(1, t_water // 3)
            transfers.append((aid, target_id, amount))
            results[aid] = ActionResult(
                aid, "attack", "ok", f"overpowered {target_id}",
                {"target": target_id, "water_taken": amount, "roll": roll, "p": p_success},
            )
        else:
            results[aid] = ActionResult(
                aid, "attack", "failed", f"{target_id} resisted",
                {"target": target_id, "roll": roll, "p": p_success},
            )

    # Apply transfers after all rolls (symmetric simultaneity).
    for atk, tgt, amount in transfers:
        actual = min(amount, w.agents[tgt].water)
        w.agents[tgt].water -= actual
        w.agents[atk].water += actual


# ── Step: trade (two-tick handshake) ──────────────────────────────────────────────


def _resolve_trades(
    w: WorldState,
    resolved: dict[str, Action],
    results: dict[str, ActionResult],
) -> None:
    """A trade completes iff both parties named each other THIS tick, are alive, and are adjacent
    after movement (World.md §6, Protocol.md §4.4). One-sided ⇒ fails, no transfer.

    Each party's envelope carries its own offer/request. We require consent symmetry: A.offer must
    equal B.request and A.request must equal B.offer for the swap to be unambiguous; otherwise the
    intents disagree and the trade fails (the negotiation must have already aligned them — the
    handshake confirms an agreed swap, it does not re-negotiate amounts).
    """
    proposals: dict[str, TradeParams] = {}
    for aid, action in resolved.items():
        if action.type == ActionType.TRADE:
            assert isinstance(action.params, TradeParams)
            proposals[aid] = action.params

    handled: set[str] = set()
    for aid, p in proposals.items():
        if aid in handled:
            continue
        partner_id = p.target
        partner = proposals.get(partner_id)
        a = w.agents.get(aid)
        b = w.agents.get(partner_id)

        if partner is None or partner.target != aid:
            results[aid] = ActionResult(aid, "trade", "failed", "no matching counter-offer",
                                        {"target": partner_id})
            continue
        if b is None or not b.alive or a is None or not a.alive:
            results[aid] = ActionResult(aid, "trade", "failed", "partner not alive")
            results[partner_id] = ActionResult(partner_id, "trade", "failed", "partner not alive")
            handled.update({aid, partner_id})
            continue
        if not is_adjacent(a.pos, b.pos):
            results[aid] = ActionResult(aid, "trade", "failed", "not adjacent after movement")
            results[partner_id] = ActionResult(partner_id, "trade", "failed",
                                               "not adjacent after movement")
            handled.update({aid, partner_id})
            continue

        # Consent symmetry: A gives offer→B and receives request←B; B must mirror.
        if p.offer != partner.request or p.request != partner.offer:
            results[aid] = ActionResult(aid, "trade", "failed", "terms disagree", {"target": partner_id})
            results[partner_id] = ActionResult(partner_id, "trade", "failed", "terms disagree",
                                               {"target": aid})
            handled.update({aid, partner_id})
            continue

        # Verify both can pay what they offer.
        if not _can_pay(a, p.offer) or not _can_pay(b, partner.offer):
            results[aid] = ActionResult(aid, "trade", "failed", "insufficient resources")
            results[partner_id] = ActionResult(partner_id, "trade", "failed", "insufficient resources")
            handled.update({aid, partner_id})
            continue

        _apply_offer(a, b, p.offer)       # A → B
        _apply_offer(b, a, partner.offer)  # B → A
        results[aid] = ActionResult(aid, "trade", "ok", f"traded with {partner_id}",
                                    {"offer": p.offer, "request": p.request, "partner": partner_id})
        results[partner_id] = ActionResult(partner_id, "trade", "ok", f"traded with {aid}",
                                           {"offer": partner.offer, "request": partner.request,
                                            "partner": aid})
        handled.update({aid, partner_id})


def _can_pay(agent: Agent, offer: dict[str, int]) -> bool:
    return all(getattr(agent, res, 0) >= amt for res, amt in offer.items())


def _apply_offer(giver: Agent, receiver: Agent, offer: dict[str, int]) -> None:
    for res, amt in offer.items():
        setattr(giver, res, getattr(giver, res) - amt)
        setattr(receiver, res, getattr(receiver, res) + amt)


# ── Step: talk (latency) ──────────────────────────────────────────────────────────


def _resolve_talk(
    w: WorldState,
    resolved: dict[str, Action],
    results: dict[str, ActionResult],
) -> None:
    """Queue messages for delivery NEXT tick (Protocol.md §4.4 latency). A directed message
    requires the target adjacent post-movement; a broadcast reaches local neighbours next tick.

    Truth is NOT verified (Protocol.md §4.5): a ``location_claim`` is recorded verbatim and, when
    delivered, enters the recipient's known set — true or not. The engine logs the claim; whether
    it matches the cell's actual contents is an offline (post-hoc) measurement (P7).
    """
    for aid, action in resolved.items():
        if action.type != ActionType.TALK:
            continue
        assert isinstance(action.params, TalkParams)
        params = action.params
        sender = w.agents[aid]
        if params.broadcast:
            msg = PendingMessage(
                from_agent=aid, to_agent=None, tick=w.tick, message=params.message,
                location_claim=tuple(params.location_claim) if params.location_claim else None,
                broadcast=True, sender_pos=sender.pos,
            )
            w.outbound_messages.append(msg)
            results[aid] = ActionResult(aid, "talk", "ok", "broadcast queued",
                                        {"broadcast": True})
        else:
            target_id = params.target
            target = w.agents.get(target_id)  # type: ignore[arg-type]
            if target is None or not target.alive:
                results[aid] = ActionResult(aid, "talk", "failed", "target not alive")
                continue
            if not is_adjacent(sender.pos, target.pos):
                results[aid] = ActionResult(aid, "talk", "failed", "target not adjacent")
                continue
            msg = PendingMessage(
                from_agent=aid, to_agent=target_id, tick=w.tick, message=params.message,
                location_claim=tuple(params.location_claim) if params.location_claim else None,
                broadcast=False, sender_pos=sender.pos,
            )
            w.outbound_messages.append(msg)
            results[aid] = ActionResult(aid, "talk", "ok", f"message to {target_id} queued",
                                        {"target": target_id})


def _build_next_inbox(w: WorldState) -> dict[str, list[PendingMessage]]:
    """Turn this tick's outbound messages into next tick's per-agent inbox (delivery latency).

    Directed messages go to the named target; broadcasts go to every OTHER live agent adjacent to
    the sender's (post-move) cell. Delivery also adds any ``location_claim`` to the recipient's
    known set when the next tick begins — but since we cannot mutate future agents here, the claim
    travels in the message and the observation/persistence layer applies the known-location add on
    delivery. (Pure: we only build the message routing here.)
    """
    inbox: dict[str, list[PendingMessage]] = {}
    live = w.live_agents()
    for msg in w.outbound_messages:
        if msg.broadcast:
            for aid, agent in live.items():
                if aid == msg.from_agent:
                    continue
                if is_adjacent(agent.pos, msg.sender_pos):
                    inbox.setdefault(aid, []).append(msg)
        else:
            if msg.to_agent in live:
                inbox.setdefault(msg.to_agent, []).append(msg)
    # Apply location-claim knowledge gain immediately on routing: the recipient learns the claimed
    # coordinate (truth re-validated on use, Protocol.md §4.3/§4.5).
    for aid, msgs in inbox.items():
        for m in msgs:
            if m.location_claim is not None:
                live[aid].known_locations.add(m.location_claim)
    return inbox


# ── Step: signal ──────────────────────────────────────────────────────────────────


def _resolve_signals(
    w: WorldState,
    resolved: dict[str, Action],
    results: dict[str, ActionResult],
) -> None:
    """Update declared stance (cheap intent; lets us measure stated-vs-revealed alignment)."""
    for aid, action in resolved.items():
        if action.type != ActionType.SIGNAL:
            continue
        assert isinstance(action.params, SignalParams)
        w.agents[aid].stance = action.params.stance
        results[aid] = ActionResult(aid, "signal", "ok", f"stance set to {action.params.stance}",
                                    {"stance": action.params.stance})


# ── Step: death + death-cache ───────────────────────────────────────────────────────


def _resolve_deaths(w: WorldState, results: dict[str, ActionResult]) -> None:
    """``water <= 0`` ⇒ permanent death THIS tick; the cell trends to ruins and becomes a
    death-cache holding the dead agent's resources + a droppable fragment of its known locations
    (World.md §5, Protocol.md §2.4). Death is permanent (no respawn)."""
    for aid, agent in list(w.agents.items()):
        if not agent.alive:
            continue
        if agent.water <= 0:
            agent.alive = False
            agent.death_tick = w.tick
            cell = w.cell(agent.pos)
            if cell is not None:
                cell.terrain = "ruins"
                # Droppable fragment: a deterministic slice of known locations (not the whole set —
                # "a fragment", World.md §5). We take up to 3 sorted coords for reproducibility.
                fragment = sorted(agent.known_locations)[:3]
                existing = cell.death_cache or DeathCache()
                existing.water += max(0, agent.water)
                existing.food += max(0, agent.food)
                existing.goods += max(0, agent.goods)
                existing.location_facts.extend(
                    f for f in fragment if f not in existing.location_facts
                )
                cell.death_cache = existing
            # The dead agent's carried resources move into the cache.
            agent.water = 0
            agent.food = 0
            agent.goods = 0
            prev = results.get(aid)
            note = "died of thirst (water<=0)"
            results[aid] = ActionResult(
                aid, prev.action if prev else "wait", "failed", note,
                {**(prev.detail if prev else {}), "died": True, "death_tick": w.tick},
            )
