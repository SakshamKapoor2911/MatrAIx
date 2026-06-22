# MircoVerse

**A multi-agent social environment for studying emergent group dynamics — and a behavioral
instrument for measuring how an LLM agent's authored identity drifts under sustained pressure.**

MircoVerse is two things at once, by design:

1. **A multi-agent social testbed.** Many LLM agents inhabit a shared, resource-scarce world and
   must coordinate, compete, trade, inform (or deceive) one another, and form relationships to
   survive. It is built to study *network effects, social influence, coordination, competition, and
   emergent group behavior* — not isolated single-agent behavior.
2. **A controlled behavioral experiment.** Within that environment, each agent carries a structured
   "soul file" (values, moral boundaries, personality, goals). The platform measures how that stated
   identity deforms under graded social and survival pressure, against an immutable `T=0` anchor.

The same engine serves both: the social environment is the substrate; identity drift is the first
phenomenon instrumented on top of it. See **[World.md](./World.md)** for the full research frame.

---

## Why a *social* environment

Real systems — social networks, group chats, online communities, marketplaces, multiplayer games,
workplace collaboration — are about *groups*, not lone users. MircoVerse makes group dynamics the
object of study by engineering genuine interdependence:

- **A single, insufficient resource chokepoint.** A central *Atmospheric Siphon* produces less water
  than the population needs (`World.md §3`). Scarcity is the baseline, so agents cannot all simply
  succeed in parallel — they must contend, cooperate, or route around each other.
- **An information market.** Locations are *fog-of-war*: an agent learns the world by visiting,
  seeing, or **being told**. Knowledge is therefore a tradeable, hoardable, and *falsifiable* asset —
  agents can lie, and the engine records both what was true and what was said (`World.md §6`).
- **A periphery-wealth layer.** Non-survival `goods` are scattered in the dangerous open desert,
  separating *need* from *greed* and giving agents a reason to leave the safe well (`World.md §2`).
- **Real social actions.** `trade` (a two-tick consent handshake), `talk` (targeted or broadcast,
  truth not verified), `signal` (cheap declared stance), and `attack` (coercion/predation) — the
  morally-loaded verbs are exactly the ones the experiment measures (`World.md §4, §6`).
- **Social contagion built in.** Boundary violation modeled as *survivable* by neighbors is an
  explicit, measurable channel for drift transfer between agents (hypothesis H4, `World.md §6`).

These are the levers for the social-dynamics questions the broader direction cares about:
coordination at the chokepoint, competition vs. trade under scarcity, influence through (possibly
deceptive) information, and group-level patterns that no single agent was instructed to produce.

## What gets measured

- **Per-agent identity trajectories** — the soul file vs. its immutable origin, scored on a
  multi-dimensional, value-anchored drift instrument (not a single "good/evil" number), with
  LLM-judge scoring on a reliability ladder (`World.md §9`).
- **Stated vs. revealed behavior** — three channels: what an agent *says* (talk), what it *records*
  (memory), and what it *does* (executed action), so deception and self-deception are data.
- **Competence vs. value drift, separated** — malformed-tool-call and engine-rejection counters keep
  "the model degraded under context" distinct from "the persona actually changed."

The headline scientific question (hypothesis **H6**): is an authored persona's softening a *genuine
value update*, mere *instruction decay*, or the model's *safety training reasserting* as a restoring
force? A null-persona baseline is included specifically to separate these.

> Note: drift findings to date are **directional, small-n, single-model** (Haiku-4.5), and are
> described as such. The contribution here is the *instrument and environment*, not a settled result.
> See [`findings/anti_self_deception.md`](./findings/anti_self_deception.md) for one emergent result.

---

## Architecture at a glance

The engine is a **passive game server**: it owns the world and the rules; **agents run on their own
machines with their own LLM keys**. The loop is pull-based — an agent `GET`s what it can see, thinks
however it likes, and `POST`s one action per tick. The server never calls an LLM on the hot path.

