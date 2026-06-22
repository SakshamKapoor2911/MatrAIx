#   MircoVerse — Architecture

> Systems & infrastructure spec. For *what is being simulated and why* — the world, its rules, and
> the moral-pressure instrument that makes identity drift measurable — see [`World.md`](./World.md).

## Research Goal

Study how agent identity drifts under long-horizon, morally difficult situations in a shared
social world. Users submit a soul file (values, personality, moral boundaries) that acts as
the agent's identity. Over many ticks, environmental pressure and social dynamics force moral
choices. Periodic self-reflection causes the agent to rewrite its own soul file. The experiment
measures how much the soul file changes from start to finish, and which pressures caused the
drift.

---

## Architecture Diagram

> Paste the rendered architecture diagram below. Keep the ASCII overview in *System Overview* as the
> text-searchable source of truth; this image is the at-a-glance companion for the portfolio/README.

<!-- Replace the line below with your diagram, e.g.:
     ![MircoVerse architecture](./assets/architecture-diagram.png)
     or an embedded draw.io / Excalidraw / Mermaid export. -->

_(architecture diagram goes here)_

---

## System Overview

This is a **game server API**, not an agent runner. The server owns world state and game logic.
Agents are external processes run by users on their own machines using their own LLM API keys.
Agents interact with the world by calling REST endpoints. The server never calls the agent.

```
User's Machine                         AWS (Game Server)
──────────────────                     ──────────────────────────────────
Agent Process                          API Gateway
 ├── runs user's LLM (their cost)  →   ├── auth, throttling, validation
 ├── calls GET /world/observe          └── routes to Lambda functions
 ├── calls POST /action                        ↓
 └── calls POST /reflection            Lambda Functions
                                        ├── state-reader
                                        ├── action-receiver
                                        ├── registration
                                        └── Step Functions (tick resolution)
                                                ↓
                                        Aurora Serverless v2 + RDS Proxy
                                        EventBridge Scheduler (tick clock)
```

---

## World Representation

The world is a 2D grid representing an arid, resource-scarce environment. Each cell is a row in
`world_cells`. The full grid is served to the frontend. Agents only receive their local FOV. (The
*mechanical* world is genre-neutral by design; narrative framing is a manipulated variable, not
baked into the schema — see [`World.md` §1, §12](./World.md).)

```
Cell {
    x, y          : int
    terrain       : "desert" | "oasis" | "mountain" | "settlement" | "ruins"
    water         : int
    food          : int
    goods         : int                  -- non-survival status/wealth ("spice" in the genre-loaded skin)
    passable      : bool
    known_name    : string | null       -- null until any agent discovers it
}
```

World state is **not stored as a JSONB blob**. Each cell is its own row in `world_cells`.
Step 7a (World State Writer) only writes rows for cells that changed that tick (~50-200 rows),
not the full grid. This avoids rewriting all cells on every tick.

**FOV is returned as a structured JSON neighborhood array**, not an image.
A radius-5 FOV covers ~121 cells at ~8-10KB per agent.

```json
{
  "position": [23, 47],
  "neighborhood": [
    [{"terrain": "desert", "water": 0, "agents": []}, ...],
    [{"terrain": "desert", "water": 0, "agents": ["bob_456"]}, ...]
  ],
  "own_resources": {"water": 5, "food": 2},
  "last_action_result": {"status": "success", "detail": "moved north"},
  "tick": 42,
  "tick_ends_at": "2026-05-30T12:01:00Z"
}
```

Known locations are stored in a separate `agent_known_locations` table, not embedded in
the FOV response. The FOV only returns what is currently visible.

### Known Locations and Fog of War

- Agents start knowing only their spawn location.
- A location enters `agent_known_locations` when the agent visits it or another agent tells them.
- Agents can only submit goal-directed movement toward a known location.
- Unknown territory requires directional exploration (move north, south, etc).
- This creates natural information asymmetry and social value in sharing knowledge.

---

## Identity / Soul File

Users submit a soul file at registration. This is the agent's immutable starting identity.
Over the experiment, the agent submits reflections that produce new identity snapshots.
Drift is measured by comparing snapshots to the original.

### Soul File Schema

```yaml
core_values:
  - "Never harm innocents"
  - "Loyalty to my tribe above all"
personality:
  - compassionate
  - cautious
moral_boundaries:
  - "Will not steal"
  - "Will not kill except self-defense"
goals:
  - "Protect my family"
  - "Find a reliable water source"
```

### Identity Tracking — Three Separate Concerns

| Concern | Storage | Mutability |
|---|---|---|
| Original soul file | Aurora `agents.original_soul` | Immutable — enforced by DB rule |
| Current identity | Aurora `agents.current_identity` | Updated each reflection |
| Drift audit log | Aurora `identity_snapshots` | Append-only |

S3 is not used. Soul files are small structured JSON (~2KB). Aurora handles them directly.
Immutability of `original_soul` is enforced at the database level with a **`BEFORE UPDATE`
trigger that raises**, not a rewrite rule:

```sql
CREATE OR REPLACE FUNCTION protect_original_soul()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.original_soul IS DISTINCT FROM NEW.original_soul THEN
        RAISE EXCEPTION 'original_soul is immutable (agent_id=%)', OLD.agent_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_protect_original_soul
    BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION protect_original_soul();
```

> **Why a trigger, not `CREATE RULE ... DO INSTEAD NOTHING`.** A `DO INSTEAD NOTHING` rule does
> not protect the *column* — it rewrites the statement so the **entire matching row's UPDATE is
> silently dropped**. An `UPDATE agents SET position_x=…, original_soul=…` would lose the position
> write too, and the caller would believe it succeeded. The trigger fails **loudly** at the
> application layer, surfacing any attempt to breach identity integrity instead of hiding it.

### Drift Measurement

- **Runtime**: at each reflection, compute cosine similarity between original soul file
  embedding and new identity embedding. Store as `drift_score` float. Fast and cheap.
- **Post-experiment**: full NLP analysis — value-level diff, behavioral alignment score,
  social influence graph. Run against Aurora after all ticks complete.

Do not run heavy NLP during the simulation. Store raw snapshots and analyze after.

