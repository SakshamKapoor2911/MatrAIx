# 🧬 Persona Team — Plan & Task Assignments

> Working plan for the [Persona team](README.md). Each task has an **Owner** field — add your name to a placeholder slot. Each task can take **1–3 people** to start, and more can be added later (just append `@you`).

---

## 📚 Related Work

Collect and summarize existing persona work, grouped into the subsections below.

**Owner(s):** @Shirley-Huang, @Eliza_Fan, @Yixuan-He, @Xiaoyi-Liu (add more as needed)

> 📌 **Default item format** — each entry should look like:
>
> ### [Paper / Dataset Title](https://link-here)
> - bullet point summarizing the key idea
> - bullet point on data / method / metrics
> - bullet point on relevance to MatrAIxPersona

### 🗃️ Persona Data
_Existing persona datasets / profile collections (also log scale + how to compare against them: Tencent ~1B, Persona-Hub 375K, NVIDIA Nemotron-Personas ~1M, Google, etc.)._

### [Scaling Synthetic Data Creation with 1,000,000,000 Personas (Persona-Hub)](https://arxiv.org/abs/2406.20094)
- Tencent AI Lab (Tao Ge et al.) curated 1 billion diverse personas automatically from web data — ~13% of the world's population — used as "distributed carriers of world knowledge" to prompt LLMs into generating diverse synthetic data (math, reasoning, instructions, NPCs, tools).
- Scale: 1B personas total; publicly released subset of ~200K preview personas plus ~370M "elite" personas, alongside ~175K synthetic data samples ([GitHub](https://github.com/tencent-ailab/persona-hub)). A 7B model trained on its synthetic math data reached 65% on MATH, matching gpt-4-turbo-preview.
- Relevance: the closest existing analog to MatrAIxPersona's scale ambition (1B vs ~8.3B), sharing the persona-driven synthetic-data approach; its released elite-persona set is the natural diversity/coverage comparison point, with MatrAIx sitting ~8x larger and population-grounded.

### [Nemotron-Personas](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA)
- NVIDIA's synthetic persona datasets grounded in real-world demographic, geographic, and personality-trait distributions — first such collection aligned to census statistics for names, sex, age, education, occupation, marital status, location.
- Scale: Nemotron-Personas-USA has 1M personas (~0.94B tokens, CC-BY-4.0); broader collection adds region-specific sets (France, India, Japan, Singapore, Korea). Built via a compound pipeline: a Probabilistic Graphical Model anchors demographic realism, then open-weight LLMs write narratives (each persona: core demographics + 16 contextual fields, 560+ occupations).
- Relevance: a close methodological reference for MatrAIxPersona's demographics domain — its PGM-then-LLM pipeline and census-aligned attributes mirror what demographic grounding requires, and its per-region census fidelity is a benchmark for distributional realism at global scale.

### [DeepPersona: A Generative Engine for Scaling Deep Synthetic Personas](https://arxiv.org/abs/2511.07338)
- A two-stage, taxonomy-guided engine that produces far deeper personas than one-paragraph profiles, addressing homogenization/stereotyping in agent-based social simulation.
- Scale/method: Stage 1 mines an 8,000+ node human-attribute taxonomy from real user–ChatGPT conversations; Stage 2 generates narratively coherent personas averaging 200+ structured attributes via progressive attribute sampling.
- Relevance: a depth-oriented counterpart to MatrAIx's breadth — its taxonomy-guided 200+-attribute personas and explicit anti-homogenization focus speak directly to MatrAIx's per-persona richness and diversity concerns.

### [PERSONA: A Reproducible Testbed for Pluralistic Alignment](https://arxiv.org/abs/2407.17387)
- SynthLabs built a procedurally generated persona testbed for evaluating and improving pluralistic alignment of LLMs across diverse viewpoints.
- Scale: 1,586 synthetic personas from US Census demographics + idiosyncratic attributes, yielding 3,868 prompts and 317,200 persona-conditioned feedback pairs.
- Relevance: a census-grounded persona testbed whose 317K persona-conditioned feedback pairs and pluralistic-alignment focus overlap MatrAIx's interest in whether persona agents express genuinely diverse, non-homogenized preferences.

### [Personalizing Dialogue Agents: I have a dog, do you have pets too? (PersonaChat)](https://arxiv.org/abs/1801.07243)
- Facebook AI Research's foundational persona-grounded dialogue dataset, where crowdworkers chat while each adopting a short profile, testing character consistency.
- Scale: 1,155 crowd-sourced personas (each 4–5 profile sentences), 10,907 dialogues, 162,000+ utterances.
- Relevance: the canonical small-scale, hand-written persona-dialogue benchmark and the historical baseline MatrAIx's scale dwarfs; it originates the profile-faithfulness-in-conversation question that MatrAIx studies.

### [OpenCharacter: Training Customizable Role-Playing LLMs with Large-Scale Synthetic Personas](https://arxiv.org/abs/2501.15427)
- Synthesizes large-scale character profiles from Persona-Hub personas and generates character-aligned instruction data (response rewriting + generation) to train customizable role-playing LLMs.
- Scale/method: builds character profiles on top of Persona-Hub personas (scalable to large numbers); fine-tuned LLaMA-3 8B reaches role-playing performance comparable to GPT-4o.
- Relevance: a demonstration that a persona database (Persona-Hub) converts into agent training data via a persona→character-profile→instruction pipeline — the same pathway from MatrAIxPersona entries to per-agent behavior data.

### [WildChat: 1M ChatGPT Interaction Logs in the Wild](https://arxiv.org/abs/2405.01470)
- Allen Institute for AI / Cornell (ICLR 2024) release a corpus of real, opt-in user–ChatGPT conversations collected in the wild — the canonical "real-conversation-derived" persona source.
- Scale: 1M conversations / 2.5M+ turns across 68 languages, each transcript enriched with geographic demographic metadata (state, country, hashed IP) and request headers.
- Relevance: highest-signal real-world seed corpus for grounding synthetic personas in actual user behavior and geography — DeepPersona mines its attribute taxonomy from exactly this kind of real ChatGPT-conversation data.

### [Synthetic-Persona-Chat: Faithful Persona-based Conversational Dataset Generation with LLMs](https://arxiv.org/abs/2312.10007)
- Google's synthetically generated, persona-grounded dialogue dataset, built with a Generator–Critic framework ([HF dataset](https://huggingface.co/datasets/google/Synthetic-Persona-Chat)).
- ~5,648 new synthetic personas with ~11K conversations (plus a 4,723-persona / 10,906-conversation PersonaChat extension); a mixture-of-experts Critic iteratively filters quality, cutting the Turing-test losing rate vs human PersonaChat from 17.2% to 8.8% over three rounds.
- Relevance: a Generator–Critic quality-control loop relevant to MatrAIx's synthetic-persona pipeline, with a measured fidelity signal (Turing-test win rate vs human personas) for how human generated personas read.

### [Virtual Personas for LMs via an Anthology of Backstories](https://arxiv.org/abs/2407.06576)
- A persona conditiong method that uses open-ended first-person life narratives to steer LLMs toward more representative, consistent, and diverse virtual personas for approximating human survey respondents.
- Scale/method: prompt the LLM with open-ended questions to self-generate a large anthology of backstories, then greedy-match backstories to real survey respondents to build aligned "virtual subjects".
- Relevance: a persona-generation recipe which is relevant to MatrAIxPersona's narrative-expansion step (Task 1, Step 3), offering a generation-plus-validation pattern for population-grounded personas through respondent matching and distribution/consistency metrics.

### [SCOPE: Sociopsychological Context Shapes Persona-Based LLM Simulations](https://arxiv.org/abs/2601.07110)
- A persona framework grounded in rich sociopsychological attributes rather than demographics alone. The authors collected a 141-question survey from 124 participants covering values, beliefs, identity, personality, social attitudes, and life experiences, then used these factors to construct persona representations for LLM simulation.
- Key finding: demographic variables explain only ~1.5% of variation in human responses, while sociopsychological factors substantially improve behavioral prediction. Across seven LLMs and evaluations on both SCOPE and SimBench, personas built from values, beliefs, and identity consistently outperform demographic-only personas and reduce demographic stereotyping and over-accentuation.
- Relevance: The paper argues that realistic human simulation requires modeling latent psychological structure—not just age, gender, occupation, or location. Its survey-derived belief, value, identity, and personality dimensions closely align with MatrAIx's goal of building personas that capture deeper behavioral drivers rather than surface demographic descriptors.

### 🛠️ Generation Methods
_Methods for synthesizing personas, persona-conditioned generation, augmentation._

### [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
- Park et al. (Stanford/Google) introduce generative agents that simulate believable individual and emergent social behavior in a sandbox of 25 agents.
- The architecture extends an LLM with a memory stream, reflection (synthesizing memories into higher-level insights), and planning; ablations show each component is critical to believability, evaluated via human-judged believability studies.
- Foundational for the agent side of MatrAIx: a concrete memory/reflection/planning loop for turning a static persona into a persistent, behaviorally coherent agent.

### [Generative Agent Simulations of 1,000 People](https://arxiv.org/abs/2411.10109)
- Park et al. (Stanford/DeepMind) build agents from ~2-hour qualitative interviews with 1,052 real people, then test how faithfully each agent reproduces that individual's survey/experimental responses.
- Agents match participants' General Social Survey answers ~85% as well as participants match themselves two weeks later, and reduce accuracy bias across racial/ideological groups vs demographic-only descriptions.
- Direct evidence that rich, interview-style conditioning outperforms thin demographic priors — bearing directly on MatrAIx's question of how deeply personas must be conditioned to behave faithfully.

### [Claude's Character](https://www.anthropic.com/research/claude-character)
- Anthropic's account of "character training": instilling stable traits (curiosity, open-mindedness, honesty about its own leanings) into a model rather than only avoiding harm.
- Uses a character variant of Constitutional AI on purely synthetic, self-generated data — the model drafts trait-relevant messages, generates trait-aligned responses, and ranks them to train a preference model, with no human feedback in the core step.
- Relevant to giving MatrAIx agents consistent, persona-faithful personalities at scale through self-generated preference data, and to trait stability across long interactions.

### [Self-Instruct: Aligning Language Models with Self-Generated Instructions](https://arxiv.org/abs/2212.10560)
- Wang et al. bootstrap instruction-following by having an LLM generate its own instructions, inputs, and outputs, then filtering low-quality/redundant samples before fine-tuning.
- Seeded from 175 human tasks, the pipeline produces 52K instructions / 82K instances; applied to GPT-3 it yields a 33% absolute gain on Super-NaturalInstructions, nearly matching InstructGPT-001 with no private data.
- The core synthetic-data-generation + filtering recipe underlying persona-conditioned augmentation — directly relevant to how MatrAIx self-generates large, deduplicated, quality-filtered persona behavior data.

### [Character-LLM: A Trainable Agent for Role-Playing](https://arxiv.org/abs/2310.10158)
- Shao et al. (Fudan) train agents to embody specific people (e.g. Beethoven, Cleopatra) with profile, experiences, and emotions rather than relying on prompt-only role-play.
- An "Experience Reconstruction" process converts profiles into formatted experience data for SFT, plus protective experiences to suppress out-of-character hallucination; evaluated via an interview playground.
- Bakes a persona into model weights (vs prompting) and defends against character drift — relevant to MatrAIx's persistent, fine-tuned persona setting.

### [LLMs are Superpositions of All Characters: Arbitrary Role-play via Self-Alignment (Ditto)](https://arxiv.org/abs/2401.12474)
- Ditto (OFA-Sys) posits that LLMs already contain latent knowledge of countless characters and elicits role-play as a self-alignment / reading-comprehension task — no proprietary teacher needed.
- Self-generates a role-play training set of 4,000 characters (10x prior datasets) for fine-tuning; maintains role identity and role-specific knowledge across multi-turn dialogue.
- A scalable, self-supervised augmentation method for massive persona-conditioned dialogue data — relevant to MatrAIx's scale, where per-persona human/GPT-4 supervision is infeasible.

### [WizardLM: Empowering LLMs to Follow Complex Instructions (Evol-Instruct)](https://arxiv.org/abs/2304.12244)
- Xu et al. (Microsoft) introduce Evol-Instruct: an LLM rewrites seed instructions step by step into progressively more complex ones via in-depth evolution (add constraints, deepen reasoning) and in-breadth evolution (novel, diverse instructions).
- Fine-tuning LLaMA 7B on 70K evolved instructions yields WizardLM, beating Vicuna by a 12.4% win rate on human eval and topping ChatGPT on the high-difficulty (level ≥8) slice; evolved instructions judged superior to human-written ones.
- Relevance: the canonical complexity/diversity-augmentation engine complementing Self-Instruct; its depth/breadth evolution bears on producing rich, non-homogenized persona behavior data and diverse per-persona prompts at scale.

### [Persona Vectors: Monitoring and Controlling Character Traits in Language Models](https://arxiv.org/abs/2507.21509)
- Chen, Arditi, Sleight, Evans, Lindsey (incl. Anthropic) identify linear directions in activation space — persona vectors — corresponding to character traits (e.g. evil, sycophancy, hallucination), extracted automatically from natural-language trait descriptions.
- The vectors monitor persona drift during deployment and finetuning, and support causal control: steering along a vector induces a trait, while inference-time and preventative steering suppress unwanted shifts and flag training data that would induce them.
- Relevance: the canonical activation-steering method for persona conditioning/enforcement; alongside Claude's Character it bears on instilling and holding trait-faithful behavior at scale and on monitoring persona drift over long interactions.

### [Persona Generators: Generating Diverse Synthetic Personas for Arbitrary Contexts](https://arxiv.org/abs/2602.03545)
- Google DeepMind introduces Persona Generators that automatically expand a short scenario description into a population of synthetic personas. Rather than matching the most likely user profiles, the method explicitly targets support coverage—capturing the full range of plausible attitudes, preferences, and behaviors, including rare long-tail combinations.
- Method: the authors use an AlphaEvolve-style evolutionary optimization loop, where LLMs mutate and improve persona-generation code over hundreds of iterations. The evolved generators learn how to produce persona populations that maximize diversity along context-relevant axes and substantially outperform prompting-based baselines on six diversity metrics across unseen scenarios.
- Relevance: While Nemotron and census-grounded methods focus on distributional realism, Persona Generators focus on coverage realism—ensuring synthetic populations span rare viewpoints, edge cases, and underrepresented behavioral patterns. This is particularly relevant for simulation, stress-testing, and discovering failure modes where long-tail personas matter more than average users.

### [Generative Agent-Based Modeling with Actions Grounded in Physical, Social, or Digital Space using Concordia](https://arxiv.org/abs/2312.03664) (@Yixuan-He)
- DeepMind's open-source framework for building generative-agent societies with grounded actions in physical, social, and digital environments.
- Provides reusable abstractions for memory, planning, observations, social interactions, and environment dynamics.
- Relevance: a practical simulation substrate for deploying MatrAIx personas as agents and evaluating emergent population-level behavior beyond static role-playing.

### 🧩 Others
_Benchmarks, evaluation, related work that doesn't fit above._

### [PersonaGym: Evaluating Persona Agents and LLMs](https://arxiv.org/abs/2407.18416)
- First dynamic evaluation framework for persona agents, measuring how faithfully LLM agents adhere to an assigned persona across diverse, persona-relevant environments rather than a single fixed setting.
- Benchmark of 200 personas and 10,000 questions; introduces PersonaScore, a decision-theory-grounded automatic metric calibrating rubric-based LLM-judge ensembles against human ratings across 6 models.
- Closely parallels MatrAIxPersonaBench: PersonaScore's rubric-calibrated, human-aligned LLM-as-judge methodology and dynamic environment generation are the same persona-adherence scoring MatrAIxPersona targets at scale.

### [RoleLLM: Benchmarking, Eliciting, and Enhancing Role-Playing Abilities of LLMs](https://arxiv.org/abs/2310.00746)
- Builds RoleBench, the first systematic fine-grained character-level role-playing benchmark, plus a pipeline (RoleGPT, Context-Instruct, role-conditioned instruction tuning) to elicit and train role-playing ability.
- 100 roles and 168,093 samples; evaluates speaking-style imitation and role-specific knowledge, producing RoleLLaMA (EN) and RoleGLM (ZH) that approach GPT-4-level role fidelity.
- A large-scale, character-grained reference for persona-adherence metrics and persona data construction, covering the style- and knowledge-consistency axes MatrAIxPersona measures.

### [CharacterEval: A Chinese Benchmark for Role-Playing Conversational Agent Evaluation](https://arxiv.org/abs/2401.01275)
- Multi-turn benchmark for role-playing conversational agents emphasizing in-character consistency over extended dialogue, complemented by detailed character profiles.
- 1,785 multi-turn dialogues / 23,020 examples / 77 characters; 13 metrics across 4 dimensions, plus CharacterRM, a learned reward model whose human correlation surpasses GPT-4 as a judge.
- Its multi-turn, multi-dimensional rubric and trained reward model target persona consistency across long interactions rather than single-turn outputs — the same long-horizon adherence axis as MatrAIxPersonaBench.

### [RoleEval: A Bilingual Role Evaluation Benchmark for Large Language Models](https://arxiv.org/abs/2312.16132)
- Probes memorization, utilization, and multi-hop reasoning over role knowledge, isolating whether models actually "know" a character's facts versus merely imitating style.
- 6,000 parallel Chinese-English MCQs over 300 influential real and fictional figures (personal info, relationships, abilities, experiences), with hybrid auto+human quality control.
- Adds an objective, MCQ-based persona-knowledge axis complementing style-based scoring — the factual-persona-fidelity dimension relevant to MatrAIxPersonaBench at population scale.

### [Out of One, Many: Using Language Models to Simulate Human Samples](https://arxiv.org/abs/2209.06899)
- Foundational "silicon sampling" work: conditioning GPT-3 on real participants' socio-demographic backstories reproduces subgroup response distributions, introducing the notion of "algorithmic fidelity."
- Conditions on thousands of demographic backstories from US surveys and compares simulated vs real human response distributions across demographic subgroups.
- Core conceptual basis for MatrAIx's population simulation; its algorithmic-fidelity criterion is a natural top-level faithfulness metric for MatrAIxPersonaBench.

### [Whose Opinions Do Language Models Reflect?](https://arxiv.org/abs/2303.17548)
- Quantitative framework (OpinionQA) measuring how well LM-expressed opinions align with those of specific US demographic groups, surfacing systematic representational bias.
- Built from public-opinion polls covering 60 demographic groups; finds substantial misalignment that persists even after steering, and identifies poorly-represented groups (e.g. 65+, widowed).
- Provides the demographic-bias and opinion-faithfulness lens essential for auditing whether MatrAIx persona agents faithfully and fairly reflect the populations they simulate.

### [Measuring and Controlling Instruction (In)Stability in Language Model Dialogs](https://arxiv.org/abs/2402.10962)
- Defines and quantifies "persona/instruction drift": LLMs progressively deviate from an assigned persona over multi-turn dialogue, and proposes a method to control it.
- Shows significant drift within ~8 conversation rounds (e.g. LLaMA2-chat-70B), attributes it partly to attention decay, and introduces a split-softmax stabilization.
- Defines a key failure mode relevant to MatrAIxPersonaBench — long-horizon persona-adherence stability — and supplies a drift metric and mitigation baseline.

### [The Price of Format: Diversity Collapse in LLMs](https://arxiv.org/abs/2505.18949)
- Shows that structured chat formatting (role markers, special tokens) causes "diversity collapse": models emit semantically near-identical outputs for open-ended prompts.
- Demonstrates the collapse persists even at high sampling temperature and is governed mainly by structural tokens, with minimal formatting yielding the most diverse responses.
- Highly relevant to large-scale persona simulation: explains how billions of distinct personas could homogenize, motivating diversity/distinctiveness metrics in MatrAIxPersonaBench.

### [From Persona to Personalization: A Survey on Role-Playing Language Agents](https://arxiv.org/abs/2404.18231)
- The canonical TMLR 2024 survey of Role-Playing Language Agents (Chen, Wang, Xu et al., Fudan), organizing the field around three persona types: demographic, character, and individualized.
- Systematizes data sourcing, agent construction, and evaluation methodologies, and catalogs risks, limitations, and applications (companions, digital clones, social simulation).
- A field-level taxonomy and evaluation-methodology map covering the demographic-vs-character axes that frame persona-adherence benchmarking in MatrAIxPersonaBench.

### [LLMs that Replace Human Participants Can Harmfully Misportray and Flatten Identity Groups](https://arxiv.org/abs/2402.01908)
- The key critique counterbalancing "silicon sampling": LLMs conditioned on demographic identities systematically misportray and flatten group diversity (a fairness-harm framing of diversity collapse).
- Empirically grounded: 4 LLMs, human studies with 3,200 participants across 16 demographic identities, plus inference-time mitigation tests (Wang, Morgenstern, Dickerson et al.; Nature Machine Intelligence 2024).
- Bears on a fairness/distinctiveness axis in MatrAIxPersonaBench — whether large-scale persona agents preserve within-group variation rather than collapsing identities into stereotypes.

### [TinyTroupe: An LLM-powered Multiagent Persona Simulation Toolkit](https://microsoft.github.io/TinyTroupe/) (Eliza_Fan)
- TinyTroupe is an LLM-powered toolkit designed to simulate realistic human persona interactions within modular, event-driven environments. By orchestrating virtual agents with distinct personalities and memories, it automates the generation of high-quality, complex synthetic data for social and market research while providing mechanisms to correct simulation biases and align agent behavior. However, it believes problem-sovling AI systems generated agents lack wider human variabilities and real world context.
- Synthetic generation of human agents with personalities, memories, actions and mental faculties. Agents can interact with each other. Scale up by distribution(population number, gender, leftwing/rightwing). The similated results are similar to real results. Use validators and propositions. Have stimulation steering and chaching mechanism, information encricher/extractor and result reducer. Benchmark: persona adherence, self-consistency, fluency, divergence, ideas qty.
- Relevance: Generation of human agents. The goal of the projects.

### [AI Town](https://github.com/a16z-infra/ai-town?utm_source=chatgpt.com) (Eliza_Fan)
- An open-source implementation of a persistent multi-agent virtual town where LLM-powered characters interact, build memories, form relationships, and generate emergent social behaviors over time.
- Combines persona profiles, long-term memory, world state management, and agent planning/action loops to support continuous simulation rather than single-turn interactions.
- Relevant to MatrAIx as a reference architecture for generating long-horizon user trajectories, modeling social influence, and studying how personas evolve through repeated interactions in shared environments.

### [τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045) (@Yixuan-He)
- Benchmark for evaluating tool-using and interactive LLM agents in realistic user-facing tasks.
- Emphasizes long-horizon interactions and human-like user behavior.
- Relevance: provides evaluation settings for testing whether MatrAIx personas behave realistically when interacting with agents rather than only answering survey questions.

### [SimBench: Benchmarking the Ability for Large Language Models to Simulate Human Behaviors](https://openreview.net/pdf?id=PL51SpN6ZJ)
- Introduces the first large-scale benchmark for evaluating whether LLMs can faithfully simulate group-level human behavior, unifying 20 datasets spanning moral decisions, economic choices, surveys, and social science tasks.
- Finds that current models achieve only modest simulation fidelity (best score ≈40.8/100), with performance improving as model size increases but showing little benefit from additional inference-time reasoning.
- Relevance: provides a standardized evaluation framework for MatrAIx-style personas, measuring whether generated personas can reproduce realistic population and demographic-group behaviors rather than only producing plausible persona descriptions.

### [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/pdf/2304.03442) (Xiaoyi-Liu added, Yuexing-Hao posted in Discord discussion)
### [Human Relations Area Files(eHRAF ​​World Culture)](https://hraf.yale.edu/resources/reference/outline-of-cultural-materials/) (Xiaoyi-Liu added, Ziyan-Wang posted in Discord)
### [OdysSim: Building Foundation Models for Human Behavior Simulation] (Xiaoyi-Liu added, Lorenzo-Xiao posted in Discord)
### [OASIS: Open Agent Social Interaction Simulations with One Million Agents](https://arxiv.org/pdf/2411.11581) (Xiaoyi-Liu added, Yuexing-Hao posted on Discord)
### [Large Language Models Assume People are More Rational than We Really are](https://arxiv.org/abs/2406.17055) (Xiaoyi-Liu added, Yucheng-Lu posted on Discord)
### [LLMs Position Themselves as More Rational Than Humans: Emergence of AI Self-Awareness Measured Through Game Theory](https://arxiv.org/abs/2511.00926v1) (Xiaoyi-Liu added, Yucheng-Lu posted on Discord)
### [SimCity: Multi-Agent Urban Development Simulation with Rich Interactions](https://arxiv.org/abs/2510.01297) (Xiaoyi-Liu added, Yucheng-Lu posted on Discord)
### [Using LLMs for Market Research](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4395751) (Xiaoyi-Liu added, Shirley-Huang posted blog on Discord)
### [LLM Economist: Large Population Models and Mechanism Design in Multi-Agent Generative Simulacra](https://arxiv.org/abs/2507.15815) (Xiaoyi-Liu added, Seth-Karen posted on Discord)
### [Beyond Cooperative Simulators: Generating Realistic User Personas for Robust Evaluation of LLM Agents](https://arxiv.org/abs/2605.12894) (Xiaoyi-Liu added, Ishan-Gupta (twitter link) and Brihi-Joshi posted on Discord)
### [CoSER: A Comprehensive Literary Dataset and Framework for Training and Evaluating LLM Role-Playing and Persona Simulation](https://arxiv.org/abs/2502.09082) (Xiaoyi-Liu added, Lorenzo-Xiao posted on Discord)
### [HER: Human-like Reasoning and Reinforcement Learning for LLM Role-playing](https://arxiv.org/abs/2601.21459) (Xiaoyi-Liu)
- reasoning-augmented version of CoSER, according to [CoSER github](https://github.com/Neph0s/CoSER）
### [The Need for a Socially-Grounded Persona Framework for User Simulation](https://arxiv.org/abs/2601.07110) (Xiaoyi-Liu added, Haiwen-Huang posted on Discord)


---

## 🧱 Task 1 — Schema & Domain Design
**Owner(s):** @Yunze Xiao @Eliza_Fan, @Xiaoyi-Liu, @brihijoshi , @Ziyan Wang(add more as needed)

The schema blocks everything else, so settle it first. **Don't over-explore** — define attributes from understanding of the target domains/tasks (limited-scope exploration).

- Organize personas around **4–5 major domains**, one of which is **basic demographics**, the rest tied to what we actually care about (see [README](README.md#-persona-structure)).
- Each domain gets a small **sub-team (1–3 people)** that designs its attributes/dimensions and builds that slice.
- Personas are then assembled by **linearly combining** the per-domain slices into one profile.
- Reuse prior attribute sets where possible (e.g. the ~25 attributes from the persona-collapse work) instead of reinventing.




[Lornezo] Generates the demographics domain slice for MatrAIxPersona: personas whose joint attribute distribution matches a real reference population. This is the shared "general" base layer that domain slices (finance / health / coding) condition on. Prototype-first; proof-of-concept before refinement.

## 1. Where the joint comes from (the only real design decision)
 
| | Approach | Joint realism | Cost / risk | Verdict |
|---|---|---|---|---|
| **A** | **Weighted resampling from census microdata** — draw real, de-identified person-records | Correct *by construction* (each record is a real person) | Zero modeling error; can't produce combinations absent from the sample | **v0** |
| **B** | **Modeled joint** — PGM / Bayes net / copula, then ancestral sampling | As good as the model | Modeling error + build time; but enables novel/conditional combos | **v1** |
 
NVIDIA's **Nemotron-Personas** uses (B) (PGM → LLM). For a prototype, (A) is faster and arguably *more* defensible — you sample an empirical joint instead of trusting a fitted one.
   
## 2. Data sources
 
- **US prototype:** **ACS PUMS** (American Community Survey, Public Use Microdata Sample). 1-year (recency) or 5-year (more records / smaller geos). Person weight = `PWGTP`.
  - Easiest access: the **`folktables`** Python package (research-standard ACS wrapper; handles download + weights), or the Census PUMS CSV / API directly.
- **Global (v1 — the eventual "population-grounded" story):**
  - **IPUMS-International** — harmonized census microdata across many countries.
  - https://international.ipums.org/international-action/sample_details/country/ar#tab_ar2001a
  - **DHS** (Demographic and Health Surveys) for low-/middle-income countries.
  - **Eurostat** microdata for the EU.
> Pin the exact reference population (country × year) per release so distributions are auditable and reproducible.

### Step 1 — Skeleton via weighted resampling
Pull ACS PUMS person records; resample with replacement **∝ `PWGTP`** to get `N` jointly-consistent demographic skeletons.
 
Working attribute set (the "general" layer; domain attrs append later):
 
| Field | PUMS var | Notes |
|---|---|---|
| age | `AGEP` | bin in Step 2 |
| sex | `SEX` | — |
| race / Hispanic origin | `RAC1P`, `HISP` | sensitive — see §5 |
| education | `SCHL` | collapse to levels |
| occupation | `OCCP` | → SOC **major group**, not 500 codes |
| industry | `INDP` | major group |
| employment status | `ESR` | — |
| income | `PINCP` / `WAGP` | → brackets |
| marital status | `MAR` | — |
| household structure | `RELSHIPP` (`RELP` pre-2019) | has-kids / lives-alone derived |
| geography | `ST` + `PUMA` | → region + urbanicity |
| language | `LANP`, `ENG` | primary language at home |
| nativity / citizenship | `NATIVITY`, `CIT` | — |
| hours worked | `WKHP` | optional |
 
### Step 2 — Coarsen by behavioral relevance *(the differentiator)*
Carry **no attribute at finer granularity than moves behavior.**
- age → child / teen / young-adult / adult / middle-aged / senior
- income → brackets
- occupation → SOC major groups
- geography → region + urbanicity (not PUMA)
Bin boundaries are decided by the **behavioral-sensitivity probe (§4)**, not intuition alone. This is "35 vs 36-year-old programmer doesn't matter" made operational.
 
### Step 3 — Narrative expansion (LLM)
Condition an LLM on the **structured skeleton** to write the rich persona text (Nemotron's PGM→LLM step, but skeleton from real data).
- **Hard rule:** the LLM *narrativizes*; it **never invents or overrides** demographic facts.
- The LLM step is where flatten-identity / stereotyping harm re-enters → use **diversity-forcing decoding** + a **stereotype audit** on outputs.
### Step 4 — Schema conformance + provenance
Emit each persona in the Task-1 demographic-slice schema (structured fields + narrative) with a **provenance tag** (`source = ACS PUMS <year>`, weight, hashed record id) so it is mergeable, auditable, and `fidelity-tier`-labelable against other sources.
  
## 4. Validation — *this is what makes it a contribution, not "anyone can resample PUMS"*
 
1. **Marginal fidelity** — each attribute vs ACS reference (TV distance / chi-square / KS).
2. **Joint fidelity** — pairwise + selected higher-order joints vs reference (e.g., age × education × income tables). **This is the check the naive pipeline fails.**
3. **Persona collapse / diversity** — reuse the geometric **Coverage / Complexity / Uniformity** codebase from the persona-collapse work + embedding dedup. `effective_count` should track `nominal_count`, not collapse below it.
4. **Behavioral sensitivity (cheap)** — vary **one** demographic axis, hold others fixed, generate persona-conditioned responses on a **tiny** task set, measure shift with cheap proxies (**HumT** + surface stats — length / markdown% / em-dash% / assistant-phrase% — à la ODYSSIM, plus task-specific checks).
   - Output: a **ranked list of which demographic axes actually move behavior** → feeds back into Step 2's coarsening and the schema-keep decision.

---

## 🏗️ Task 2 — MatrAIxPersona-8B Data Construction

Build the raw persona pool through four complementary sources, all conforming to the Task 1 schema so they're mergeable. Many external contributors will also submit personas (accepted past a quality threshold).

| # | Subtask | Description | Owner(s) |
|---|---------|-------------|----------|
| 2.1 | 📥 **Collect open-source datasets** | Gather existing persona datasets (from the related work), clean and normalize into the MatrAIx schema. | @Xiaoyi-Liu, @AravindMohan10, @Eliza_Fan |
| 2.2 | 🧪 **Heuristic + synthetic generation** | Per-domain attribute combination + generation with multiple strong models (GPT, Claude, DeepSeek). Seed with real-world demographic priors for realism. | @ElegantLin, @AravindMohan10, @brihijoshi @isgla @Eliza_Fan|
| 2.3 | 🧑 **Personas from real human info** | Build personas seeded by public/real signals (public figures, social profiles, chat/conversation data), properly anonymized. | @Laerdon Kim, @brihijoshi, @rosierogao, @name3_ |
| 2.4 | 📝 **Questionnaire → volunteers** | Design a questionnaire, collect volunteer data, and expand each response into a full persona via synthetic augmentation. | _@name1, @name2, @name3_ |
| 2.5 | 🔁 **Continuous-growth intake** | Let contributors keep adding personas over time (upload conversations, fill/extend a profile) so the pool grows; gate on the Task 3 quality bar. | _@name1, @name2, @name3_ |

> 🔑 Output: a unified, schema-conformant persona pool feeding into Task 3.

---

## 🧹 Task 3 — Data Quality Filtering & Evaluation
**Owner(s):** @Eliza_Fan, @Yun Shen, @rosierogao, @ziweil2 (add more as needed)
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

---

## 📊 Task 4 — MatrAIxPersonaBench
**Owner(s):** @Eliza_Fan, @Keyang Xuan, @Wenkai Li, @isgla (add more as needed)
Build the coreset for benchmarking **persona simulation quality**. For each persona, derive concrete tasks + evaluation tied to specific profile attributes.

- For each persona → generate task(s) targeting one or more attributes.
- Define **eval per task**: rule-based checks + LLM-judge.
- Cover multiple aspects (demographics, personality, preferences, behavior, communication).

> 🧩 Example: profile says *"dislikes comments in code"* → task: ask the agent (as this persona) to write a function → eval: check whether the output contains comments.

---

## 🎓 Task 5 — MatrAIxPersonaTrain

A train-oriented coreset. **Goal: train a persona-conditioned model** that, given a persona profile, role-plays / responds *as* that person.

- Build `(persona, query) → persona-consistent response` pairs (synthetic, generated by strong models).
- Use for instruction tuning / fine-tuning so a model can faithfully follow any given persona.
- Keep it lightweight — this is a supporting artifact, not the paper's focus.

**Owner(s):** @Eliza_Fan, @Wenkai Li, @name3_ (add more as needed)

---

## ✅ Task 6 — Human Validation
**Owner(s):** _@name1, @name2, @name3_ (add more as needed)
A small human study to validate data quality and benchmark ground-truth.

- Sample a subset (a few hundred personas / bench tasks).
- Annotators rate each on a simple 1–5 rubric: **realism**, **internal consistency**, and (for bench) **correctness of the expected behavior / eval**.
- Report inter-annotator agreement; use results to calibrate the LLM-judge.

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
2. Open an issue for your task to track details and progress.
3. Align early on the shared persona **schema** (Task 1) — it blocks Tasks 2–5.
4. Keep your own `Status Update - <Your Name>` issue and add the `status-update` + `team: persona` labels so it's easy to find.

