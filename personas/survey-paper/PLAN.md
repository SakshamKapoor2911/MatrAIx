# PLAN.md


# Survey Paper Plan: Systematic and Theoretically Grounded Synthetic Persona Generation for LLM Agents

## 0. Working Title

**From Demographic Prompts to Synthetic Populations: A Survey and Framework for Systematic Persona Generation in LLM Agents**

Alternative titles:

- **Synthetic Personas for LLM Agents: A Survey of Data, Theory, and Evaluation**
- **Persona Generation as Population Modeling: A Survey of Methods for LLM-Based Agents**
- **Beyond Demographic Prompting: Toward Principled Synthetic Persona Generation for LLM Agents**
- **The Science of Synthetic Personas: A Survey of Representation, Grounding, and Validation for LLM Agents**


**AIM for ~ 10 body pages**

## 1A. Core Paper Idea

The paper should not claim that there is no prior work on personas. There are already adjacent surveys on role-playing language agents, LLM-based autonomous agents, and LLM-driven social simulation. The paper should instead claim a narrower and stronger gap:

> Existing surveys review role-playing language agents, autonomous LLM agents, and LLM-based social simulation, while recent primary papers propose demographic, psychometric, cultural, and socially grounded persona frameworks. However, the literature lacks a focused survey and theoretical synthesis of **synthetic persona generation as a methodological object**: how persona spaces should be specified, sampled, grounded in data and theory, validated, and audited for diversity, realism, uncertainty, and representational harms.

This framing is important because reviewers may point to role-playing-agent surveys and social-simulation surveys. The contribution should be to reorganize the literature around the persona-generation pipeline itself, rather than around downstream agent architectures or applications.


## 1B. Core Paper Thesis

Current LLM persona generation often jumps directly from narrative vividness to behavioral simulation, skipping the statistical middle layer where persona attributes must be sampled, fused, and validated as a coherent joint distribution.

Synthetic personas are often evaluated for plausibility one profile at a time, but realism is fundamentally relational: a persona is realistic only if its attributes are jointly coherent and if the population of personas preserves meaningful marginal and joint distributions.

## Tentative Taxonomy

See `taxonomy_options.md` and `TAXONOMY_AGENT_CONTEXT.md` for the current taxonomy-focused debate brief. The current direction is to classify persona-generation methods by the source and construction logic of the persona distribution, rather than by the identity being enacted.

- Prompted Priors: mostly implicit, uncontrolled joint structure.
- Authored Archetypes: manually coherent, but not distributionally representative.
- Sampled Populations: best positioned to preserve joint structure.
- Reconstructed Individuals: joint structure is real at the individual level, but sampling coverage may be biased.
- Optimized Coverage Sets: deliberately violates density realism sometimes, but should still enforce feasibility constraints.

## Conceptual Map: From Persona to Simulation

Where validity has three levels:
1. Marginal validity
Does the generated population match individual attribute distributions? Example: age, gender, education, income.

Joint validity
2. Does it preserve correlations and constraints among attributes? Example: age and education, occupation and income, household structure and age.

Behavioral validity
3. Do persona-conditioned agents act or respond in ways consistent with the structured profile and target population?

**Persona validity is not behavioral fidelity.**

Target population
      |
      v
Persona generator
      |
      v
Structured persona population
      |        validity problem 1: generation validity
      v
Prompt / memory / conditioning interface
      |
      v
LLM agent
      |
      v
Behavior / response / interaction trace
               validity problem 2: enactment validity

## 2. Target Contribution

The survey should contribute four things:

1. **A taxonomy of persona-generation regimes**
   - demographic prompting
   - role/character personas
   - survey-grounded synthetic respondents
   - psychometric/value-based personas
   - HCI/user-research personas
   - synthetic-population personas
   - LLM-generated open-ended personas
   - hybrid theory-and-data-grounded personas

2. **A unifying theoretical framework**
   - persona generation as construction of a distribution over structured latent agent states
   - distinction between observed attributes, latent traits, narrative realization, and behavioral policy
   - distinction between representativeness, diversity, realism, controllability, and validity

3. **A discussion of identification limits**
   - many persona attributes are not jointly observed in real datasets
   - cross-dataset fusion requires assumptions
   - the effective dimension of a persona space is not simply the number of observed variables
   - unknown joint distributions should be handled through explicit assumptions, uncertainty, and sensitivity analysis

4. **An evaluation and reporting checklist**
   - data provenance
   - theoretical grounding
   - sampling procedure
   - marginal and joint-distribution checks
   - persona consistency
   - behavioral fidelity where relevant
   - diversity/coverage
   - stereotype and representational-harm audit
   - reproducibility and prompt/model dependence

## 3. Central Research Questions

The survey can be organized around the following research questions:

### RQ1. What is a synthetic persona for an LLM agent?

Is a persona a demographic profile, a narrative biography, a latent psychological state, a role prompt, a memory state, a simulated respondent, or a distributional draw from a synthetic population? The paper should argue that current literature uses the word “persona” inconsistently.

### RQ2. What should a persona generator be expected to generate?

Possible outputs include:

- a structured attribute vector
- a natural-language backstory
- a latent trait vector
- a memory bank
- a set of goals/preferences/beliefs
- a policy over actions/responses
- a population of interacting agents

A key argument: **narrative richness is not the same as statistical grounding**. A detailed backstory may be coherent and persuasive but still arbitrary or biased.

