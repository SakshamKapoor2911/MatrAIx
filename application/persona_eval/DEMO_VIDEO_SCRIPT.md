# MatrAIx Cockpit — Video Demo Script (English)

**Audience:** Investors, research partners, YC-style demos, external stakeholders  
**Estimated runtime:** ~20–24 min (full tutorial) · ~9 min (pitch cut)  
**Tone:** Precise, mission-led, research-grade. Confident without hype. Every sentence earns its place.

---

## OPEN — Home (0:00–1:45)

**[VISUAL: MatrAIx logo. Dark mission-control UI. Globe animation.]**

> Most product teams still learn how users behave *after* launch — through A/B tests, support tickets, and churn.
>
> **MatrAIx** asks a different question: *What if you could observe realistic user behavior across your product — before a single real person touches it?*
>
> We built PersonaBench to answer that. MatrAIx is a workbench for **persona-conditioned simulation**: digital humans with real demographics, preferences, and behavioral signatures, running structured evaluations against chatbots, surveys, live websites, and native applications.
>
> **[VISUAL: Home hero — "Planetary-scale digital humans", 8.3B personas stat]**

> The ambition is planetary scale. Not one synthetic user — cohorts. Not one scenario — a library of evaluation tasks with domain-specific metrics. Not a demo toy — reproducible Harbor jobs you can archive, compare, and build research on.
>
> The application organizes around three surfaces:
>
> - **Persona Eval** — the developer cockpit where you configure and launch simulations
> - **Runs** — where cohort results, aggregation reports, and per-persona evidence live
> - **Persona Store** — where you browse and design persona cohorts from a curated library
>
> **[CLICK: "PersonaEval cockpit" CTA]**

> Let's walk the full loop — from a single smoke test to a distributed cohort evaluation — starting where the work actually happens.

---

## ACT I — Persona Eval Overview (1:45–2:45)

**[VISUAL: Cockpit setup — "Configure a simulation"]**

> This is the **Persona Eval cockpit** — a focused developer surface, not a dashboard decoration. Researchers and engineers come here to answer one question: *How does this product perform when realistic users interact with it?*
>
> Four **application types** share one evaluation philosophy:
>
> | Type | What it tests |
> |------|---------------|
> | **Survey** | Structured questionnaires — product feedback, concept testing, policy comprehension |
> | **Chatbot** | Multi-turn dialogue — recommenders, support bots, domain assistants |
> | **Web** | Live browser tasks on real public URLs — navigation, comparison, decision-making |
> | **OS app** | Native application behavior on Linux, macOS, and iOS — settings, workflows, computer-use |
>
> Each type uses the same configure → run → score → report pipeline. The interaction surface and evaluation metrics change; the scientific rigor does not.
>
> We begin with **Survey** — the fastest path to a complete evaluation loop.

---

## ACT II — Survey: Quick Run (2:45–6:15)

**[VISUAL: Application type → Survey]**

> Every simulated user is driven by two layers of intelligence.
>
> First, a **persona** — a structured identity drawn from our bench: demographics, psychographics, source provenance. Second, a **persona model** — the LLM you select here that decides how this identity thinks, answers, and behaves under task pressure.
>
> **[VISUAL: Persona model dropdown]**
>
> That separation matters for research. The persona is the experimental subject. The model is a controlled variable you can ablate, swap, or hold constant across cohorts.
>
> Persona sampling offers three modes:
>
> - **Quick pick** — hand-select one or a few personas for rapid iteration
> - **Random sample** — draw a cohort from the pool, with optional dimensional filters
> - **Stratified** — balance representation across attributes like age, source, or occupation
>
> For our first run: **Quick pick**.
>
> **[VISUAL: Select persona card, e.g. persona-0042]**
>
> **[VISUAL: Task card — Product concept survey / FocusLoop]**
>
> Select an existing task. Each ships with its own instruction, input materials, output schema, and verifier — a complete experimental protocol, not a prompt template.
>
> **[CLICK: Run eval]**
>
> The cockpit launches a Harbor job in **auto mode** — identical execution to the CLI path, fully visualized.
>
> **[VISUAL: Live run — pipeline strip, trajectory]**
>
> Watch the persona work through the survey. When it completes, the **scorecard** surfaces.
>
> **[VISUAL: Evaluation tab / scorecard metrics]**
>
> These are not generic LLM rubric scores. Each task defines **domain-specific metrics** — coverage, persona alignment, friction signals, comprehension — designed by specialists to answer: *What did this cohort experience, and what does that mean for the product?*
>
> That is the core research value: structured behavioral evidence, not vibes.
>
> **[CLICK: Reset]**