> **Embedding is a server-side dependency (operator cost, not agent cost).** Computing
> `drift_score` requires an embedding model call at reflection time. This is the *one* place the
> server invokes a model, so it is an explicit operator-borne cost and latency — it does **not**
> contradict the "users bear all LLM cost" framing, but it is not free either. Default:
> **Amazon Bedrock Titan/Cohere embeddings** invoked from the reflection Lambda (keeps it in-VPC,
> no extra vendor). ~1000 agents × (ticks/N) reflections is a small, bursty embedding load. The
> call is off the tick-resolution critical path (it runs on the reflection write, not in Step
> Functions), so it never blocks a tick.

---

## Agent Memory Model

The engine stores three layers of agent memory. The distinction between objective (what
happened) and subjective (what the agent chose to remember) is itself a research signal.

### Short-Term Memory (Objective — Engine Owned)

`agent_tick_results` is an ephemeral serving table. It holds the precomputed FOV and
action outcome for the current tick only. Rows are retained briefly (Step 0 deletes tick
N−2 and older) so an agent that reads slightly late still finds its row, then they age out.
The full history is recoverable by replaying `action_log` through the resolver —
`agent_tick_results` is a serving cache, not a record of truth.

### Long-Term Memory (Subjective — Agent Selected)

Each tick, the agent may submit a `memory_update` **delta** alongside its action — append one entry,
update one line, or nothing. It never re-submits the whole store; persistence is server-side. This is
what the agent *chose* to remember — written in the agent's own words. Stored in `agent_memory` as
**typed markdown** (`memory_type` ∈ `event | relationship | reflection`; see [`World.md` §7](./World.md))
so the subjective layer is not collapsed into one blob. Retrieval is **index-driven and agentic** (the
agent judges relevance over a compact index — no embedding/vector search). The engine never writes to
this table on the agent's behalf. Working ("short-term") memory is **not** stored here — it is the
per-tick FOV the engine already computes (Short-Term Memory, above).

### Identity Memory (Reflective — Agent-Revised, Engine-Measured)

This layer separates **who the agent becomes** (agent-driven) from **how we measure it**
(engine-driven). See [`World.md` §7 & §9](./World.md) for the full research rationale; the
mechanism is:

**Agent-driven revision (organic).** Identity is mutable by design — `current_identity` evolves as
experience accumulates, because long-horizon drift is the phenomenon under study. Revision is
**agent-initiated and importance-triggered**, not on an engine clock: the agent accumulates memories
(each with an *importance* score), and when accumulated importance crosses a threshold it may reflect
and `POST /reflection` a revised identity. The engine **never forces, gates, or schedules** this —
there is no `needs_reflection` flag, and `POST /action` is **never blocked** on reflection. Forcing
it would introduce a demand characteristic and bias the sampling rate by the very variable measured.

**Engine-driven measurement (uniform).** Independently, every N ticks Step 9 takes a **measurement
snapshot** — it copies whatever `current_identity` currently is into `identity_snapshots`
(`trigger = engine_measurement`) and the offline pipeline scores behavior against it. This requires
nothing of the agent and produces the uniform longitudinal series analysis needs.

So `identity_snapshots` accrues two kinds of rows: `agent_revision` (the agent chose to change, with
its authored new identity) and `engine_measurement` (the engine sampled the current state on cadence).
A final `forced_end` snapshot is taken for every agent at experiment end (see Experiment Lifecycle).

### Why the Gap Between Layers Matters

An agent that experienced violence but recorded it neutrally in long-term memory is drifting
differently from one that recorded it as justified. The engine's objective record (action_log)
versus the agent's subjective record (agent_memory) is an analytically meaningful signal.

---

## Tick System

### Full Tick Flow

```
SETUP
├── 1000 soul files registered → stored in Aurora
└── Agents spawned: positions assigned, resources initialized in world_cells

T=0s    EventBridge Scheduler fires → attempts to acquire tick lock:
        UPDATE tick_state SET window_open = FALSE
        WHERE tick_number = N AND window_open = TRUE
        → 1 row updated: this caller owns tick resolution → start Step Functions
        → 0 rows updated: another execution already running → exit immediately

        Step Functions state machine runs (Steps 0-9)
        On completion: tick_state row for N+1 inserted with window_open = TRUE

T=0-30s  Action window open
        ├── Agents call GET /world/observe
        │   └── reads precomputed row from agent_tick_results → instant response
        │       response includes tick_ends_at
        ├── Agent runs LLM on their machine (their latency, their cost)
        ├── Agent calls POST /action → action-receiver Lambda → Aurora action_log
        │   INSERT ... ON CONFLICT (agent_id, tick_number) DO NOTHING
        │   → 0 rows inserted ⇒ already submitted this tick ⇒ reject 429
        │   → 1 row inserted  ⇒ atomically bump tick_state.submitted_count and
        │                       test the early-close condition in ONE statement
        │                       (no race-prone read-then-write — see Early Window Close)
        └── Agent sleeps until tick_ends_at

T=30s   (or earlier if all agents responded)
        EventBridge fires → attempts same conditional lock
        → If early close already locked it → exits immediately (no double execution)
        → If not yet locked → acquires lock → starts Step Functions
```

### Early Window Close

Early close must not re-`COUNT` the table on every insert. At 1000 agents that is ~O(n²)
index scans per tick, and a read-then-trigger block lets two near-simultaneous final inserts
both observe `count == active_agent_count` and both fire Step Functions. Instead, the close
decision is folded into the **same atomic statement** that records the action, using a
`submitted_count` counter on `tick_state`:

```sql
-- 1) Record the action. ON CONFLICT makes double-submission a no-op (0 rows).
INSERT INTO action_log (log_id, agent_id, tick_number, action_type, params, submitted_at, status)
VALUES ($1, $2, $3, $4, $5, NOW(), 'accepted')
ON CONFLICT (agent_id, tick_number) DO NOTHING;
-- (Lambda: if 0 rows affected → return 429, do nothing further.)

-- 2) Only on a real insert: atomically bump the counter AND flip the lock iff we are
--    the last expected submitter. RETURNING tells THIS caller whether it won the close.
UPDATE tick_state
SET    submitted_count = submitted_count + 1,
       window_open  = CASE WHEN submitted_count + 1 >= active_agent_count THEN FALSE ELSE window_open END,
       tick_ends_at = CASE WHEN submitted_count + 1 >= active_agent_count THEN NOW()  ELSE tick_ends_at END,
       closed_at    = CASE WHEN submitted_count + 1 >= active_agent_count THEN NOW()  ELSE closed_at    END
WHERE  tick_number = $3 AND window_open = TRUE
RETURNING (NOT window_open) AS i_closed_the_window;
```

