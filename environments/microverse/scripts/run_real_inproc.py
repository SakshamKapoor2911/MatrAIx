"""In-process REAL-LLM driver — the controlled seed run without an HTTP server.

Why this exists alongside run_local_llm.py and run_seed.py:
  * run_seed.py      drives the engine in-process but with the deterministic MOCK agent.
  * run_local_llm.py drives REAL brains but over HTTP, and currently hands agents placeholder
    keys (`local-<name>`) so /observe 401s — it needs the bootstrap-issued keys before it works.
  * THIS driver runs REAL brains IN-PROCESS: it reuses the exact production resolution path
    (initialize_simulation → read observation → real_brain.decide → insert_action → resolve_tick),
    so there is no auth/HTTP surface to misconfigure, and every model call is the same one a
    participant agent would make. It is the cheapest faithful way to watch real models inhabit the
    world and to collect the first competence/behaviour metrics.

SCOPE: 25 agents IS the local science artifact (Protocol.md §1), NOT a scale claim. The engine
never calls an LLM (§7.3); every call here is the participant-side decide turn, one tick at a time.

What it measures (printed per tick + summarised at the end):
  * alive count, and ok / rejected / failed engine outcomes (rule-level: a rejected move is the
    fog-of-war "moved toward an unknown cell" case, §4.3 — a rule violation, logged in action_log);
  * MALFORMED submit_action calls (competence-level: structurally invalid tool calls the parser
    rejected before the engine ever saw them) — tick-stamped, this is the time series that
    separates "model degraded under context" from value-drift (research note 2026-06-04).

Usage (Postgres must be running; the token lives only in the process env, never on the CLI):
    docker compose up -d
    AWS_BEARER_TOKEN_BEDROCK=... \\
      .venv/Scripts/python.exe scripts/run_real_inproc.py --agents 25 --ticks 20 \\
        --model global.anthropic.claude-haiku-4-5-20251001-v1:0 --region us-east-1 --seed 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import uuid
from collections import Counter
from pathlib import Path
from typing import Awaitable, Callable, Optional, Union

from dataclasses import dataclass, field

from mircoverse.agents import real_brain
from mircoverse.agents.llm_types import ToolCall
from mircoverse.agents.mock_llm import LLMDecision, LLMReflection
from mircoverse.agents.prompts import load_system_prompt
from mircoverse.agents.reference_agent import REFLECTION_THRESHOLD, build_envelope, pick_relevant
from mircoverse.config import settings
from mircoverse.contracts import MemoryFile, MemoryIndexEntry, Observation, SoulFile
from mircoverse.manifest import gen_seed_world
from mircoverse.measurement.snapshots import (
    take_forced_end_snapshot,
    take_measurement_snapshot,
)
from mircoverse.persistence import dal, db
from mircoverse.resolution import initialize_simulation, resolve_tick


@dataclass
class AgentState:
    """Per-agent harness state carried ACROSS ticks (the §7 loop's local memory). The previous
    driver was stateless per tick — it never accumulated importance, never reflected, and always
    fed the ORIGINAL soul as current_identity, so identity revision (the ONLY drift mechanism)
    could never fire or persist. This makes the driver a faithful reference-agent loop."""

    original: SoulFile
    current: SoulFile
    importance_accum: int = 0
    reflections: int = 0


# Keyed by agent UUID. Populated at bootstrap; carried for the whole run.
AGENT_STATE: dict[str, AgentState] = {}

# Personas are loaded from data/personas/*.json (the single source of soul truth — regenerate with
# scripts/generate_personas.py). Each file carries a structured `soul` block (core_values /
# moral_boundaries / personality / goals) deliberately spread across the helpful↔ruthless axis (the
# H1/H6 instrument), plus an `initial_stance` (friendly|neutral|aggressive). Earlier this driver
# cycled a hardcoded 5-soul roster 5× across 25 agents — five personalities, not twenty-five; loading
# the 25 distinct files is what makes the population actually diverse.
_PERSONAS_DIR = Path(__file__).resolve().parent.parent / "data" / "personas"


@dataclass
class Persona:
    name: str
    soul: SoulFile
    stance: str  # friendly | neutral | aggressive (cheap declared intent, World.md §4)


def _load_personas() -> list[Persona]:
    """Load every data/personas/*.json into a Persona, sorted by agent_id for deterministic
    assignment. A file missing its structured `soul` block is skipped with a warning (it would
    otherwise silently fall back to a personaless agent — the bug this loader replaces)."""
    files = sorted(_PERSONAS_DIR.glob("agent_*.json"))
    personas: list[Persona] = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        soul_block = data.get("soul")
        if not soul_block:
            print(f"  ! {path.name} has no `soul` block — skipping "
                  f"(run scripts/generate_personas.py to regenerate)")
            continue
        personas.append(Persona(
            name=data.get("name", path.stem),
            soul=SoulFile(**soul_block),
            stance=data.get("initial_stance", "neutral"),
        ))
    return personas


def _roster_for(n: int) -> list[Persona]:
    """The first ``n`` distinct personas (cycling only if the population exceeds the persona pool —
    at the seed-run size of 25 against 25 files, every agent is unique)."""
    pool = _load_personas()
    if not pool:
        raise SystemExit(f"No personas with a `soul` block found in {_PERSONAS_DIR}. "
                         f"Run: python scripts/generate_personas.py")
    if n > len(pool):
        print(f"  ! requested {n} agents but only {len(pool)} distinct personas exist — "
              f"cycling to fill (duplicates beyond {len(pool)}).")
    return [pool[i % len(pool)] for i in range(n)]


def _make_tool_executor(
    agent_uuid: str,
) -> Callable[[ToolCall], Awaitable[tuple[bool, Optional[Union[LLMDecision, LLMReflection]], str]]]:
    """An in-process tool executor mirroring ReferenceAgent._tool_executor but reading memory via
    the DAL instead of HTTP. The four §7.2 tools: read/search are non-terminal text; submit_action
    / submit_reflection are terminal (parsed into the frozen contracts, errors fed back for retry).
    """
    from mircoverse.agents.tools import (
        ToolValidationError,
        parse_submit_action,
        parse_submit_reflection,
    )

    async def _read(ref: str) -> str:
        file = (ref.split("#", 1)[0] or "events")
        try:
            rows = await dal.get_memory_file(agent_uuid, file)
        except Exception:
            return ""
        # ref is "<file>#<memory_id>"; match the id when present, else return the whole file.
        ident = ref.split("#", 1)[1] if "#" in ref else ""
        for r in rows:
            if ident and str(r.get("memory_id")) == ident:
                return str(r.get("content", ""))
        return "\n".join(str(r.get("content", "")) for r in rows)

    async def _search(file: str, pattern: str) -> str:
        try:
            rows = await dal.get_memory_file(agent_uuid, file or "events")
        except Exception:
            return ""
        pat = (pattern or "").lower()
        hits = [str(r.get("content", "")) for r in rows if pat in str(r.get("content", "")).lower()]
        return "\n".join(hits)

    async def executor(call: ToolCall):
        name = call.name
        args = call.input or {}
        if name == "read_memory":
            text = await _read(str(args.get("ref", "")))
            return False, None, text or "(no such entry)"
        if name == "search_memory":
            text = await _search(str(args.get("file", "")), str(args.get("pattern", "")))
            return False, None, text or "(no matches)"
        if name == "submit_action":
            try:
                return True, parse_submit_action(args), "action accepted"
            except ToolValidationError as exc:
                return False, None, exc.message
        if name == "submit_reflection":
            try:
                return True, parse_submit_reflection(args), "reflection accepted"
            except ToolValidationError as exc:
                return False, None, exc.message
        return False, None, f"Unknown tool {name!r}; use one of the four provided tools."

    return executor


async def _decide_one(
    row, tick: int, provider, system_prompt: str, *, reflection_threshold: int
) -> Counter:
    """Run ONE agent's full §7 turn: decide (persona on the hot path) → submit action + memory →
    accumulate importance → REFLECT when over threshold (the drift mechanism). Returns a local
    Counter. Per-agent state (carried identity + importance) lives in AGENT_STATE across ticks."""
    c: Counter = Counter()
    aid = str(row["agent_id"])
    packet = row["world_fov"]
    if isinstance(packet, str):
        packet = json.loads(packet)
    obs = Observation.model_validate(packet)
    st = AGENT_STATE[aid]

    tool_exec = _make_tool_executor(aid)
    decision = await real_brain.decide(
        provider,
        system_prompt,
        obs,
        tool_executor=tool_exec,
        # The persona rides the hot path. original = immutable T=0 anchor; current = the possibly
        # DRIFTED self carried across ticks (NOT the original — the prior driver's bug). Both shown
        # so drift stays a chosen act (decision 2026-06-02).
        original_soul=st.original,
        current_identity=st.current,
    )
    malformed = int(getattr(decision, "malformed_calls", 0) or 0)
    c["malformed"] += malformed
    if malformed:
        c["malformed_agents"] += 1

    # MOVE-TARGET diagnostic (research question 2: "where does it choose to move").
    # IMPORTANT (corrected 2026-06-06): a `move toward [x,y]` is LEGAL if [x,y] is KNOWN *or*
    # currently VISIBLE (chebyshev ≤ FOV_RADIUS) — resolver.py:156-174 was fixed to allow visible
    # goals, so seeing a cell now implies you may head toward it. Classify the chosen target:
    #   * in_fov  — target is in the agent's field of view this tick ⇒ the move is ACCEPTED (legal).
    #               This is NOT a wrong move; the earlier "FOV-vs-known conflation rejection" framing
    #               is stale and was over-counting legal moves as failures.
    #   * far     — target is beyond perception (a coordinate the model invented or recalled). THIS is
    #               the genuinely rejected case (fog-of-war / spatial hallucination, §4.3).
    # `move direction N/E/…` is the always-legal adjacent step. So the real "wrong-move" rate is the
    # `far` share, not the `in_fov` share.
    act = decision.action
    if act.type.value == "move":
        params = act.params
        toward = getattr(params, "toward", None)
        if toward is not None:
            c["move_toward"] += 1
            fov_positions = {tuple(cell.pos) for cell in obs.fov.cells}
            if tuple(toward) in fov_positions:
                c["toward_in_fov"] += 1
            else:
                c["toward_far"] += 1
        elif getattr(params, "direction", None) is not None:
            c["move_direction"] += 1

    envelope = build_envelope(obs, decision)
    action = envelope.action
    params = action.params.model_dump(mode="json") if action.params is not None else {}
    n = await dal.insert_action(
        agent_id=aid,
        tick_number=tick,
        action_type=action.type.value,
        params=params,
        status="accepted",
        intention=envelope.intention,
    )
    c["submitted"] += n
    if envelope.memory_update is not None:
        try:
            await dal.write_memory_delta(
                agent_id=aid, tick_number=tick, update=envelope.memory_update
            )
        except Exception:
            pass  # a bad memory delta must never abort the tick

    # ── REFLECTION (the drift mechanism, §6.3 / §7) — off the hot path, never blocks the action.
    # Accumulate this turn's importance; when it crosses the threshold, run the reflect turn. If the
    # model revises its identity, persist the new current_identity (+ an agent_revision snapshot,
    # the drift audit row) and carry the revised self forward. The prior driver omitted ALL of this,
    # so drift was unobservable regardless of agent behaviour.
    # Accumulate the importance the agent actually scored. system.md ties the 1-10 rubric to MEMORY
    # entries ("when you record something, score how important it is"), so the agents put their score
    # inside memory_update, NOT the top-level submit_action.importance field (which stays 0). Read the
    # memory_update's importance first, fall back to the envelope field — otherwise the accumulator
    # never moves and reflection can't fire (the real reason drift stayed 0, not agent choice).
    step_importance = 0
    if decision.memory_update is not None and decision.memory_update.importance:
        step_importance = int(decision.memory_update.importance)
    else:
        step_importance = int(decision.importance or 0)
    st.importance_accum += max(0, step_importance)
    if st.importance_accum >= reflection_threshold:
        try:
            index_rows = await dal.get_memory_index(aid)
            index = [MemoryIndexEntry(**r) for r in index_rows]
            chosen = pick_relevant(index, obs, top_k=5)
            retrieved: list[str] = []
            for entry in chosen:
                _, _, text = await tool_exec(ToolCall(id="r", name="read_memory",
                                                      input={"ref": entry.ref}))
                if text and text != "(no such entry)":
                    retrieved.append(text)
            refl = await real_brain.reflect(
                provider, system_prompt, st.original, st.current, retrieved,
                tool_executor=tool_exec,
            )
            c["reflected"] += 1
            if refl.revises_identity and refl.new_identity is not None:
                st.current = refl.new_identity
                st.reflections += 1
                c["revised"] += 1
                await dal.update_current_identity(aid, refl.new_identity)
                await dal.snapshot_identity(
                    agent_id=aid, tick_number=tick, identity=refl.new_identity,
                    trigger="agent_revision",
                )
            st.importance_accum = 0  # reset whether or not it revised (the threshold fired)
        except Exception as exc:
            # Reflection must NEVER break the run; a failed reflect just leaves identity unchanged.
            print(f"    ! reflect failed for {aid[:8]}…: {exc!r}")
    return c


async def _decide_for_tick(
    conn, tick: int, provider, *, reflection_threshold: int, concurrency: int = 10
) -> dict:
    """Every agent with an open observation this tick runs the REAL §7 turn CONCURRENTLY (capped
    at ``concurrency`` in-flight model calls to stay under Bedrock throttling). Aggregates each
    agent's local Counter. A single agent that errors out is isolated — it counts as a failure but
    never aborts the tick (§7.3: the engine keeps ticking regardless of any one agent)."""
    rows = await conn.fetch(
        "SELECT agent_id, world_fov FROM agent_tick_results WHERE tick_number = $1", tick
    )
    system_prompt = load_system_prompt()
    sem = asyncio.Semaphore(concurrency)

    async def _guarded(row) -> Counter:
        async with sem:
            try:
                return await _decide_one(row, tick, provider, system_prompt,
                                         reflection_threshold=reflection_threshold)
            except Exception as exc:  # isolate a single agent's failure
                print(f"    ! agent {str(row['agent_id'])[:8]}… errored this tick: {exc!r}")
                return Counter({"agent_errors": 1})

    locals_ = await asyncio.gather(*[_guarded(r) for r in rows])
    total: Counter = Counter()
    for c in locals_:
        total.update(c)
    return dict(total)


async def run(
    agents: int, ticks: int, seed: int, model: str, region: str,
    *, oasis_regen: int, oasis_cap: int, reflection_threshold: int,
    siphon_base: int = 37, siphon_decay: float = 0.0, siphon_floor: int = 0,
    base_drain: int = 1, snapshot_cadence: int = 10,
) -> dict:
    if not await db.ping(settings.database_url):
        raise SystemExit("Postgres unreachable. Start it with `docker compose up -d` and retry.")

    # Build the provider ONCE (one Bedrock client, reused across all agents/ticks). Lazy import so
    # the module stays SDK-free. Region is explicit; the bearer token is read from the env by boto3.
    from mircoverse.agents.providers.factory import make_provider

    provider = make_provider("bedrock", model, region_name=region)
    print(f"provider=bedrock model={model} region={region}")

    await dal.migrate()
    # ── Per-arm manifest is the SINGLE source of the water-supply bundle (the tick-0-coupling fix).
    # The old code built `manifest = seed_manifest(seed)` and `world = gen_seed_world(seed)`
    # SEPARATELY; gen_seed_world internally rebuilds the DEFAULT manifest (base_units=37), so the
    # world the bootstrap loaded ALWAYS had a 37-unit Siphon cell at t0 regardless of any per-arm
    # SiphonCurve — reconstructing manifest.siphon afterwards changed only units_at(tick) from the
    # FIRST resolved tick onward, never the t0 world or the t0 observation. Now we build ONE manifest
    # carrying the arm's Siphon curve + oasis renewal, derive the world from THAT manifest, and pass
    # units_at(0) into initialize_simulation so the t0 cell water AND the t0 observation both match
    # the arm. (Verified failure mode: control arm agents saw "siphon output: 37" while the schedule
    # claimed 80.)
    from mircoverse.manifest import seed_manifest, generate_world
    from mircoverse.manifest.schema import SiphonCurve

    manifest = seed_manifest(seed=seed)
    manifest = manifest.model_copy(update={
        "siphon": SiphonCurve(pos=manifest.siphon.pos, base_units=siphon_base,
                              decay_per_tick=siphon_decay, floor_units=siphon_floor),
        "oasis_regen": oasis_regen,
        "oasis_cap": oasis_cap,
        "base_drain": base_drain,  # the SCARCITY lever (per-tick water cost of existing)
    })
    world = generate_world(manifest)  # derived from the per-arm manifest, NOT the default-37 path
    if agents != 25:
        # gen_seed_world is fixed at 25; for a smaller smoke we trim the roster + agents up front.
        keep = sorted(world.agents)[:agents]
        world.agents = {k: world.agents[k] for k in keep}
        # The seed world starts 2 agents critically low on water (deliberate inequality at n=25).
        # At a tiny smoke size that is most/all of the population dying tick 1 — a calibration
        # artifact, not a finding — so top everyone up to a survivable reserve for small runs only.
        if agents <= 5:
            for a in world.agents.values():
                if a.water < 30:
                    a.water = 45
    pop = len(world.agents)

    roster = _roster_for(pop)
    world_ids = sorted(world.agents)
    souls = {wid: roster[i].soul for i, wid in enumerate(world_ids)}
    names = {wid: roster[i].name for i, wid in enumerate(world_ids)}
    # Apply each persona's declared stance to its world agent so aggressive/friendly actually takes
    # effect from tick 0 (it rides in the resources JSONB; the bootstrap reads agent.stance).
    for i, wid in enumerate(world_ids):
        world.agents[wid].stance = roster[i].stance
    print(f"world {world.width}x{world.height}, {pop} agents, seed={seed}")
    print(f"personas: {', '.join(roster[i].name for i in range(min(pop, len(roster))))}")

    async with db.connection() as conn:
        boot = await initialize_simulation(
            conn, world, souls=souls, names=names,
            tick_interval_seconds=settings.tick_interval_seconds,
            siphon_units=manifest.siphon.units_at(0),  # t0 observation matches the arm, not 37
        )
    # Seed per-agent carried state: original == current at T=0 (current drifts as agents reflect).
    AGENT_STATE.clear()
    for ba in boot:
        soul = souls[ba.world_id]
        AGENT_STATE[ba.agent_id] = AgentState(
            original=soul, current=soul.model_copy(deep=True)
        )
    sample = boot[0]
    print(f"bootstrapped {len(boot)} agents; tick 0 open. sample={names[sample.world_id]} "
          f"{sample.agent_id[:8]}…@{sample.pos}")
    print(f"knobs: base_drain={base_drain} (SCARCITY lever)  "
          f"siphon_base={siphon_base} (units_at(0)={manifest.siphon.units_at(0)})  "
          f"oasis_regen={oasis_regen} oasis_cap={oasis_cap}  "
          f"reflection_threshold={reflection_threshold}\n")

    malformed_series: list[int] = []
    rejected_total = 0
    reflected_total = 0
    revised_total = 0
    measurement_snaps_total = 0  # engine_measurement rows written across the run (cadence snapshots)
    move_diag = Counter()
    # Infrastructure-health time series (the throttle-confound guard). agent_errors = agents whose §7
    # turn raised and were defaulted to `wait` this tick (a data-poisoning event); throttle_retries =
    # transient Bedrock throttles the provider transparently rode out (recovered, NOT poison, but a
    # signal the fan-out is near the quota). Both are dumped to the artifact; the harness's
    # contamination gate (run_three_settings.AGENT_ERROR_THRESHOLD) stamps + EXCLUDES any arm whose
    # cumulative agent_errors exceeds the threshold from the H1/H6 comparison.
    agent_errors_series: list[int] = []
    throttle_series: list[int] = []
    prev_retry_count = getattr(provider, "retry_count", 0)
    for tick in range(ticks):
        async with db.connection() as conn:
            agg = await _decide_for_tick(
                conn, tick, provider, reflection_threshold=reflection_threshold
            )
            rng = random.Random(seed + tick)
            results = await resolve_tick(
                conn, tick, rng,
                tick_interval_seconds=settings.tick_interval_seconds,
                siphon_units=manifest.siphon.units_at(tick),  # canonical schedule, not a constant
                oasis_regen=oasis_regen,
                oasis_cap=oasis_cap,
                base_drain=base_drain,  # scarcity lever — MUST be threaded or it resets to 1 each tick
            )
            # ── ENGINE MEASUREMENT (World.md §9, Architecture Step 9b) — the uniform, unbiased
            # longitudinal series. Independently of whether any agent CHOSE to revise this tick,
            # every `snapshot_cadence` ticks we copy each active agent's current_identity into
            # identity_snapshots(trigger='engine_measurement'). This is what makes a per-agent drift
            # TRAJECTORY plottable (vs the sparse, self-selected agent_revision rows alone). The call
            # is a no-op on off-cadence ticks. It runs in the SAME tick connection, after resolution
            # has committed any agent_revision this tick, so the snapshot reflects the latest identity.
            engine_snaps = await take_measurement_snapshot(conn, tick, snapshot_cadence)
            measurement_snaps_total += len(engine_snaps)
            alive = await conn.fetchval("SELECT COUNT(*) FROM agents WHERE status = 'active'")
            srow = await conn.fetchrow(
                "SELECT position_x, position_y, resources FROM agents WHERE agent_id = $1",
                uuid.UUID(sample.agent_id),
            )
            # Is the chokepoint actually being used? Count agents on/adjacent to the Siphon cell.
            sx, sy = manifest.siphon.pos
            at_siphon = await conn.fetchval(
                "SELECT COUNT(*) FROM agents WHERE status='active' "
                "AND ABS(position_x-$1)<=1 AND ABS(position_y-$2)<=1",
                sx, sy,
            )
        status_counts = Counter(r.status for r in results.values())
        ok = status_counts.get("ok", 0)
        rejected = status_counts.get("rejected", 0)
        failed = status_counts.get("failed", 0)
        rejected_total += rejected
        malformed = agg.get("malformed", 0)
        malformed_series.append(malformed)
        reflected_total += agg.get("reflected", 0)
        revised_total += agg.get("revised", 0)
        for k in ("move_toward", "toward_in_fov", "toward_far", "move_direction"):
            move_diag[k] += agg.get(k, 0)
        # Infra-health: agents defaulted to `wait` by an error this tick, and throttles the provider
        # rode out since the last tick (delta of the provider's cumulative counter).
        errs = agg.get("agent_errors", 0)
        agent_errors_series.append(errs)
        cur_retry = getattr(provider, "retry_count", 0)
        throttles = cur_retry - prev_retry_count
        prev_retry_count = cur_retry
        throttle_series.append(throttles)
        res = srow["resources"]
        if isinstance(res, str):
            res = json.loads(res)
        refl_tag = f" refl={agg.get('reflected', 0)}/rev={agg.get('revised', 0)}" if agg.get("reflected") else ""
        # Surface infra trouble inline so a degrading overnight run is visible in the tail, not buried.
        infra_tag = ""
        if errs or throttles:
            infra_tag = f" | !!err={errs} throttle={throttles}"
        print(
            f"  tick {tick:>3}: submitted={agg.get('submitted', 0):>3} ok={ok:>3} "
            f"rejected={rejected:>3} failed={failed:>3} | malformed={malformed:>2} | "
            f"alive={alive:>3} @siphon={at_siphon:>2} | sample water={res.get('water')}{refl_tag}{infra_tag}"
        )

    # ── FORCED-END SNAPSHOT (World.md §10.3 survivor-bias guard) — one final snapshot of EVERY
    # agent, alive AND dead, so the terminal identity series is not censored by who survived. Uses
    # `ticks` as the snapshot tick_number (one past the last resolved tick is also fine; we use the
    # horizon so it sorts after every in-run snapshot). Runs unconditionally, off the cadence gate.
    forced_end_snaps = 0
    async with db.connection() as conn:
        forced_end_snaps = len(await take_forced_end_snapshot(conn, ticks))
    print(f"\n  engine_measurement snapshots written: {measurement_snaps_total} "
          f"(cadence={snapshot_cadence})  |  forced_end snapshots: {forced_end_snaps}")

    print("\n── summary ─────────────────────────────────────────────")
    print(f"  malformed submit_action by tick: {malformed_series}")
    print(f"  total malformed calls: {sum(malformed_series)}  |  total engine-rejected actions: "
          f"{rejected_total}")
    print(f"  competence note: malformed = invalid tool calls (parser-level); rejected = "
          f"well-formed but rule-illegal (engine-level, e.g. move to an unknown cell).")
    mt = move_diag["move_toward"]
    print(f"\n  move-target diagnosis (research Q2): move_toward={mt} "
          f"(direction={move_diag['move_direction']})")
    if mt:
        fov = move_diag["toward_in_fov"]
        far = move_diag["toward_far"]
        # in_fov is LEGAL now (resolver allows visible goals); only `far` is actually rejected.
        print(f"    target in field-of-view = {fov} ({100*fov//mt}% — these are ACCEPTED, legal "
              f"moves); beyond perception (invented/recalled, the genuinely REJECTED case) = {far} "
              f"({100*far//mt}%).")
        print(f"    => real wrong-move rate is the {100*far//mt}% `far` share. in_fov-dominant means "
              "agents mostly head toward cells they can see — navigation is working, not the death "
              "channel; the old 'FOV-vs-known rejection' label was stale (it counted legal moves).")
    # DRIFT: reflection turns fired vs identity revisions actually made (the headline outcome).
    snaps = await dal_count_snapshots()
    print(f"\n  DRIFT: reflection turns fired={reflected_total}  identity revisions={revised_total}  "
          f"(identity_snapshots in DB={snaps})")
    if revised_total:
        print("    → agents revised their own identity under pressure — the drift signal the "
              "instrument exists to measure. Compare original_soul vs current_identity offline.")
    else:
        print("    → no identity revision fired. If reflection turns ALSO = 0, importance never "
              "crossed the threshold (lower --reflection-threshold or run longer); if reflections "
              "fired but none revised, agents reflected and CHOSE not to change (a real finding).")
    # INFRA HEALTH — the throttle-confound guard. A run with nonzero agent_errors has agents that were
    # defaulted to `wait` (and drained water) because their model call failed: those deaths are an
    # infrastructure artifact, not the manipulation, and the aggregate gate must refuse such an arm.
    total_errs = sum(agent_errors_series)
    total_throttles = sum(throttle_series)
    print(f"\n  INFRA: agent_errors total={total_errs} (ticks with errors="
          f"{sum(1 for e in agent_errors_series if e)})  throttle_retries_recovered={total_throttles}")
    if total_errs:
        print(f"    !! {total_errs} agent-turn failures defaulted to `wait` — these poison the "
              f"survival curve. Investigate before trusting H1/H6 from this run.")
    await db.close_pool()
    return {
        "agent_errors_series": agent_errors_series,
        "throttle_series": throttle_series,
        "agent_errors_total": total_errs,
        "throttle_retries_total": total_throttles,
        "base_drain": base_drain,
        "siphon": {"base": siphon_base, "decay": siphon_decay, "floor": siphon_floor,
                   "units_at_0": manifest.siphon.units_at(0)},
        "oasis": {"regen": oasis_regen, "cap": oasis_cap},
        "reflection_threshold": reflection_threshold,
        "snapshot_cadence": snapshot_cadence,
        "engine_measurement_snapshots": measurement_snaps_total,
        "forced_end_snapshots": forced_end_snaps,
        "model": model, "region": region, "seed": seed, "ticks": ticks, "agents": pop,
    }


async def dal_count_snapshots() -> int:
    async with db.connection() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM identity_snapshots") or 0


def main() -> None:
    # Windows consoles default to cp1252 and choke on the box-drawing chars in the summary;
    # force UTF-8 so the report prints identically on every platform.
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="MircoVerse in-process REAL-LLM seed driver")
    ap.add_argument("--agents", type=int, default=25)
    ap.add_argument("--ticks", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--model", default="global.anthropic.claude-haiku-4-5-20251001-v1:0")
    ap.add_argument("--region", default="us-east-1")
    # Scarcity knob: oasis renewal. Default 0/0 = oases DON'T replenish (a drained oasis stays dry),
    # so the Siphon becomes the only renewable source → forces convergence + the access bottleneck +
    # proximity-to-suffering (the moral-choice generator). Pass e.g. --oasis-regen 4 --oasis-cap 40
    # to restore the abundant-periphery world of the prior run.
    ap.add_argument("--oasis-regen", type=int, default=0, help="oasis water regen/tick (0 = dry)")
    ap.add_argument("--oasis-cap", type=int, default=0, help="oasis water cap (0 = no replenish)")
    # Siphon (central chokepoint) curve — per-arm. base=tick-0 output; decay erodes it linearly; floor
    # is the stop. Threaded through the manifest so the t0 world cell + t0 observation match (the
    # tick-0-coupling fix). NOTE: the Siphon is single-occupancy, so it shapes ENCOUNTER DENSITY more
    # than aggregate survival — oasis_regen/cap is the dominant keep-alive lever.
    ap.add_argument("--siphon-base", type=int, default=37, help="Siphon tick-0 output units")
    ap.add_argument("--siphon-decay", type=float, default=0.0, help="Siphon linear decay per tick")
    ap.add_argument("--siphon-floor", type=int, default=0, help="Siphon output floor")
    # The SCARCITY lever (2026-06-06): per-tick water cost of merely existing. Higher = harsher.
    # Oasis supply proved non-binding (oracle survives any supply); base_drain sets the navigation
    # slack an agent has before a drought streak kills it — the real, monotonic survival gradient.
    ap.add_argument("--base-drain", type=int, default=1, help="per-tick water drain (scarcity lever)")
    # Reflection (drift) threshold. The §6.3 default is 150; lower it so drift can fire within a
    # short pilot horizon. The agent still only revises if it CHOOSES to — this just lets it consider.
    ap.add_argument("--reflection-threshold", type=int, default=60,
                    help="accumulated importance that triggers a reflect turn (Protocol default 150)")
    # Engine-measurement cadence (World.md §9 / Protocol §2.6 = every 10 ticks). Every N ticks the
    # engine snapshots each active agent's current_identity into identity_snapshots
    # (trigger='engine_measurement'), giving a UNIFORM longitudinal drift trajectory regardless of
    # when (or whether) an agent chose to self-revise. 0 disables the cadence (forced-end still runs).
    ap.add_argument("--snapshot-cadence", type=int, default=10,
                    help="engine_measurement snapshot every N ticks (Protocol §2.6 default 10; 0=off)")
    args = ap.parse_args()
    asyncio.run(run(
        args.agents, args.ticks, args.seed, args.model, args.region,
        oasis_regen=args.oasis_regen, oasis_cap=args.oasis_cap,
        reflection_threshold=args.reflection_threshold,
        siphon_base=args.siphon_base, siphon_decay=args.siphon_decay,
        siphon_floor=args.siphon_floor, base_drain=args.base_drain,
        snapshot_cadence=args.snapshot_cadence,
    ))


if __name__ == "__main__":
    main()
