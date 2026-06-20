# Objective-Axis Taxonomy

Status: working definition for the second taxonomy axis only. This file defines what a persona set is meant to accomplish. It complements `taxonomy_construction_technique.md`, which defines where persona information comes from.

## Short Version

Classify synthetic persona methods by the validity or use claim the persona set is meant to support:

1. **Population Representation**: represent a target population.
2. **Coverage and Stress Testing**: span important, rare, risky, or adversarial cases.
3. **Individual Fidelity**: preserve specific people, traces, memories, styles, or histories.
4. **Behavioral Calibration**: reproduce observed actions, responses, or interaction patterns.
5. **Design Communication**: help humans reason, design, deliberate, or align stakeholders.
6. **Bias and Harm Auditing**: expose stereotypes, erasure, unfairness, or representational harms.
7. **Agent / Model Evaluation**: test whether models follow, preserve, or are affected by personas.

Memorable contrast:

> The construction axis asks where personas come from; the objective axis asks what the persona set is valid for.

## Detailed Definition

The objective axis classifies the **inferential or practical purpose** of a persona set. It records the claim a method makes about why the generated personas are useful. A method can have multiple objectives, and objective labels should not be treated as mutually exclusive.

This axis is necessary because the same construction technique can support different claims. A population-sampled persona set may aim at population representation, behavioral calibration, or bias auditing. A model-generated persona set may aim at brainstorming, coverage, stress testing, or model evaluation. A trace-grounded persona may aim at individual fidelity, behavioral calibration, or design communication.

The objective axis should be kept separate from the construction axis:

- Construction source: where the persona information comes from.
- Objective: what the persona set is meant to do.

## The Seven Objective Families

| Objective | Core question | Includes | Typical evidence |
|---|---|---|---|
| **Population Representation** | Does the persona set represent a target population? | density matching, marginal validity, joint validity, weighting, quota/stratified balance, subgroup representation | comparisons to census, surveys, panels, official statistics, known marginals and joint distributions |
| **Coverage and Stress Testing** | Does the set span important, rare, difficult, or risky cases? | support coverage, long-tail cases, edge cases, adversarial users, robustness tests, scenario coverage | diversity/coverage metrics, held-out scenario coverage, discovered failures, red-team outcomes |
| **Individual Fidelity** | Does the persona preserve a specific person, user, trace, or history? | memory continuity, style fidelity, preference consistency, longitudinal consistency, digital-twin fidelity | comparisons to individual logs, interviews, histories, repeated responses, human judgments of personal fidelity |
| **Behavioral Calibration** | Do persona-conditioned agents reproduce observed behavior? | survey response fidelity, action prediction, interaction realism, aggregate response matching, task-specific user simulation | accuracy against human responses/actions, distributional response matching, benchmark performance, behavioral correlations |
| **Design Communication** | Do personas help humans reason, design, or coordinate? | HCI personas, requirements elicitation, stakeholder alignment, product/UX ideation, scenario design | expert approval, stakeholder usefulness, design relevance, interpretability, qualitative validation |
| **Bias and Harm Auditing** | Does the method reveal or reduce representational harms? | stereotype audits, fairness checks, intersectional bias, erasure, over-accentuation, harmful group portrayals | bias metrics, subgroup analysis, fairness audits, harm taxonomies, affected-group or expert review |
| **Agent / Model Evaluation** | Does persona conditioning test model behavior or capabilities? | persona following, role-play fidelity, persona steering, capability shifts, safety/alignment effects, jailbreak/vulnerability testing | role-play benchmarks, consistency tests, safety/capability evaluations, model-behavior comparisons |

## Objective Boundaries

### Population Representation vs Behavioral Calibration

Population Representation concerns whether the persona set has the right population structure. Behavioral Calibration concerns whether the model's responses or actions match observed behavior after conditioning.

Example: [German General Social Survey Personas](https://arxiv.org/abs/2511.21722) can be coded for Population Representation because it is survey-derived, and Behavioral Calibration when it evaluates simulated response distributions.

### Population Representation vs Coverage and Stress Testing

Population Representation tries to preserve prevalence. Coverage and Stress Testing may deliberately overrepresent rare, risky, or underexplored cases.

Example: [Persona Generators: Generating Diverse Synthetic Personas for Arbitrary Contexts](https://arxiv.org/abs/2602.03545) should be coded for Coverage and Stress Testing because it explicitly contrasts support coverage with density matching.

### Individual Fidelity vs Behavioral Calibration

Individual Fidelity asks whether a persona preserves a specific person or trace. Behavioral Calibration asks whether generated behavior matches observed behavior, either individually or in aggregate.

Example: [TwinVoice: A Multi-dimensional Benchmark Towards Digital Twins via LLM Persona Simulation](https://arxiv.org/abs/2510.25536) can receive both Individual Fidelity and Behavioral Calibration if it evaluates memory, style, opinion consistency, or other person-specific simulation behavior.

### Design Communication vs Narrative Enrichment

Narrative enrichment is not a top-level objective by itself. It is usually a means to make personas interpretable, memorable, or enactable. Code Design Communication when the purpose is human understanding, requirements work, product design, or stakeholder coordination.

Example: [PersonaCite: VoC-Grounded Interviewable Agentic Synthetic AI Personas for Verifiable User and Design Research](https://arxiv.org/abs/2601.22288) should be considered for Design Communication because it is explicitly framed around user and design research.

### Bias and Harm Auditing vs Agent / Model Evaluation

Bias and Harm Auditing focuses on representational harms, stereotypes, fairness, and subgroup treatment. Agent / Model Evaluation focuses on what persona conditioning reveals about model capability, safety, role following, or steering.

Example: [When LLMs Imagine People](https://arxiv.org/abs/2602.00044) should be coded for Bias and Harm Auditing because it audits open-ended persona generation for bias and fairness. [The Chameleon's Limit](https://arxiv.org/abs/2604.24698) should be considered for Agent / Model Evaluation because it studies persona collapse and homogenization in model behavior.

## Coding Rules

1. Objective labels are multi-label. Assign all clearly supported objectives.
2. Do not infer an objective only because a method could be used for it. Code what the paper claims, evaluates, or clearly designs for.
3. Keep construction source and objective separate. A Population-Sampled method can be used for bias auditing; a Model-Generated method can be used for coverage; a Trace-Grounded method can be used for design communication.
4. Treat **narrative enrichment** as a means, not an objective family. Map it to Design Communication, Individual Fidelity, Behavioral Calibration, or Agent / Model Evaluation when the purpose is clear.
5. Treat **role-playing evaluation**, persona following, persona steering, and capability/safety testing under **Agent / Model Evaluation**.
6. Treat **joint-structure preservation**, density matching, population alignment, quota sampling, and subgroup prevalence under **Population Representation**.
7. Treat **support coverage**, edge cases, long-tail personas, red-team users, non-cooperative users, and robustness scenarios under **Coverage and Stress Testing**.
8. If local metadata is insufficient, mark the objective as `Unclear - needs full-text check`.
9. Always include links when referencing papers.

## Recommended Axis Sentence

> Along the objective axis, persona-generation methods differ by the claim their persona sets are meant to support: population representation, coverage and stress testing, individual fidelity, behavioral calibration, design communication, bias and harm auditing, or agent/model evaluation.

