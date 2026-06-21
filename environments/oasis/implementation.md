# OASIS Implementation Plan

> Integrating OASIS (Open Agent Social Interaction Simulations) into MatrAIx.
> Load MatrAIx personas → build social graph → run agents on a shared platform → collect trajectories.

---

## How OASIS Actually Works (from source code analysis)

### The Real Architecture

OASIS separates concerns into:
1. **Agents** — LLM-powered actors with a persona system prompt. Each agent is always active (the LLM decides `do_nothing` as an action). At 1M scale, activation probability gates which agents get a turn.
2. **Platform** — A single async event loop processing all actions sequentially via SQLite. This is the shared state layer — posts, follows, likes, comments all live here.
3. **Channel** — Async queue connecting agents ↔ platform. Each action gets a UUID, agent polls until response arrives.
4. **RecSys** — Controls what each agent sees when they "refresh" their feed. This is the information flow bottleneck.

### What They Actually Do for Networks

OASIS's network generation is deliberately simple:
- Load pre-curated "star" (influencer) accounts from a CSV categorized by topic
- For each regular user, iterate over their 2 topic interests
- For each star account matching that topic, follow with **flat probability 0.2**
- No affinity calculation, no personality weighting, no region similarity
- The philosophy: simple topology + LLM behavioral complexity = emergent realism

### What They Actually Do for Profiles

- Each agent has one `user_char` field: a RAG-generated narrative paragraph
- Generated via GPT-3.5 + `BAAI/bge-m3` embeddings over real Twitter bios
- Demographics: age (weighted), gender, MBTI (weighted), 2 topics from 9, 1 profession from 16
- Activity level: `[100] * 24` for ALL agents (= always active, LLM decides inaction)
- The 1M experiment overrides stars to 10% threshold

### What They Actually Do for Simulation

- `env.step(actions)`: updates recsys table → all agents act concurrently via asyncio
- Each agent: refresh feed → LLM with function calling → selected tools execute as actions
- Platform processes actions one at a time (SQLite serializes)
- All actions recorded in `trace` table with full JSON
- Semaphore (default 128) limits concurrent LLM calls

### CSV Format (the actual runtime input)

```
user_id, name, username, description, user_char, following_agentid_list,
previous_tweets, activity_level, activity_level_frequency, tweets_id
```

