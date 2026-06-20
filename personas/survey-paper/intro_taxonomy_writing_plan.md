# Writing Plan: Introduction and Taxonomy Definition

Status: handoff plan for drafting `sections/01_introduction.tex` and `sections/05_taxonomy.tex`. This plan reflects the current two-axis taxonomy:

- First axis: `taxonomy_construction_technique.md`
- Second axis: `taxonomy_objective_axis.md`

Do not treat the older five-family taxonomy in `taxonomy_options.md` or `PLAN.md` as current. Those files are useful historical debate notes, but the working taxonomy is now two-axis.

Always include links when discussing papers in notes, summaries, or handoff text. In LaTeX prose, use citation keys if available, but keep a comment or adjacent note with the paper link if the citation key is uncertain.

## Core Message

The paper should argue that synthetic persona generation for LLM agents is not merely prompt writing or role assignment. It is a methodological problem about constructing, enriching, validating, and deploying representations of heterogeneous agents.

Two slogans should structure the argument:

1. **Narrative vividness is not population validity.**
2. **Persona validity is not behavioral fidelity.**

The taxonomy operationalizes these slogans:

- The **construction-technique axis** asks where persona information comes from.
- The **objective axis** asks what the persona set is meant to be valid for.

## Introduction Writing Plan

Target length: roughly 900-1,200 words for a compact survey paper introduction.

### Paragraph 1: Motivation and Stakes

Open with the rise of LLM agents used to simulate users, citizens, customers, patients, students, workers, voters, or communities. Emphasize that these systems rely on personas to encode heterogeneity.

Purpose:

- Establish that personas are now infrastructure for LLM-agent simulation and evaluation.
- Avoid sounding like personas are new; the novelty is systematic generation for LLM agents.

Candidate examples to mention with links:

- [From Individual to Society](https://arxiv.org/abs/2412.03563): LLM social simulation context.
- [From Persona to Personalization](https://arxiv.org/abs/2404.18231): role-playing language-agent context.
- [German General Social Survey Personas](https://arxiv.org/abs/2511.21722): survey-derived population-aligned personas.
- [Synthia](https://arxiv.org/abs/2507.14922): social-media-grounded virtual populations.

### Paragraph 2: Problem Statement

State the core failure mode: many workflows move from a plausible persona prompt directly to simulated behavior, skipping the statistical and methodological layer where persona attributes must be specified, sampled, fused, and validated.

Key claims:

- A detailed backstory can be vivid but distributionally arbitrary.
- A persona set can match marginals while violating joint structure.
- A persona-conditioned model can match aggregate behavior for the wrong reasons.

Use examples:

- [LLM Generated Persona is a Promise with a Catch](https://arxiv.org/abs/2503.16527): critiques ad hoc LLM-generated personas and downstream bias.
- [Marginal Alignment Does Not Guarantee Joint-Distribution Fidelity](https://arxiv.org/abs/2606.12433): directly supports the marginal-vs-joint validity point.
- [The Chameleon's Limit](https://arxiv.org/abs/2604.24698): supports behavioral/persona collapse and population-level evaluation concerns.

### Paragraph 3: Positioning Against Adjacent Surveys

Acknowledge existing surveys and explain the narrower contribution.

Required contrast:

> Whereas role-playing-agent surveys classify personas by the identity being enacted, this survey classifies persona-generation methods by the source and construction logic of the persona distribution and by the objective the persona set is meant to support.

Use linked examples:

- [From Persona to Personalization](https://arxiv.org/abs/2404.18231): classifies role-playing personas and agent issues.
- [From Individual to Society](https://arxiv.org/abs/2412.03563): surveys LLM social simulation pipeline and applications.

Do not overclaim that no one has studied personas. The precise gap is that there is not yet a focused synthesis of persona generation as a methodological object: specification, sampling, grounding, validation, auditing, and uncertainty.

### Paragraph 4: Conceptual Framework

Introduce the paper's conceptual separation:

```text
Target population / person / scenario
    -> persona construction
    -> structured persona set
    -> prompt, memory, or narrative realization
    -> LLM enactment
    -> behavior / response / interaction trace
```

Explain the validity distinction:

- **Marginal validity**: one-dimensional distributions match.
- **Joint validity**: dependencies and feasibility constraints across attributes are preserved.
- **Enactment validity**: the LLM behaves consistently with the persona after conditioning.
- **Use-relative fidelity**: required fidelity depends on downstream use.

This paragraph should set up why the taxonomy has two axes.

### Paragraph 5: Contributions

List contributions clearly, likely 3-4 bullets or prose with signposting:

1. A two-axis taxonomy of synthetic persona generation methods.
2. A framework separating construction source, objective, persona validity, and enactment validity.
3. A synthesis of evidence and failure modes from the curated corpus.
4. Reporting/evaluation guidance for future persona-generation work.

Tie to local coding artifacts:

- Construction-axis coding file: `literature/papers_top100_taxonomy_coding.csv`
- Objective-axis coding file: `literature/papers_top100_objective_axis_coding.csv`

### Paragraph 6: Roadmap

Keep short. Mention definitions/scope, related work, taxonomy, persona-space design, sampling/identification, evaluation, ethics, and open problems.

## Taxonomy Definition Section Plan

Target length: roughly 1,200-1,600 words, plus one main table.

This section should define the taxonomy, not review every paper. It should be crisp enough that readers remember the two axes.

### Opening: Why Two Axes?

Start by explaining why a single list of persona types is insufficient. Demographic, psychometric, cultural, character, and individualized personas describe what attributes or identities appear in a persona, but not how the persona distribution was constructed or what validity claim it supports.

Core sentence:

> We therefore classify persona-generation methods along two orthogonal axes: construction technique and objective.

Explain:

- **Construction technique**: source of persona information.
- **Objective**: claim the persona set is meant to support.

### Subsection 1: Construction-Technique Axis

Use the four families from `taxonomy_construction_technique.md`.

Recommended compact table columns:

| Family | Source | Construction logic | Typical use | Main risk |

Rows:

1. **Authored Archetypes**
   - Human-designed representative types.
   - Mention HCI/requirements tradition and expert/customer personas.
   - Example: [PersonaBOT](https://arxiv.org/abs/2505.17156) or [Agentic Persona Generation with Critique-Refinement](https://arxiv.org/abs/2606.09637) as boundary cases where expert/user-research artifacts matter.

2. **Model-Generated Personas**
   - LLM invents persona distribution from broad prompts or weak constraints.
   - Examples: [LLM Generated Persona is a Promise with a Catch](https://arxiv.org/abs/2503.16527), [When LLMs Imagine People](https://arxiv.org/abs/2602.00044).
   - Key risk: opaque model prior; surface diversity can hide stereotypes and incoherent joints.

3. **Population-Sampled Personas**
   - Top-down from census, survey, synthetic-population, or fused data.
   - Examples: [NVIDIA Nemotron-Personas-USA](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA), [German General Social Survey Personas](https://arxiv.org/abs/2511.21722), [PERSONA](https://arxiv.org/abs/2407.17387).
   - Key concept: joint distribution, not just plausible rows.

4. **Trace-Grounded Personas**
   - Bottom-up from person-level traces, interviews, logs, social media, protocols, or histories.
   - Examples: [Synthia](https://arxiv.org/abs/2507.14922), [SCOPE](https://arxiv.org/abs/2601.07110), [TwinVoice](https://arxiv.org/abs/2510.25536).
   - Key risk: selection bias, privacy, consent, weak representativeness.

Boundary paragraph:

- Same surface prompt can belong to different categories depending on source.
- Hybrids inherit from the anchor source.
- Census scaffold plus MBTI enrichment remains Population-Sampled Personas.
- Social-media traces plus population weighting remains Trace-Grounded Personas with population calibration.

### Subsection 2: Objective Axis

Use the seven families from `taxonomy_objective_axis.md`.

Recommended compact table columns:

| Objective | Question answered | Example evidence | Failure if confused |

Rows:

1. **Population Representation**
   - Does the set represent a target population?
   - Includes density matching and joint-structure preservation.
   - Example: [German General Social Survey Personas](https://arxiv.org/abs/2511.21722).

2. **Coverage and Stress Testing**
   - Does the set span rare, risky, difficult, or adversarial cases?
   - Example: [Persona Generators](https://arxiv.org/abs/2602.03545).

3. **Individual Fidelity**
   - Does the persona preserve a specific person or trace?
   - Example: [TwinVoice](https://arxiv.org/abs/2510.25536).

4. **Behavioral Calibration**
   - Do persona-conditioned agents reproduce observed responses/actions?
   - Example: [SCOPE](https://arxiv.org/abs/2601.07110) or [Synthia](https://arxiv.org/abs/2507.14922).

5. **Design Communication**
   - Do personas help humans reason, design, or align stakeholders?
   - Example: [PersonaCite](https://arxiv.org/abs/2601.22288).

6. **Bias and Harm Auditing**
   - Does the method expose stereotypes, erasure, unfairness, or representational harm?
   - Example: [A Tale of Two Identities](https://arxiv.org/abs/2505.07850), [When LLMs Imagine People](https://arxiv.org/abs/2602.00044).

7. **Agent / Model Evaluation**
   - Does persona conditioning test model behavior, role following, safety, alignment, or capability shifts?
   - Example: [The Chameleon's Limit](https://arxiv.org/abs/2604.24698), [Measure what Matters](https://arxiv.org/abs/2510.22170).

Boundary paragraph:

- Objectives are multi-label.
- Narrative enrichment is a means, not a top-level objective.
- Agent/model evaluation is included because many papers use personas to test model behavior rather than generate population-valid personas.

### Subsection 3: How The Axes Interact

Use a small matrix or prose examples:

- Model-Generated + Bias and Harm Auditing: [When LLMs Imagine People](https://arxiv.org/abs/2602.00044).
- Population-Sampled + Population Representation + Behavioral Calibration: [German General Social Survey Personas](https://arxiv.org/abs/2511.21722).
- Trace-Grounded + Individual Fidelity + Behavioral Calibration: [SCOPE](https://arxiv.org/abs/2601.07110), [TwinVoice](https://arxiv.org/abs/2510.25536).
- Model-Generated + Coverage and Stress Testing: [Persona Generators](https://arxiv.org/abs/2602.03545).

Make the point:

> A construction family does not imply a validity claim. The same source can serve different objectives, and the same objective can be pursued with different sources.

### Subsection 4: Implications For Evaluation

End the taxonomy section by connecting to evaluation:

- Population Representation requires marginal and joint checks.
- Coverage and Stress Testing requires coverage metrics or failure-discovery evidence.
- Individual Fidelity requires person-level comparisons.
- Behavioral Calibration requires response/action benchmarks.
- Bias and Harm Auditing requires subgroup/intersectional analysis.
- Agent / Model Evaluation requires role-following, consistency, safety, or capability tests.

This should transition naturally into later sections on persona space, sampling/identification, and evaluation standards.

## Style Constraints

- Do not write as if the taxonomy is the only possible taxonomy. Present it as a methodological lens.
- Avoid saying grounded methods are always better. They are better for some validity claims, but not all uses.
- Keep the contrast with adjacent surveys precise and respectful.
- Do not use paper examples without links in notes or handoff text.
- In the final manuscript, use citations rather than raw URLs, but keep links in comments or notes until citation keys are verified.
- Preserve the two slogans:
  - Narrative vividness is not population validity.
  - Persona validity is not behavioral fidelity.

## Drafting Agent Inputs

Before drafting, read:

1. `personas/survey-paper/sections/01_introduction.tex`
2. `personas/survey-paper/sections/05_taxonomy.tex`
3. `personas/survey-paper/taxonomy_construction_technique.md`
4. `personas/survey-paper/taxonomy_objective_axis.md`
5. `personas/survey-paper/literature/papers_top100_construction_axis_review.md`
6. `personas/survey-paper/literature/papers_top100_objective_axis_review.md`
7. `personas/survey-paper/TAXONOMY_AGENT_CONTEXT.md`

If drafting LaTeX, write only `sections/01_introduction.tex` and `sections/05_taxonomy.tex`. Leave citation-key TODOs where keys are uncertain, and include URL comments for any paper whose key needs verification.

