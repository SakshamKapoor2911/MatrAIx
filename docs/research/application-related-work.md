# Application Related Work

This note migrates the MatrAIx Application team related-work notes from
`MatrAIx-ai/MatrAIx@e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`,
`docs/applications/PLAN.md`. It preserves the research map without importing
the old task-assignment plan.

The source note listed @Shirley-Huang, @Qianfeng-Wen, and @Yifan-Liu as
related-work owners. Individual entries that named a contributor in the source
are marked below.

The notes are grouped by how each work informs the application layer:
simulated-user evaluation, domain-specific benchmarks, and reporting or
simulation methodology.

## User Simulation And Evaluation

### [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)

- Introduces LLM-backed agents with observation, memory, reflection, and
  planning in a small social sandbox.
- Application takeaway: gives MatrAIx the canonical loop for turning sampled
  personas into agents whose behavior can create useful telemetry.

### [Out of One, Many: Using Language Models to Simulate Human Samples](https://arxiv.org/abs/2209.06899)

- Shows that persona-conditioned language models can reproduce some
  demographically correlated survey response distributions.
- Application takeaway: supports simulated cohorts as pilot and hypothesis
  tools, while requiring fidelity checks before trusting conclusions.

### [Can Large Language Models Replace Human Subjects? A Large-Scale Replication of Scenario-Based Experiments](https://arxiv.org/abs/2409.00128)

- Replicates many psychology and management studies with frontier models and
  identifies where synthetic subjects diverge.
- Application takeaway: motivates calibration in feedback reports, especially
  around inflated effect sizes and socially sensitive topics.

### [UXAgent: An LLM Agent-Based Usability Testing Framework for Web Design](https://arxiv.org/abs/2502.12561)

- Generates persona-driven agents that interact with real websites and produce
  interviews, action counts, and video logs.
- Application takeaway: a close template for product or UX tasks in which
  personas exercise an environment and produce reportable evidence.

### [Free Lunch for User Experience: Crowdsourcing Agents for Scalable User Studies](https://arxiv.org/abs/2505.22981)

- Uses large pools of LLM agents to run scalable user studies and surface
  edge cases before a human study.
- Application takeaway: frames simulated users as complementary coverage for
  recruited users, not a replacement for all human evaluation.

### [Evaluating LLMs as Generative User Simulators for Conversational Recommendation](https://arxiv.org/abs/2403.09738)

- Defines protocols for testing whether LLMs emulate human users across
  recommendation tasks.
- Application takeaway: provides concrete failure modes such as popularity
  bias, weak preference alignment, and under-personalized requests.

### [LLMs Reproduce Human Purchase Intent via Semantic Similarity Elicitation of Likert Ratings](https://arxiv.org/abs/2510.08338)

- Maps free-text model responses into Likert-style distributions using
  semantic similarity rather than directly asking for numeric ratings.
- Application takeaway: a useful technique for turning persona reactions into
  survey-grade metrics for market or product research.

### [Can Large Language Models Be an Alternative to Human Evaluations?](https://arxiv.org/abs/2305.01937)

- Gives models the same evaluation instructions, samples, and questions used
  in human studies.
- Application takeaway: supports using stable LLM judges as one part of the
  report stage, with bias controls and human calibration where needed.

### [Social Simulacra: Creating Populated Prototypes for Social Computing Systems](https://arxiv.org/abs/2208.04024)

- Populates prototype social systems with synthetic users so designers can
  observe likely behavior before launch.
- Application takeaway: directly matches the design -> simulated population ->
  observe -> revise loop expected from MatrAIx applications.

### [AgentA/B: Automated and Scalable Web A/B Testing with Interactive LLM Agents](https://arxiv.org/abs/2504.09723)

- Runs autonomous persona agents through competing web interfaces to compare
  behavioral outcomes.
- Application takeaway: a strong reference for A/B testing tasks where
  subgroup behavior and interaction traces matter.

