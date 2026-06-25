# 🧪 Application Team — Plan & Task Assignments

> Working plan for the [Application team](README.md). Each task has an **Owner** field — add your name to a placeholder slot. Each task can take **1–3 people** to start, and more can be added later (just append `@you`).

> 🧭 **Scope from kickoff (Jun 13).** Block 3 is where many contributors plug in: each application = **a defined task + a concrete environment** (ideally an open-source app/website/prototype). We **sample** the personas that fit the task (e.g. 10K–100K, not the whole pool), run them through the environment (Block 2), collect the **telemetry**, and turn it into a **feedback report**. Keep each scenario simple; the value is a working task → simulation → report loop.

---

## 📚 Related Work

Collect and summarize prior work on user simulation, evaluation scenarios, and domain-specific agent benchmarks.

**Owner(s):** @Shirley-Huang, @Qianfeng-Wen, @Yifan-Liu, @Eliza_Fan, @Wenqian-Ye (add more as needed)

> 📌 **Default item format** — each entry should look like:
>
> ### [Paper / Benchmark Title](https://link-here)
> - bullet point summarizing the key idea
> - bullet point on the task / domain / evaluation design
> - bullet point on relevance to MatrAIx applications

### 🧪 User Simulation & Evaluation
_Synthetic users, LLM-based user studies, product/UX evaluation._

### [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
- Introduces "generative agents": LLM-backed agents with an observation–planning–reflection memory architecture that produce believable, emergent human behavior in a sandbox of 25 agents.
- Evaluation centers on believability (agents form opinions, plan days, remember events, spread information); ablations show each architectural component is critical.
- Foundational for MatrAIx: the memory/reflection/planning stack is the canonical blueprint for persona-driven agents that can be sampled and run through an environment to generate realistic telemetry.

### [Out of One, Many: Using Language Models to Simulate Human Samples](https://arxiv.org/abs/2209.06899)
- Shows GPT-3 can act as a "silicon sample" — conditioned on real socio-demographic backstories, it reproduces fine-grained, demographically correlated human response distributions.
- Validated on U.S. political surveys (outgroup word lists, attitude/behavior correlations), comparing silicon vs human samples across many subgroups.
- Underpins MatrAIx's persona-sampling premise — conditioned LLM personas as proxies for exploring hypotheses before real deployment — while flagging the conditioning that fidelity requires.

### [Can Large Language Models Replace Human Subjects? A Large-Scale Replication of Scenario-Based Experiments](https://arxiv.org/abs/2409.00128)
- Replicates 156 psychology/management experiments with GPT-4, Claude 3.5 Sonnet, and DeepSeek v3, finding 73–81% replication of main effects.
- Quantifies failure modes: LLMs inflate effect sizes and replicate poorly on socially sensitive topics (race, gender, ethics), positioning them as pilot/hypothesis tools, not replacements.
- A calibration reference for MatrAIx's feedback reports: it maps where simulated-user conclusions hold and where they diverge (inflated effect sizes, socially sensitive topics).

### [UXAgent: An LLM Agent-Based Usability Testing Framework for Web Design](https://arxiv.org/abs/2502.12561)
- Builds an end-to-end usability-testing system that auto-generates thousands of persona-driven LLM agents to interactively test a real website before any human study.
- Combines a Persona Generator, an LLM Agent reasoning module, and a Universal Browser Connector; outputs qualitative (agent interviews), quantitative (action counts), and video logs.
- Almost a one-to-one template for a MatrAIx application: defined task (test a web design) + concrete environment (browser) → sampled personas → telemetry → UX report.

### [Free Lunch for User Experience: Crowdsourcing Agents for Scalable User Studies](https://arxiv.org/abs/2505.22981)
- Proposes crowdsourcing large pools of LLM agents to run scalable user studies, surfacing edge cases and usability feedback that human cohorts miss.
- Frames simulation as complementary to small human studies, generating substantial qualitative feedback and helping discover pitfalls in study/UX design.
- Reinforces MatrAIx's scale advantage: a large persona population produces broader coverage and risk discovery than feasible with recruited participants.