---

## ACT III — Survey: Batch Run (6:15–10:45)

> A single run validates the loop. **Batch runs** are where PersonaBench becomes infrastructure.
>
> **[VISUAL: Switch persona mode → Random sample]**
>
> We sample randomly. No filters applied yet — but notice the filter control.
>
> **[VISUAL: Briefly open Persona filter modal — age, source, occupation, dimensions]**
>
> Filters let you define a study cohort with intent: price-sensitive shoppers, older adults, synthetic versus curated sources. The same filter vocabulary appears in Persona Store and in batch sampling — one cohort definition, reusable everywhere.
>
> Close the modal. Run unfiltered for this demo.
>
> **[VISUAL: Sample size → 24]**
>
> Cohort size: **24 personas**.
>
> **[VISUAL: Parallel → 8]**
>
> **Parallel trials: 8.** This is distributed batch execution — eight personas running concurrently. At scale, this is the difference between an afternoon and a weekend.
>
> **[CLICK: Run eval]**
>
> **[VISUAL: Batch trial grid — 24 cells. Spinning → green on completion.]**
>
> Each cell is one persona, one trial. Running cells pulse. Completed cells turn green. Failures surface in red — first-class, not hidden. You always know where the batch stands.
>
> **[VISUAL: All green → View job]**
>
> Batch complete. Open **View job** to enter the cohort report.

---

## ACT IV — Survey: Job Report & Trial Drill-down (10:45–12:45)

**[VISUAL: Harbor job detail — cohort aggregation]**

> A **job** is one batch execution. Inside it: **trials** — one per persona.
>
> At the job level, you read **cohort-level evaluation**: aggregate metrics, distributions, summaries. This answers: *How did this group perform on this task?*
>
> Walk through two or three headline metrics. Enough to show these are actionable product insights grounded in verifier output — not vanity numbers.
>
> **[VISUAL: Trial list below aggregation]**
>
> Every persona has its own row in the trial list.
>
> **[CLICK: Open one trial]**
>
> The **trial report** is the evidence layer: full trajectory, submission artifact, verifier results, per-persona scores. This is what a researcher cites. This is what a product team acts on. *What did persona 0042 actually answer, and why?*
>
> **[VISUAL: Back to cockpit]**
>
> That is a complete persona evaluation for surveys: configure, run, cohort insight, per-subject evidence.
>
> The same architecture extends to conversational systems. Switch to **Chatbot**.

---

## ACT V — Chatbot: Context & Quick Run (12:45–15:15)

**[VISUAL: Application type → Chatbot]**

> Chatbot mode evaluates dialogue products. We use **RecAI** — a recommender-agent exposed through a REST chat API. The persona drives a multi-turn conversation and produces transcript and recommendation artifacts.
>
> Before running, establish context. Two affordances matter:
>
> **[VISUAL: Click info icon on persona card → Persona detail modal]**
>
> The **persona info** icon reveals who is being simulated — attributes, preferences, behavioral profile.
>
> **[VISUAL: Click info icon on task card → Instruction panel]**
>
> The **task info** icon reveals what they are trying to accomplish — the scenario instruction.
>
> Together: **who** meets **what to do**. That pairing is the experimental design, visible before you spend a single API call.
>
> **[VISUAL: Quick pick — one persona, RecAI task selected]**
>
> **[CLICK: Run eval]**
>
> **[VISUAL: Live chat trajectory — user/assistant turns]**
>
> The persona conducts a multi-turn conversation. The scorecard captures recommendation quality, persona adherence, turn efficiency — metrics defined for dialogue, not borrowed from surveys.
>
> **[VISUAL: Results / scorecard briefly]**

