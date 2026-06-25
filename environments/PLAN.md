# 🌐 Environment Team — Plan & Task Assignments

> Working plan for the [Environment team](README.md). Each task has an **Owner** field — add your name to a placeholder slot. Each task can take **1–3 people** to start, and more can be added later (just append `@you`).

> 🧭 **Scope from kickoff (Jun 13).** Block 2 is mostly **engineering** and **task-agnostic**: given a persona-conditioned agent (persona injected via system prompt) and a defined environment, make the agent *run* and emit a full **telemetry trace**. We do **not** design tasks here (that's the Application team) — we provide a few general environment *types* they plug into. Keep each type **basic** so the end-to-end pipeline works first; depth can come later.

---

## 📚 Related Work

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

### [AgentA/B: Automated and Scalable Web A/B Testing with Interactive LLM Agents](https://arxiv.org/abs/2504.09723) (Keyang Xuan)
- Uses interactive LLM agents as **simulated users** to run A/B tests on live web UIs, comparing design variants without diverting real user traffic.
- Environment design: agents perceive the web page, take realistic UI actions against variant A vs B; outcomes are aggregated into A/B metrics.
- Relevance: a concrete Web environmen pattern for the "test a product surface with simulated users" use case, and a clean source of interaction telemetry → decision metrics.


### [BASES: Large-scale Web Search User Simulation with LLM-based Agents](https://arxiv.org/abs/2402.17505) (Keyang Xuan)
- LLM-based agents simulate large-scale search users to generate realistic search behavior for evaluating/​training information-access systems.
- Environment design: a query→results→click interaction loop driven by agent user profiles, scalable to large simulated user populations.
- Relevance: a search/web surface for the user-simulation pipeline and a reference for scaling simulated users (toward MatrAIx's population-scale ambition).



- _add items here..._

### 📊 Evaluation & Telemetry
_Interaction logging, metrics, LLM-as-judge, human eval protocols._

- _add items here..._

### 🧩 Others
_Multi-agent / social simulation, long-horizon tasks, related work._

### [Magentic Marketplace: An Open-Source Environment for Studying Agentic Markets](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/10/multi-agent-marketplace.pdf)
- Proposes an open-source multi-agent marketplace simulation where consumer-side assistant agents interact with business-side service agents to search, communicate, receive proposals, and complete transactions.
- The environment is built around a centralized marketplace server and a simple action protocol supporting agent registration, search, message passing, proposal submission, payment, and full interaction logging; evaluation focuses on transaction success, consumer utility, welfare, search quality, manipulation resistance, and behavioral biases such as first-proposal bias.
- Relevant to MatrAIx because it provides a reusable pattern for long-horizon multi-agent social/economic simulations with heterogeneous roles, private preferences, strategic service agents, market-level outcomes, and extensible domains beyond restaurants/contractors.

### [SOTOPIA: Interactive Evaluation for Social Intelligence in Language Agents](https://arxiv.org/abs/2310.11667) (Keyang Xuan)
- Introduces an open-ended interactive environment where LLM agents role-play characters with personas, goals, relationships, and private information, interacting turn by turn to pursue their social goals.
- Method & scale: 90 social scenarios paired with 40 characters into role-play episodes; turn-based interaction over a structured action space, scored by a multidimensional LLM-as-judge.
- Relevance: a good structure and template for Task 1's shared interface and telemetry (e.g. a structured observation/action schema, a "scenario + persona + goal" configuration that maps cleanly onto `reset → step → done` with persona injected via system prompt).

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

**Owner(s):** @JianhengHou, @dipeshbabu, _@AravindMohan10_ (add more as needed)

---

## 📝 Task 2 — Type 1: Survey Environment _(simplest / start here)_

The simplest surface — the agent reads a stimulus (product concept, message, description, UI mockup, decision scenario) and returns structured feedback. Behaves like an LLM answering a questionnaire rather than a tool-using agent.

- Define input formats and a **structured output schema** (rating scores, free-form feedback, ranked preferences, objections, predicted adoption).
- Reference implementation + a couple of example stimuli.

**Owner(s):** @JianhengHou, @dipeshbabu, @Keyang Xuan, @Peiyang-Song (add more as needed)

---

## 💬 Task 3 — Type 2: Chatbot Environment _(priority)_

High-value surface — many target products *are* AI systems, so they can be tested directly through conversation. Prioritized at kickoff.

- Persona agent converses with a target system (assistant, support bot, tutor, coding assistant).
- Adapter to connect an external chatbot (API).
- Conversation logging + metrics (helpfulness, trust, clarity, satisfaction, length).
- Cover **cooperative** users **and** hard/realistic users (privacy-sensitive, low-literacy / elderly, confused, adversarial) — the realistic-but-hard cases are where simulation adds value.

**Owner(s):** @JianhengHou, @dipeshbabu, @Xiaoyi-Liu, @ahmd-mohsin (add more as needed)

---

## 🌐 Task 4 — Type 3: Web Environment

Agent interaction with web surfaces (landing pages, prototypes, dashboards, **forum / social** sub-form).

- Sandbox playground (host a supplied web surface) **and/or** agent API path.
- Capture signals: pages, clicks, scroll, hesitation, failed actions, final decision.
- Forum/social subtype: read posts, comment, initiate DMs — same interaction layer, different surface.

**Owner(s):** @JianhengHou, @dipeshbabu, _@ahmd-mohsin, @wenkai-li (add more as needed)

---

## 📱 Task 5 — Type 4: App / Sandbox Environment _(longer-term, deprioritized)_

Complex interactive products (mobile / desktop / sandbox builds). Pulls in low-value engineering (auth, captchas, device state, reset) — explicitly **deprioritized** for early stages.

- Scope build formats and UI-automation approach for later.

**Owner(s):** @JianhengHou, @dipeshbabu, _@AravindMohan10_ (add more as needed)

---

## 🤝 How to Contribute

1. Pick a task above and add your name to its **Owner** field.
2. Open an issue for your task to track details and progress.
3. Align early on the shared **interface + telemetry** (Task 1) — it blocks Tasks 2–5.
4. Keep your own `Status Update - <Your Name>` issue and add the `status-update` + `team: environment` labels so it's easy to find.
4. Build **Type 1 (survey)** and **Type 2 (chatbot)** first; they're the fastest path to a working end-to-end pipeline.