`UPDATE` takes a row lock, so the increment is serialized: exactly one caller observes
`submitted_count + 1 >= active_agent_count` **while `window_open` is still TRUE**, gets
`i_closed_the_window = TRUE`, and is the only one that calls `trigger_step_functions`.
Every other caller either sees `window_open` already FALSE (0 rows returned) or
`i_closed_the_window = FALSE`. No double execution, no table re-count.

**`active_agent_count` — authoritative source.** This is *not* the registered population; it
is the count of agents with `status = 'active'` (excluding `dead` and `idle`) **as of the start
of this action window**. Step 2 (Death & Status) computes it during resolution, and Step 9
writes it onto the `tick_state` row for tick N+1 alongside `window_open = TRUE`. Reading a stale
or population-wide count is the classic bug that makes early close *never fire* (deaths mean the
live count is always below the registered count) — pinning it to the per-tick `tick_state` value
avoids that.

Agents always use the server's `tick_ends_at` from responses, not a locally computed value.
Agents that do not submit within the window default to `{"action": "wait"}`.

### Double Trigger Prevention

The conditional `UPDATE ... WHERE window_open = TRUE` is a single atomic PostgreSQL
operation. Both EventBridge and the early-close path use it (early close folds the
completeness test into the same statement — see Early Window Close). Only one caller flips
`window_open` from TRUE and proceeds; everyone else sees it already FALSE and exits. No
distributed lock service needed.

> **Note on who knows the tick number.** EventBridge Scheduler fires on a wall clock and does
> not carry `N`. The lock-acquirer first reads the open tick
> (`SELECT tick_number FROM tick_state WHERE window_open = TRUE`, equivalently
> `simulation_state.current_tick`) and then runs the conditional `UPDATE` against it.

### One Action Per Tick

Enforced at two layers:

1. **Lambda**: `INSERT ... ON CONFLICT DO NOTHING` — 0 rows affected ⇒ already submitted ⇒ 429
2. **Database**: unique constraint as the hard guarantee that backs the `ON CONFLICT`

```sql
CREATE UNIQUE INDEX one_action_per_tick ON action_log (agent_id, tick_number);
```

```json
{
  "action": {
    "type": "move | trade | attack | talk | wait | explore",
    "params": {}
  },
  "memory_update": {
    "type": "append",
    "content": "I chose to share water despite being low."
  }
}
```

> **Canonical memory path: embedded `memory_update` on `POST /action`.** Memory is written as an
> optional field on the action submission, not via the standalone `POST /memory` endpoint. This
> keeps "what I did" and "what I chose to remember about doing it" in **one atomic write per tick**,
> tied to the same `tick_number`, which is exactly the objective-vs-subjective pairing the research
> depends on (see [`World.md` §7](./World.md)). `POST /memory` is retained only as a convenience
> alias for clients that submit memory separately; it writes the same `agent_memory` row and is
> subject to the same one-entry-per-tick rule. It does **not** count as the tick's action and does
> not satisfy the reflection gate.

**Reflection is not gated or rate-limited.** `POST /reflection` is accepted whenever the agent
chooses to submit one (it is agent-initiated and importance-triggered — see Agent Memory Model).
It writes a new `current_identity` and an `identity_snapshots` row with `trigger = agent_revision`.
It does **not** consume the tick's action and does **not** block `POST /action`. The only
engine-scheduled writes to this layer are Step 9's `engine_measurement` snapshots and the final
`forced_end` snapshot at experiment end.

---

## Tick Resolution — Step Functions State Machine

The Tick Resolver is a Step Functions state machine orchestrating focused Lambdas in
sequence. Steps communicate via `tick_scratch` in Aurora — **not** the Step Functions
context payload — to avoid the hard 256KB state payload limit.

### Why tick_scratch, Not Context Payload

Step Functions has a hard 256KB limit on the JSON passed between states. At 1000 agents,
positions + damage maps + messages + cell updates easily exceeds this. The context payload
only carries `{"tick": 42}`. All inter-step data lives in `tick_scratch`.

### State Machine

