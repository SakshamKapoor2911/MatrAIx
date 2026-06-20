# Construction-Technique Taxonomy

Status: working definition for the first taxonomy axis only. This file defines the construction-source / construction-technique axis. It does not finalize the second objective axis.

## Short Version

Classify synthetic persona generation methods by the source and construction logic behind the persona-conditioning inputs:

1. **Authored Archetypes**: human-designed persona types.
2. **Model-Generated Personas**: LLM-invented persona distributions.
3. **Population-Sampled Personas**: top-down draws from population structure.
4. **Trace-Grounded Personas**: bottom-up reconstructions from person-level evidence.

Memorable contrast:

> Authored archetypes are designed types; model-generated personas are model-invented people; population-sampled personas are top-down from population structure; trace-grounded personas are bottom-up from person-level evidence.

## Detailed Definition

This taxonomy axis classifies methods by **where the substantive persona information comes from before LLM enactment**. The final representation may be a prompt, profile, memory, backstory, structured row, or natural-language persona. The category is not determined by whether an LLM is prompted at the end; it is determined by what source anchors the persona distribution or persona state.

The taxonomy is intentionally distinct from role-playing-agent taxonomies that classify personas by the identity being enacted, such as demographic, character, or individualized personas. Here, demographic, psychometric, cultural, value-based, narrative, and behavioral attributes are persona dimensions or enrichment layers, not top-level method families.

## The Four Families

| Family | Construction source | Construction logic | Main validity claim | Main risks |
|---|---|---|---|---|
| **Authored Archetypes** | Human designers, domain experts, stakeholders, user researchers | Manually craft a small number of interpretable representative types | Persona is useful, plausible, communicative, and domain-relevant | Subjectivity, stereotyping, overgeneralization, weak population representativeness |
| **Model-Generated Personas** | LLM internal priors plus broad prompts, labels, or weak constraints | Ask the model to invent personas, attributes, backstories, or diverse user/citizen/customer sets | Persona set is scalable, vivid, broad, or useful for exploration | Opaque sampling distribution, prompt sensitivity, stereotypes, incoherent joint attributes |
| **Population-Sampled Personas** | Census data, survey data, panels, synthetic population models, fused datasets | Draw, weight, impute, calibrate, or synthesize anonymous persona records from a target population distribution | Persona set preserves marginal and joint population structure | Missing variables, marginal-only alignment, unobserved dependencies, data fusion assumptions |
| **Trace-Grounded Personas** | Interviews, logs, social media, behavioral histories, user profiles, longitudinal records | Reconstruct persona states from evidence about specific people or person-level traces | Persona preserves individual continuity, memory, style, preferences, or behavior | Privacy, consent, selection bias, memorization, weak representativeness |

## Examples

Always include paper links when using examples.

### Authored Archetypes