### RQ3. What are the sources of persona diversity?

The survey should distinguish diversity from:

- observed demographic variation
- socioeconomic variation
- psychometric variation
- cultural/value variation
- social-position variation
- preference heterogeneity
- life-history variation
- network-position variation
- LLM-internal stochastic variation

### RQ4. How can persona generation be grounded?

Grounding can come from:

- surveys and microdata
- synthetic population methods
- psychometrics
- social psychology
- economic theory
- anthropology/cultural frameworks
- HCI/user-research personas
- domain expert elicitation
- real behavioral traces
- LLM prior knowledge, treated cautiously

### RQ5. What makes a persona set “good”?

A persona set may be good for one purpose but bad for another. Evaluation criteria include:

- population representativeness
- coverage of minority or edge cases
- internal consistency
- behavioral validity
- controllability
- interpretability
- reproducibility
- calibration to known distributions
- robustness to prompt/model changes
- avoidance of stereotyping and representational harm

### RQ6. What are the limits of persona generation when joint distributions are not observed?

This is one of the paper’s strongest theoretical angles. If income, education, personality, ideology, values, risk preference, media diet, and domain-specific beliefs are spread across different datasets, then their full joint distribution is not identified without assumptions. Persona generation should therefore be framed as a partially identified problem, not merely a prompting problem.

## 4. Positioning Against Existing Surveys

### 4.1 Role-Playing Language Agents

Key adjacent survey:

- Chen et al. (2024), **“From Persona to Personalization: A Survey on Role-Playing Language Agents.”**

How to use it:

- This is the closest existing survey.
- It categorizes role-playing personas into demographic, character, and individualized personas.
- It reviews data sourcing, agent construction, evaluation, applications, and risks.

How your survey differs:

- Their unit of analysis is the **role-playing language agent**.
- Your unit of analysis is the **persona-generation procedure**.
- Their scope includes characters, fictional/historical figures, individualized assistants, and digital clones.
- Your scope is synthetic persona distributions for LLM agents, with special attention to systematic sampling, theoretical grounding, joint distribution recovery, and validation.

Suggested sentence:

> Whereas role-playing-agent surveys ask how LLMs can simulate assigned personas, this survey asks how those personas should be constructed in the first place.

### 4.2 LLM-Based Social Simulation

Key adjacent survey:

- Mou et al. (2024), **“From Individual to Society: A Survey on Social Simulation Driven by Large Language Model-based Agents.”**

How to use it:

- This survey organizes LLM social simulation into individual simulation, scenario simulation, and society simulation.
- It is highly relevant because persona generation is foundational to individual and society-level simulation.

How your survey differs:

- Their focus is the simulation pipeline and application landscape.
- Your focus is the representation and generation of agents’ latent and observed characteristics.
- Their review covers agent architectures, benchmarks, and simulation types; your review would cut across these to ask how agent heterogeneity is generated and justified.

Suggested sentence:

> LLM social-simulation surveys establish the need for heterogeneous agents, but they do not provide a dedicated synthesis of how such heterogeneity should be specified, sampled, or validated.

### 4.3 LLM-Based Autonomous Agents

Key adjacent survey:

- Wang et al. (2023/2024), **“A Survey on Large Language Model based Autonomous Agents.”**

How to use it:

- This survey is useful background for agent architecture: memory, planning, tools, action, and environment.
- It helps explain where personas fit in the broader LLM-agent stack.

How your survey differs:

- Autonomous-agent surveys are mostly about capabilities and architectures.
- Persona generation is usually treated as input conditioning or role specification.
- Your paper treats persona generation as a statistical, theoretical, and representational problem.

### 4.4 Requirements Engineering and HCI Persona Surveys

Key adjacent survey/mapping work:

- Muzammel et al. (2025), **“Towards Using Personas in Requirements Engineering: What Has Been Changed Recently?”**
- HCI/data-driven persona literature, including classic work by Pruitt & Grudin and data-driven persona development by McGinn & Kotamraju.

How to use it:

- This literature predates LLM agents and treats personas as design artifacts representing user groups.
- It supplies important vocabulary: archetypes, data-driven personas, qualitative vs quantitative personas, stakeholder validation, and persona criticism.

How your survey differs:

- HCI personas are usually few, interpretable archetypes for design and communication.
- LLM-agent personas may be thousands or millions of sampled agents used in simulations.
- The HCI persona literature is nonetheless useful for evaluating interpretability, stakeholder validation, stereotyping, and the gap between fictional narrative and empirical grounding.

### 4.5 Synthetic Population and Microsimulation Literature

Key adjacent areas:

- synthetic population generation
- microsimulation
- agent-based modeling
- iterative proportional fitting / raking
- combinatorial optimization
- Bayesian networks and generative models
- statistical matching and data fusion

How to use it:

- This is essential for the theoretical backbone of the paper.
- Synthetic population methods already address the problem of generating heterogeneous agents whose marginals match census/survey data.
- Statistical matching/data fusion literature directly addresses the case where variables are distributed across multiple datasets and not jointly observed.

How your survey differs:

- Traditional synthetic populations usually focus on demographic and socioeconomic attributes.
- LLM-agent personas also need beliefs, values, goals, memories, emotions, and narrative descriptions.
- Your paper can bridge synthetic population methods with LLM persona prompting and psychometric/social-theory grounding.