```
EventBridge Scheduler / early-close event
    ↓
Conditional tick lock acquired
    ↓
Step Functions: Tick Resolution State Machine
    │
    ├── Step 0: Cleanup
    │   deletes tick_scratch rows for tick N-2 and older
    │   deletes agent_tick_results rows for tick N-2 and older
    │   (agent_tick_results is ephemeral — replayable from action_log)
    │
    ├── Step 1: Environmental Update
    │   reads:   world_cells, simulation global_events
    │   computes: water PRODUCTION (Siphon re-stock to scheduled output — hard set, unused lost;
    │             oasis regen toward cap — World.md §3), resource depletion, new storm/drought events
    │   writes:  tick_scratch("hazard_zones"), tick_scratch("cell_updates")
    │   note:    production runs BEFORE the action resolvers consume — the resolver only drains.
    │
    ├── Step 2: Death & Status Checks
    │   reads:   agents.resources, tick_scratch("hazard_zones")
    │   computes: starvation, thirst, hazard deaths; the live active-agent count
    │   writes:  tick_scratch("dead_agents"), tick_scratch("active_agents"),
    │            tick_scratch("active_agent_count")  -- consumed by Step 9 for next tick's window
    │
    ├── Step 3: Movement Resolver
    │   reads:   action_log (move actions), tick_scratch("active_agents")
    │   resolves: cell contention — multiple agents targeting same cell
    │             winner chosen by reproducible tick seed (deterministic replay)
    │   writes:  tick_scratch("positions"), tick_scratch("movement_results")
    │
    ├── Step 4: Attack Resolver
    │   reads:   action_log (attack actions), tick_scratch("positions", "active_agents")
    │   resolves: simultaneous attacks, adjacency checks post-movement
    │   writes:  tick_scratch("damage_map")
    │
    ├── Step 5: Trade Resolver
    │   reads:   action_log (trade actions), tick_scratch("positions", "active_agents")
    │   resolves: mutual consent, adjacency, resource availability
    │   writes:  tick_scratch("completed_trades"), tick_scratch("resource_changes")
    │
    ├── Step 6: Conversation Resolver
    │   reads:   action_log (talk actions), tick_scratch("positions", "active_agents")
    │   resolves: message delivery, location knowledge sharing
    │   writes:  tick_scratch("messages_delivered"), tick_scratch("location_reveals")
    │
    ├── Step 7a: World State Writer (small atomic transaction)
    │   reads:   tick_scratch("cell_updates", "positions", "damage_map", "resource_changes")
    │   writes:  world_cells (changed cells only — not full grid)
    │             agents (positions, resources, status)
    │   transaction kept small: world geometry + live agent state only
    │
    ├── Step 7b: Audit Writer (outside main transaction)
    │   reads:   tick_scratch (all keys), action_log for current tick
    │   writes:  action_log.result + resolved_at (audit data, not live state)
    │             agent_known_locations (new discoveries from conversations)
    │
    ├── Step 8: FOV Precomputer (Step Functions Map — BATCHED, not per-agent)
    │   reads:   world_cells, agent positions (committed in 7a)
    │   computes: 11×11 neighborhood per agent, in ~5-10 batch workers (not 1000)
    │   writes:  agent_tick_results via set-based bulk insert per batch
    │   note:    no inter-agent conflicts; see "Step 8: Batched, Not Per-Agent" below
    │
    ├── Step 9: Tick Advance
    │   inserts: tick_state row for tick N+1
    │            (window_open = TRUE, tick_ends_at = NOW()+interval,
    │             active_agent_count = tick_scratch("active_agent_count"), submitted_count = 0)
    │   ensures: next action_log range partition exists (idempotent — see schema)
    │
    └── Step 9b: Measurement Snapshot (every N ticks only; see World.md §9)
        when N | tick_number: snapshot current_identity → identity_snapshots
                 (trigger = engine_measurement, drift_score = cosine tripwire via Bedrock).
        Engine-driven and uniform; requires nothing of the agent. Independent of any
        agent-initiated reflection (agent_revision snapshots arrive via POST /reflection).
```

### Error Recovery

Every step has a Step Functions Catch block. On any unhandled exception:

```
Catch → Lambda: Tick Error Handler
        ├── writes to tick_errors (tick, step, error, timestamp)
        ├── defaults all agents to wait this tick
        ├── runs Step 7a with safe defaults (no movement, no damage)
        ├── runs Step 8 (agents still receive their FOV)
        └── runs Step 9 (simulation advances — never gets stuck)
        └── publishes to SNS for operator alert
```

The simulation never stalls. A step failure degrades to a no-op tick.

### Conflict Resolution Rules

**Movement (Step 3) — cell contention:**
```
Multiple agents targeting same cell:
→ Winner chosen by hash(tick_seed + agent_id) — deterministic, reproducible
→ Losers remain at original position
→ All receive outcome in agent_tick_results
```

**Attacks (Step 4) — simultaneous combat:**
```
A attacks B while B attacks A → both take damage (symmetric)
A attacks B while C attacks B → B takes damage from both
Target not adjacent after movement → attack fails silently
```

**Trades (Step 5) — mutual consent:**
```
Both parties must have submitted trade actions naming each other
One-sided submission → fails, no transfer
Both alive and adjacent after movement → trade completes
Either dead or not adjacent → trade fails
```

**Conversations (Step 6):**
```
A talks to B while B talks to C → both messages deliver same tick
B cannot respond to A until next tick
```

### Step 8: Batched, Not Per-Agent

A naïve Step 8 uses a Step Functions Map state with one parallel branch **per agent** — 1000
concurrent Lambda invocations, each doing a single-row read of `world_cells` and a single-row
write to `agent_tick_results`. At 1000 agents this is the wrong shape:

- 1000 simultaneous connections slam **RDS Proxy** and serialize on Aurora CPU / row contention,
  erasing the benefit of precomputing.
- The Map state pays Lambda invocation + warm-start overhead 1000× per tick.

Instead, **shard agents into a small fixed fan-out** (~5–10 workers via a Map over batches, e.g.
by `agent_id` hash bucket). Each worker handles 100–250 agents and uses **set-based SQL**: one
region read covering the batch, FOV JSON assembled in the worker, then a single bulk
`INSERT INTO agent_tick_results (...) SELECT ...` (or multi-row insert) per batch. Postgres set
operations over 250 agents run orders of magnitude faster than 250 round-trips, and connection
count drops from 1000 to ~10.

> The 11×11 *nested neighborhood JSON* is awkward to assemble in pure SQL, so the realistic split
> is: **bulk-fetch** the cells the batch needs in one query, **assemble** each agent's FOV object
> in the worker, **bulk-write** the batch. The principle is "few set-based workers," not
> "one INSERT…SELECT does everything."

This is also why provisioned concurrency belongs **here** (a known, bounded fan-out that fires
every tick) rather than spread across all step Lambdas (see Lambda Provisioned Concurrency).

### End-of-Tick Delivery

Step 8 precomputes all results before the action window opens. 1000 agents waking
simultaneously each get an instant Aurora read of their precomputed row (~5ms).

**Fairness — the visibility barrier is Step 9, not "Step 8 finished."** Because Step 8 writes in
batches (see "Step 8: Batched, Not Per-Agent"), batch A's `agent_tick_results` rows land slightly
before batch B's. Write-ordering after the Step 7a commit guarantees no agent ever sees *stale,
mid-resolution* state — but it does **not**, on its own, make the new tick readable to every agent
at the same instant: a fast-polling batch-A agent could read its new FOV a few hundred ms before a
batch-B agent. That skew confers no advantage by itself (action resolution is simultaneous and
seeded — submitting earlier wins nothing — and the N+1 action window is not open yet), but the
contract must not *depend* on agents being well-behaved, since the client controls its own polling.
So the authoritative barrier is `tick_state.window_open` for tick N+1, which **Step 9 flips to TRUE
in one atomic statement only after every Step 8 batch has committed**: `GET /world/observe` serves
the N+1 row only once that flag is set. Step 8's batching skew is therefore invisible to agents —
every view becomes readable at the same instant — and a greedy poll loop just sees "window not open"
(plus per-key throttling) until the barrier lifts.