---

## ACT VI — Chatbot: Filtered Batch (15:15–17:45)

> **[VISUAL: Random sample. Open filters. Apply a cohort-specific filter.]**
>
> This time we **filter** the pool — a slice of personas whose attributes are relevant to movie recommendations.
>
> **[VISUAL: Sample size → 4. Parallel → 4.]**
>
> Four personas. Four parallel trials. The entire cohort runs concurrently.
>
> **[CLICK: Run eval → wait → View job]**
>
> **[VISUAL: Job report for RecAI chatbot cohort]**
>
> The job report shows how this filtered cohort experienced the recommender: engagement patterns, satisfaction signals, recommendation relevance across the group.
>
> **[CLICK: One trial → chat history / transcript]**
>
> Open a trial for the **full chat history** — every turn, every recommendation, every artifact. Aggregate metrics tell you *what happened at scale*. Trial reports tell you *why*.
>
> **[VISUAL: Back to cockpit. Switch to Web.]**
>
> Surveys capture structured responses. Chatbots capture dialogue. **Web** captures something harder: autonomous browsing behavior on live sites.

---

## ACT VII — Web: Cocoa Step Replay (17:45–19:45)

**[VISUAL: Application type → Web. Select Cocoa plan-choice task.]**

> Web mode runs personas against **live public URLs** in a real browser environment. We use the **Cocoa** example: a persona comparing pricing plans on pythonanywhere.com.
>
> Under the hood, PersonaBench supports multiple web interaction stacks — Playwright, browser-use, Cocoa, CUA — each tuned for different fidelity-cost tradeoffs. The cockpit abstracts the stack; you pick the task, the right agent attaches.
>
> **[VISUAL: Quick pick. One persona.]**
>
> **[CLICK: Run eval — note: first run may build a Docker image]**
>
> **[VISUAL: Live browser trajectory — steps unfolding]**
>
> You do not receive only a final answer. You receive **steps**: navigations, clicks, reasoning at each decision point.
>
> **[VISUAL: Step list → replay one step]**
>
> Click any step to replay and inspect what the persona observed and did at that moment. This is auditable behavioral evidence — the kind of data that supports both product decisions and research publication.
>
> **[VISUAL: Final decision JSON / scorecard]**
>
> The run concludes with a structured decision artifact — which plan was chosen, on what basis — plus evaluation metrics.
>
> Web simulation closes the loop on public-facing products. But many critical user experiences live inside **native operating systems**.

---

## ACT VIII — OS App: Native Platform Playground (19:45–21:15)

**[VISUAL: Application type → OS app]**

> The fourth mode is the **OS app playground** — PersonaBench's surface for testing persona behavior inside native application environments.
>
> We support three platforms:
>
> - **Linux** — desktop workflows in containerized environments
> - **macOS** — native macOS application interaction via computer-use simulation
> - **iOS** — mobile settings, permissions, and in-app flows on simulated devices
>
> **[VISUAL: Task picker showing platform-tagged tasks — notification preferences, settings workflows, etc.]**
>
> Each platform task defines a realistic native scenario: adjusting notification preferences, navigating system settings, completing in-app workflows. The persona does not fill a form or chat — it operates the UI the way a real user would, through screenshot-driven computer-use agents.
>
> **[VISUAL: Setup screen — persona selection, task card, Run eval CTA]**
>
> The cockpit workflow is identical: sample personas, configure parallelism, launch. But OS app runs are heavier — they may require platform-specific runtimes, longer timeouts, and in some cases dedicated infrastructure.
>
> **[VISUAL: Optionally start a quick run or show a pre-completed run with step trajectory]**
>
> If time permits, we launch a quick run here. Otherwise, notice the setup is ready — task selected, persona assigned, evaluation pipeline wired.
>
> We will not wait for a full OS app run to complete in this demo. These simulations are intentionally thorough, and a single trial can take several minutes. That depth is the point: native app behavior is where persona fidelity matters most, and where premature shipping is most expensive.
>
> **[VISUAL: Hold on OS app cockpit setup]**
>
> We encourage you to run one yourself after this walkthrough. Pick a platform, select a persona, and watch a digital human navigate a real application environment. That firsthand experience is the best argument for what PersonaBench makes possible.
>
> Four application types. One evaluation architecture. From a two-minute survey to a ten-minute native app session — the cockpit scales with the fidelity your research demands.