- `following_agentid_list`: Python list as string literal, e.g. `"[32, 55, 12]"`
- `activity_level`: `"['active'] * 24"`
- `activity_level_frequency`: `"[100] * 24"` (100 = always active in OASIS's framework)
- Parsed at runtime with `ast.literal_eval()`

---

## Our Architecture (what we're building differently)

### Key Difference from OASIS

OASIS runs everything in one Python process with async concurrency. We split into:
- **Agents in isolated Docker containers** — each agent runs as a persona-conditioned LLM process in its own container, receiving the persona via system prompt
- **Shared platform as a service** — the social media environment (SQLite + recsys + action processing) runs as a separate service that all agent containers connect to
- **Trajectory storage** — all actions and traces persisted for post-hoc analysis

This separation means:
- Agents can use different LLM backends (vLLM, OpenAI, Anthropic) per container
- Platform scales independently from agent compute
- Agent crashes don't kill the platform
- Trajectories survive agent failures

---

## Module Structure

```
environments/oasis/
├── README.md                          # Reference documentation
├── implementation.md                  # This file
├── __init__.py                        # Package root (re-exports all public API)
│
├── persona_loader/                    # MODULE 1: Load & convert personas
│   ├── __init__.py
│   ├── adapter.py                     # MatrAIx YAML → OasisUserInfo → CSV export
│   └── tests/
│       ├── __init__.py
│       ├── test_adapter.py            # 45 tests
│       └── fixtures/                  # 5 deep dummy personas (50+ dims each)
│           ├── persona_young_tech.yaml
│           ├── persona_older_healthcare.yaml
│           ├── persona_young_creative.yaml
│           ├── persona_finance_introvert.yaml
│           └── persona_rural_educator.yaml
│
├── network/                           # MODULE 2: Social graph construction
│   ├── __init__.py
│   ├── builder.py                     # Affinity graph + simple topic graph + CSV export
│   └── tests/
│       ├── __init__.py
│       └── test_builder.py            # 44 tests
│
├── platform/                          # MODULE 3: Shared social media environment
│   ├── __init__.py
│   ├── server.py                      # FastAPI service (SQLite + recsys + action queue)
│   ├── database.py                    # Schema creation + queries (16 tables)
│   ├── recsys.py                      # Recommendation algorithms
│   ├── actions.py                     # Action processing (post, like, follow, etc.)
│   └── Dockerfile                     # Container for the platform service
│
└── agents/                            # MODULE 4: Persona-conditioned agent containers
    ├── __init__.py
    ├── runner.py                       # Agent loop: refresh → LLM → act → repeat
    ├── llm_client.py                   # LLM backend abstraction (vLLM, OpenAI, etc.)
    ├── persona_prompt.py               # System prompt assembly from persona data
    ├── Dockerfile                      # Agent container template
    └── docker-compose.yaml             # Orchestration (platform + N agents)
```

---

## Module 1: Persona Loader (DONE)

**Status**: Implemented and tested (45 tests passing)

**What it does**: Loads MatrAIx persona YAML files (with 50+ dimensions per persona) and converts them to OASIS-compatible format. Two output modes:

1. **`OasisUserInfo` objects** — Python dataclass for programmatic use
2. **OASIS CSV export** — Exact format OASIS runtime expects (`export_oasis_csv()`)

**Key design**: We export with `activity_level_frequency = [100] * 24` (OASIS standard = always active) because OASIS expects the LLM to decide inaction. Our per-hour activity curves are available for custom scheduling but not used in OASIS-compatible mode.

**Mapping decisions**:
- Big Five → MBTI via threshold mapping (E/I at 0.5, N/S from openness, T/F from agreeableness, J/P from conscientiousness)
- `topic_*` dimensions with Passionate/Interested/Neutral/Indifferent/Averse levels → OASIS topic list (top 2 by score)
- `domain` → profession string
- `region` → deterministic country selection
- Full persona dimensions → `user_char` narrative text (the system prompt content)

---

## Module 2: Network (DONE)

**Status**: Implemented and tested (44 tests passing)

**What it does**: Constructs the directed follow graph. Two modes:

### Mode A: `build_simple_topic_graph()` — OASIS-compatible
Mirrors OASIS's exact algorithm:
- Identify influencer accounts (top 10% by extraversion + conscientiousness + openness score)
- For each regular user, check topic overlap with each influencer
- Follow with flat probability (default 0.2) if topics match
- Output: adjacency list compatible with OASIS CSV `following_agentid_list`

### Mode B: `build_social_graph()` — MatrAIx-enhanced
Richer topology for research experiments:
- Multi-factor affinity (interest cosine 40%, domain Jaccard 25%, region 15%, personality distance 20%)
- Extraversion-scaled follow budgets (introverts follow 3-6, extraverts follow 15-30)
- Openness-scaled cross-topic bridging
- Reciprocal follow probability (0.15)
- Influencer boost (5x affinity)
- Deterministic with seed for reproducibility

Both modes output `SocialGraph` objects with `to_adjacency_list()` and `to_edge_list_csv()` for OASIS integration.

---

## Module 3: Platform (TODO)

**What it builds**: The shared social media environment as a service.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│              Platform Service (Docker)                │
│                                                     │
│  ┌─────────────────┐  ┌──────────────────────────┐  │
│  │   FastAPI/HTTP   │  │      Action Queue         │  │
│  │   (agent API)    │  │  (async, UUID-keyed)      │  │
│  └────────┬────────┘  └────────────┬─────────────┘  │
│           │                        │                 │
│  ┌────────▼────────────────────────▼─────────────┐  │
│  │           SQLite Database (16 tables)          │  │
│  │  user | post | follow | like | comment | rec   │  │
│  │  trace | dislike | mute | report | ...         │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │         Recommendation System                  │  │
│  │  random | reddit_hot | miniLM | twhin_bert     │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### API Endpoints (what agents call)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/signup` | Register agent |
| POST | `/refresh` | Get recommended + following posts |
| POST | `/action` | Execute action (create_post, like, follow, etc.) |
| GET | `/state/{agent_id}` | Get agent's current state |
| GET | `/traces` | Dump all traces for analysis |
| POST | `/step` | Advance simulation clock |

### Key Design (matching OASIS internals)

- SQLite with `PRAGMA synchronous = OFF` for performance
- Action processing is sequential (one at a time) to maintain consistency
- RecSys rebuilds the `rec` table each step before agents act
- `trace` table stores every action with full JSON payload + timestamp
- Agent feed = recommended posts (from rec table) + posts from followed users (sorted by likes)

### Trajectory Storage

Every agent action produces a trace record:
```json
{
    "trace_id": 1,
    "user_id": 42,
    "action": "create_post",
    "info": {"content": "Just discovered...", "post_id": 157},
    "created_at": "2026-06-21T10:30:00"
}
```

These trajectories are the primary output for analysis — information spread, engagement patterns, behavioral diversity, persona adherence.

---

## Module 4: Agents (TODO)

**What it builds**: Persona-conditioned LLM agents running in Docker containers.

### Architecture

```
┌──────────────────────────────────────┐
│         Agent Container (Docker)      │
│                                      │
│  ┌────────────────────────────────┐  │
│  │        System Prompt            │  │
│  │  (persona narrative from YAML)  │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │         Agent Loop              │  │
│  │  1. Call platform /refresh      │  │
│  │  2. Build observation text      │  │
│  │  3. LLM call (function calling) │  │
│  │  4. Execute selected actions    │  │
│  │  5. Repeat until step ends      │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │      LLM Client                 │  │
│  │  (vLLM / OpenAI / Anthropic)    │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### How Persona Becomes Behavior

OASIS uses OpenAI function calling. The agent sees:
1. **System message**: persona narrative (our `user_profile` text)
2. **User message**: "Here is your feed: [posts]. Choose actions from available tools."
3. **Available tools**: action methods as function definitions (create_post, like_post, follow, do_nothing, etc.)

The LLM returns `tool_calls` — structured action selection driven by the persona system prompt.

### Docker Isolation

Each agent container:
- Receives persona YAML path + platform URL as env vars
- Runs the agent loop independently
- Connects to platform service via HTTP
- Can be killed/restarted without affecting other agents
- Logs its own trajectory locally (also stored in platform)

### docker-compose.yaml (orchestration)

```yaml
services:
  platform:
    build: ./platform
    ports: ["8000:8000"]
    volumes: ["./data:/app/data"]
    environment:
      - RECSYS_TYPE=twitter
      - DB_PATH=/app/data/simulation.db

  agent-0:
    build: ./agents
    environment:
      - PLATFORM_URL=http://platform:8000
      - PERSONA_PATH=/app/personas/ID0001.yaml
      - LLM_BACKEND=vllm
      - LLM_URL=http://host.docker.internal:8002/v1
    depends_on: [platform]

  # ... agent-1 through agent-N
```

---

## Implementation Order

| Phase | Module | What | Status |
|-------|--------|------|--------|
| 1 | `persona_loader/` | YAML loading, dimension mapping, CSV export | DONE (45 tests) |
| 2 | `network/` | Graph construction (simple + affinity modes) | DONE (44 tests) |
| 3 | `platform/` | FastAPI service, SQLite, recsys, action queue | TODO |
| 4 | `agents/` | Docker agent loop, LLM client, persona prompt | TODO |

### Phase 3 Steps (Platform)

1. Port OASIS's 16-table SQLite schema into `database.py`
2. Implement action processing (sequential, one-at-a-time)
3. Implement the 4 recsys algorithms (start with `random` and `reddit_hot`)
4. Expose as FastAPI HTTP service
5. Add trace recording
6. Dockerize

### Phase 4 Steps (Agents)

1. Build the agent loop (refresh → observe → LLM → act)
2. Implement LLM client abstraction (vLLM for Greenland, OpenAI for dev)
3. Build system prompt from persona data
4. Expose all 29 actions as function tool definitions
5. Dockerize with env-var configuration
6. Build docker-compose orchestrator

---

## Running Modes

### Dev (local, 5-10 agents)

```bash
# Start platform
python -m environments.oasis.platform.server --db ./data/dev.db --recsys random

# Run agents (no Docker, direct Python)
python -m environments.oasis.agents.runner \
  --platform http://localhost:8000 \
  --persona personas/Jun20_1k_persona_description/ID0001.yaml \
  --llm-backend openai --model gpt-4o-mini
```

### Production (Greenland, 1000+ agents)

```bash
# Push code
./scripts/greenland-sync.sh push

# Start vLLM
./scripts/greenland-sync.sh runbg "python -m vllm.entrypoints.openai.api_server --model meta-llama/Meta-Llama-3-8B-Instruct --tensor-parallel-size 4 --port 8002"

# Run simulation via docker-compose
./scripts/greenland-sync.sh run "docker compose -f environments/oasis/agents/docker-compose.yaml up"
```

### OASIS-native (for comparison/validation)

```bash
# Export MatrAIx personas to OASIS CSV
python -c "
from environments.oasis import load_personas_from_directory, build_simple_topic_graph, export_oasis_csv, build_oasis_follow_data
personas = load_personas_from_directory('personas/Jun20_1k_persona_description/', max_agents=100)
graph = build_simple_topic_graph(personas, follow_probability=0.2)
adj = graph.to_adjacency_list()
export_oasis_csv(personas, 'data/oasis_agents.csv', following_lists=[adj[i] for i in range(len(personas))])
"

# Run with upstream OASIS directly
python examples/experiment/twitter_simulation/run.py --csv data/oasis_agents.csv
```

---

## Differences from Upstream OASIS (intentional)

| Aspect | OASIS | Our Implementation | Why |
|--------|-------|-------------------|-----|
| Agent isolation | Single process, asyncio | Docker containers | Fault tolerance, mixed LLM backends |
| Platform | In-process event loop | HTTP service | Independent scaling, persistence |
| Network | Flat p=0.2 | Two modes (simple + affinity) | Research flexibility |
| Personas | ~6 fields + narrative | 50+ dimensions + narrative | MatrAIx's richer schema |
| Activity gating | frequency=100 (always active) | Exported as 100 for OASIS compat | LLM decides inaction |
| Trace storage | SQLite trace table | Same + optional export | Analysis pipeline |

### What we preserve exactly from OASIS

- CSV format (column names, Python list literals, ast.literal_eval compatibility)
- 16-table SQLite schema
- Action types (all 29)
- Recommendation algorithms (4 types)
- System prompt structure (persona narrative + available tools)
- Function calling for action selection
