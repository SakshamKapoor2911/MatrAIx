# Objective-Axis Coding Review

Scope: top-100 records in `papers_merged_top100.*`, coded only for the persona-set objective axis. Labels are multi-label, so counts can exceed 100.

## Counts by objective category

| Objective category | Count |
|---|---:|
| Population Representation | 24 |
| Coverage and Stress Testing | 10 |
| Individual Fidelity | 15 |
| Behavioral Calibration | 44 |
| Design Communication | 8 |
| Bias and Harm Auditing | 23 |
| Agent / Model Evaluation | 56 |
| Unclear - needs full-text check | 0 |
| Not applicable | 1 |

## High-confidence exemplars

- **Coverage and Stress Testing:** [Persona Generators: Generating Diverse Synthetic Personas for Arbitrary Contexts](https://arxiv.org/abs/2602.03545) optimizes persona generators for support coverage and rare trait combinations.
- **Individual Fidelity, Behavioral Calibration, Bias and Harm Auditing:** [The Need for a Socially-Grounded Persona Framework for User Simulation](https://arxiv.org/abs/2601.07110) grounds personas in participant sociopsychological protocols, predicts human responses, and evaluates over-accentuation/bias.
- **Population Representation and Behavioral Calibration:** [German General Social Survey Personas: A Survey-Derived Persona Prompt Collection for Population-Aligned LLM Studies](https://arxiv.org/abs/2511.21722) builds representative ALLBUS-derived persona prompts and evaluates survey-response distributions.
- **Population Representation, Individual Fidelity, Behavioral Calibration, Bias and Harm Auditing:** [Synthia: Scalable Grounded Persona Generation from Social Media Data](https://arxiv.org/abs/2507.14922) grounds personas in social-media users, evaluates opinion distribution alignment, network structure, and fairness/bias.
- **Design Communication and Individual Fidelity:** [PersonaCite: VoC-Grounded Interviewable Agentic Synthetic AI Personas for Verifiable User and Design Research](https://arxiv.org/abs/2601.22288) creates VoC-grounded interviewable personas for verifiable user and design research.
- **Bias and Harm Auditing:** [A Tale of Two Identities: An Ethical Audit of Human and AI-Crafted Personas](https://arxiv.org/abs/2505.07850) audits LLM-generated personas for racial representational harms, stereotyping, erasure, and algorithmic othering.
- **Agent / Model Evaluation:** [Measure what Matters: Psychometric Evaluation of AI with Situational Judgment Tests](https://arxiv.org/abs/2510.22170) uses persona conditioning and situational judgment tests to evaluate stable LLM behavioral tendencies.
- **Coverage, Behavioral Calibration, Agent / Model Evaluation:** [Beyond Cooperative Simulators: Generating Realistic User Personas for Robust Evaluation of LLM Agents](https://arxiv.org/abs/2605.12894) generates non-cooperative user personas for robust LLM-agent evaluation.
- **Bias and Harm Auditing plus Agent / Model Evaluation:** [Bullying the Machine: How Personas Increase LLM Vulnerability](https://arxiv.org/abs/2505.12692) stress-tests persona-conditioned LLMs for safety vulnerability under bullying tactics.

## Important ambiguous boundary cases

- [Sycamore: Characterizing Synthetic Personas for Evaluating Genomics Visualization Retrieval](https://arxiv.org/abs/2605.08630): coded as Behavioral Calibration and Agent / Model Evaluation because personas evaluate genomics visualization retrieval, but this stretches the model-evaluation label beyond LLM role-following. Keep `needs_followup=yes`.
- [Verifiable User Simulation for Search and Recommendation Systems](https://arxiv.org/abs/2606.14474): coded as Behavioral Calibration and Bias and Harm Auditing because it proposes an auditable user-simulation framework; it is a tutorial/framework paper rather than an evaluated persona set. Keep `needs_followup=yes`.
- [Synonymix: Unified Group Personas for Generative Simulations](https://arxiv.org/abs/2603.28066): coded as Population Representation and Behavioral Calibration because group personas mediate between individual personas and population models. Full text should confirm whether the life-story personas are empirical or model-invented.
- [Whose Personae? Synthetic Persona Experiments in LLM Research and Pathways to Transparency](https://arxiv.org/abs/2512.00461): coded by the objectives it reviews, not as a new persona-generation method. It belongs in Population Representation and Agent / Model Evaluation because it assesses representativeness and ecological validity of persona-based LLM alignment experiments.
- [From Individual to Society: A Survey on Social Simulation Driven by Large Language Model-based Agents](https://arxiv.org/abs/2412.03563): survey paper coded across Population Representation, Individual Fidelity, and Behavioral Calibration because its abstract explicitly organizes individual, group, and society simulation objectives.
- [MultiActor-Audiobook: Zero-Shot Audiobook Generation with Faces and Voices of Multiple Speakers](https://arxiv.org/abs/2505.13082): coded as Individual Fidelity and Agent / Model Evaluation for speaker-persona/prosody consistency, but it is outside the core social/persona-simulation literature. Keep `needs_followup=yes`.
- [Dynamic In-Group Persona Generation for Enhancing Human-AI Rapport](https://arxiv.org/abs/2606.18256): rapport enhancement is not one of the seven objective labels; current best fit is Agent / Model Evaluation because personas condition chatbot behavior. Keep `needs_followup=yes`.
- [Creativity Has Left the Chat: The Price of Debiasing Language Models](https://arxiv.org/abs/2406.05587): the only `Not applicable` record. Local metadata discusses RLHF creativity and mentions customer persona generation only as an application implication, not as a persona-set objective.

## Coverage assessment

The seven objective categories cover the corpus well. After applying the objective-axis rule that persona-use papers can be Agent / Model Evaluation, only one record remains Not applicable and no record remains Unclear. The most common pressure points are: (1) user-simulation papers that evaluate recommender, retrieval, or workflow systems rather than LLM persona-following directly; (2) survey or position papers that describe objectives rather than contributing a persona set; and (3) character, speaker, or NPC persona papers where Individual Fidelity refers to authored character continuity rather than real-person trace fidelity. These cases are covered, but several should remain flagged for full-text follow-up in the CSV.

## Follow-up notes

- Rows with `needs_followup=yes` should be checked against full text before using them as anchor examples in the survey.
- Multi-label counts intentionally exceed 100 because many papers combine representation, behavioral simulation, harm auditing, and model evaluation objectives.
