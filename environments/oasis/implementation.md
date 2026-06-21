# OASIS Implementation — Complete Technical Reference

> MatrAIx integration of OASIS (Open Agent Social Interaction Simulations).
> Load MatrAIx personas → build social graph → run persona-conditioned agents on a shared platform → collect trajectories.

---

## How OASIS Actually Works (from source code analysis)

### Architecture

OASIS separates concerns into:
1. **Agents** — LLM-powered actors with a persona system prompt. Each agent is always active (the LLM decides `do_nothing` as an action). At 1M scale, activation probability gates which agents get a turn.
2. **Platform** — A single async event loop processing all actions sequentially via SQLite (`PRAGMA synchronous = OFF`). 16-table schema. All state lives here.
3. **Channel** — Async queue connecting agents ↔ platform. Each action gets a UUID, agent polls `asyncio.sleep(0.1)` until response arrives in `AsyncSafeDict`.
4. **RecSys** — Controls what each agent sees in their feed. Rebuilt every timestep before agents act. 4 algorithms (random, reddit hot-score, MiniLM cosine, Twhin-BERT + time decay).
5. **Clock** — Discrete `time_step` integer for Twitter mode. `time_transfer(now, start)` with magnification factor k=60 for Reddit mode.

### Network Generation (exact algorithm from `generator/twitter/network.py`)

- Load pre-curated "star" accounts from `new_stars.csv` categorized by topic
- For each regular user, iterate over their 2 topic interests
- For each star account matching that topic, follow with **flat probability 0.2**
- No affinity calculation, no personality weighting, no region similarity
- Output: CSV with `following_agentid_list` as Python list literal string
- Philosophy: simple topology + LLM behavioral complexity = emergent realism

### Profile Generation (exact algorithm from `generator/twitter/gen.py`)

- Demographics: age (weighted: 13-17=6.6%, 18-24=17.1%, 25-34=38.5%, 35-49=20.7%, 50+=17.1%)
- 16 MBTI types with specific probability distribution
- 16 career clusters (uniform)
- Each agent gets exactly 2 topics from 9 available (combinatorial C(9,2)=36 combos)
- Profile text generated via RAG: GPT-3.5 + `BAAI/bge-m3` embeddings + Chroma vector store over `complete_user_char.csv`
- Activity level: `['active'] * 24` with `frequency = [100] * 24` for ALL agents (= always active)

### Platform Actions (31 total from `typing.py`)

```
EXIT, REFRESH, SEARCH_USER, SEARCH_POSTS, CREATE_POST, LIKE_POST,
UNLIKE_POST, DISLIKE_POST, UNDO_DISLIKE_POST, REPORT_POST, FOLLOW,
UNFOLLOW, MUTE, UNMUTE, TREND, SIGNUP, REPOST, QUOTE_POST,
UPDATE_REC_TABLE, CREATE_COMMENT, LIKE_COMMENT, UNLIKE_COMMENT,
DISLIKE_COMMENT, UNDO_DISLIKE_COMMENT, DO_NOTHING, PURCHASE_PRODUCT,
INTERVIEW, JOIN_GROUP, LEAVE_GROUP, SEND_TO_GROUP, CREATE_GROUP,
LISTEN_FROM_GROUP
```

Default action sets:
- **Twitter**: create_post, like_post, repost, follow, do_nothing, quote_post
- **Reddit**: like_post, dislike_post, create_post, create_comment, like_comment, dislike_comment, search_posts, search_user, trend, do_nothing, follow, mute

### Repost Resolution Logic (critical detail from `platform.py`)

OASIS resolves reposts to root posts before any engagement action:
- `like_post(repost_id)` → finds `original_post_id` → likes the root
- `repost(already_reposted_id)` → finds root → creates new repost pointing to root
- Duplicate check: user cannot repost the same root post twice

### CSV Format (the actual runtime input)

```
user_id, name, username, description, user_char, following_agentid_list,
previous_tweets, activity_level, activity_level_frequency, tweets_id
```

- `following_agentid_list`: Python list as string literal (`"[32, 55, 12]"`), parsed with `ast.literal_eval()`
- `activity_level`: `"['active'] * 24"`
- `activity_level_frequency`: `"[100] * 24"` (100 = always active)
- `user_char`: Full persona narrative (the system prompt content)
- `tweets_id`: Counter starting at "0"