### [SimUSER: Simulating User Behavior with Large Language Models for Recommender System Evaluation](https://arxiv.org/abs/2504.12722)

- Builds simulated recommender-system users with persona, memory, perception,
  and reasoning modules mined from interaction logs.
- Application takeaway: a close analog for application loops that generate
  behavioral telemetry and use it to improve a product surface.

### [On Generative Agents in Recommendation](https://arxiv.org/abs/2310.10108)

- Agent4Rec models user profiles, memory, satisfaction, and exit decisions
  while agents browse recommendations.
- Application takeaway: provides a profile/memory/action decomposition for
  recommender-oriented MatrAIx application tasks.

### [User Behavior Simulation with Large Language Model based Agents](https://arxiv.org/abs/2306.02552)

- RecAgent simulates users in a virtual world where agents browse, rate,
  chat, and post socially.
- Application takeaway: supports a sandbox pattern for generating interaction
  logs that can become feedback reports.

### [AgentCF: Collaborative Learning with Autonomous Language Agents for Recommender Systems](https://arxiv.org/abs/2310.09233)

- Models users and items as agents that reflect on discrepancies between
  simulated decisions and real interactions.
- Application takeaway: suggests correction loops for aligning simulated
  persona behavior with real-world telemetry.

### [MEMARD: A Conversational Recommendation Dataset via Memory-Enhanced Multi-Agent Dialogue Synthesis](https://openreview.net/forum?id=3Df83swog6) (source note: Eliza Fan)

- Extracts persona traits from Amazon review data and synthesizes
  conversational recommendation dialogues with memory-enhanced agents.
- Application takeaway: a practical benchmark design for recommender tasks
  that require user control, specificity, relevance, and consistency checks.

## Domain Benchmarks

### [WebArena: A Realistic Web Environment for Building Autonomous Agents](https://arxiv.org/abs/2307.13854)

- Provides self-hosted web apps and long-horizon tasks scored by resulting
  environment state.
- Application takeaway: maps to web application scenarios such as checkout,
  forums, and content-management workflows.

### [WebShop: Towards Scalable Real-World Web Interaction with Grounded Language Agents](https://arxiv.org/abs/2207.01206)

- Simulates e-commerce search, navigation, customization, and purchase tasks
  over real product data.
- Application takeaway: a benchmark pattern for shopper personas and
  auto-rewarded product-selection tasks.

### [Mind2Web: Towards a Generalist Agent for the Web](https://arxiv.org/abs/2306.06070)

- Collects open-ended web tasks and action sequences across many real
  websites and domains.
- Application takeaway: informs cross-domain web generalization for MatrAIx
  scenarios that should not overfit one surface.

### [tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045)

- Emulates customer-service conversations between a simulated user and a
  tool-using agent with domain APIs and policy constraints.
- Application takeaway: maps to support, airline, retail, and policy-following
  chatbot scenarios.

### [AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents](https://arxiv.org/abs/2407.18901)

- Provides an execution engine of everyday apps, APIs, fictitious users, and
  multi-app tasks.
- Application takeaway: a reference for sandboxed app workflows where agents
  act on behalf of simulated people.

### [AgentBench: Evaluating LLMs as Agents](https://arxiv.org/abs/2308.03688)

- Evaluates agents across multiple interactive environments including OS,
  database, web shopping, web browsing, and household tasks.
- Application takeaway: a precedent for unified multi-environment evaluation
  and long-horizon task reporting.

### [MT-Bench-101: A Fine-Grained Benchmark for Evaluating LLMs in Multi-Turn Dialogues](https://arxiv.org/abs/2402.14762)

- Measures fine-grained abilities across multi-turn dialogue tasks.
- Application takeaway: useful for chatbot scenarios that need turn-level
  scoring rather than only final-answer evaluation.

### [GAIA: a Benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)

