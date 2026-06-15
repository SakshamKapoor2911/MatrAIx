# 🌐 Environment Team — Plan & Task Assignments

> Working plan for the [Environment team](README.md). Each task has an **Owner** field — add your name to a placeholder slot. Each task can take **1–3 people** to start, and more can be added later (just append `@you`).

> 🧭 **Scope from kickoff (Jun 13).** Block 2 is mostly **engineering** and **task-agnostic**: given a persona-conditioned agent (persona injected via system prompt) and a defined environment, make the agent *run* and emit a full **telemetry trace**. We do **not** design tasks here (that's the Application team) — we provide a few general environment *types* they plug into. Keep each type **basic** so the end-to-end pipeline works first; depth can come later.

---

## 📚 Literature Review

Collect and summarize prior work on agent environments, evaluation harnesses, and simulation frameworks.

**Owner(s):** _@ahmd-mohsin, @name2, @name3_ (add more as needed)

> 📌 **Default item format** — each entry should look like:
>
> ### [Paper / Framework Title](https://link-here)
> - bullet point summarizing the key idea
> - bullet point on the environment / interface / evaluation design
> - bullet point on relevance to MatrAIx environments

### 🕹️ Agent Environments & Benchmarks
_Web agents, GUI/app automation, tool-use sandboxes, simulation frameworks (e.g. τ-bench / tau-bench style customer-service settings)._

### [τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045)
- Emulates multi-turn conversations between an **LLM-simulated user** and a tool-using agent that must follow a domain **policy document** (retail, airline), testing whether the agent can gather/convey the right information and obey rules across a full dialogue.
- Each task is framed as a POMDP; the agent acts on databases via API tools and on the simulated user via messages, and the **reward compares the final database state to an annotated goal state** rather than grading the dialogue text. Introduces `pass^k` to measure reliability across *k* trials. The successor [τ²-bench](https://github.com/sierra-research/tau2-bench) adds telecom/voice/dual-control domains and **automatic detection of when the simulated user drifts off its instructions** (re-running the affected eval).
- Closest template for our **Chatbot Environment (Task 3)**: gives us the user-simulator-as-component design, state-based rewards, policy-following tests, and a reliability metric. The off-instruction detection maps directly onto the persona-adherence checks we'll need for hard/realistic users.

### [WebArena: A Realistic Web Environment for Building Autonomous Agents](https://arxiv.org/abs/2307.13854)
- A **self-hostable, reproducible** web environment built from four fully functional open-source sites (e-commerce, a Reddit-style forum, GitLab, a CMS) plus utility tools (map, calculator, scratchpad), with 812 long-horizon natural-language tasks.
- Evaluates **functional correctness** — whether the resulting site state achieves the goal — instead of matching action sequences, which admits multiple valid paths; the best GPT-4 agent reached only ~14% vs ~78% for humans, showing even "lightweight" web tasks are hard. Extended by VisualWebArena (visual grounding) and unified under [BrowserGym/AgentLab](https://github.com/web-arena-x/webarena) for parallel runs and a shared leaderboard.
- Direct reference for our **Web Environment (Task 4)**, including the forum/social subtype. The self-hosted-sandbox pattern matches our hosted-playground integration path, and the functional-correctness checker is the template for our web success signals.

### [AndroidWorld: A Dynamic Benchmarking Environment for Autonomous Agents](https://arxiv.org/abs/2405.14573)
- A fully functional **Android environment on a live emulator** with 116 hand-crafted tasks across 20 real apps, dynamically parameterized to generate millions of task variations.
- Rewards are derived from **device system state**, and each task ships dedicated **initialization, success-checking, and teardown** logic; a strong multimodal baseline (M3A) solved only ~31%, and a desktop web agent ported to mobile did worse — cross-surface transfer is not free.
- Template for our **App/Sandbox Environment (Task 5)** and a concrete illustration of why it's deprioritized — but the `init → success-check → teardown` lifecycle and task parameterization are patterns worth adopting in the **shared interface (Task 1)** for *every* surface.

### 📊 Evaluation & Telemetry
_Interaction logging, metrics, LLM-as-judge, human eval protocols._

### [Generative Agent Simulations of 1,000 People](https://arxiv.org/abs/2411.10109)
- Builds agents from two-hour qualitative **interviews with 1,052 real individuals**, then measures how faithfully each agent reproduces its source person's attitudes and behaviors.
- Agents replicate **General Social Survey responses ~85% as accurately** as the humans replicate their own answers two weeks later, with comparable results on Big Five traits and replicated behavioral-economics experiments; interview-grounded agents **reduce accuracy bias** across racial/ideological groups vs demographic-only personas. The eval protocol is the gold standard: compare simulated answers against the real person's held-out answers.
- Defines how we should **validate persona fidelity** for the Survey/Chatbot environments — the metric is "does the agent match the real person." The finding that thin demographic personas underperform rich ones tells us how much persona context our telemetry must carry.

### [Synthetic Replacements for Human Survey Data? The Perils of Large Language Models](https://www.cambridge.org/core/journals/political-analysis/article/synthetic-replacements-for-human-survey-data-the-perils-of-large-language-models/B92267DC26195C7F36E63EA04A47D2FE)
- Stress-tests "silicon sampling" (prompting an LLM to answer as a persona) and finds important **validity failures even when averaged opinions look plausible**.
- Synthetic responses show **compressed variance** and regression coefficients that diverge — sometimes flipping sign — versus real survey data, making them unreliable for inference; related work documents social-desirability bias and a distinct "machine bias" with lower between-subgroup variance.
- A required caution for our **evaluation layer**: synthetic feedback is a signal for exploration/debugging, not ground truth. We should ship calibration against real distributions, report variance (not just means), and label outputs as synthetic — consistent with the project's stated Limitations.

### 🧩 Others
_Multi-agent / social simulation, long-horizon tasks, related work._

### [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
- 25 LLM agents living in a Sims-like sandbox ("Smallville"), producing believable individual behavior and **emergent group dynamics** (information diffusion, relationship memory, coordinating a Valentine's party).
- Introduces the **memory-stream architecture** — observations retrieved by recency, importance, and relevance — plus periodic **reflection** and re-planning; believability is evaluated via ablations and TrueSkill ratings.
- The foundational design for the **"lightweight self-evolving memory"** and long-horizon/multi-agent directions on our roadmap; the memory/reflection loop is the reference architecture if our persona agents need to persist and adapt across sessions.

### [AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents](https://arxiv.org/abs/2502.08691)
- A large-scale **societal simulator** running 10k+ psychologically-grounded agents (memory, emotion, needs) through ~5M interactions in a multi-layer urban/social/economic environment.
- A **Ray-based distributed engine** scales to ~30k agents faster than real time; used as a testbed for polarization, inflammatory-message spread, UBI, and external shocks (hurricanes); finds **environment-grounded agents match real-world mobility/behavior data far better** than prompt-only "text simulators."
- The strongest reference for our **Stage-4 planet-scale** ambitions — it shows the scaling path is distributed infrastructure, and externally validates our core thesis that the *environment* (not just the persona) drives behavioral fidelity.

### [Magentic Marketplace: An Open-Source Environment for Studying Agentic Markets](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/10/multi-agent-marketplace.pdf)
- Proposes an open-source multi-agent marketplace simulation where consumer-side assistant agents interact with business-side service agents to search, communicate, receive proposals, and complete transactions.
- The environment is built around a centralized marketplace server and a simple action protocol supporting agent registration, search, message passing, proposal submission, payment, and full interaction logging; evaluation focuses on transaction success, consumer utility, welfare, search quality, manipulation resistance, and behavioral biases such as first-proposal bias.
- Relevant to MatrAIx because it provides a reusable pattern for long-horizon multi-agent social/economic simulations with heterogeneous roles, private preferences, strategic service agents, market-level outcomes, and extensible domains beyond restaurants/contractors.

### [OASIS: Open Agent Social Interaction Simulations with One Million Agents](https://arxiv.org/pdf/2411.11581)
- Proposes a scalable open-source social media simulation framework where LLM-based agents act as users on platforms like X/Twitter and Reddit, enabling studies of large-scale social phenomena such as information spreading, group polarization, and herd behavior.
- The environment includes dynamic social networks, evolving post/content states, diverse user actions such as posting, following, reposting, liking, and commenting, plus recommendation systems based on user interests and hot-score ranking; it supports simulations with up to one million agents.
- Relevant to MatrAIx because it provides a strong reference for large-scale multi-agent social simulation: agent personas, network evolution, recommender-mediated interaction, long-horizon collective dynamics, and environment-level metrics for studying emergent behavior.

---

## 🧩 Task 1 — Shared Environment Interface & Telemetry

Define the common contract every environment implements so personas, tasks, and loggers are interchangeable.

- Standard **observation / action / tool** schema for an agent ↔ environment loop.
- Episode lifecycle: `reset → step → done`, plus state and reset semantics.
- Persona injected via **system prompt** (Block 1) + task plugged in by Block 3.
- **Telemetry trace** is the required output: full record of steps, actions, signals, timings, outcome — this feeds the Application team's report (Block 3).
- Two integration paths: **(a) hosted sandbox playground** (contributor supplies the surface) and **(b) agent API** that an external system drives.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 📝 Task 2 — Type 1: Survey Environment _(simplest / start here)_

The simplest surface — the agent reads a stimulus (product concept, message, description, UI mockup, decision scenario) and returns structured feedback. Behaves like an LLM answering a questionnaire rather than a tool-using agent.

- Define input formats and a **structured output schema** (rating scores, free-form feedback, ranked preferences, objections, predicted adoption).
- Reference implementation + a couple of example stimuli.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 💬 Task 3 — Type 2: Chatbot Environment _(priority)_

High-value surface — many target products *are* AI systems, so they can be tested directly through conversation. Prioritized at kickoff.

- Persona agent converses with a target system (assistant, support bot, tutor, coding assistant).
- Adapter to connect an external chatbot (API).
- Conversation logging + metrics (helpfulness, trust, clarity, satisfaction, length).
- Cover **cooperative** users **and** hard/realistic users (privacy-sensitive, low-literacy / elderly, confused, adversarial) — the realistic-but-hard cases are where simulation adds value.

**Owner(s):** _@ahmd-mohsin, @name2, @name3_ (add more as needed)

---

## 🌐 Task 4 — Type 3: Web Environment

Agent interaction with web surfaces (landing pages, prototypes, dashboards, **forum / social** sub-form).

- Sandbox playground (host a supplied web surface) **and/or** agent API path.
- Capture signals: pages, clicks, scroll, hesitation, failed actions, final decision.
- Forum/social subtype: read posts, comment, initiate DMs — same interaction layer, different surface.

**Owner(s):** _@ahmd-mohsin, @name2, @name3_ (add more as needed)

---

## 📱 Task 5 — Type 4: App / Sandbox Environment _(longer-term, deprioritized)_

Complex interactive products (mobile / desktop / sandbox builds). Pulls in low-value engineering (auth, captchas, device state, reset) — explicitly **deprioritized** for early stages.

- Scope build formats and UI-automation approach for later.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 🤝 How to Contribute

1. Pick a task above and add your name to its **Owner** field.
2. Open a sub-issue / sub-doc for your task to track details and progress.
3. Align early on the shared **interface + telemetry** (Task 1) — it blocks Tasks 2–5.
4. Build **Type 1 (survey)** and **Type 2 (chatbot)** first; they're the fastest path to a working end-to-end pipeline.
