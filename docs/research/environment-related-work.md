# Environment Related Work

This note migrates the MatrAIx Environment team related-work notes from
`MatrAIx-ai/MatrAIx@e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`,
`docs/environments/PLAN.md`. It preserves the useful research references
without importing the old task-assignment plan.

The source note listed _@ahmd-mohsin, @name2, @name3_ as related-work owners.
The original environment review was sparse: its "Agent Environments &
Benchmarks" and "Evaluation & Telemetry" subsections were placeholders, and
only three complete entries appeared under "Others". That was a source coverage
gap, not a clean-main import omission.

To make the environment research map usable, this note keeps those three
source environment entries and adds environment-relevant benchmark references
that were originally written in the Application team review. Those cross-links
are marked as application-source entries.

## Source Environment Entries

### [Magentic Marketplace: An Open-Source Environment for Studying Agentic Markets](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/10/multi-agent-marketplace.pdf)

- Proposes a multi-agent marketplace where consumer-side assistant agents and
  business-side service agents search, communicate, submit proposals, and
  complete transactions.
- Environment takeaway: a pattern for long-horizon market environments with
  heterogeneous roles, private preferences, strategic service agents, full
  interaction logging, and market-level metrics.

### [SOTOPIA: Interactive Evaluation for Social Intelligence in Language Agents](https://arxiv.org/abs/2310.11667)

- Defines turn-based role-play episodes with personas, goals, relationships,
  private information, and multidimensional LLM-as-judge scoring.
- Environment takeaway: a strong template for a shared `reset -> step -> done`
  interface with structured observations, actions, persona injection, and
  telemetry.

### [OASIS: Open Agent Social Interaction Simulations with One Million Agents](https://arxiv.org/pdf/2411.11581)

- Simulates social-media platforms with evolving networks, recommendation, and
  user actions such as posting, following, reposting, liking, and commenting.
- Environment takeaway: a reference for population-scale social environments,
  long-horizon collective dynamics, recommender-mediated interaction, and
  environment-level metrics.

## Application-Source Environment Benchmarks

These entries were written in the Application review but are directly relevant
to `environment/` because they define runtime surfaces, action spaces, scoring
interfaces, or telemetry conventions.

### [WebArena: A Realistic Web Environment for Building Autonomous Agents](https://arxiv.org/abs/2307.13854)

- Self-hosted web applications plus long-horizon tasks scored by resulting
  environment state.
- Environment takeaway: useful precedent for web surfaces where clicks,
  forms, state changes, and final task success can be replayed and checked.

### [WebShop: Towards Scalable Real-World Web Interaction with Grounded Language Agents](https://arxiv.org/abs/2207.01206)

- Simulated e-commerce site with search, navigation, customization, and
  purchase actions over real product data.
- Environment takeaway: gives a compact, auto-rewarded web-shopping interface
  for shopper personas and checkout-style tasks.

### [Mind2Web: Towards a Generalist Agent for the Web](https://arxiv.org/abs/2306.06070)

- Web task dataset spanning many real websites, domains, and action sequences.
- Environment takeaway: helps define general web-agent action logging and
  cross-site evaluation beyond one curated surface.

### [tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045)

- Simulates policy-constrained conversations between a user and a tool-using
  agent over domain APIs.
- Environment takeaway: a strong template for chatbot and support
  environments where the final database state is the reward signal.

### [AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents](https://arxiv.org/abs/2407.18901)

- Provides a high-fidelity execution engine of everyday apps, APIs, and
  fictitious users.
- Environment takeaway: a reference for app/sandbox environments that need
  controllable state, realistic APIs, and multi-app task execution.

### [AgentBench: Evaluating LLMs as Agents](https://arxiv.org/abs/2308.03688)

- Evaluates agents across multiple interactive environments including OS,
  database, knowledge graph, web shopping, web browsing, and household tasks.
- Environment takeaway: a useful precedent for a unified harness that supports
  heterogeneous environment adapters.

### [GAIA: a Benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)

- Tests assistants on tasks requiring reasoning, web browsing, multimodality,
  and tool use.
- Environment takeaway: relevant to tool and browser runtime integration where
  multiple capabilities must be orchestrated in one episode.

### [ToolLLM: Facilitating LLMs to Master 16000+ Real-world APIs (ToolBench)](https://arxiv.org/abs/2307.16789)

- Builds a broad tool/API environment with annotated solution paths and an
  automatic evaluator.
- Environment takeaway: informs external-tool adapters, tool-selection traces,
  and API-level telemetry.

### [UXAgent: An LLM Agent-Based Usability Testing Framework for Web Design](https://arxiv.org/abs/2502.12561)

- Connects persona agents to real websites and records qualitative feedback,
  quantitative action counts, and video logs.
- Environment takeaway: directly relevant to browser connectors and rich
  telemetry capture for web/application tasks.

### [Social Simulacra: Creating Populated Prototypes for Social Computing Systems](https://arxiv.org/abs/2208.04024)

- Populates social prototypes with synthetic users and interaction traces.
- Environment takeaway: a reference for social/forum environments where the
  surface itself changes as simulated users act.

### [AgentA/B: Automated and Scalable Web A/B Testing with Interactive LLM Agents](https://arxiv.org/abs/2504.09723)

- Runs many interactive agents over competing web designs and compares their
  behavior.
- Environment takeaway: motivates deterministic recipe setup, reproducible
  environment versions, and subgroup-level telemetry aggregation.

### [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)

- Establishes LLM judge evaluation and analyzes judge biases.
- Environment takeaway: useful when environment traces must be converted into
  scores, but judge outputs should remain auditable artifacts.

## Environment Design Implications

- The shared environment API should make observation, action, tool calls,
  state transitions, reset semantics, and episode termination explicit.
- Telemetry is not optional: application reporting depends on full step logs,
  timing, outcome state, screenshots or recordings when relevant, and
  structured metrics.
- Browser, chatbot, app/sandbox, and external-benchmark adapters should land as
  small PRs with manifests instead of a bulk adapter dump.
- Multi-agent environments need role definitions, private preferences or
  goals, network or market state, and aggregate-level metrics in addition to
  per-agent traces.