## 5. Proposed Taxonomy of Persona Generation Methods

### 5.1 Demographic Prompting

Persona is specified by a short demographic description:

```text
You are a 45-year-old low-income rural woman living in Ohio.
```

Strengths:

- simple
- easy to control
- maps to common survey/census variables
- scalable

Weaknesses:

- high risk of stereotypes
- demographics often weakly predict fine-grained attitudes or decisions
- under-specifies mechanisms
- may exaggerate group differences
- creates false confidence because attributes look objective

Representative work:

- demographic persona prompting studies
- virtual survey respondent benchmarks
- LLM social-simulation papers that condition agents on demographic profiles

### 5.2 Character / Role Personas

Persona is a named role, fictional character, historical figure, professional type, or stakeholder category.

Examples:

```text
You are a skeptical central banker.
You are a small business owner facing a credit constraint.
You are Elizabeth Bennet after Chapter 20.
```

Strengths:

- vivid
- useful for role-play, education, deliberation, and narrative environments
- often easier for LLMs to enact than abstract demographic profiles

Weaknesses:

- may rely heavily on model priors
- hard to validate
- limited distributional meaning
- character consistency is not the same as population validity

Representative work:

- role-playing language agent surveys
- generative agents
- character-fidelity benchmarks

### 5.3 Survey-Grounded Synthetic Respondents

Persona is derived from or calibrated to survey respondents.

Possible approaches:

- sample real survey rows and convert them into prompts
- impute missing attributes
- ask LLMs to answer as a respondent with given attributes
- calibrate synthetic response distributions to observed survey marginals

Strengths:

- empirically grounded
- directly evaluable against survey data
- useful for public opinion, policy, and market research

Weaknesses:

- limited to survey items
- depends on survey design and measurement validity
- many relevant traits are unobserved
- joint distributions across datasets remain difficult

Representative work:

- Argyle et al., “Out of One, Many”
- LLM-S³ / virtual survey respondent benchmark
- synthetic public opinion studies

### 5.4 Psychometric and Value-Based Personas

Persona is specified through latent traits or value dimensions.

Examples:

- Big Five personality
- Moral Foundations Theory
- Schwartz values
- Inglehart-Welzel cultural dimensions
- risk aversion
- time preference
- locus of control
- institutional trust

Strengths:

- theoretically meaningful
- more behavioral than demographics
- can improve internal consistency
- supports dimensional persona spaces rather than ad hoc descriptions

Weaknesses:

- measurement scales may not transfer cleanly to LLM behavior
- traits may not map uniquely to actions
- psychometric validity of LLM enactment is uncertain
- cultural and linguistic validity issues

Representative work:

- SCOPE socially grounded persona framework
- Persona Alchemy
- culturally grounded personas using WVS / Inglehart-Welzel / Moral Foundations Theory
- personality-fidelity evaluations of role-playing agents

### 5.5 Data-Driven HCI Personas

Persona is generated from user research data through clustering, dimensionality reduction, qualitative synthesis, or mixed methods.

Strengths:

- long tradition in user-centered design
- combines quantitative and qualitative evidence
- focuses on interpretability and stakeholder communication

Weaknesses:

- often small number of archetypes rather than full populations
- historically criticized as fictional, reductive, or difficult to validate
- not designed for large-scale LLM-agent simulations

Representative work:

- classic HCI persona literature
- data-driven persona development
- recent AI-assisted persona construction in requirements engineering

### 5.6 Synthetic Population Personas

Persona is sampled from a synthetic population calibrated to demographic, socioeconomic, geographic, or behavioral marginals.

Strengths:

- strongest tradition for population representativeness
- compatible with agent-based modeling and microsimulation
- explicit calibration targets
- can support geographic and household structure

Weaknesses:

- traditional synthetic populations rarely include rich psychological/narrative attributes
- high-dimensional joint distributions are difficult
- adding subjective traits requires data fusion or assumptions

Representative methods:

- iterative proportional fitting / raking
- combinatorial optimization
- Bayesian networks
- copulas
- generative models
- statistical matching
- multiple imputation

### 5.7 LLM-Generated Open-Ended Personas

Persona is generated directly by an LLM, often with a diversity prompt.

Example:

```text
Generate 1,000 diverse personas for a study of consumer financial behavior.
```

Strengths:

- very scalable
- rich narrative detail
- low setup cost
- can cover rare or complex situations

Weaknesses:

- opaque distribution
- model priors dominate
- can generate stereotyped, incoherent, or unrepresentative profiles
- difficult to reproduce across models and prompt versions
- not statistically identified

Representative work:

- “LLM Generated Persona is a Promise with a Catch”
- population-aligned persona generation
- ethical audits of AI-crafted personas

### 5.8 Hybrid Theory/Data/LLM Persona Generation

Persona is generated through a structured pipeline:

1. sample demographic and socioeconomic anchors from data
2. infer latent traits from psychometric/survey sources
3. impute missing blocks through statistical matching or hierarchical models
4. calibrate marginals and selected correlations
5. use LLMs only to verbalize structured facts into coherent narrative prompts
6. validate consistency, diversity, and harms

This should be presented as the most promising direction.

## 6. Proposed Conceptual Framework

### 6.1 Persona as Latent State

Define a persona as a latent state vector plus a narrative realization:

```text
Persona_i = (A_i, Z_i, B_i, M_i, N_i)
```