---

## ACT IX — Runs (21:15–22:15)

**[VISUAL: Top nav → Runs]**

> Every batch run creates a **job** in **Runs** — your experiment archive.
>
> One job. Many trials. One cohort report.
>
> **[VISUAL: Job list — search, sort, app-type tags]**
>
> Search and browse past jobs. Survey batches, chatbot cohorts, web runs, OS app sessions — unified in one history. This is how teams revisit results, compare experimental conditions, and share evidence without re-executing.
>
> Runs is not a log viewer. It is the **persistent research record** behind every cockpit session.

---

## ACT X — Persona Store (22:15–23:15)

**[VISUAL: Top nav → Persona Store]**

> **Persona Store** is the library that powers every simulation.
>
> Our bench pools personas from multiple curated sources — Nemotron, OASIS, PRIMEX, PersonaHub — alongside synthetic personas, each with rich dimensional attributes.
>
> **[VISUAL: Search / filter by source, age, occupation]**
>
> Browse freely, or **filter** to a cohort that matches your study design.
>
> **[VISUAL: Apply a specific attribute filter → filtered grid]**
>
> For example: personas from a given source, within an age band, with a particular occupation. The store is both exploration and cohort design — the same filters feed directly into Persona Eval sampling.
>
> Persona quality is the foundation. Everything downstream — survey answers, chat tone, browsing patterns, app navigation — is only as credible as the identities you start with.

---

## CLOSE — Home & Mission (23:15–24:00)

**[VISUAL: Navigate to Home. Globe animation.]**

> We walked the full MatrAIx loop:
>
> - Configure simulations across four application types in **Persona Eval**
> - Scale from one persona to distributed cohorts with parallel execution
> - Read cohort insights and per-persona evidence in **Runs**
> - Design study populations in the **Persona Store**
>
> The research promise is straightforward: **replace guesswork with structured behavioral evidence** — before real users encounter your product.
>
> The mission is larger: build the infrastructure for **planetary-scale digital human simulation** — so every team, from a two-person startup to a research lab, can evaluate products against realistic users at the speed software deserves.
>
> **[VISUAL: Hero — "Planetary-scale digital humans"]**
>
> **MatrAIx** — simulate users across your applications, before real users do.
>
> Planetary-scale digital humans. Evidence-driven product development. Open the cockpit and run your first cohort.
>
> **[VISUAL: MatrAIx logo hold.]**

---

## Pitch Cut (~9 min)

| Segment | Duration | Keep / Cut |
|---------|----------|------------|
| Home + mission framing | 1:30 | **Keep** — problem + ambition |
| Persona Eval overview (4 types) | 0:45 | **Keep** — one sentence per type |
| Survey quick run + scorecard | 2:00 | **Keep** — research value of metrics |
| Survey batch 24×8 + View job | 2:00 | **Keep** — scale story |
| Job aggregation + 1 trial | 1:00 | **Keep** — evidence layer |
| Chatbot quick run (who × what) | 1:00 | **Keep** — context affordances |
| Chatbot filtered batch 4×4 | — | **Cut** — mention in one line |
| Web Cocoa step replay | 1:00 | **Keep** — behavioral evidence |
| OS app playground | 0:45 | **Keep** — platform breadth, invite to try |
| Runs + Persona Store | 0:30 each | **Compress** — one sentence each |
| Home close + mission | 0:45 | **Keep** — land the promise |

---

## Presenter Notes

- **Never rush the scorecard.** The metrics are the research differentiator.
- **Batch grid is the scale moment.** Let the audience watch cells turn green.
- **OS app: do not wait for a full run.** Frame the depth as a feature, invite hands-on.
- **Avoid:** "AI-powered", "revolutionary", "game-changing". Use: "structured evidence", "reproducible jobs", "cohort-level insight".
- **Land on mission in the close**, not feature list. YC cares about *why this matters*, not *what buttons exist*.