### [Evaluating LLMs as Generative User Simulators for Conversational Recommendation](https://arxiv.org/abs/2403.09738)
- Defines a reproducible protocol for measuring how well LLMs emulate human users in conversational recommendation across five tasks (item selection, binary/open preferences, requesting recs, giving feedback).
- Reveals concrete deviations from human behavior — popularity bias, weak preference alignment, under-personalized requests — and shows model choice/prompting can reduce them.
- A rigorous evaluation-design protocol bearing on whether MatrAIx's simulated users behave human-like before their telemetry is trusted, plus a catalog of simulator failure modes (popularity bias, weak preference alignment).

### [LLMs Reproduce Human Purchase Intent via Semantic Similarity Elicitation of Likert Ratings](https://arxiv.org/abs/2510.08338)
- Introduces Semantic Similarity Rating (SSR): elicit free-text LLM responses and map them to Likert distributions via embedding similarity, avoiding unrealistic distributions from direct numeric prompting.
- Benchmarked against 9,300 human survey responses on personal-care products, reaching 90% of human test–retest reliability with realistic distributions and qualitative rationales.
- A technique relevant to MatrAIx feedback reports: converting persona reactions into survey-grade, comparable metrics (purchase intent, ratings) for synthetic market research.

### [Can Large Language Models Be an Alternative to Human Evaluations?](https://arxiv.org/abs/2305.01937)
- Tests LLMs as drop-in human evaluators by giving them the identical instructions, samples, and questions used in human studies (ACL 2023).
- Across open-ended story generation and adversarial attacks, LLM ratings track human-expert judgments consistently and more reproducibly than unstable human evaluation.
- Relevant to the "report" stage of MatrAIx's loop: evidence that LLMs can act not only as simulated users but as stable, reproducible evaluators that score outputs and assemble feedback.