Where:

- `A_i`: observed or assigned attributes, such as age, gender, income, education, geography
- `Z_i`: latent traits, such as personality, values, time preference, risk preference, trust
- `B_i`: beliefs and domain-specific attitudes
- `M_i`: memory/history/social context
- `N_i`: natural-language narrative or prompt representation

The key claim: many existing works collapse these layers into one prompt, but a systematic framework should keep them separate.

### 6.2 Four Layers of Persona Generation

#### Layer 1: Population Anchors

Variables with strong empirical support:

- age
- sex/gender
- region
- education
- occupation
- income
- household composition
- urban/rural status

Primary sources:

- census microdata
- nationally representative surveys
- administrative or panel data where available

#### Layer 2: Latent Traits

Variables that are not always observed but explain behavior:

- risk preference
- time preference
- Big Five
- values
- ideology
- moral foundations
- institutional trust
- locus of control
- social identity

Primary sources:

- psychometric surveys
- values surveys
- behavioral experiments
- longitudinal panels
- domain-specific datasets

#### Layer 3: Domain-Specific States

Variables relevant to the simulation context:

- financial literacy for financial agents
- political knowledge for voting agents
- health constraints for health simulations
- climate concern for climate-policy simulations
- technology adoption for innovation diffusion

#### Layer 4: Narrative Realization

The persona is translated into a prompt or memory representation:

- short structured prompt
- JSON profile
- autobiographical narrative
- memory bank
- dialogue history
- goal hierarchy

Important principle:

> The LLM should ideally verbalize a structured persona, not invent the persona distribution from scratch.

## 7. Identification and Dimension: A Key Theoretical Section

This section can be one of the paper’s most original contributions.

### 7.1 The Problem

Suppose dataset A observes:

```text
X = demographics, income, education
Y = financial behavior
```

Dataset B observes:

```text
X = demographics, income, education
Z = personality, values, trust
```

But no dataset jointly observes `Y` and `Z`.

Then the joint distribution:

```text
P(X, Y, Z)
```

is not identified by the data alone.

### 7.2 Why This Matters for Persona Generation

Many synthetic personas combine variables from multiple sources:

```text
age + income + ideology + Big Five + media diet + risk preference + life history
```

But if these are drawn from separate datasets, the synthetic joint distribution may be largely assumption-driven.

### 7.3 Possible Assumptions

#### Conditional Independence

Assume:

```text
Y ⟂ Z | X
```

This is common in statistical matching but often too strong.

#### Latent Factor Model

Assume both observed blocks depend on shared latent traits:

```text
Y = f(X, U, epsilon_y)
Z = g(X, U, epsilon_z)
```

#### Copula / Correlation Priors

Specify plausible residual correlations among unobserved blocks.

#### Bayesian Hierarchical Model

Treat unobserved dependence as uncertain and propagate posterior uncertainty.

#### Sensitivity Analysis

Generate persona populations under multiple assumptions and test how conclusions change.

### 7.4 Principle

The paper should propose the following principle:

> A persona generator should distinguish between **data-identified structure**, **theory-implied structure**, and **assumption-imputed structure**.

## 8. Evaluation Framework

The evaluation section should separate evaluation of the **persona generator** from evaluation of downstream task performance.

### 8.1 Distributional Validity

Does the generated persona population match target marginals and known joint distributions?

Metrics:

- marginal distribution error
- correlation error
- Wasserstein distance
- KL / JS divergence
- calibration error
- coverage of rare subgroups
- household/geographic consistency checks

### 8.2 Internal Consistency

Are persona attributes mutually coherent?

Examples of incoherence:

- impossible age/education/occupation combinations
- contradictory values and beliefs
- inconsistent income, occupation, and housing status
- narrative details that conflict with structured fields

Metrics:

- rule-based constraint violation rate
- LLM-based consistency judge, with caution
- structured validation tests
- cross-field plausibility checks

### 8.3 Theoretical Validity

Does the persona structure align with the theory it claims to use?

Examples:

- Big Five personas should show stable trait-consistent answers
- Social Cognitive Theory personas should operationalize cognitive, affective, biological, and motivational factors
- cultural personas should align with declared value frameworks

Metrics:

- scale reconstruction
- factor structure recovery
- trait-response consistency
- known-groups validity

### 8.4 Behavioral Fidelity

Although your paper is not mainly about downstream prediction, it should still discuss behavioral fidelity as one possible validation criterion.

Questions:

- Do agents with different persona traits behave differently in expected ways?
- Do aggregate responses match known survey or experimental distributions?
- Are differences due to meaningful persona structure or prompt stereotypes?

### 8.5 Diversity and Coverage

A persona population should cover a meaningful space, not merely sample common stereotypes.

Metrics:

- entropy over categorical attributes
- effective sample size
- coverage of intersectional groups
- distance-based coverage in latent space
- cluster balance
- tail coverage
- rare persona inclusion

### 8.6 Robustness

Generated personas should not be artifacts of one prompt or model.

Tests:

- prompt perturbation
- model substitution
- temperature variation
- sampling seed variation
- narrative vs structured-prompt comparison
- ablation of demographic, psychometric, and narrative components

### 8.7 Representational Harm and Bias

Synthetic personas may reproduce or amplify stereotypes.

Evaluation should examine:

- overemphasis on racial/ethnic markers
- exoticization
- deficit framing
- homogenization of minority groups
- benevolent stereotyping
- intersectional erasure
- association between protected attributes and negative traits

Potential methods:

- lexical audits
- human/community review
- counterfactual persona comparison
- stereotype association tests
- narrative harm coding

## 9. Proposed Paper Outline

## Abstract

One paragraph motivation: LLM agents increasingly rely on synthetic personas, but persona construction remains fragmented and often ad hoc. Existing surveys cover role-playing agents and social simulation, but not persona generation as a methodological object. This survey synthesizes LLM personas, synthetic respondents, HCI personas, psychometrics, and synthetic population methods. It proposes a taxonomy, a layered framework, an identification perspective, and an evaluation checklist.

## 1. Introduction

Main points:

- LLM agents are increasingly used to simulate individuals, groups, markets, organizations, and societies.
- Personas are often the mechanism for encoding heterogeneity.
- But persona generation is frequently treated as a prompt-engineering detail.
- This is problematic because persona choice determines the simulated population’s structure, diversity, and bias.
- Existing surveys review role-playing agents and social simulation, but not persona generation itself.

Suggested introduction thesis:

> Persona generation is not merely prompt design; it is a problem of population representation, latent-variable modeling, narrative construction, and validation under partial identification.

## 2. Scope and Definitions

Define:

- LLM agent
- persona
- synthetic persona
- persona generator
- persona population
- role-playing persona
- synthetic respondent
- synthetic population
- narrative realization
- behavioral fidelity

Clarify what is outside the scope:

- general autonomous-agent architecture, except where personas enter
- downstream simulation applications, except as motivation
- pure character role-play, except as adjacent literature
- synthetic data generation unrelated to agents/personas

## 3. Adjacent Surveys and Why a New Survey Is Needed

Discuss:

- role-playing language agents
- LLM social simulation
- LLM autonomous agents
- multi-agent surveys
- HCI persona surveys / requirements engineering mappings
- population synthesis and microsimulation reviews

Contribution table:

| Literature | Object of review | Persona generation treatment | Gap for this survey |
|---|---|---|---|
| Role-playing agents | LLMs simulating assigned personas | central but broad | does not focus on distributional/persona-generation methodology |
| Social simulation | agent-based LLM simulations | one component | does not systematize persona construction |
| Autonomous agents | architecture and capabilities | role/profile input | not a representation problem |
| HCI personas | design archetypes | human-centered design method | not LLM-agent population generation |
| Synthetic populations | calibrated micro-populations | strong on marginals/joints | weak on narrative/psychological LLM personas |

## 4. Historical Roots of Persona Construction

Subsections:

### 4.1 HCI and User-Centered Design Personas

Focus:

- personas as design artifacts
- qualitative, quantitative, and mixed-method personas
- criticisms: fictionalization, stereotyping, lack of reproducibility

### 4.2 Psychometrics and Social Psychology

Focus:

- traits, values, preferences, identity
- measurement validity
- latent variables
- scale construction

### 4.3 Synthetic Populations and Microsimulation

Focus:

- generating agent populations from census/survey data
- IPF/raking, combinatorial optimization, Bayesian networks
- calibration to population marginals

### 4.4 Statistical Matching and Data Fusion

Focus:

- integrating datasets with overlapping variables
- conditional independence assumption
- identifiability
- uncertainty and sensitivity

## 5. Taxonomy of LLM Persona Generation Methods

Use taxonomy from Section 5 above.

Possible table:

| Method family | Persona representation | Grounding source | Strength | Weakness |
|---|---|---|---|---|
| Demographic prompting | short attribute prompt | census/survey categories | simple/control | stereotypes/weak explanatory power |
| Character role-play | role or named character | text corpora/lore | vivid | hard to validate |
| Survey-grounded respondent | survey profile | public survey data | evaluable | narrow domains |
| Psychometric persona | latent traits | scales/theory | interpretable | mapping uncertainty |
| Data-driven HCI persona | archetype | user research | communicative | few clusters |
| Synthetic population | micro-agent row | census/surveys | representative | weak psychology |
| LLM-generated persona | narrative profile | model prior | scalable/rich | opaque/bias-prone |
| Hybrid framework | structured + narrative | data + theory + LLM | principled | complex/costly |

## 6. Persona Space Design

Key question: what dimensions should be included?

Subsections:

### 6.1 Observed Attributes

- demographics
- socioeconomic status
- geography
- household structure
- occupation

### 6.2 Latent Traits

- personality
- values
- trust
- risk/time preferences
- ideology
- identity

### 6.3 Domain-Specific Variables

- health
- finance
- political behavior
- labor market
- climate
- technology adoption

### 6.4 Narrative and Memory Variables

- backstory
- goals
- relationships
- prior experiences
- memories

### 6.5 Minimal Sufficient Persona

Introduce the idea that a persona should include variables that materially affect behavior in the intended environment, not every imaginable feature.

## 7. Sampling and Population Construction

Subsections:

### 7.1 Independent Sampling

Simple but usually unrealistic.

### 7.2 Stratified and Quota Sampling

Useful for coverage and controlled comparisons.

### 7.3 Population-Proportional Sampling

Useful when simulating a target population.

### 7.4 Synthetic Population Calibration

Use census/survey marginals and joint constraints.

### 7.5 Data Fusion and Statistical Matching

