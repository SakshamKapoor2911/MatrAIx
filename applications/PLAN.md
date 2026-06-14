# 🧪 Application Team — Plan & Task Assignments

> Working plan for the [Application team](README.md). Each task has an **Owner** field — add your name to a placeholder slot. Each task can take **1–3 people** to start, and more can be added later (just append `@you`).

> 🧭 **Scope from kickoff (Jun 13).** Block 3 is where many contributors plug in: each application = **a defined task + a concrete environment** (ideally an open-source app/website/prototype). We **sample** the personas that fit the task (e.g. 10K–100K, not the whole pool), run them through the environment (Block 2), collect the **telemetry**, and turn it into a **feedback report**. Keep each scenario simple; the value is a working task → simulation → report loop.

---

## 📚 Literature Review

Collect and summarize prior work on user simulation, evaluation scenarios, and domain-specific agent benchmarks.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

> 📌 **Default item format** — each entry should look like:
>
> ### [Paper / Benchmark Title](https://link-here)
> - bullet point summarizing the key idea
> - bullet point on the task / domain / evaluation design
> - bullet point on relevance to MatrAIx applications

### 🧪 User Simulation & Evaluation
_Synthetic users, LLM-based user studies, product/UX evaluation._

- _add items here..._

### 🗂️ Domain Benchmarks
_Task suites for tutoring, e-commerce, support, gaming, enterprise, etc._

- _add items here..._

### 🧩 Others
_Red-teaming, synthetic data generation, related work._

- _add items here..._

---

## 📐 Task 1 — Application Template & Conventions

Lock down the shared scenario format so every application runs end-to-end and is reproducible.

- Finalize the [Application Template](README.md#-application-template) fields.
- Define how a scenario references personas (Team 1) and an environment (Team 2), including **persona sampling** (which subset to pull and how many).
- One fully worked reference scenario others can copy.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

> 📌 The next four tasks mirror the four [environment types](../environments/PLAN.md). Each task = build the **task library + metrics** for scenarios running on that environment type. Start with Types 1 & 2.

## 📝 Task 2 — Type 1: Survey Scenarios _(start here)_

Scenarios where the agent reads a stimulus and returns structured feedback.

- 2–3 scenarios (e.g. product concept testing, messaging eval, UI-mockup feedback).
- Each with task prompt, persona requirements, structured output schema, metrics, example run.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 💬 Task 3 — Type 2: Chatbot Scenarios _(priority)_

Scenarios where the agent converses with a target AI system and evaluates it.

- 2–3 scenarios (e.g. AI tutor, AI customer support / returns flow, onboarding helper).
- Include **hard users** (privacy-sensitive, low-literacy/elderly, confused, adversarial).
- Each with task prompt, persona requirements, metrics, example run.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 🌐 Task 4 — Type 3: Web Scenarios

Scenarios on web surfaces (landing pages, prototypes, dashboards, forums) — contributors supply a **concrete open-source surface**.

- Example shapes: a **landing/checkout** flow → where do users drop off? a **web/forum** feature → does it attract usage?
- Tag each with persona requirements + the signals to capture (clicks, scroll, hesitation, final decision).

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 📱 Task 5 — Type 4: App / Sandbox Scenarios _(longer-term)_

Scenarios on complex interactive products (mobile / desktop / sandbox builds). Deprioritized for early stages.

- Example shapes: a **game** prototype → do users engage with a new feature (dwell time, click frequency)? a **coding assistant** → is the output good, who likes/dislikes it and why?
- Tag each with persona requirements + environment build format.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 📊 Task 6 — Evaluation Metrics & Report Generation

Cross-cutting layer: standardize how scenario outputs are scored, then turn raw telemetry into a deliverable.

- Per-domain metric sets (rule-based + LLM-judge).
- **Report generation**: given the task + the full telemetry trace from Block 2, produce the final **feedback report** (e.g. "users engaged X with feature Y; main objections were Z").
- Reusable analysis/report templates over collected traces.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## � How to Contribute

1. Pick a task above and add your name to its **Owner** field.
2. Open a sub-issue / sub-doc for your task to track details and progress.
3. Align early on the shared **Application Template** (Task 1) — it blocks Tasks 2–6.
4. Build **Type 1 (survey)** and **Type 2 (chatbot)** scenarios first.