### [Social Simulacra: Creating Populated Prototypes for Social Computing Systems](https://arxiv.org/abs/2208.04024)
- Pioneers using an LLM to populate a prototype social space — given a design (goal, rules, seed personas), it generates a large set of synthetic users and interactions, including rare/antisocial behaviors, so designers can probe a system before any real users exist.
- Park et al. (UIST '22): SimReddit-style prototypes shift behavior appropriately in response to design changes, and human participants often cannot distinguish simulated community activity from real activity.
- The most on-thesis prior work for MatrAIx Applications: it *is* the design→populate-with-simulated-users→observe→revise loop, the canonical citation for the whole task→simulation→feedback pattern.

### [AgentA/B: Automated and Scalable Web A/B Testing with Interactive LLM Agents](https://arxiv.org/abs/2504.09723)
- Replaces live human traffic in A/B tests with autonomous LLM agents performing realistic multi-step web behavior (search, click, filter, purchase) across diverse personas.
- Lu et al.: deployed 1,000 LLM agents to run an A/B test on a real Amazon interface, comparing against genuine human shopping logs and surfacing interface-sensitive, subgroup-level differences faster and at lower risk.
- A direct analog of a MatrAIx application: a concrete task (compare two designs) + real environment → sampled persona agents → behavioral telemetry → decision report.

### [SimUSER: Simulating User Behavior with Large Language Models for Recommender System Evaluation](https://arxiv.org/abs/2504.12722)
- Bougie & Watanabe propose an agent framework that mines self-consistent personas from historical interaction logs, then equips each simulated user with persona, memory, perception, and reasoning modules so it behaves like a believable human proxy when interacting with a recommender.
- Validates that simulated click/rating behavior aligns with real human behavior on recommender benchmarks, then demonstrates downstream utility by using the simulator's feedback to optimize recommender design choices (e.g., UI elements like thumbnails) without live A/B traffic.
- Almost a one-to-one analogue of the MatrAIx loop: persona-driven simulated users → interact with a recommender environment → emit behavioral telemetry → feed back into improving the system — a direct architectural reference for the Chatbot environment (Task 3) recommender focus.

### [On Generative Agents in Recommendation](https://arxiv.org/abs/2310.10108)
- Zhang et al. (SIGIR 2024) introduce Agent4Rec, an LLM-driven generative-agent simulator where each agent has a profile (initialized from real users), a memory module storing factual and emotional traces, and an action module that emulates taste, satisfaction, and exit decisions while browsing recommendations.
- Built on MovieLens, Steam, and Amazon-Book; studies how faithfully agents reproduce real user preferences plus emergent phenomena like filter bubbles, framed around the gap between offline metrics and online performance.
- A canonical persona-driven-simulated-user → recommender-agent design: MatrAIx can reuse its profile/memory/action decomposition to sample LLM users, run them through a recommender environment, and turn their browsing trajectories into telemetry for a feedback report.

### [User Behavior Simulation with Large Language Model based Agents](https://arxiv.org/abs/2306.02552)
- Wang et al. present RecAgent, an LLM-agent framework with a sandbox "virtual world" where agents not only browse and rate items but also chat and post socially, producing high-fidelity simulated user-behavior data for recommendation research.
- Simulates within a controllable environment, validates that generated behaviors match real human conduct, and reproduces social phenomena such as information cocoons and conformity, offering a reusable simulation paradigm rather than a single benchmark.
- Strongly on-thesis for MatrAIx's sample-personas → run-in-environment → collect-telemetry stages: its sandbox-plus-agent architecture is a template for standing up an environment where simulated users generate the interaction logs that become a feedback report.

### [AgentCF: Collaborative Learning with Autonomous Language Agents for Recommender Systems](https://arxiv.org/abs/2310.09233)
- Zhang et al. (WWW 2024) model both users and items as autonomous language agents that interact, then collaboratively reflect on discrepancies between their simulated decisions and real interactions to optimize their profiles — bridging language modeling and collaborative-filtering-style behavior simulation.
- Trained and evaluated on standard recommendation datasets (e.g., Amazon); the learned agents capture user-item, user-user, and item-item interaction patterns and can personalize behavior simulation comparable to real users.
- Relevant to making MatrAIx's simulated users faithful: its reflection-based correction loop is a concrete mechanism for aligning persona-driven agent behavior with real telemetry before that telemetry is trusted in a feedback report.

### [MEMARD: A Conversational Recommendation Dataset via Memory-Enhanced Multi-Agent Dialogue Synthesis](https://openreview.net/forum?id=3Df83swog6)(Eliza Fan)
- Extracts persona traits from real Amazon review data and proposes a memory-enhanced multi-agent framework to automatically synthesize high-quality conversational recommendation dialogues
- The dataset comprises 50,166 conversational turns derived from real Amazon movie reviews. Evaluation is rigorous, utilizing a mix of human blind tests and LLM-as-a-judge scoring across six key dimensions—user control, expertise, specificity, relevance, naturalness, and consistency—to measure dialogue quality and behavioral diversity.
- MEMARD serves as the foundational blueprint for MatrAIx’s recommendation-focused simulations. Its turn-level verifiers (quality gates) and persona-based memory retrieval provide the exact logic needed for MatrAIx to simulate "intelligent users" interacting with live product surfaces. By adopting the MEMARD benchmark design, MatrAIx can effectively measure whether its agents truly understand nuanced user needs (e.g., preference shifts, avoidance of disliked items) rather than just performing generic chat, bridging the gap between isolated model training and realistic, large-scale product-environment simulation.

### 🗂️ Domain Benchmarks
_Task suites for tutoring, e-commerce, support, gaming, enterprise, etc._

### [WebArena: A Realistic Web Environment for Building Autonomous Agents](https://arxiv.org/abs/2307.13854)
- Provides a reproducible, self-hosted web environment with four functional apps (online shopping, discussion forum, collaborative software dev, content management) plus utility tools (map, calculator).
- 812 long-horizon natural-language tasks scored by functional correctness on the resulting environment state; best GPT-4 agent reached only 14.4% vs 78.2% for humans.
- Maps directly to the Web environment type (Task 4) — landing pages, checkout, forums — and exemplifies realistic, state-checkable web-agent task suites.

### [WebShop: Towards Scalable Real-World Web Interaction with Grounded Language Agents](https://arxiv.org/abs/2207.01206)
- A simulated e-commerce site with 1.18M real products and 12,087 crowd-sourced instructions where an agent must search, navigate, customize, and purchase the matching item.
- Tests compositional instruction following, query reformulation, and acting on noisy webpage text; trained agents show non-trivial sim-to-real transfer to amazon.com and ebay.com.
- Maps to the Web (e-commerce/checkout) environment type, providing a scalable, auto-rewarded shopping task suite for persona-driven shopper agents.

### [Mind2Web: Towards a Generalist Agent for the Web](https://arxiv.org/abs/2306.06070)
- The first dataset for building generalist web agents that follow language instructions across arbitrary real-world websites rather than simulated ones.
- 2,000+ open-ended tasks with crowd-sourced action sequences spanning 137 real websites across 31 domains, enabling cross-domain and cross-website generalization evaluation.
- Maps to the Web environment type; its breadth of real sites speaks to web-agent generalization across MatrAIx web task suites.

### [τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045)
- Emulates dynamic conversations between an LLM-simulated user and a customer-service agent equipped with domain APIs and a policy document, across retail and airline domains.
- Evaluates by comparing the final database state to an annotated goal state and introduces the pass^k metric for reliability; even gpt-4o solves under 50% (pass^8 <25% in retail).
- Maps to the Chatbot environment type (customer support, Task 3) and is the strongest reference for policy-following, tool-using conversational agents with simulated user personas.

### [AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents](https://arxiv.org/abs/2407.18901)
- A high-fidelity execution engine (60K LOC) of 9 everyday apps operated via 457 APIs, populated with ~100 fictitious users and their simulated digital lives.
- 750 diverse multi-app autonomous tasks requiring rich interactive code generation with complex control flow; GPT-4o solves only ~49% normal / ~30% challenge tasks.
- Maps to the App/Sandbox environment type (Task 5) and exemplifies persona-grounded, multi-app sandbox simulation where agents act on behalf of simulated people.

### [AgentBench: Evaluating LLMs as Agents](https://arxiv.org/abs/2308.03688)
- A multi-dimensional benchmark of 8 interactive environments (OS, database, knowledge graph, card game, web shopping, web browsing, household, lateral thinking) for evaluating LLM-as-agent reasoning.
- Evaluates 29+ models, finding poor long-horizon reasoning, decision-making, and instruction-following as the main blockers; reveals a large commercial-vs-OSS gap.
- Spans Web, App/Sandbox, and game environment types simultaneously, offering MatrAIx a precedent for unified multi-environment agent evaluation harnesses.

### [MT-Bench-101: A Fine-Grained Benchmark for Evaluating LLMs in Multi-Turn Dialogues](https://arxiv.org/abs/2402.14762)
- Built on a three-tier hierarchical ability taxonomy with 4,208 turns across 1,388 multi-turn dialogues spanning 13 conversational tasks.
- Moves beyond single-turn or coarse multi-turn assessment to measure fine-grained dialogue abilities; evaluating 21 LLMs shows alignment techniques yield little multi-turn improvement.
- Maps to the Chatbot environment type (AI tutor, support), giving MatrAIx a fine-grained, turn-level scoring framework for evaluating target AI systems in conversation.

### [GAIA: a Benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)
- 466 human-authored questions for general AI assistants requiring reasoning, multi-modality, web browsing, and broad tool use, with unambiguous factual answers.
- Inverts the usual benchmark paradigm — tasks are easy for humans (92%) but hard for AI (15% for GPT-4 with plugins) — and ships with a public leaderboard.
- Maps to the App/Sandbox and Web environment types as a general assistant/tool-use suite, useful for stress-testing everyday-task competence of MatrAIx agents.

### [MathDial: A Dialogue Tutoring Dataset Grounded in Math Reasoning Problems](https://arxiv.org/abs/2305.14536)
- 3k one-to-one teacher–student tutoring dialogues collected by pairing human teachers with an LLM role-playing a student making typical multi-step math errors, annotated with a taxonomy of pedagogical teacher moves.
- Evaluated automatically and by humans, including an interactive setting measuring the trade-off between student solving success and prematurely "telling" the answer.
- Maps to the Chatbot environment type (AI-tutor, Task 3): the canonical tutoring benchmark, directly relevant to MatrAIx LLM-simulated-student personas stress-testing a tutoring system.

### [Rethinking Evaluation for Conversational Recommendation in the Era of LLMs (iEvaLM)](https://arxiv.org/abs/2305.13112)
- Shows static single-turn protocols drastically underestimate conversational recommenders, and introduces iEvaLM, an interactive evaluation driven by LLM-based user simulators seeded from ground-truth target items.
- Two interaction modes (attribute QA, free-form chit-chat) on ReDial/OpenDialKG; recall@50 on ReDial jumps 0.218 → 0.739 under interactive evaluation, showing the protocol was the bottleneck.
- Maps to the Chatbot environment type (conversational recommendation): the closest published analog to MatrAIx's core loop — a persona-driven LLM user simulator interactively evaluating a target system.

### [ToolLLM: Facilitating LLMs to Master 16000+ Real-world APIs (ToolBench)](https://arxiv.org/abs/2307.16789)
- Builds ToolBench from 16,464 real RESTful APIs across 49 categories (RapidAPI Hub), with single- and multi-tool instructions, annotated solution paths, and an automatic ToolEval evaluator.
- Targets large-scale real-world tool/API orchestration with a DFS-based decision-tree reasoning method, beyond the handful of domain APIs in τ-bench/AppWorld.
- Maps to the enterprise / App-Sandbox tool-use environment type: the canonical reference for breadth of real API tool-use MatrAIx enterprise agents must navigate.

### [Large Language Models as Zero-Shot Conversational Recommenders](https://arxiv.org/abs/2308.10053)
- He et al. (CIKM 2023) run a large empirical study showing off-the-shelf LLMs, with no fine-tuning, can act as conversational recommenders and outperform fine-tuned baselines, with probing analyses explaining where the gains come from.
- Contributes the largest public "in-the-wild" conversational-recommendation dataset (scraped from a real discussion forum) and evaluates multiple LLMs against fine-tuned CRS models with ranking metrics.
- Grounds the recommender-agent side of MatrAIx's loop: it defines the conversational-recommendation task and a realistic dataset/baseline suite that a persona-driven simulated user could converse against, with telemetry feeding the feedback report.

### 🧩 Others
_Red-teaming, synthetic data generation, related work._

### [AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents](https://arxiv.org/abs/2502.08691)
- Builds a large-scale social simulator with 10k+ LLM-driven agents (each with memory, planning, social-relationship modules) interacting across spatial, economic, and social environments, generating millions of interactions.
- Validated by replicating real behavioral experiments and surveys; used to study political polarization, rumor diffusion, and the effects of universal basic income.
- Closely related to MatrAIx's persona-based population simulation: it instantiates and validates large agent societies before real-world deployment.

### [OASIS: Open Agent Social Interaction Simulations with One Million Agents](https://arxiv.org/abs/2411.11581)
- A scalable social-media simulator modeled on real platforms (X, Reddit) with dynamic social networks, rich action spaces (follow, comment, post), and recommendation systems, scaling to one million LLM agents.
- Reproduces emergent social phenomena including information spread, group polarization, and herd effects across two platform settings.
- Telemetry-driven user simulation scaled to population level with realistic engagement dynamics — the population-scale end of MatrAIx's pre-deployment-feedback goal.

### [Project Sid: Many-agent simulations toward AI civilization](https://arxiv.org/abs/2411.00114)
- Presents the PIANO architecture letting agents run concurrent processes while staying coherent, scaling many-agent simulations from 10 to 1000+ agents.
- Run in a Minecraft environment where agents autonomously develop professions, follow and amend collective rules, and transmit culture — measuring emergent civilizational progress.
- Relevant for understanding emergent collective behavior, role specialization, and norm formation in large persona-agent populations.

### [Curiosity-driven Red-teaming for Large Language Models](https://arxiv.org/abs/2402.19464)
- Frames automated red-teaming as a curiosity-driven RL exploration problem so a red-team LLM generates a broader, more diverse set of prompts that elicit undesirable target-model responses.
- Achieves greater test-case coverage while maintaining or improving attack effectiveness over prior RL-based red-teaming (ICLR 2024).
- Directly relevant to MatrAIx red-teaming: simulating adversarial users to stress-test agent/application behavior before deployment with high-coverage synthetic attacks.

### [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)
- Establishes the LLM-as-a-judge evaluation methodology, showing strong judges (GPT-4) reach over 80% agreement with human preferences — matching human-human agreement on open-ended tasks.
- Introduces MT-Bench (multi-turn questions) and Chatbot Arena (crowdsourced pairwise battles), and characterizes judge biases (position, verbosity, self-enhancement) with mitigations.
- Core evaluation methodology for MatrAIx's feedback reports: a scalable, validated way to turn simulated interactions into quality judgments without exhaustive human annotation.

### [Self-Instruct: Aligning Language Models with Self-Generated Instructions](https://arxiv.org/abs/2212.10560)
- A near annotation-free pipeline that bootstraps instruction-tuning data from a model's own generations, generating instructions/inputs/outputs and filtering invalid or redundant samples.
- Yields a 33% absolute gain over vanilla GPT-3 on Super-NaturalInstructions and nearly matches InstructGPT-001, releasing a large synthetic instruction dataset (ACL 2023).
- A synthetic-data-generation method relevant to MatrAIx: diverse persona/task data for training or calibrating simulated users without costly human annotation.

### [EconAgent: LLM-Empowered Agents for Simulating Macroeconomic Activities](https://arxiv.org/abs/2310.10436)
- Integrates LLM agents with human-like perception and memory into a macroeconomic simulation covering labor/consumption markets plus fiscal and monetary policy.
- Reproduces classic phenomena (inflation, unemployment dynamics) more realistically than rule-based or learning-based agents, with human-like adaptive decision-making (ACL 2024).
- Relevant for economic/market simulation: shows how heterogeneous persona agents can model aggregate human economic behavior as a policy and product test bed.

### [Red Teaming Language Models with Language Models](https://arxiv.org/abs/2202.03286)
- The foundational automated red-teaming paper: one LM generates adversarial test cases that elicit harmful behavior from a target LM (zero-shot, few-shot, supervised, and RL-based generation), with a classifier scoring harmful responses.
- Evaluated on a 280B dialogue model, uncovering offensive replies, leaked training data, generated PII, and distributional bias — establishing the generate-case → classify-harm methodology later RL red-teaming builds on.
- The canonical reference that the existing Curiosity-driven red-teaming entry extends, and the grounding work behind MatrAIx's "simulate adversarial users to stress-test an application" use case.

### [A Survey on Large Language Models for Recommendation](https://arxiv.org/abs/2305.19860)
- Wu et al. survey LLMs-for-recommendation, organizing the field into Discriminative (DLLM4Rec) and Generative (GLLM4Rec) paradigms, covering fine-tuning, prompting, and key open challenges.
- A literature survey (not a method or benchmark): it categorizes methodologies across both paradigms and maintains a companion index of papers in the area.
- Provides taxonomy and grounding for MatrAIx's recommender-agent subarea, helping situate persona-driven user simulation and conversational recommendation within the broader LLMs-for-rec landscape.

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

**Owner(s):** @Shirley-Huang, @Xiaoyi-Liu, @rosierogao (add more as needed)

---

## 💬 Task 3 — Type 2: Chatbot Scenarios _(priority)_

Scenarios where the agent converses with a target AI system and evaluates it.

- 2–3 scenarios (e.g. AI tutor, AI customer support / returns flow, onboarding helper).
- Include **hard users** (privacy-sensitive, low-literacy/elderly, confused, adversarial).
- Each with task prompt, persona requirements, metrics, example run.

**Owner(s):** @Shirley-Huang, @Eliza_Fan, @Xiaoyi-Liu, @Qianfeng-Wen, @Yifan-Liu, @rosierogao (add more as needed)

> 🎯 **@Qianfeng-Wen & @Yifan-Liu** are focusing on **AI recommender agent** settings — a persona-driven simulated user converses with a recommender chatbot (conversational recommendation) and we evaluate the quality of its suggestions. Builds on [iEvaLM](https://arxiv.org/abs/2305.13112) and [Evaluating LLMs as Generative User Simulators for Conversational Recommendation](https://arxiv.org/abs/2403.09738) from Related Work.

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

**Owner(s):** @Shirley-Huang, @Eliza_Fan, @name3_ (add more as needed)

---

## 🤝 How to Contribute

1. Pick a task above and add your name to its **Owner** field.
2. Open an issue for your task to track details and progress.
3. Align early on the shared **Application Template** (Task 1) — it blocks Tasks 2–6.
4. Keep your own `Status Update - <Your Name>` issue and add the `status-update` + `team: application` labels so it's easy to find.
4. Build **Type 1 (survey)** and **Type 2 (chatbot)** scenarios first.