- Tests general assistants on tasks requiring reasoning, multimodality, web
  browsing, and tool use.
- Application takeaway: a stress-test reference for everyday task competence
  in app and web environments.

### [MathDial: A Dialogue Tutoring Dataset Grounded in Math Reasoning Problems](https://arxiv.org/abs/2305.14536)

- Collects teacher-student tutoring dialogues grounded in math errors and
  pedagogical moves.
- Application takeaway: directly relevant to AI tutor scenarios with
  simulated student personas.

### [Rethinking Evaluation for Conversational Recommendation in the Era of LLMs (iEvaLM)](https://arxiv.org/abs/2305.13112)

- Uses LLM-based user simulators to evaluate conversational recommenders
  interactively.
- Application takeaway: a close analog to persona-driven users evaluating a
  target system through dialogue.

### [ToolLLM: Facilitating LLMs to Master 16000+ Real-world APIs (ToolBench)](https://arxiv.org/abs/2307.16789)

- Builds a large tool-use benchmark with real APIs, solution paths, and an
  automatic evaluator.
- Application takeaway: informs enterprise and app-sandbox tasks where agents
  must choose and coordinate tools.

### [Large Language Models as Zero-Shot Conversational Recommenders](https://arxiv.org/abs/2308.10053)

- Studies off-the-shelf LLMs as conversational recommenders and releases a
  large conversational-recommendation dataset.
- Application takeaway: grounds recommender-agent applications and gives
  baseline tasks for persona-driven evaluation.

## Other Simulation And Reporting Methods

### [AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents](https://arxiv.org/abs/2502.08691)

- Builds large social simulations with memory, planning, and social
  relationship modules.
- Application takeaway: relevant for population-scale application feedback and
  emergent behavior analysis.

### [OASIS: Open Agent Social Interaction Simulations with One Million Agents](https://arxiv.org/abs/2411.11581)

- Simulates social-media platforms with dynamic networks, recommendation, and
  actions such as follow, post, comment, and like.
- Application takeaway: a population-scale reference for engagement dynamics
  and social effects.

### [Project Sid: Many-agent simulations toward AI civilization](https://arxiv.org/abs/2411.00114)

- Uses a many-agent architecture in a Minecraft environment to study role
  specialization, norms, and cultural transmission.
- Application takeaway: useful for thinking about emergent collective
  behavior in long-running simulations.

### [Curiosity-driven Red-teaming for Large Language Models](https://arxiv.org/abs/2402.19464)

- Frames automated red-teaming as curiosity-driven exploration to discover
  diverse risky prompts.
- Application takeaway: maps to adversarial-user application scenarios and
  high-coverage safety testing.

### [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)

- Establishes LLM-as-a-judge methodology and characterizes common judge
  biases.
- Application takeaway: informs report generation and evaluation templates
  over simulated traces.

### [Self-Instruct: Aligning Language Models with Self-Generated Instructions](https://arxiv.org/abs/2212.10560)

- Generates and filters synthetic instruction data from model outputs.
- Application takeaway: a reusable method for creating diverse tasks,
  prompts, and calibration data.

### [EconAgent: LLM-Empowered Agents for Simulating Macroeconomic Activities](https://arxiv.org/abs/2310.10436)

- Integrates LLM agents into macroeconomic simulations of labor, consumption,
  fiscal policy, and monetary policy.
- Application takeaway: expands the application design space toward economic
  and market simulations.

### [Red Teaming Language Models with Language Models](https://arxiv.org/abs/2202.03286)

- Uses one language model to generate adversarial test cases against another.
- Application takeaway: the canonical generate-case -> classify-harm pattern
  for adversarial simulated users.

### [A Survey on Large Language Models for Recommendation](https://arxiv.org/abs/2305.19860)

- Surveys discriminative and generative uses of LLMs for recommendation.
- Application takeaway: gives taxonomy and grounding for recommender-focused
  MatrAIx applications.