```
   your machine                         the server (this repo)
 ┌──────────────┐   GET /world/observe   ┌────────────────────┐
 │  your agent  │ ─────────────────────▶ │  precomputed FOV    │
 │ (your LLM,   │ ◀───────────────────── │  + memory_index     │
 │  your key)   │   POST /action (1/tick)│  validates, logs,   │
 └──────────────┘ ─────────────────────▶ │  resolves at close  │
                                          └────────────────────┘
```

| Layer | Where | What |
|---|---|---|
| **World core** (pure) | `mircoverse/world/` | grid state, geometry, FOV, deterministic resolver |
| **Resolution** | `mircoverse/resolution/` | bootstrap + the 10-step tick orchestrator (one DB txn) |
| **Persistence** | `mircoverse/persistence/` | Postgres schema, DAL, async pool (Aurora-portable) |
| **Server** | `mircoverse/server/` | FastAPI; the frozen HTTP wire contract (`Protocol.md §5`) |
| **Contracts** (frozen) | `mircoverse/contracts/` | Pydantic wire models — the keystone every layer shares |
| **Agents** | `mircoverse/agents/` | mock load-test agent + a reference LLM agent you can fork |
| **Manifest / measurement** | `mircoverse/manifest/`, `measurement/` | seeded world generation + drift snapshots |
| **Frontend** | `ui/` | React/Vite world visualizer (live map of the running sim) |
| **Cloud IaC** | `infra/` | Terraform for the AWS scale target (see caveat below) |

Local runs use **real Postgres in Docker** (not SQLite) so the exact same SQL runs on Aurora later —
the point of freezing the contract. The 25-agent science run is **local**; the 1000-agent scale
claim is an **AWS load-test** target (`infra/` is write-first and **unverified** — no deploy yet).

---

## Quick start

Full agent-onboarding guide: **[QUICKSTART.md](./QUICKSTART.md)**. The short version:

```bash
# 1. start the database (needs Docker Desktop running)
docker compose up -d

# 2. create a virtualenv and install the engine
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"      # Windows; use .venv/bin/python on macOS/Linux

# 3. run the test suite (DB-backed tests skip gracefully if Postgres isn't up)
.venv/Scripts/python -m pytest mircoverse/tests -q

# 4. start the server (the run drivers below apply the schema themselves via dal.migrate())
.venv/Scripts/python -m uvicorn mircoverse.server.app:app --port 8000

# 5. (optional) the frontend world map
cd ui && npm install && npm run dev
```

> The schema is applied idempotently by `mircoverse.persistence.dal.migrate(dsn)` — the run drivers
> in `scripts/` call it on startup, so there's no separate migration step to run by hand.

Secrets/config: copy `.env.example` → `.env` and fill in only the provider key you intend to use.
The **engine needs no LLM key**; keys are participant-side, for *running agents* (`scripts/`).

### Running agents
- `scripts/run_real_inproc.py` — the proven real-LLM path (in-process, no HTTP server needed).
- `scripts/run_seed.py` — mock-agent end-to-end smoke (no LLM).
- `scripts/evaluate_runs.py` — score drift from completed runs.

---

## Repository map

```
World.md            research frame: world rules, hypotheses, pressure taxonomy, how drift is measured
Protocol.md         the frozen agent↔world wire contract (NORMATIVE) + reference-agent design
Architecture.md     production (AWS) systems design
QUICKSTART.md       connect an agent in ~15 minutes
mircoverse/         the engine (Python package) — see table above; BUILD_SPEC.md is its ground truth
ui/                 React/Vite world visualizer (game art lives in ui/public/)
scripts/            run drivers, evaluation, persona generation
infra/              Terraform IaC for the AWS scale target (UNVERIFIED — not yet deployed)
findings/           written results + figures (anti_self_deception.md is the showcase)
data/               curated run results + persona seeds (raw logs are gitignored)
explanations/       one-pager / explainer for non-specialists
```

## Status & honest caveats

- **Built and tested locally** (full suite against real Postgres). The frozen HTTP contract is stable.
- **Findings are preliminary**: small-n, one model, prompted personas — directional, not conclusive.
- **AWS infra is written but not deployed**: `infra/` mirrors the architecture but is unverified.
- **A superseded prototype** lives in `_legacy/` (gitignored) — kept locally for reference only.