Combine datasets with overlapping variables.

### 7.6 Latent Variable Sampling

Draw traits from estimated latent distributions.

### 7.7 LLM-Assisted Expansion

Use LLMs to convert structured profiles into narrative personas while preserving constraints.

### 7.8 Adaptive / Task-Specific Persona Sampling

Generate personas targeted to a scenario while preserving global population alignment.

## 8. Theoretical Grounding

Potential theoretical backbones:

### 8.1 Bounded Rationality and Economic Preferences

- time preference
- risk aversion
- beliefs
- constraints
- attention
- social preferences

Useful for economic agents.

### 8.2 Social Cognitive Theory

- personal factors
- behavior
- environment
- self-efficacy
- observational learning

Relevant to Persona Alchemy.

### 8.3 Identity and Social Position

- social identity
- role identity
- group membership
- status
- norms

Useful for social simulations.

### 8.4 Cultural Values Frameworks

- World Values Survey
- Inglehart-Welzel map
- Moral Foundations Theory
- Schwartz values

Relevant to culturally grounded personas.

### 8.5 Psychometrics

- latent trait models
- factor analysis
- item response theory
- validity and reliability

### 8.6 HCI/User Research Theory

- personas as communicative artifacts
- stakeholder validation
- scenario-based design

## 9. Evaluation and Reporting Standards

Propose a checklist named something like **PERSONA-GEN**.

### 9.1 P — Population Target

- What population is the persona set supposed to represent?
- Is the population real, hypothetical, domain-specific, or fictional?

### 9.2 E — Evidence and Data Sources

- What data sources ground each feature?
- Are variables jointly observed or fused?
- What is the provenance of every persona field?

### 9.3 R — Representation and Coverage

- What dimensions are included/excluded?
- How are rare groups represented?
- Are intersectional groups covered?

### 9.4 S — Sampling Design

- How are personas sampled?
- Population-proportional, stratified, balanced, adversarial, or theory-driven?

### 9.5 O — Ontology and Structure

- What schema defines persona attributes?
- Are observed, latent, and narrative fields separated?

### 9.6 N — Narrative Realization

- How are structured attributes converted into prompts or memories?
- How is consistency enforced?

### 9.7 A — Assumptions and Uncertainty

- What dependencies are assumed?
- What parts of the joint distribution are not identified?
- Is uncertainty propagated?

### 9.8 G — Grounding and Validation

- Are generated personas compared to real data?
- Are psychometric/theoretical constructs validated?

### 9.9 E — Ethical and Representational Audit

- Are stereotypes, erasure, and representational harms evaluated?
- Are affected communities or domain experts involved?

### 9.10 N — Non-Robustness Checks

- Does the persona set change under prompt, model, or seed perturbation?

## 10. Proposed Figures

### Figure 1. Literature Map

Axes:

- x-axis: data grounding from weak to strong
- y-axis: narrative/psychological richness from low to high

Place literatures:

- demographic prompting
- HCI personas
- synthetic populations
- psychometric personas
- LLM-generated personas
- survey-grounded respondents
- hybrid persona generation

### Figure 2. Layered Persona Generator

Pipeline:

```text
Target population
    ↓
Data sources + theory sources
    ↓
Structured schema
    ↓
Latent trait model / data fusion / calibration
    ↓
Persona population
    ↓
Narrative realization by LLM
    ↓
Validation and audit
    ↓
Deployment in LLM agents
```

### Figure 3. Identification Problem

Show two datasets:

```text
Dataset A: X + Y
Dataset B: X + Z
Wanted: X + Y + Z
```

Highlight unobserved dependence between Y and Z.

### Figure 4. Evaluation Cube

Dimensions:

- representativeness
- diversity/coverage
- behavioral/theoretical validity
- harm/ethics

## 11. Candidate Tables

### Table 1. Adjacent Surveys

Columns:

- paper
- year
- domain
- unit of analysis
- how personas are treated
- relevance to this survey

Rows:

- From Persona to Personalization
- From Individual to Society
- A Survey on LLM-based Autonomous Agents
- LLM-based multi-agent surveys
- requirements engineering persona mapping
- synthetic population / microsimulation reviews

### Table 2. Persona Generation Methods

Columns:

- method family
- representation
- data source
- assumptions
- evaluation
- risks

### Table 3. Persona Dimensions

Rows:

- demographics
- socioeconomic status
- geography
- household/social network
- personality
- values
- beliefs
- preferences
- information environment
- domain-specific states
- narrative memory

Columns:

- examples
- data availability
- typical source
- identification difficulty
- risk of stereotyping

### Table 4. Evaluation Metrics

Rows:

- marginal validity
- joint validity
- internal consistency
- theory consistency
- behavioral fidelity
- diversity coverage
- robustness
- representational harm

Columns:

- definition
- metric
- required data
- limitation

## 12. Relevant Work to Include

### 12.1 Adjacent Surveys

- **Chen et al. (2024), “From Persona to Personalization: A Survey on Role-Playing Language Agents.”**
  - Closest persona-centered survey.
  - Important to cite in the introduction and positioning section.

- **Mou et al. (2024), “From Individual to Society: A Survey on Social Simulation Driven by Large Language Model-based Agents.”**
  - Important for social simulation context.

- **Wang et al. (2023/2024), “A Survey on Large Language Model based Autonomous Agents.”**
  - Useful for general LLM-agent architecture.