Use this family for classic HCI, requirements, design, stakeholder, or expert-created personas where humans decide the persona types and details. In the LLM corpus, systems such as [PersonaCite: VoC-Grounded Interviewable Agentic Synthetic AI Personas for Verifiable User and Design Research](https://arxiv.org/abs/2601.22288) and [Agentic Persona Generation with Critique-Refinement: An Industrial Evaluation](https://arxiv.org/abs/2606.09637) may touch this tradition when they compare against or refine expert/user-research personas, but code them carefully by the source actually used.

Boundary note: if an LLM generates personas from interviews, surveys, or job postings, do not automatically code it as Authored Archetypes. It may be Trace-Grounded, Population-Sampled, or Model-Generated depending on what anchors the generated content.

### Model-Generated Personas

Use this family when the LLM substantially invents the persona distribution from broad prompts or labels rather than from a sampling frame, trace data, or expert-authored design.

Examples:

- [LLM Generated Persona is a Promise with a Catch](https://arxiv.org/abs/2503.16527): discusses LLM-generated personas and critiques ad hoc, heuristic persona generation for population-level simulations.
- [When LLMs Imagine People: A Human-Centered Persona Brainstorm Audit for Bias and Fairness in Creative Applications](https://arxiv.org/abs/2602.00044): audits open-ended persona generation across many generated personas and bias dimensions.

Boundary note: a final prompt like "45-year-old rural woman" is not enough to classify a method. If that phrase is invented by the model from a broad "generate diverse Americans" prompt, code Model-Generated Personas. If it comes from Census, code Population-Sampled Personas.

### Population-Sampled Personas

Use this family when personas are anonymous or synthetic micro-records whose credibility comes from population-level data, calibration, or modeled joint distributions.

Examples:

- [NVIDIA Nemotron-Personas-USA](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA): census/ACS-grounded synthetic persona records aligned with demographic, geographic, occupational, and related distributions.
- [German General Social Survey Personas](https://arxiv.org/abs/2511.21722): survey-derived persona prompt collection built from the German General Social Survey / ALLBUS.
- [PERSONA: A Reproducible Testbed for Pluralistic Alignment](https://arxiv.org/abs/2407.17387): procedurally generates diverse user profiles from US census data.

Key point: the central reason to sample from census, survey microdata, or synthetic population methods is not merely to create plausible people. It is to preserve or explicitly model **joint structure**, such as age by education by rurality by income by household composition.

Subtype: **Enriched Population-Sampled Personas** start with a population scaffold and add values, psychometrics, communication style, beliefs, memories, or narrative detail through data fusion, survey joining, theory, traces, or LLM rendering. These remain Population-Sampled Personas if the population scaffold anchors the validity claim.

### Trace-Grounded Personas

Use this family when personas are reconstructed from evidence about specific people or person-level traces, even if anonymized.

Examples:

- [Synthia: Scalable Grounded Persona Generation from Social Media Data](https://arxiv.org/abs/2507.14922): grounds LLM-generated personas in real social-media posts and preserves interaction-graph structure among personas grounded in real social network users.
- [The Need for a Socially-Grounded Persona Framework for User Simulation](https://arxiv.org/abs/2601.07110): introduces SCOPE, built from a detailed sociopsychological protocol collected from 124 U.S.-based participants.
- [TwinVoice: A Multi-dimensional Benchmark Towards Digital Twins via LLM Persona Simulation](https://arxiv.org/abs/2510.25536): evaluates persona simulation for digital-twin-like individual communication style, memory, tone, and behavior.

Subtype: **Population-Calibrated Trace Personas** start from trace-grounded individuals and then filter, weight, or calibrate them toward population targets. [Population-Aligned Persona Generation for LLM-based Social Simulation](https://arxiv.org/abs/2509.10127) is a bridge case because it begins from long-term social-media-derived narrative personas and uses importance sampling to align with reference psychometric distributions.

## Boundary Rules

1. **Classify by anchor source, not final format.** Nearly all methods can end in an LLM prompt. The source of the persona information determines the family.
2. **Same surface prompt, different category.** "45-year-old rural woman" is Authored Archetype if manually chosen, Model-Generated if invented by the LLM, Population-Sampled if drawn from Census/survey structure, and Trace-Grounded if summarizing a real participant or user.
3. **Hybrids inherit from the anchor.** Census scaffold plus MBTI imputation is Population-Sampled. Social-media user profiles reweighted to population targets are Trace-Grounded with population calibration.
4. **Psychometric, cultural, demographic, and value variables are dimensions, not top-level method families.** They can appear in any family.
5. **Narrative rendering is not a source family.** If an LLM only verbalizes a structured row, code the method by the row's source.
6. **Separate source from objective.** Coverage, density matching, quota balancing, stress testing, individual fidelity, behavioral calibration, and narrative enrichment are design objectives, not construction-source families.

## Objective Axis Placeholder

Use a second axis to record what the persona set is designed to achieve. This second axis still needs separate discussion and refinement.

Candidate objective tags:

- density matching
- joint-structure preservation
- quota or stratified balance
- support coverage
- stress or edge-case testing
- individual fidelity
- behavioral calibration
- narrative enrichment
- design communication
- bias or harm auditing

Example: [Persona Generators: Generating Diverse Synthetic Personas for Arbitrary Contexts](https://arxiv.org/abs/2602.03545) should not become a fifth construction-source family. Code its source/technique separately, then code its objective as support coverage because it explicitly contrasts density matching with support coverage.

## Recommended Axis Sentence

> Along the construction-technique axis, persona-generation methods differ by the source used to construct persona-conditioning inputs: Authored Archetypes, Model-Generated Personas, Population-Sampled Personas, and Trace-Grounded Personas.