### Data Sources OASIS Ships With

| File | Content |
|------|---------|
| `data/twitter_dataset/all_topics.csv` | 198 rumor stories from twitter15/twitter16 (True/False labels, 9 topics) |
| `data/twitter_dataset/anonymous_topic_200_1h/*.csv` | ~200 pre-built agent CSVs per story |
| `data/twitter_dataset/group_polarization/` | 197 conservative + 197 progressive users |
| `data/reddit/user_data_36.json` | 36 LLM-generated Reddit personas |
| `data/reddit/counterfactual_36.json` | ~160 counterfactual experiment entries with up/down/control groups |
| `data/emall/product.json` | 3 product descriptions for e-commerce simulation |
| `generator/twitter/new_stars.csv` | Categorized influencer accounts |
| `generator/twitter/users.json` | 10,000+ generated profiles |
| `generator/twitter/complete_user_char.csv` | RAG training data for profile generation |

### 1M Agent Scaling (from `twitter_simulation_1M_agents/`)

- Replace AgentGraph with plain Python list (igraph too slow)
- 72 vLLM endpoints across 3 GPU servers (24 ports each)
- `scheduling_strategy='random_model'` distributes across endpoints
- Activation probability: `active_threshold[hour]` per agent (only ~1% act per step)
- Reduced action space: do_nothing, repost, like_post, follow
- Bulk DB operations for signup and follow

---

## Our Architecture

### Key Differences from OASIS

| Aspect | OASIS | Our Implementation |
|--------|-------|-------------------|
| Communication | Async Channel (in-process queues) | HTTP REST API (Docker-isolated) |
| Agent isolation | Same Python process, asyncio | Docker containers (crash-isolated) |
| Platform | Event loop in same process | FastAPI service (independent scaling) |
| SQLite | `PRAGMA synchronous = OFF` | WAL mode + thread lock |
| LLM backend | CAMEL ChatAgent with tool calling | Direct OpenAI-compatible API (vLLM/OpenAI/etc) |
| Action dispatch | `getattr(self, action.value)` reflection | Explicit handler dict |
| Clock | In-process Clock object | Clock in PlatformState |

### What We Preserve Exactly

- 16-table SQLite schema (all columns, foreign keys, constraints)
- Repost resolution to root post before engagement
- Duplicate repost prevention
- Trace recording for every action
- RecSys rebuilds rec table each step
- Feed = recommended posts + following posts (deduplicated, muted excluded)
- Agent sees observation text + selects tools via function calling
- `do_nothing` is a valid action the LLM can choose
- OASIS CSV export with `ast.literal_eval`-compatible list literals

---

## Module Structure (57 files)

```
environments/oasis/
├── README.md
├── implementation.md                          # This file
├── __init__.py
├── docker-compose.yaml                        # Platform + N agent containers
│
├── persona_loader/                            # MODULE 1: YAML → OASIS format
│   ├── __init__.py
│   ├── adapter.py                             # Dimension mapping, MBTI, CSV export
│   └── tests/
│       ├── test_adapter.py                    # 45 tests
│       └── fixtures/                          # 5 deep personas (50+ dims each)
│
├── network/                                   # MODULE 2: Social graph construction
│   ├── __init__.py
│   ├── builder.py                             # Simple (p=0.2) + affinity modes
│   └── tests/
│       └── test_builder.py                    # 44 tests
│
├── platform/                                  # MODULE 3: Shared social media service
│   ├── __init__.py
│   ├── clock.py                               # Sandbox time (discrete steps / time dilation)
│   ├── database.py                            # SQLite layer (16 tables, WAL, thread-safe)
│   ├── actions.py                             # 22 action handlers with trace recording
│   ├── recsys.py                              # 3 algorithms (random, reddit hot, twitter cosine)
│   ├── server.py                              # FastAPI HTTP service + PlatformState
│   ├── Dockerfile
│   ├── schema/                                # 16 SQL schema files
│   │   ├── user.sql
│   │   ├── post.sql
│   │   ├── follow.sql
│   │   ├── like.sql
│   │   ├── dislike.sql
│   │   ├── comment.sql
│   │   ├── comment_like.sql
│   │   ├── comment_dislike.sql
│   │   ├── mute.sql
│   │   ├── rec.sql
│   │   ├── trace.sql
│   │   ├── report.sql
│   │   ├── product.sql
│   │   ├── chat_group.sql
│   │   ├── group_member.sql
│   │   └── group_message.sql
│   └── tests/
│       └── test_platform.py                   # 39 tests
│
├── agents/                                    # MODULE 4: Docker-isolated persona agents
│   ├── __init__.py
│   ├── tools.py                               # 19 OpenAI function-calling tool schemas
│   ├── prompt.py                              # System prompt + observation prompt builders
│   ├── llm_client.py                          # OpenAI-compatible HTTP client (vLLM/GPT/etc)
│   ├── platform_client.py                     # HTTP client for platform API
│   ├── runner.py                              # Single-agent loop (refresh → LLM → act)
│   ├── orchestrator.py                        # Multi-agent simulation controller
│   ├── entrypoint.py                          # Docker container entry point
│   ├── Dockerfile
│   └── tests/
│       └── test_agents.py                     # 21 tests
│
└── data/                                      # Sample data + generator
    ├── generate.py                            # CLI: personas → OASIS CSV + edges + seed posts
    ├── reddit/
    │   ├── user_data_sample.json              # 5 sample personas (OASIS format)
    │   └── counterfactual_sample.json         # 5 misinformation experiment entries
    └── twitter/
        └── seed_posts.json                    # 5 initial posts for feed bootstrapping
```