---

## Experiment Lifecycle

```
States: REGISTRATION → RUNNING → PAUSED → ENDED
```

| Endpoint | Action |
|---|---|
| `POST /admin/simulation/start` | Validate soul files, assign spawn positions, initialize world_cells, create tick 0 row, enable EventBridge rule |
| `POST /admin/simulation/pause` | Disable EventBridge rule — current tick completes first |
| `POST /admin/simulation/resume` | Re-enable EventBridge rule |
| `POST /admin/simulation/end` | Disable EventBridge, wait for current tick, force final identity snapshot for ALL active agents, set status = ended |

`/end` captures the final soul file for every agent regardless of when they last submitted
a reflection. This is the primary research artifact — it must not depend on agents
having recently submitted voluntarily.

---

## Movement

- **Incremental**: agents move one cell per tick (terrain may cost additional ticks).
- **Goal-directed**: agent submits `{"toward": [x, y]}` — only valid for known locations.
- **Directional**: agent submits `{"direction": "north"}` for exploration of unknown areas.
- **No teleportation**: emergent encounters during travel are the primary moral pressure source.

### Terrain Movement Cost

| Terrain | Water cost | Food cost | Ticks to cross |
|---|---|---|---|
| Desert | 2 | 1 | 1 |
| Mountain | 1 | 2 | 2 |
| Oasis | 0 | 0 | 1 |
| Settlement | 0 | 0 | 1 |

---

## AWS Architecture

### Components

```
API Gateway
├── Agent routes (/api/v1/agents/*, /world/*, /simulation/status):
│   per-agent API key auth, throttling, request validation
└── Admin routes (/api/v1/admin/*): SEPARATE auth — NOT an API key.
    AWS IAM (SigV4) via an admin IAM role, fronting a small operator group.
    Rationale: admin endpoints start/end the experiment, dump the full world,
    and read any agent's drift history — the most sensitive surface, so it must
    not share the agent key mechanism. (Cognito user pool is an alternative if a
    human-facing admin UI is later needed.)

Lambda Functions
├── registration      — POST /agents/register
├── state-reader      — GET /world/observe, GET /agents/{id}/status
├── action-receiver   — POST /action, POST /reflection, POST /memory
└── (reflection path also calls Bedrock embeddings to compute drift_score)

Amazon Bedrock (embeddings)
└── Titan/Cohere embedding model, invoked by the reflection path only.
    Operator-borne cost; off the tick-resolution critical path.

RDS Proxy
└── connection pooler — prevents Aurora connection exhaustion
    under 1000 concurrent Lambda instances

Aurora Serverless v2
└── autoscales in 0.5 ACU increments
    near-zero between ticks, bursts during Step Functions resolution
    can scale to 0 ACU (auto-pause) when truly idle, but with 30–60s ticks
    it never idles long enough to pause — effective floor is the warm ACU during a run

Step Functions Standard Workflow
└── 10 steps per tick (Steps 0-9, see Tick Resolution section)
    context payload carries only {"tick": N} — inter-step data in tick_scratch
    every step has Catch → error handler (simulation never stalls)
    triggered by EventBridge Scheduler OR early-close path

EventBridge Scheduler
└── fires every 30s (configurable)
    rule enabled/disabled by lifecycle admin endpoints
```

### API Authentication

- **Agent keys** issued at registration are **high-entropy random tokens** (≥128 bits, e.g.
  `secrets.token_urlsafe(32)`). Only their SHA-256 is stored (`agents.api_key_hash`); the
  plaintext is returned once and never persisted. High entropy is what makes an unsalted, fast
  hash safe here — there is nothing to brute-force. (Do **not** issue low-entropy or
  human-chosen keys against this scheme.)
- **Admin** routes use AWS IAM / SigV4, a separate mechanism from agent keys (see API Gateway above).

### Lambda Provisioned Concurrency

Step Functions Lambdas fire on a predictable schedule, so cold starts are addressable. But
provisioned concurrency bills 24/7, so target it rather than blanket-applying it:

- **Steps 0–7, 9 run sequentially, once per tick.** A small warm pool (or SnapStart for
  JVM/Python) keeps these warm cheaply; their cold starts are mostly a one-time cost per pool,
  not 500ms × every step × every tick.
- **Step 8 is the real fan-out** — the ~5–10 batch workers (see "Step 8: Batched, Not Per-Agent")
  all fire at once each tick. **This is where provisioned concurrency earns its cost**, because
  concurrent cold starts here directly delay end-of-tick delivery.

Reserve provisioned concurrency for the bounded Step 8 fan-out; warm the sequential steps with a
minimal pool. (This also corrects the older "500ms × 10 sequential steps = 5s" estimate — sequential
cold starts amortize across a warm pool; the parallel fan-out is the latency that actually compounds.)

**Concurrency, precisely.** A *worker* here is one concurrent invocation of the single Step 8 Lambda:
a Step Functions Map state runs the same function across the agent batches in parallel, and each
parallel branch is a separate execution environment. It is **not** 5–10 different functions. A *cold
start* is the one-time cost of building a fresh environment before the handler runs — download code →
boot the runtime → run init (imports, the DB/RDS-Proxy client) → then handle. *Provisioned
concurrency* keeps N environments pre-initialized and parked so requests up to N skip that init
entirely (the double-digit-ms path); anything beyond N spills to on-demand and may cold-start.

**Treat it as a load-test-gated hedge, not a 24/7 default.** With 30–60s ticks, Lambda very likely
keeps the Step 8 environments warm *between* ticks anyway (idle reclaim is on the order of minutes),
so in steady state the cold-start tax may only appear on tick 1, on the first tick after a `pause`,
or when scaling past the warm set (e.g. the 10k breakage probe). Provisioned concurrency bills 24/7,
so per the discipline rule below, turn it on **only if the load test's p99 tick-latency graph shows a
cold-start tail** — and size it from the measured Step 8 fan-out width plus AWS's recommended ~10%
buffer. Provisioning speculatively because "a function is on the critical path" is exactly the
unjustified-component habit this architecture rejects.

