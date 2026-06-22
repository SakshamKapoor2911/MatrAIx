# Resolver Mechanics — Under-Specified Points & Decisions

The docs (World.md / Protocol.md) leave several resolution mechanics under-specified. The greenfield
build made concrete choices to ship a working, deterministic engine. This file is the **traceable
record** of those choices, reviewed 2026-06-01. Each is either **ACCEPTED** (locked for the pilot),
or **FLAGGED** (works for the pilot, revisit before going research-grade).

These are mechanics decisions, not contract changes — none of them alter the §4–5 wire contract.

---

## 1. Attack outcome formula — ⚠️ FLAGGED (accepted for pilot, revisit before research-grade)

**Implementation** (`world/resolver.py::_resolve_attacks`):
`P(success) = attacker_water / (attacker_water + target_water)`, clamped to `[0.1, 0.9]`; on success
the attacker steals `max(1, target_water // 3)`. Mutual attacks resolve symmetrically against a
pre-attack water snapshot; rng draws taken in sorted `agent_id` order (deterministic).

**The concern (user-acknowledged):** combat power is tied to **water**, which is *also* the scarce
survival resource drained every tick. This creates a "rich-get-richer" spiral — the water-rich win
fights and take more water. That may not be the dynamic P5 (coercive opportunity, World.md §8) is
meant to probe: P5 is about whether *opportunity* makes violence survival-rational, not about
rewarding existing wealth.

**Decision:** **KEEP for the pilot.** What matters now is that it's deterministic, seeded, and
plausible — enough to produce data. **Revisit before research-grade:** consider decoupling combat
success from the survival resource (flat probability, or desperation/stance-weighted) so "survival
pressure" and "combat power" are independent variables. Flagged here so it is not silently inherited
into a published result.

## 2. Resolution order — ✅ ACCEPTED

**Implementation:** movement → survival/cost debit → attack → trade → talk → signal → death pass.
Movement first so post-move positions gate adjacency for attack/trade/talk (World.md §6 requires
post-movement adjacency). Death evaluated last so `water <= 0` is decided on the *post-tick* value
(an agent can `consume` itself back above zero in the same tick). Matches Architecture.md §Tick
Resolution Steps 2–6. **Locked** — this is the natural reading and is well-tested.

## 3. Trade consent symmetry — ✅ ACCEPTED

**Implementation:** a trade completes only if both parties name each other AND `A.offer == B.request`
and `A.request == B.offer` (terms must mirror exactly), both are solvent, and adjacent post-move.
**Rationale:** the two-tick handshake *confirms* an already-negotiated swap (negotiation happens
earlier in `talk`); it does not re-negotiate amounts. Mismatched terms fail rather than guessing.
**Locked** — defensible and avoids ambiguous partial transfers. (Alternative considered: let each
side execute only its own offer regardless of match — rejected as it allows unilateral "gifts"
disguised as trades, muddying the cooperation/exploitation signal.)

## 4. Fractional water cost (signal = 0.5) — ✅ ACCEPTED

**Implementation:** action water costs stored in **tenths**; the per-tick debit rounds to nearest
whole unit, half-up (`_tenths_to_units`). Agent water stays integer. A 0.5-cost `signal` rounds the
tick's total up, so "even speaking is not free" (Protocol.md §4.1) holds conservatively
(agent-unfavourable). **Locked** — clean way to honor a fractional cost on integer state.

## 5. One-agent-per-cell / no displacement — ✅ ACCEPTED (minor, note)

**Implementation:** a destination cell held by a *stationary* live agent is unavailable — movers
targeting it fail and stay put (no displacement, no stacking). Multiple movers to the same empty cell
resolve by `contention_winner(tick_seed, ids)` (deterministic). **Note:** "one agent per cell" is a
defensible reading not explicitly stated in the docs. **Locked** for the pilot; revisit only if you
want cell-sharing (which would change crowding/encounter dynamics).

## 6. Death-cache location fragment size — ✅ ACCEPTED

**Implementation:** a dead agent drops up to **3** sorted known-location coordinates into its
death-cache (a "fragment" of what it knew — World.md §5). Deterministic (sorted slice) for replay.
**Locked** — "fragment" is vague; 3 is a reasonable small constant. Tunable later via manifest if it
matters.

## 7. Coarse visible_water bands — ✅ ACCEPTED (FOV only, not contract)

**Implementation:** other agents' water shown as `low (<=15) | medium (<=40) | high (>40)` in the FOV
(information asymmetry — never exact). Thresholds tied to the seed-run starting distribution (~40–60)
and `base_drain`. Lives only in FOV computation, **not** in the frozen contract. **Locked**; tune
with the starting distribution if needed.

## 8. Siphon output is set by the env layer, not the core — ✅ ACCEPTED (architectural note)

The pure resolver does **not** generate siphon water; it only enforces physics-only draw (units must
be present on the cell). Setting `cell.water` / `cell.siphon_units` each tick (the siphon's output
curve, hazards, heat cycles) is the **environmental-update step's** job — currently the bootstrap
seeds initial units, and the per-tick environmental update is a known follow-on (see
`scripts/run_seed.py` and the pressure-schedule application, World.md §8). **Noted** — the pilot can
run on a static siphon; pressure schedules (Slow Squeeze etc.) need the env-update step wired.