---

## Module Details

### Module 1: Persona Loader (45 tests)

**Input**: MatrAIx persona YAML files (50+ dimensions from the 1,276-dimension schema)

**Output**: `OasisUserInfo` objects + OASIS-compatible CSV export

**Key operations**:
- Big Five (Very low→0.15 ... Very high→0.85) → MBTI (4-letter via threshold)
- `topic_*` dimensions (Passionate/Interested/Neutral/Indifferent/Averse) → topic list
- Region → deterministic country
- Domain → profession string
- All dimensions → `user_char` narrative text
- Activity: exported as `[100]*24` for OASIS compatibility (always active, LLM decides)

### Module 2: Network (44 tests)

**Two modes**:

| Mode | Function | Algorithm | When to use |
|------|----------|-----------|-------------|
| OASIS-compatible | `build_simple_topic_graph()` | Flat p=0.2 per topic-matching influencer | OASIS comparison experiments |
| MatrAIx-enhanced | `build_social_graph()` | Multi-factor affinity (interest cosine + domain + region + personality) | Research on topology effects |

**Also provides**: `export_oasis_csv()`, `to_edge_list_csv()`, `build_oasis_follow_data()`, seed post generation.

### Module 3: Platform (39 tests)

**Architecture**: FastAPI HTTP service with SQLite backend.

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| POST | `/signup` | Register agent |
| POST | `/signup/bulk` | Batch register agents |
| POST | `/action` | Execute action (all 22 types) |
| POST | `/follow/bulk` | Batch insert follow edges |
| POST | `/seed_post` | Insert initial content |
| POST | `/step` | Advance clock + rebuild recommendations |
| GET | `/state/{agent_id}` | Agent profile |
| GET | `/traces` | Trajectory data |
| GET | `/stats` | Platform statistics |
| GET | `/health` | Liveness check |

**Action processing** (matching OASIS behavior):
- Sequential execution via thread lock
- Repost resolution: likes/dislikes on reposts target the root post
- Duplicate prevention: cannot repost same root twice
- Every action recorded in trace table with full JSON
- Muted users excluded from refresh results