### Step Functions: Standard Workflow

Use Standard (not Express):
- Full execution history per tick — essential for debugging corrupt world state
- ~11 state transitions/tick (Steps 0–9, with 7a/7b) × 1000 ticks ≈ 11k transitions — well within limits
- Cost: ~$0.025 per 1000 state transitions — negligible

### Why No SQS

Action-receiver writes directly to Aurora via RDS Proxy:
- Action Receiver writes one row (~20ms) — no heavy computation per message
- RDS Proxy handles connection burst (the only problem SQS would solve here)
- Priority ordering enforced by Step Functions resolution order, not queue order
- API Gateway handles throttling at entry point

### Why Aurora Serverless v2

- Relational schema with foreign keys across agents, actions, world cells
- Post-experiment analytics need JOINs (action_log JOIN identity_snapshots)
- Bursty load profile — pays for burst only, not 24/7 provisioning
- DynamoDB throughput advantage irrelevant at this latency tolerance

### Why No ALB

ALB is cost-effective above ~3-5M requests/day. Total experiment: 1000 agents × 1000
ticks × 5 calls = 5M requests for the whole experiment. API Gateway handles this with
built-in auth and throttling that ALB lacks natively.

---

## Database Schema (Aurora)

```sql
CREATE TABLE agents (
    agent_id          UUID PRIMARY KEY,
    display_name      VARCHAR(100),
    registered_at     TIMESTAMP,
    original_soul     JSONB,               -- immutable, enforced by DB rule below
    current_identity  JSONB,               -- updated each reflection
    position_x        INT,
    position_y        INT,
    resources         JSONB,               -- {water, food, goods}
    status            VARCHAR(20),         -- active | dead | idle
    api_key_hash      VARCHAR(100),        -- SHA-256 of a high-entropy random token (see API Auth)
    webhook_url       VARCHAR(500)         -- reserved; NOT used — server never calls the agent
);

-- Immutability enforced by a BEFORE UPDATE trigger (raises loudly), not a
-- DO INSTEAD NOTHING rule (which would silently drop the whole row's update).
CREATE OR REPLACE FUNCTION protect_original_soul()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.original_soul IS DISTINCT FROM NEW.original_soul THEN
        RAISE EXCEPTION 'original_soul is immutable (agent_id=%)', OLD.agent_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_protect_original_soul
    BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION protect_original_soul();

-- One row per cell, updated in place — no full-grid JSONB blob
CREATE TABLE world_cells (
    x             INT,
    y             INT,
    terrain       VARCHAR(20),
    water         INT,
    food          INT,
    goods         INT,                   -- non-survival status/wealth ("spice" in the genre-loaded skin)
    passable      BOOLEAN,
    known_name    VARCHAR(100),
    PRIMARY KEY (x, y)
);

-- Separate table — not JSONB in agents row (avoids unbounded growth per agent)
CREATE TABLE agent_known_locations (
    agent_id          UUID REFERENCES agents(agent_id),
    x                 INT,
    y                 INT,
    location_type     VARCHAR(50),
    discovered_tick   INT,
    PRIMARY KEY (agent_id, x, y)
);

CREATE TABLE identity_snapshots (
    snapshot_id       UUID PRIMARY KEY,
    agent_id          UUID REFERENCES agents(agent_id),
    tick_number       INT,
    snapshot_at       TIMESTAMP,
    identity_json     JSONB,
    drift_score       FLOAT,               -- cosine distance from original_soul (online tripwire only)
    trigger           VARCHAR(20)          -- agent_revision | engine_measurement | forced_end
);

-- Partitioned for analytics performance
CREATE TABLE action_log (
    log_id            UUID PRIMARY KEY,
    agent_id          UUID REFERENCES agents(agent_id),
    tick_number       INT,
    action_type       VARCHAR(50),
    params            JSONB,
    result            JSONB,               -- filled by Step 7b
    submitted_at      TIMESTAMP,
    resolved_at       TIMESTAMP,
    status            VARCHAR(20)          -- accepted | rejected | timeout | defaulted
) PARTITION BY RANGE (tick_number);

-- Partition lifecycle MUST be automated or inserts fail at an unprovisioned tick boundary.
-- Use pg_partman to pre-create partitions ahead of the tick clock (premake several ranges),
-- AND keep a DEFAULT partition as a safety net so an insert never errors on a missing range:
--   CREATE TABLE action_log_default PARTITION OF action_log DEFAULT;
-- Step 9 additionally performs an idempotent "ensure next partition exists" check when it
-- advances the tick, so partition creation can never lag the simulation.

CREATE UNIQUE INDEX one_action_per_tick ON action_log (agent_id, tick_number);

-- Ephemeral serving table — rows deleted after 2 ticks by Step 0
-- Replayable from action_log + world_cells if needed — not a record of truth
CREATE TABLE agent_tick_results (
    agent_id          UUID,
    tick_number       INT,
    world_fov         JSONB,
    action_result     JSONB,
    events            JSONB,               -- messages received, things witnessed
    fetched_at        TIMESTAMP,           -- set when agent calls GET /world/observe
    PRIMARY KEY (agent_id, tick_number)
);

-- Inter-step scratch space — avoids Step Functions 256KB context payload limit
CREATE TABLE tick_scratch (
    tick_number       INT,
    key               VARCHAR(100),        -- "positions", "damage_map", "dead_agents", etc.
    value             JSONB,
    PRIMARY KEY (tick_number, key)
);

CREATE TABLE tick_state (
    tick_number        INT PRIMARY KEY,
    window_open        BOOLEAN DEFAULT TRUE, -- conditional lock for double-trigger prevention
    active_agent_count INT,                  -- live agents as of window start; set by Step 9 from Step 2
    submitted_count    INT DEFAULT 0,        -- atomically incremented per accepted action (early-close)
    opened_at          TIMESTAMP,
    closed_at          TIMESTAMP,
    tick_ends_at       TIMESTAMP             -- updated on early close
);

CREATE TABLE tick_errors (
    error_id          UUID PRIMARY KEY,
    tick_number       INT,
    step_name         VARCHAR(50),
    error_message     TEXT,
    occurred_at       TIMESTAMP
);

-- Long-term subjective memory: what agent chose to remember (not what engine recorded).
-- A purpose-built MARKDOWN layer (no vector DB / no Mem0). The subjective layer is TYPED into
-- events / relationships / reflections markdown files (see World.md §7); each entry is one row.
-- Retrieval is index-driven and AGENTIC: the agent reads a compact index and judges relevance
-- itself — no embedding model, no engine-side vector search. The engine only STORES the submitted
-- memory delta for the audit/eval record. `importance` ranks the index AND accumulates toward the
-- agent's reflection trigger (World.md §7). In the controlled arm the markdown reference config
-- (file taxonomy + importance rubric + index format) is fixed as a control; the open arm allows
-- bring-your-own memory (World.md §10.5). NOTE: identity (the reflective layer) is NOT stored here
-- — it lives in agents.current_identity / identity_snapshots; this table is the subjective layer only.
CREATE TABLE agent_memory (
    memory_id         UUID PRIMARY KEY,
    agent_id          UUID REFERENCES agents(agent_id),
    tick_number       INT,
    memory_type       VARCHAR(16),         -- 'event' | 'relationship' | 'reflection' (the typed markdown file)
    subject_agent_id  UUID,                -- for 'relationship' rows: who the belief is about (else NULL)
    content           TEXT,                -- the markdown entry, in the agent's own words
    importance        SMALLINT,            -- 1-10 salience; high for moral/high-pressure events
    created_at        TIMESTAMP
);

CREATE TABLE simulation_state (
    id                INT PRIMARY KEY DEFAULT 1,  -- singleton row
    status            VARCHAR(20),                -- registration | running | paused | ended
    current_tick      INT,
    started_at        TIMESTAMP,
    ended_at          TIMESTAMP
);

-- ── Evaluation artifacts (written by the OFFLINE analysis pipeline, not the live engine) ──
-- The drift instrument is multi-dimensional and value-anchored (see World.md §9). These tables
-- are populated post-experiment and are re-runnable: the analysis can be revised without
-- re-running the simulation, because they derive purely from the immutable logs.

-- Per-boundary state trajectory: one row per (agent, T=0 boundary, measurement tick).
CREATE TABLE boundary_state (
    agent_id          UUID REFERENCES agents(agent_id),
    boundary_text     TEXT,                -- a specific moral_boundary/core_value from original_soul
    tick_number       INT,
    state             VARCHAR(12),         -- upheld | eroded | inverted | abandoned
    evidence_refs     JSONB,               -- action_log / agent_memory ids the judge cited
    judged_by         VARCHAR(20),         -- llm_judge | human
    PRIMARY KEY (agent_id, boundary_text, tick_number, judged_by)
);

-- Stated-vs-revealed alignment: did actions match the stated identity at each snapshot?
CREATE TABLE alignment_scores (
    agent_id          UUID REFERENCES agents(agent_id),
    tick_number       INT,
    alignment         FLOAT,               -- 0-1, professed vs enacted agreement
    violations        JSONB,               -- enumerated mismatches with evidence refs
    PRIMARY KEY (agent_id, tick_number)
);

-- Judge-vs-human validation set: the number every downstream result rests on (World.md §9.2).
CREATE TABLE judge_validation (
    item_id           UUID PRIMARY KEY,
    sampled_from      VARCHAR(30),         -- boundary_state | alignment_scores
    item_ref          JSONB,               -- pointer to the judged decision
    llm_verdict       JSONB,
    human_verdicts    JSONB,               -- multiple annotators
    agreement         FLOAT                -- per-item agreement; aggregate → reported kappa
);
```

