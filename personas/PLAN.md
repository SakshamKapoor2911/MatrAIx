# 🧬 Persona Team — Plan & Task Assignments

> Working plan for the [Persona team](README.md). Each task has an **Owner** field — add your name to a placeholder slot. Each task can take **1–3 people** to start, and more can be added later (just append `@you`).

---

## 📚 Literature Review

Collect and summarize existing persona work, grouped into the subsections below.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

> 📌 **Default item format** — each entry should look like:
>
> ### [Paper / Dataset Title](https://link-here)
> - bullet point summarizing the key idea
> - bullet point on data / method / metrics
> - bullet point on relevance to MatrAIxPersona

### 🗃️ Persona Data
_Existing persona datasets / profile collections (also log scale + how to compare against them: Tencent ~1B, Persona-Hub 375K, NVIDIA Nemotron-Personas ~1M, Google, etc.)._

- _add items here..._

### 🛠️ Generation Methods
_Methods for synthesizing personas, persona-conditioned generation, augmentation._

- _add items here..._

### 🧩 Others
_Benchmarks, evaluation, related work that doesn't fit above._

- _add items here..._

---

## 🧱 Task 1 — Schema & Domain Design

The schema blocks everything else, so settle it first. **Don't over-explore** — define attributes from understanding of the target domains/tasks (limited-scope exploration).

- Organize personas around **4–5 major domains**, one of which is **basic demographics**, the rest tied to what we actually care about (see [README](README.md#-persona-structure)).
- Each domain gets a small **sub-team (1–3 people)** that designs its attributes/dimensions and builds that slice.
- Personas are then assembled by **linearly combining** the per-domain slices into one profile.
- Reuse prior attribute sets where possible (e.g. the ~25 attributes from the persona-collapse work) instead of reinventing.

**Owner(s):** _@name1, @name2_ (add more as needed)

---

## 🏗️ Task 2 — MatrAIxPersona-8B Data Construction

Build the raw persona pool through four complementary sources, all conforming to the Task 1 schema so they're mergeable. Many external contributors will also submit personas (accepted past a quality threshold).

| # | Subtask | Description | Owner(s) |
|---|---------|-------------|----------|
| 2.1 | 📥 **Collect open-source datasets** | Gather existing persona datasets (from the lit review), clean and normalize into the MatrAIx schema. | _@name1, @name2, @name3_ |
| 2.2 | 🧪 **Heuristic + synthetic generation** | Per-domain attribute combination + generation with multiple strong models (GPT, Claude, DeepSeek). Seed with real-world demographic priors for realism. | _@name1, @name2, @name3_ |
| 2.3 | 🧑 **Personas from real human info** | Build personas seeded by public/real signals (public figures, social profiles, chat/conversation data), properly anonymized. | _@name1, @name2, @name3_ |
| 2.4 | 📝 **Questionnaire → volunteers** | Design a questionnaire, collect volunteer data, and expand each response into a full persona via synthetic augmentation. | _@name1, @name2, @name3_ |
| 2.5 | 🔁 **Continuous-growth intake** | Let contributors keep adding personas over time (upload conversations, fill/extend a profile) so the pool grows; gate on the Task 3 quality bar. | _@name1, @name2, @name3_ |

> 🔑 Output: a unified, schema-conformant persona pool feeding into Task 3.

---

## 🧹 Task 3 — Data Quality Filtering & Evaluation

Turn the raw pool into clean, trustworthy data, and *measure* that quality (our differentiator). This is a **foundation** task — we generate a lot, then filter hard.

**Filtering**
- **Conflict checks** — flag internally impossible profiles (e.g. a 6-year-old who is married). Rule-based first.
- **Length / completeness** — drop too-thin or malformed profiles.
- **Deduplication** — remove near-duplicates by embedding similarity; when two are too close, keep one. (Reuse measurements / codebase from the persona-collapse work.)
- **Pipeline** — rule-based filters first, then **LLM-judge** for consistency/realism scoring.
- **Contributor threshold** — define a bar (e.g. N high-quality personas in a domain) for accepting external submissions.

**Quality evaluation**
- **Diversity / coverage** — personas should spread out, not collapse. Weight the **domains we care about higher** than basic demographics (don't end up with 1M personas that differ only by age).
- **Fidelity** — do persona-conditioned agents actually *behave* in line with the profile? The harder, more important axis (links to MatrAIxPersonaBench, Task 4).
- **Persona-factor analysis** — find which attributes actually shift agent action distributions (heatmap/matrix) to justify which dimensions are worth keeping. Note: behavior testing is expensive (API cost) — design it cheaply.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 📊 Task 4 — MatrAIxPersonaBench

Build the coreset for benchmarking **persona simulation quality**. For each persona, derive concrete tasks + evaluation tied to specific profile attributes.

- For each persona → generate task(s) targeting one or more attributes.
- Define **eval per task**: rule-based checks + LLM-judge.
- Cover multiple aspects (demographics, personality, preferences, behavior, communication).

> 🧩 Example: profile says *"dislikes comments in code"* → task: ask the agent (as this persona) to write a function → eval: check whether the output contains comments.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 🎓 Task 5 — MatrAIxPersonaTrain

A train-oriented coreset. **Goal: train a persona-conditioned model** that, given a persona profile, role-plays / responds *as* that person.

- Build `(persona, query) → persona-consistent response` pairs (synthetic, generated by strong models).
- Use for instruction tuning / fine-tuning so a model can faithfully follow any given persona.
- Keep it lightweight — this is a supporting artifact, not the paper's focus.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## ✅ Task 6 — Human Validation

A small human study to validate data quality and benchmark ground-truth.

- Sample a subset (a few hundred personas / bench tasks).
- Annotators rate each on a simple 1–5 rubric: **realism**, **internal consistency**, and (for bench) **correctness of the expected behavior / eval**.
- Report inter-annotator agreement; use results to calibrate the LLM-judge.

**Owner(s):** _@name1, @name2, @name3_ (add more as needed)

---

## 🚀 Task 7 — Final Release

| # | Artifact | Release form | Owner(s) |
|---|----------|--------------|----------|
| 1 | 🌍 **MatrAIxPersona-8B** (≈8.3B) | Not released as a full dump — **API only**: sample/retrieve a subset on demand (e.g. retrieve relevant personas by description), with a max sample cap. | _@name1, @name2, @name3_ |
| 2 | 🎓 **MatrAIxPersonaTrain** | Released coreset for training. | _@name1, @name2, @name3_ |
| 3 | 📊 **MatrAIxPersonaBench** | Released benchmark + eval suite. | _@name1, @name2, @name3_ |

---

## 🤝 How to Contribute

1. Pick a task above and add your name to its **Owner** field.
2. Open a sub-issue / sub-doc for your task to track details and progress.
3. Align early on the shared persona **schema** (Task 1) — it blocks Tasks 2–5.

