# 🌐 Environment Team — Plan & Task Assignments

> Working plan for the [Environment team](README.md). Each task has an **Owner** field — add your name to a placeholder slot. Each task can take **1–3 people** to start, and more can be added later (just append `@you`).

> 🧭 **Scope from kickoff (Jun 13).** Block 2 is mostly **engineering** and **task-agnostic**: given a persona-conditioned agent (persona injected via system prompt) and a defined environment, make the agent *run* and emit a full **telemetry trace**. We do **not** design tasks here (that's the Application team) — we provide a few general environment *types* they plug into. Keep each type **basic** so the end-to-end pipeline works first; depth can come later.

---

## 📚 Literature Review

Collect and summarize prior work on agent environments, evaluation harnesses, and simulation frameworks.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

> 📌 **Default item format** — each entry should look like:
>
> ### [Paper / Framework Title](https://link-here)
> - bullet point summarizing the key idea
> - bullet point on the environment / interface / evaluation design
> - bullet point on relevance to MatrAIx environments

### 🕹️ Agent Environments & Benchmarks
_Web agents, GUI/app automation, tool-use sandboxes, simulation frameworks (e.g. τ-bench / tau-bench style customer-service settings)._

- _add items here..._

### 📊 Evaluation & Telemetry
_Interaction logging, metrics, LLM-as-judge, human eval protocols._

- _add items here..._

### 🧩 Others
_Multi-agent / social simulation, long-horizon tasks, related work._

- _add items here..._

### [Magentic Marketplace: An Open-Source Environment for Studying Agentic Markets](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/10/multi-agent-marketplace.pdf)

* Proposes an open-source environment for studying **agentic markets**, where LLM-powered assistant agents act on behalf of consumers and service agents act on behalf of businesses.
* The core idea is to simulate future marketplaces where autonomous agents search, communicate, negotiate-like through proposals, and complete transactions under different market and information conditions.
* This is directly relevant to MatrAIx because it provides a concrete reference environment for building multi-agent simulations with heterogeneous roles, strategic behavior, long-horizon interactions, and measurable market-level outcomes.

### 🕹️ Agent Environments & Benchmarks

*Web agents, GUI/app automation, tool-use sandboxes, simulation frameworks (e.g. τ-bench / tau-bench style customer-service settings).*

* Introduces a simulated two-sided marketplace where Assistant Agents represent customers and Service Agents represent businesses.
* The environment supports agent-to-agent discovery, search, messaging, proposal exchange, payment, and final transaction completion.
* Uses synthetic service-market domains such as restaurants and home contractors, making it a benchmark for studying agent behavior in realistic economic decision-making scenarios.
* Relevant to MatrAIx because it offers a reusable environment pattern for marketplace-style simulations: agents have roles, preferences, constraints, private information, and multi-step interaction protocols.

### 📊 Evaluation & Telemetry

*Interaction logging, metrics, LLM-as-judge, human eval protocols.*

* Evaluates agents using market-level utility rather than only task completion; a transaction is successful only if it satisfies the customer’s required needs.
* Measures outcomes such as consumer utility, transaction success, welfare loss, search degradation, manipulation resistance, and behavioral bias.
* Compares different market conditions, including perfect search vs. noisy lexical search, varying consideration-set sizes, strategic manipulation by services, and first-proposal bias.
* Relevant to MatrAIx because it suggests a strong telemetry design: log search results, messages, proposals, payments, transaction outcomes, final utility, and failure/bias cases.

### 🧩 Others

*Multi-agent / social simulation, long-horizon tasks, related work.*

* Shows that frontier LLM agents can perform well under ideal search conditions, but their performance degrades when search is noisy, the market scales, or service agents use manipulation tactics.
* Finds that assistant agents can exhibit first-proposal bias, meaning faster-responding service agents may gain an advantage even when they are not the optimal choice.
* Positions agentic marketplaces as a testbed for studying emergent economic behavior, strategic interaction, hybrid human-agent markets, and protocol/mechanism design.
* Relevant to MatrAIx because it shows how a single environment can support both benchmark-style evaluation and broader social/economic simulation research.

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

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 🌐 Task 4 — Type 3: Web Environment

Agent interaction with web surfaces (landing pages, prototypes, dashboards, **forum / social** sub-form).

- Sandbox playground (host a supplied web surface) **and/or** agent API path.
- Capture signals: pages, clicks, scroll, hesitation, failed actions, final decision.
- Forum/social subtype: read posts, comment, initiate DMs — same interaction layer, different surface.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

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