---

## REST API Endpoints

```
-- Agent endpoints
POST   /api/v1/agents/register              submit soul file → returns agent_id + api_key
GET    /api/v1/world/observe                get precomputed FOV + last tick result
POST   /api/v1/agents/{id}/action           submit action (+ optional embedded memory_update)
POST   /api/v1/agents/{id}/reflection       agent-initiated identity revision (never gated/forced)
POST   /api/v1/agents/{id}/memory           convenience alias — append one memory entry (same agent_memory row)
GET    /api/v1/agents/{id}/status           current resources, position, status
GET    /api/v1/simulation/status            current tick, window open/closed, tick_ends_at

-- Admin lifecycle endpoints
POST   /api/v1/admin/simulation/start       spawn agents, initialize world, begin tick loop
POST   /api/v1/admin/simulation/pause       halt EventBridge after current tick completes
POST   /api/v1/admin/simulation/resume      re-enable EventBridge
POST   /api/v1/admin/simulation/end         force final snapshots for all agents, stop loop

-- Observation endpoints
GET    /api/v1/admin/world                  full world_cells grid for frontend
GET    /api/v1/admin/agents/{id}/drift      full identity snapshot history for one agent
GET    /api/v1/admin/tick/{n}/errors        errors from tick N resolution
```

---

## Scaling Path

| Phase | Agents | Tick duration | Key changes |
|---|---|---|---|
| POC | 25 | 60s | No provisioned concurrency needed |
| Beta | 100 | 60s | Add RDS Proxy, tune Aurora min ACUs |
| Production | 1000 | 30-60s | Provisioned concurrency on the Step 8 batch workers; warm pool for sequential steps |
| Large scale | 10,000 | TBD | More Step 8 batch shards, raise Lambda concurrency limit |
| Very large | 100,000 | TBD | World sharding by zone, Redis for agent_tick_results, DynamoDB for action_log |

### Scale Demonstration — load-test to 1000, run the science at 25

Two different claims need two different proofs, and only one of them costs money:

| Claim | What proves it | Marginal cost |
|---|---|---|
| **The engine is a distributed sim that holds at 1000+ agents** | A **mock-agent load test** of the tick engine | ~free |
| **Identity drifts under moral pressure (validated instrument)** | **25 real-LLM agents** | the only real spend |

The expensive part of "1000 agents" is the **LLM inference**, and that is *not on this architecture* — agents
run participant-side with their own model keys (see [`World.md` §10.5](./World.md)). The work the server actually
does — accept action intents, resolve a tick atomically, fan out state, persist — has near-zero marginal cost per
agent on the operator side. So the engine's scale can be demonstrated **without any API bill**.