- **Recent requirements-engineering persona mapping/survey work.**
  - Useful to connect to HCI persona construction and validation.

### 12.2 Primary LLM Persona Papers

- **Li et al. (2025), “LLM Generated Persona is a Promise with a Catch.”**
  - Central motivation: current methods are ad hoc and heuristic.
  - Use as evidence that the field itself recognizes the need for rigorous persona-generation science.

- **Hu et al. (2025), “Population-Aligned Persona Generation for LLM-based Social Simulation.”**
  - Important primary paper on aligning persona sets to population-level psychometric distributions.

- **Venkit et al. (2026), “The Need for a Socially-Grounded Persona Framework for User Simulation.”**
  - Key evidence against demographic-only personas.
  - Introduces SCOPE.

- **Kim et al. (2025), “Persona Alchemy.”**
  - Theory-grounded persona design using Social Cognitive Theory.

- **Greco et al. (2026), “Culturally Grounded Personas in Large Language Models.”**
  - Uses WVS, Inglehart-Welzel, and Moral Foundations Theory.

- **Lutz et al. (2025), “The Prompt Makes the Person(a).”**
  - Shows prompt formulation affects persona simulation outcomes.

- **Venkit et al. (2025), “A Tale of Two Identities.”**
  - Ethical audit of AI-crafted personas and representational harms.

- **Zhao et al. (2025), “Large Language Models as Virtual Survey Respondents.”**
  - Benchmark for sociodemographic response generation.

- **Park et al. (2023), “Generative Agents.”**
  - Foundational for LLM agents with memory, reflection, planning, and naturalistic behavior.

### 12.3 Older and Adjacent Foundations

- HCI personas:
  - Cooper
  - Pruitt & Grudin
  - McGinn & Kotamraju, data-driven persona development

- Synthetic populations:
  - IPF/raking
  - population synthesis for microsimulation
  - synthetic populations for transport, epidemiology, urban simulation, and ABM

- Statistical matching/data fusion:
  - Rubin-style statistical matching
  - conditional independence assumption
  - fractional imputation
  - optimal transport / balanced sampling approaches

- Psychometrics:
  - factor analysis
  - item response theory
  - Big Five
  - values/moral foundations

## 13. Method for Conducting the Survey

Use a transparent search protocol.

### 13.1 Search Sources

- ACL Anthology
- arXiv
- ACM Digital Library
- Google Scholar
- Semantic Scholar
- NeurIPS / ICML / ICLR proceedings
- CHI / CSCW / UIST proceedings
- AAMAS proceedings
- social simulation / computational social science venues

### 13.2 Search Strings

Core strings:

```text
"LLM" "persona" "survey"
"synthetic persona" "large language model"
"persona generation" "LLM agents"
"role-playing language agents" "persona"
"LLM agents" "social simulation" "persona"
"synthetic respondents" "large language models"
"virtual survey respondents" "LLM"
"data-driven personas" "LLM"
"population-aligned persona generation"
"socially grounded persona" "LLM"
"psychologically grounded" "LLM agents" "persona"
```

Adjacent strings:

```text
"synthetic population" "agent-based model" survey
"population synthesis" microsimulation review
"statistical matching" data fusion conditional independence
"data-driven personas" HCI
"personas" requirements engineering systematic mapping
"user simulation" "large language models" persona
```

### 13.3 Inclusion Criteria

Include papers that:

- construct or evaluate personas for LLMs or agents
- simulate individuals, groups, or populations with LLMs
- propose persona prompting, persona tuning, or persona datasets
- discuss synthetic respondents or public-opinion simulation
- provide methods for population synthesis or data fusion relevant to persona generation
- discuss HCI/user personas in ways relevant to systematic persona construction

### 13.4 Exclusion Criteria

Exclude or downweight papers that:

- use “persona” only as a chatbot style without population or agent implications
- discuss personalization without explicit persona construction
- focus only on downstream task performance with no persona methodology
- use synthetic data unrelated to human-like agents or respondents

### 13.5 Coding Scheme

For each paper, code:

- domain
- persona type
- representation format
- generation method
- grounding data
- theoretical grounding
- sampling design
- target population
- evaluation metrics
- bias/harm analysis
- reproducibility artifacts
- limitations

## 14. Potential Novel Framework: Persona Generation as Partially Identified Population Synthesis

This could be the conceptual heart of the paper.

### 14.1 Claim

> Synthetic persona generation for LLM agents should be understood as a partially identified population synthesis problem with narrative realization.

### 14.2 Why This Is Useful

This formulation explains why existing ad hoc persona prompts are unsatisfactory:

- they do not define a target population
- they do not specify a sampling distribution
- they do not separate observed from latent attributes
- they do not report assumptions about dependencies
- they often let the LLM invent joint distributions
- they do not propagate uncertainty

### 14.3 Framework Components

```text
Target population P
Schema S
Observed data sources D_1, ..., D_K
Theoretical constraints T
Assumption set A
Sampling design Q
Narrative renderer R
Validation suite V
```

The persona generator is:

```text
G(P, S, D, T, A, Q, R, V) -> {persona_i}_{i=1}^N
```

### 14.4 Reporting Requirement

Every persona field should have metadata:

```json
{
  "field": "institutional_trust",
  "value": 0.31,
  "scale": "standardized",
  "source": "survey-fused",
  "observed_jointly_with": ["age", "education", "income"],
  "imputation_assumption": "latent factor model",
  "uncertainty": 0.18,
  "used_in_prompt": true
}
```

## 15. Possible Paper Abstract Draft

Large language model (LLM) agents are increasingly used to simulate individuals, groups, markets, organizations, and societies. These systems often rely on synthetic personas to encode agent heterogeneity, yet persona construction remains fragmented across demographic prompting, role-play, synthetic respondents, HCI personas, psychometrics, and synthetic population methods. Existing surveys review role-playing language agents and LLM-based social simulation, but do not treat persona generation itself as a central methodological object. This survey synthesizes work across LLM agents, computational social science, HCI, psychometrics, and microsimulation to ask: how should synthetic personas be specified, sampled, grounded, validated, and audited? We propose a taxonomy of persona-generation methods, distinguish observed attributes, latent traits, domain-specific states, and narrative realizations, and frame persona generation as a partially identified population-synthesis problem. We further develop an evaluation checklist covering distributional validity, internal consistency, theoretical validity, diversity and coverage, robustness, and representational harms. By organizing fragmented work around the persona-generation pipeline, this survey aims to support more transparent, reproducible, and theoretically grounded LLM-agent research.

## 16. Concrete Next Steps

### Week 1: Literature Corpus

- Collect 80–120 papers.
- Create Zotero collection.
- Tag by category:
  - LLM persona / role-play
  - LLM social simulation
  - synthetic respondents
  - HCI personas
  - synthetic populations
  - statistical matching
  - psychometrics
  - bias/ethics

### Week 2: Coding Spreadsheet

Create columns:

```text
paper_id
title
year
venue/domain
is_survey
persona_type
persona_representation
generation_method
data_grounding
theoretical_grounding
sampling_design
evaluation_type
bias_audit
reproducibility
main_limitations
relevance_score
```

### Week 3: Taxonomy and Figures

- Draft method taxonomy.
- Create literature map figure.
- Create layered persona pipeline figure.
- Create identification problem figure.

### Week 4: Core Writing

Draft sections:

1. Introduction
2. Definitions and scope
3. Adjacent surveys
4. Taxonomy
5. Persona space design
6. Sampling and identification
7. Evaluation and reporting
8. Open problems

### Week 5: Refinement

- Tighten claims about existing surveys.
- Add references.
- Add tables.
- Polish abstract and introduction.
- Decide target venue.

## 17. Potential Venues

Depending on final emphasis:

### NLP / LLM-Agent Focus

- ACL Findings
- EMNLP Findings
- NAACL Findings
- COLM
- NeurIPS workshop on agents / social AI
- ACL workshop on NLP + CSS / simulation / ethics

### HCI / CSCW Focus

- CHI
- CSCW
- DIS
- UIST if system/tool oriented

### Computational Social Science Focus

- IC2S2
- WebSci
- SocInfo
- JASSS if agent-based social simulation oriented

### Survey-Oriented Journals

- ACM Computing Surveys, if broad and mature enough
- AI Magazine
- Journal of Artificial Societies and Social Simulation
- Computational Social Networks

## 18. Risks and How to Handle Them

### Risk 1: Reviewers say role-playing-agent surveys already cover personas.

Response:

- Acknowledge them directly.
- Say they review agents that enact personas, not the statistical/theoretical generation of persona populations.

### Risk 2: Scope becomes too broad.

Response:

- Keep the central object fixed: persona generation for LLM agents.
- Use adjacent literatures only when they inform generation, grounding, or evaluation.

### Risk 3: Too few directly relevant papers.

Response:

- Frame as an emerging-methods survey plus synthesis.
- Use adjacent fields to build the theoretical foundation.

### Risk 4: Lack of empirical contribution.

Response:

- Add a small scoping review dataset and coding analysis.
- Optionally include a small meta-analysis of persona-generation choices across papers.

### Risk 5: Fast-moving literature.

Response:

- Maintain a living bibliography.
- Include search date and reproducible search protocol.

## 19. Strongest Original Angle

The strongest version of the paper is not simply “a survey of LLM personas.” It is:

> A survey and theoretical synthesis that reframes synthetic persona generation for LLM agents as **population synthesis under partial identification, followed by narrative realization and agent deployment**.

This gives the paper intellectual grounding beyond a descriptive taxonomy.

## 20. Minimal Viable Paper Structure

If the paper needs to be short, use this structure:

1. Introduction: why personas matter and why ad hoc generation is problematic
2. Existing surveys and gap
3. Taxonomy of persona-generation methods
4. Persona generation as layered population synthesis
5. Identification limits and data fusion
6. Evaluation checklist
7. Open problems and research agenda

## 21. Full Paper Structure

If the paper can be longer, use this structure:

1. Introduction
2. Scope and definitions
3. Search methodology
4. Adjacent surveys
5. Historical roots: HCI, psychometrics, synthetic populations
6. Taxonomy of LLM persona-generation methods
7. Persona dimensions and schema design
8. Sampling, calibration, and data fusion
9. Theoretical grounding
10. Evaluation framework
11. Ethics and representational harms
12. Open problems
13. Conclusion

## 22. One-Sentence Pitch

> This survey explains how to construct synthetic personas for LLM agents not as ad hoc prompts, but as theoretically grounded, data-informed, uncertainty-aware representations of heterogeneous agents.
