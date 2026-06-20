# Two-Axis Taxonomy Pitch

## One-Sentence Pitch

Synthetic persona generation should be classified by **where the persona information comes from** and **what the persona set is meant to be valid for**.

This avoids confusing a vivid prompt with a valid population, or a coherent persona with faithful LLM behavior.

## Why This Taxonomy?

Existing role-playing-agent surveys often classify personas by the identity being enacted, such as demographic, character, or individualized personas. This survey instead treats persona generation as the methodological object.

The central distinction:

> The construction axis asks where personas come from; the objective axis asks what the persona set is valid for.

Two slogans:

- **Narrative vividness is not population validity.**
- **Persona validity is not behavioral fidelity.**

## Axis 1: Construction Technique

This axis classifies the source and construction logic behind the persona-conditioning input.

| Category | Brief definition | Example papers |
|---|---|---|
| **Authored Archetypes** | Human-designed persona types, often for design, requirements, or stakeholder communication. | [PersonaBOT](https://arxiv.org/abs/2505.17156) brings customer personas to life with LLMs and RAG, using verified customer persona / segment artifacts rather than raw population sampling. [Agentic Persona Generation with Critique-Refinement](https://arxiv.org/abs/2606.09637) uses an LLM generator/critic loop over interviews, surveys, and job postings, and compares against expert-created personas. |
| **Model-Generated Personas** | The LLM substantially invents the persona distribution from broad prompts, labels, or weak constraints. | [LLM Generated Persona is a Promise with a Catch](https://arxiv.org/abs/2503.16527) studies large-scale LLM-generated personas and argues that ad hoc heuristic generation causes downstream bias. [When LLMs Imagine People](https://arxiv.org/abs/2602.00044) audits open-ended LLM persona brainstorming across 120,000 generated personas. |
| **Population-Sampled Personas** | Personas are top-down draws, syntheses, or enrichments from census, survey, panel, synthetic-population, or fused population data. | [German General Social Survey Personas](https://arxiv.org/abs/2511.21722) builds persona prompts from the German General Social Survey / ALLBUS. [PERSONA](https://arxiv.org/abs/2407.17387) procedurally generates synthetic user profiles from US census data. [NVIDIA Nemotron-Personas-USA](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA) grounds synthetic records in US Census / ACS-style demographic and geographic distributions. |
| **Trace-Grounded Personas** | Personas are bottom-up reconstructions from evidence about specific people or person-level traces. | [Synthia](https://arxiv.org/abs/2507.14922) grounds personas in real social-media posts and preserves social-network structure. [SCOPE](https://arxiv.org/abs/2601.07110) builds personas from a detailed 141-item sociopsychological protocol collected from participants. [TwinVoice](https://arxiv.org/abs/2510.25536) evaluates digital-twin-style persona simulation for memory, tone, style, and opinion consistency. |

### Key Boundary Rule

Classify by the **anchor source**, not by the final prompt.

The same surface persona, such as "a 45-year-old rural woman," can belong to different categories:

- manually selected by a designer -> **Authored Archetype**
- invented by an LLM from "generate diverse Americans" -> **Model-Generated Persona**
- drawn from census or survey structure -> **Population-Sampled Persona**
- summarized from a real participant or user trace -> **Trace-Grounded Persona**

Hybrid methods inherit from their anchor source:

- census scaffold plus MBTI/value/style enrichment -> **Population-Sampled Persona**
- social-media personas reweighted toward population targets -> **Trace-Grounded Persona**, population-calibrated subtype

## Axis 2: Persona-Set Objective

This axis classifies what the persona set is meant to support. These labels are multi-label: one paper can have several objectives.

| Objective | Brief definition | Example papers |
|---|---|---|
| **Population Representation** | The persona set should represent a target population's marginals, joint structure, weights, or subgroup prevalence. | [German General Social Survey Personas](https://arxiv.org/abs/2511.21722) aims to align persona-prompted LLM responses with the German population. [Marginal Alignment Does Not Guarantee Joint-Distribution Fidelity](https://arxiv.org/abs/2606.12433) audits why marginal demographic alignment is insufficient for joint persona validity. |
| **Coverage and Stress Testing** | The persona set should span rare, difficult, risky, adversarial, or long-tail cases. | [Persona Generators](https://arxiv.org/abs/2602.03545) explicitly contrasts density matching with support coverage and optimizes generators for diverse, rare trait combinations. [Beyond Cooperative Simulators](https://arxiv.org/abs/2605.12894) generates more realistic/non-cooperative user personas for robust LLM-agent evaluation. |
| **Individual Fidelity** | The persona should preserve a specific person, trace, memory, style, or history. | [TwinVoice](https://arxiv.org/abs/2510.25536) evaluates whether LLMs can simulate individual communication style, memory recall, tone, and syntactic style. [Synthia](https://arxiv.org/abs/2507.14922) uses real social-media posts as grounding for persona construction. |
| **Behavioral Calibration** | Persona-conditioned agents should reproduce observed actions, survey responses, or interaction patterns. | [SCOPE](https://arxiv.org/abs/2601.07110) evaluates whether sociopsychologically grounded personas improve human response similarity. [Text-Based Personas for Simulating User Privacy Decisions](https://arxiv.org/abs/2603.19791) grounds personas in prior privacy decisions and evaluates prediction of privacy choices. |
| **Design Communication** | Personas should help humans reason, design, deliberate, or align stakeholders. | [PersonaCite](https://arxiv.org/abs/2601.22288) creates voice-of-customer-grounded interviewable personas for user and design research. [Agentic Persona Generation with Critique-Refinement](https://arxiv.org/abs/2606.09637) targets software-engineering persona creation for requirements, design, and validation. |
| **Bias and Harm Auditing** | Personas should reveal stereotypes, erasure, unfairness, or representational harm. | [When LLMs Imagine People](https://arxiv.org/abs/2602.00044) audits open-ended LLM persona generation for bias across identity and social-role dimensions. [A Tale of Two Identities](https://arxiv.org/abs/2505.07850) audits human- and AI-crafted personas for representational harms. |
| **Agent / Model Evaluation** | Persona conditioning is used to test model behavior, role following, capability shifts, safety, or persona collapse. | [The Chameleon's Limit](https://arxiv.org/abs/2604.24698) studies persona collapse and homogenization in LLMs. [Measure what Matters](https://arxiv.org/abs/2510.22170) uses persona conditioning and situational judgment tests to evaluate stable LLM behavioral tendencies. |

## What This Buys Us

The two-axis taxonomy makes validity claims explicit:

- **Population-Sampled + Population Representation**: asks whether the persona set matches a target population, including joint structure.
- **Trace-Grounded + Individual Fidelity**: asks whether the persona preserves a specific user's evidence, style, or history.
- **Model-Generated + Bias Auditing**: asks what kinds of people the model imagines and what stereotypes appear.
- **Model-Generated + Coverage Testing**: asks whether generated personas span useful edge cases rather than match real-world prevalence.
- **Any construction source + Behavioral Calibration**: asks whether the LLM actually enacts the persona in observed behavior.

The payoff is simple:

> A persona method should be evaluated against the claim it actually makes, not against every possible notion of realism.