**Mock agent.** A dumb HTTP loop, no model and no key: `GET` world state → `POST` a randomly chosen *valid*
action → repeat each tick. Spin up 1,000–5,000 of these (containers / a fleet of lightweight processes) to drive
the engine at production concurrency for free.

**Target numbers.** The **primary claim is 1000 agents** — the field-meaningful figure (Joon's
"Generative Agent Simulations of 1,000 People") and the number this single-Aurora design is built for.
A push to **10,000 is a deliberate stress-to-breakage probe**, not a clean success claim: the expected
limiter is the **global tick-lock serializing window-close** (the atomic submission counter), so beyond
~M agents the design needs zone-sharding (see the *Very large* row). Reporting "linear to 1000, then
here is exactly where it bends and why" demonstrates more maturity than a bigger round number. 100,000
stays aspirational — not demoed.

**Metrics to report** (the portfolio artifact is a graph of these from N=25 → 1000, with a 10k breakage probe):
- **Tick-resolution latency** — p50 / p99 ms per tick as N grows.
- **Throughput** — actions/sec sustained; Step Functions execution time per tick.
- **Concurrency correctness** — the atomic submission counter and early window-close behave under
  thousands of simultaneous `/action` submissions (no double-count, no lost close).
- **Contention-resolution correctness at scale** — movement conflicts and resource grabs resolve
  deterministically under load (seeded RNG, same inputs → same world).
- **Persistence under sustained write load** — Aurora ACU autoscaling, RDS Proxy pooling, partition
  rollover behaving at 1000-agent write rates.

**Discipline.** Every component (Step Functions, Aurora Serverless v2, RDS Proxy, provisioned concurrency) must be
justified by a real tick-resolution requirement that shows up in the load test — if a piece isn't load-bearing
under the test, cut it. A deployed, benchmarked system at modest complexity beats an elaborate diagram that never
ran. The architecture is the *credibility that this can be productionized*, not the headline — the drift finding
leads; the engine is the proof it ships. The cross-model tournament that genuinely needs 1000 *thinking* agents is
parked as a separate project in [`World.md` §10.6](./World.md).

**Bottom line:** load-test the engine to 1000+ for free; run the experiment at 25 real LLMs. Two clean claims,
neither faked.

---

## Open Decisions

- Grid size (suggest 50×50 for 25 agents, 200×200 for 1000)
- Reflection frequency minimum interval (suggest every 10 ticks)
- Vision radius (suggest 5 cells = 11×11 neighborhood)
- Whether agents can see other agents' soul files (conformity pressure vs isolation)
- Tick duration tuning based on observed LLM latency during testing
- Whether to expose a spectator WebSocket feed for real-time frontend updates
- Random seed strategy for reproducible conflict resolution (movement contention winner)

---

## Revision Notes

Changes from the initial draft, with rationale (kept for design-review traceability):

1. **`original_soul` immutability: rewrite RULE → `BEFORE UPDATE` trigger.** A
   `DO INSTEAD NOTHING` rule silently drops the *entire* matching row's UPDATE, not just the
   protected column — a combined `SET position_x=…, original_soul=…` would lose the position
   write with no error. The trigger raises loudly instead.
2. **Early window close: read-then-trigger → single atomic counter statement.** Re-`COUNT(*)`
   on every insert is ~O(n²)/tick and lets two simultaneous final inserts both fire Step
   Functions. Now an atomic `submitted_count` increment + conditional `window_open` flip with
   `RETURNING` elects exactly one closer. Added `submitted_count` + `active_agent_count` to
   `tick_state`, and pinned `active_agent_count`'s source to Step 2 → Step 9 (live agents only).
3. **Step 8 FOV: 1000-wide per-agent Map → ~5–10 set-based batch workers.** Per-agent fan-out
   storms RDS Proxy and pays 1000× invocation overhead per tick. Batched set-based inserts cut
   connections to ~10 and run far faster. Provisioned concurrency retargeted to this bounded
   fan-out rather than blanket-applied.
4. **Identity model: decoupled agent-revision from engine-measurement.** `current_identity` is
   mutable and revised **by the agent**, importance-triggered and never gated/forced (no
   `needs_reflection`, no 409 on `/action`) — forcing it biases sampling by the measured variable
   and adds a demand characteristic. Separately, Step 9b takes uniform `engine_measurement`
   snapshots every N ticks. `identity_snapshots.trigger` ∈ {agent_revision, engine_measurement,
   forced_end}. (Supersedes an earlier "mandated reflection checkpoint" design.)
5. **Evaluation instrument: value-anchored & validated, not a scalar.** Drift is measured against
   the agent's own `T=0` boundaries along four registers (per-boundary state, stated-vs-revealed
   alignment, identity-text diff, justification gap), scored by an **LLM judge validated against
   human raters** (reported κ); cosine is an online tripwire only. Added offline-pipeline tables
   `boundary_state`, `alignment_scores`, `judge_validation`; `agent_memory` carries `importance`
   for index ranking + the reflection trigger (relevance·recency·importance). See
   [`World.md` §9–10](./World.md).
6. **Memory layer: Mem0 → purpose-built typed markdown.** The subjective layer is now typed markdown
   files (`event | relationship | reflection`) in `agent_memory`, retrieved **index-driven and
   agentically** (no embedding/vector search; dropped the `embedding VECTOR` column). Working memory is
   the engine-given FOV, not agent-stored; per-tick writes are deltas. Rationale: the build-vs-rent
   case inverted once the memory system became part of the instrument — typed files keep the
   three-layer separation structural and the record human-auditable. The drift-score cosine *tripwire*
   (Bedrock embeddings, §Drift Measurement) is unaffected — it is measurement, not retrieval.
   (Supersedes the Mem0 "rent the commodity" design; see [`World.md` §7](./World.md).)
7. **Resolved open contracts:** admin auth (IAM/SigV4, separate from agent keys); drift embedding
   declared as a Bedrock operator-cost dependency off the critical path; `action_log` partition
   lifecycle (pg_partman + DEFAULT partition + Step 9 ensure-next); canonical memory path
   (embedded `memory_update` on `/action`, `POST /memory` a convenience alias); API-key entropy
   note for the SHA-256 scheme.
