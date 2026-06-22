# MircoVerse Build Spec — ground truth for all builders

You are building ONE module of a greenfield Python engine. The authoritative design is in
the repo-root docs `World.md` (rules/why), `Architecture.md` (infra/schema), `Protocol.md`
(wire contract). This file is the engineering contract between modules. **Do not contradict
the three docs; if they conflict, Protocol.md wins for the wire, Architecture.md for schema,
World.md for rules.**

## Non-negotiables (Simile-style ownership + rigor)
1. **The wire contract is frozen** in `mircoverse/contracts/` (already built & tested). Import
   and build against those Pydantic models — never redefine them.
2. **Every function you write gets a test.** Use pytest in `mircoverse/tests/`. Pure logic →
   plain unit tests. DB/HTTP logic → mark with `from mircoverse.tests.conftest import requires_db`
   and the test must SKIP (not fail) when Postgres is down.
3. **Determinism is sacred.** All stochastic resolution flows through a single seeded RNG
   passed in — never `random` module globals, never `time`-based seeds. Same manifest + same
   actions ⇒ identical world (World.md §11).
4. **Pure core, no I/O.** The world core (`mircoverse/world/`) must be pure functions over
   plain dataclasses — no DB, no network, no clock. This is what makes it testable and fast.
5. Type-hint everything. Match the existing code's style (see `mircoverse/contracts/`).
6. Return a short report: files created, test names, `pytest` result, and any doc ambiguity
   you had to resolve (state the resolution).

## Canonical vocabulary (genre-neutral — World.md §1)
Resources: `water`, `food`, `goods` (NOT "spice"). Terrain: `desert|oasis|mountain|settlement|ruins`.
The water machine is the `siphon` at the settlement cell. Narrative framing is a separate skin,
never baked into mechanics.

## Seed-run world parameters (Protocol.md §2, committed)
- Grid 50×50, integer coords `0 ≤ x,y < 50`, no teleport, Moore-8 adjacency, FOV = Chebyshev radius 2 (5×5).
- `base_drain=1`; water cost per action per Protocol.md §4.1; terrain costs per §2.2.
- Siphon at (25,25), ~37 units/tick. Engine enforces ONLY physics (on/adjacent + units available),
  never fairness.
- Death: `water<=0` ⇒ permanent death this tick; cell trends to `ruins` + becomes a death-cache.
- 8 actions: move, wait, consume, scavenge, trade, talk, attack, signal (semantics in Protocol.md §4).
- Conversation latency: msg in tick N acted on in N+1. Trade = two-tick handshake (both name each other,
  alive, adjacent post-move).

## Module dependency order (yours is one of these)
1. `world/` — pure core: dataclasses for cell/agent/world; the 8-action resolver as pure functions;
   seeded contention resolution; FOV computation. NO db. **This is where most correctness lives.**
2. `persistence/` — Postgres schema (DDL exactly per Architecture.md: agents w/ BEFORE UPDATE trigger,
   world_cells, action_log partitioned, agent_memory, identity_snapshots, tick_state, tick_scratch,
   simulation_state) + async data-access functions. `mircoverse/persistence/db.py` already exists.
   Provide `schema.sql` + a `migrate()` that applies it + DAL functions.
3. `resolution/` — the tick resolver: read accepted actions for tick N from DB → run the pure
   world-core resolver → write world state + action results + precompute next-tick observations.
   This is Architecture.md Steps 1-9 collapsed into one local orchestration function.
4. `server/` — FastAPI app implementing Protocol.md §5 endpoints exactly (register, observe, action,
   reflection, memory/{file}, simulation/status). One-action-per-tick via DB unique constraint.
5. `agents/` — (a) mock agent: dumb HTTP loop, random VALID action, for load testing; (b) reference
   agent: the §7 loop (observe → index-driven retrieve → 1 LLM call → action → maybe reflect), with a
   mock LLM so it's testable with no API key.
6. `measurement/` — engine snapshots every N ticks + cosine tripwire (tripwire may be a stub/optional
   import; do NOT add a hard embedding dependency).
7. `manifest/` — load/validate YAML experiment manifest + build the seeded RNG; world generators for
   25-agent (50×50) and 1000-agent (200×200) worlds.

## Environment — ALWAYS use the project venv (never global Python/pip)
- Run everything through `.venv/Scripts/python.exe` (Windows venv at the repo root).
- Test command: `.venv/Scripts/python.exe -m pytest mircoverse/tests -q`
- If you genuinely need a NEW dependency: add it to `pyproject.toml` `[project].dependencies`
  (you may edit pyproject ONLY to add a dep) and install it INTO the venv with
  `.venv/Scripts/python.exe -m pip install <pkg>`. Never `pip install` against global Python.
  Prefer NOT adding deps — the stack (fastapi, pydantic, asyncpg, pyyaml, httpx, pytest) is enough.