**RecSys** (3 of OASIS's 4 algorithms):
- `random`: Random sample of posts per user
- `reddit`: Hot-score = sign × log10(|votes|) + epoch/45000
- `twitter`: Word-overlap between user bio and post content (lightweight cosine proxy)

### Module 4: Agents (21 tests)

**Architecture**: Persona-conditioned LLM agents that connect to platform via HTTP.

**The agent loop** (mirrors OASIS's `perform_action_by_llm`):
```
1. POST /action {refresh} → get feed posts
2. Build observation text: "[Post #1 by user 5] content (likes: 3, ...)"
3. LLM call with system_prompt (persona) + user_msg (observation) + tools (19 functions)
4. Parse tool_calls from response
5. For each tool_call: POST /action {action_type, params}
6. If no tool_calls or error: POST /action {do_nothing}
```

**LLM client**: OpenAI-compatible API (works with vLLM, OpenAI, Together, local Ollama). Parses both native `tool_calls` and JSON-in-content fallback.

**Orchestrator**: In-process mode for local testing (no Docker needed). Registers agents, injects graph/seed posts, runs N timesteps, collects results.

---

## Running

### Local Development (no Docker, no GPU)

```bash
# Generate OASIS-compatible data from MatrAIx personas
python environments/oasis/data/generate.py \
  --persona-dir personas/Jun20_1k_persona_description \
  --output-dir environments/oasis/data/generated \
  --max-agents 20

# Run tests (149 passing, no external dependencies)
python -m pytest environments/oasis/ -q
```

### Local with LLM (OpenAI API)

```python
from environments.oasis.agents.orchestrator import Orchestrator, SimulationConfig
from environments.oasis.persona_loader import load_personas_from_directory
from environments.oasis.network import build_social_graph, NetworkConfig

personas = load_personas_from_directory("personas/Jun20_1k_persona_description/", max_agents=10)
graph = build_social_graph(personas, NetworkConfig(random_seed=42))

config = SimulationConfig(
    max_agents=10, num_steps=5,
    llm_base_url="https://api.openai.com/v1",
    llm_api_key="sk-...",
    llm_model="gpt-4o-mini",
    recsys_type="random",
    available_actions=["create_post", "like_post", "repost", "follow", "do_nothing"],
)
orch = Orchestrator(config)
orch.setup(personas=personas, graph=graph)
result = orch.run()
print(f"Posts: {result.platform_stats['post']}, Traces: {result.platform_stats['trace']}")
orch.close()
```

### Greenland (p4d.24xlarge, 8x A100, vLLM)

```bash
# 1. Push code
./scripts/greenland-sync.sh push

# 2. Start vLLM with Qwen3-4B (or Llama-3-8B)
./scripts/greenland-sync.sh runbg "python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-4B --tensor-parallel-size 2 --port 8002"

# 3. Generate data
./scripts/greenland-sync.sh run "python environments/oasis/data/generate.py \
  --persona-dir personas/Jun20_1k_persona_description \
  --output-dir environments/oasis/data/generated \
  --max-agents 1000 --network-mode affinity"

# 4. Run simulation
./scripts/greenland-sync.sh run "python -c \"
from environments.oasis.agents.orchestrator import Orchestrator, SimulationConfig
from environments.oasis.persona_loader import load_personas_from_directory
from environments.oasis.network import build_social_graph, NetworkConfig

personas = load_personas_from_directory('personas/Jun20_1k_persona_description/', max_agents=1000)
graph = build_social_graph(personas, NetworkConfig(random_seed=42))
config = SimulationConfig(max_agents=1000, num_steps=20, llm_base_url='http://localhost:8002/v1', llm_model='Qwen/Qwen3-4B')
orch = Orchestrator(config)
orch.setup(personas=personas, graph=graph)
result = orch.run()
print(result.platform_stats)
orch.close()
\""

# 5. Pull results
./scripts/greenland-sync.sh pull data/outputs/
```

### Docker Compose (multi-container)

```bash
docker compose -f environments/oasis/docker-compose.yaml up
```

### OASIS-native (export CSV, run upstream OASIS directly)

```bash
python environments/oasis/data/generate.py \
  --persona-dir personas/Jun20_1k_persona_description \
  --output-dir /tmp/oasis_data --max-agents 200

# Then use with upstream OASIS:
# python -m oasis.run --csv /tmp/oasis_data/agents.csv --recsys reddit
```

---

## Test Summary

| Module | Tests | Coverage |
|--------|-------|----------|
| persona_loader | 45 | YAML loading, dimension mapping, MBTI, activity thresholds, CSV export, batch ops, real persona integration |
| network | 44 | Affinity computation, influencer ID, clustering, edge generation, graph properties, determinism, OASIS format |
| platform | 39 | All 16 tables CRUD, 22 action handlers, repost resolution, duplicate prevention, trace recording, recsys, full simulation cycle |
| agents | 21 | Tool schemas, prompt construction, LLM client parsing, orchestrator setup/run, mock LLM, error fallback |
| **Total** | **149** | All passing in ~19s, no external dependencies required |
