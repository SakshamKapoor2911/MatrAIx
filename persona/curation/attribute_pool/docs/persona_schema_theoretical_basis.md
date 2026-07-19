# Persona Schema Theoretical Basis and Attribute Construction Plan

Last updated: 2026-06-19

## Purpose

This document summarizes the current theoretical basis for the MatrAIx persona attribute schema and explains how external sources such as SCOPE, DeepPersona, Nemotron, PrimeX, WVS, GSS, ACS PUMS, Big Five, HEXACO, Facet MAP, and IPIP should be used.

The goal is not to collect as many attributes as possible. The goal is to build a theory-grounded, simulation-oriented persona schema that supports:

- realistic user / agent simulation;
- deduplication and source grounding;
- attribute correlation and conflict analysis;
- domain-specific persona modules;
- transparent justification for why each attribute belongs in the candidate pool.

## Core Position

Our top-level schema should not directly copy DeepPersona, SCOPE, Nemotron, or any single dataset.

Instead:

- SCOPE provides a recent LLM-persona framework and evidence that demographic-only personas are insufficient.
- DeepPersona provides broad long-tail attribute coverage and useful subcategory granularity.
- Nemotron provides demographic, geographic, occupation, skills, hobbies, cultural background, and career-goal grounding.
- PrimeX, WVS, and GSS provide worldview, belief, opinion, attitude, and social-science grounding.
- Big Five, HEXACO, Facet MAP, and IPIP provide validated personality trait and facet sources.

Our schema should use a synthesized theoretical architecture, then map each external source into that architecture.

## Theoretical Stack

### 1. McAdams' Three Levels of Personality

McAdams' framework is useful as the high-level architecture for "what it means to know a person."

It separates personality into:

- Level 1: dispositional traits;
- Level 2: characteristic adaptations, such as goals, values, coping strategies, motives, roles, relationships, and habits;
- Level 3: narrative identity, or the internalized life story that gives a person continuity and meaning.

Mapping to our schema:

- `Personality Traits` corresponds to dispositional traits.
- `Values, Goals & Motivations`, `Behavioral Patterns & Preferences`, and `Social Identity, Relationships & Community` correspond to characteristic adaptations.
- `Narrative Identity & Life History` corresponds to narrative identity.

Why it matters:

McAdams gives us the strongest argument that persona should not be only demographics or trait scores. A realistic persona needs stable traits, context-sensitive adaptations, and life narrative.

Primary source:

- McAdams, D. P. (1995). What Do We Know When We Know a Person? Journal of Personality. https://onlinelibrary.wiley.com/doi/10.1111/j.1467-6494.1995.tb00500.x
- McAdams, D. P., & Pals, J. L. (2006). A New Big Five: Fundamental Principles for an Integrative Science of Personality. https://pubmed.ncbi.nlm.nih.gov/16594837/

### 2. Trait Psychology: Big Five, HEXACO, Facet MAP, and IPIP

Trait psychology supports the personality layer.

Useful sources:

- Big Five / BFI-2: broad five-factor personality domains and 15 facets.
- HEXACO: six-factor model, adding Honesty-Humility as a major dimension.
- Facet MAP: fine-grained open-access personality facet taxonomy.
- IPIP: public-domain personality item and scale pool.

Mapping to our schema:

- `Personality Traits`
- part of `Cognitive & Capability Profile`
- part of `Emotional and Relational Skills` as a subcategory

Why it matters:

These sources give us validated names, definitions, and scales for personality attributes. We should use them to avoid inventing vague traits such as "nice" or "smart" without measurement grounding.

Sources:

- BFI-2: https://www.colby.edu/academics/departments-and-programs/psychology/research-opportunities/personality-lab/the-bfi-2/
- HEXACO: https://hexaco.org/
- Facet MAP: https://facetmap.org/facet-labels-and-definitions/
- IPIP: https://ipip.ori.org/

### 3. Values, Worldview, Beliefs, and Attitudes

Values and beliefs explain why a person prefers certain choices, makes certain judgments, or reacts to social situations in a particular way.

Useful sources:

- Schwartz Theory of Basic Human Values;
- World Values Survey (WVS);
- General Social Survey (GSS);
- PrimeX / Primal World Beliefs;
- Pew-style public opinion and internet behavior surveys.

Mapping to our schema:

- `Values, Goals & Motivations`
- `Worldview, Beliefs & Attitudes`
- part of `Behavioral Patterns & Preferences`

Why it matters:

Two people with similar demographics and similar traits can still behave differently because they hold different values, worldviews, moral priorities, political attitudes, religious beliefs, or levels of institutional trust.

Sources:

- Schwartz values overview: https://scholarworks.gvsu.edu/orpc/vol2/iss1/11/
- WVS: https://www.worldvaluessurvey.org/
- GSS: https://gss.norc.org/
- PrimeX: https://github.com/apple/ml-primex

### 4. Social Identity and Population Grounding

Demographics are not behavior-deterministic, but they are important as social position, lived context, and structural constraint.

Useful sources:

- Social Identity Theory;
- U.S. Census / ACS PUMS / IPUMS;
- Nemotron-Personas-USA;
- OASIS;
- population survey metadata.

Mapping to our schema:

- `Demographics & Population Grounding`
- `Life Context & Constraints`
- `Social Identity, Relationships & Community`
- `Cultural and Social Context` as a subcategory

Why it matters:

Age, gender, race / ethnicity, region, education, occupation, income, household structure, language, and cultural background should be included as grounding variables. However, they should not be used as simplistic proxies for behavior. SCOPE's findings are especially useful here: demographic-only personas can amplify stereotypes and explain only a small part of behavioral similarity.

Sources:

- Social Identity Theory overview: https://www.simplypsychology.org/social-identity-theory.html
- Census ACS PUMS documentation: https://www.census.gov/programs-surveys/acs/microdata/documentation.html
- 2024 ACS PUMS documentation and data dictionary: https://www.census.gov/programs-surveys/acs/microdata/documentation/2024.html
- IPUMS: https://www.ipums.org/projects
- Nemotron-Personas-USA: https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA

### 5. Person-Situation Interaction and Simulation Grounding

For simulation, persona attributes should not be treated as static labels that mechanically determine behavior. Behavior emerges from interaction between:

- stable dispositions;
- values and goals;
- life context;
- social role;
- prior experience;
- current environment;
- task framing;
- interaction history.

Mapping to our schema:

- all top-level categories;
- especially `Domain-Specific Overlays`;
- future interaction-state or environment-conditioned persona modules.

Why it matters:

This lets us separate base persona attributes from task-specific overlays. For example, a finance simulation needs risk tolerance, numeracy, financial stress, trust, and time horizon; an education simulation needs self-efficacy, learning style, motivation, prior knowledge, and anxiety.

Sources:

- SCOPE paper: https://arxiv.org/html/2601.07110v2
- SCOPE dataset: https://huggingface.co/datasets/Salesforce/SCOPE-Persona

## Proposed Top-Level Schema

### 1. Demographics & Population Grounding

Purpose:

Ground the persona in population-level variables and social position.

Example subcategories:

- age;
- gender;
- race / ethnicity;
- location;
- language;
- education level;
- household structure;
- citizenship / migration background;
- income bracket;
- occupation class.

Primary grounding:

- Census / ACS PUMS / IPUMS;
- Nemotron;
- OASIS;
- SCOPE demographic facet.

### 2. Life Context & Constraints

Purpose:

Capture the practical conditions that shape what a person can do.

Example subcategories:

- physical and health characteristics;
- financial constraints;
- time constraints;
- housing context;
- family / caregiving responsibilities;
- technology access;
- mobility constraints;
- work context;
- education context.

Primary grounding:

- DeepPersona physical / health category;
- Census / ACS;
- GSS;
- domain-specific surveys.

### 3. Personality Traits

Purpose:

Capture stable psychological dispositions.

Example subcategories:

- Big Five domains;
- HEXACO domains;
- selected Facet MAP facets;
- selected IPIP scales;
- emotional tendencies;
- interpersonal disposition.

Primary grounding:

- Big Five / BFI-2;
- HEXACO;
- Facet MAP;
- IPIP;
- SCOPE Big Five facet.

### 4. Values, Goals & Motivations

Purpose:

Capture what the person cares about and what they are trying to optimize for.

Example subcategories:

- Schwartz values;
- life goals;
- achievement orientation;
- security orientation;
- autonomy;
- benevolence;
- tradition;
- self-direction;
- short-term and long-term goals.

Primary grounding:

- Schwartz values;
- SCOPE values facet;
- PrimeX;
- WVS / ESS.

### 5. Worldview, Beliefs & Attitudes

Purpose:

Capture broader interpretations of society, institutions, morality, and the world.

Example subcategories:

- political orientation;
- institutional trust;
- religiosity;
- moral beliefs;
- social issue attitudes;
- environmental concern;
- primal world beliefs;
- optimism / pessimism about society.

Primary grounding:

- WVS;
- GSS;
- PrimeX;
- Pew-style public opinion surveys.

### 6. Cognitive & Capability Profile

Purpose:

Capture what the person knows, can do, and how they process information.

Example subcategories:

- domain expertise;
- literacy;
- numeracy;
- digital literacy;
- language proficiency;
- learning style;
- decision style;
- need for cognition;
- problem-solving style;
- communication skill.

Primary grounding:

- DeepPersona education / learning category;
- Nemotron skills;
- OECD PIAAC;
- CEFR;
- DigComp;
- IPIP / Facet MAP for selected cognitive styles.

### 7. Behavioral Patterns & Preferences

Purpose:

Capture routines, habits, tastes, and repeated behavior.

Example subcategories:

- hobbies and interests;
- lifestyle preferences;
- daily routine;
- media consumption;
- shopping behavior;
- travel preference;
- food / culinary preference;
- sports / fitness behavior;
- communication behavior;
- technology use.

Primary grounding:

- DeepPersona hobbies, lifestyle, routine, and media categories;
- Nemotron sports / arts / travel / culinary / hobbies fields;
- SCOPE behavioral patterns facet;
- GSS / WVS behavior items.

### 8. Social Identity, Relationships & Community

Purpose:

Capture the social groups, roles, relationships, and communities that shape identity and behavior.

Example subcategories:

- cultural background;
- community belonging;
- family relationships;
- friendship network;
- workplace role;
- group identity;
- social network structure;
- civic participation.

Primary grounding:

- Social Identity Theory;
- DeepPersona cultural / relationship categories;
- Nemotron cultural background;
- GSS / WVS civic and social trust items;
- SCOPE sociodemographic behavior.

### 9. Narrative Identity & Life History

Purpose:

Capture the person's self-story, formative experiences, and meaning-making.

Example subcategories:

- personal story;
- formative events;
- turning points;
- self-description;
- aspirations;
- life themes;
- identity change over time.

Primary grounding:

- McAdams narrative identity theory;
- SCOPE identity narratives;
- DeepPersona life story and background.

### 10. Domain-Specific Overlays

Purpose:

Add attributes needed for specific simulation tasks without bloating the core schema.

Example modules:

- finance persona;
- health persona;
- education persona;
- recommender persona;
- political survey persona;
- workplace persona;
- media / social platform persona.

Primary grounding:

- domain-specific benchmarks;
- survey sources;
- task-specific literature;
- application requirements.

## DeepPersona Subcategory Mapping

DeepPersona's 12 top-level categories are useful as subcategory coverage, not as our final top-level schema.

| DeepPersona category | Where it maps in our schema | Notes |
|---|---|---|
| Demographic Information | Demographics & Population Grounding | Direct match. |
| Physical and Health Characteristics | Life Context & Constraints; Domain-Specific Overlays | Health should be a strong subcategory, especially for health simulations. |
| Psychological and Cognitive Aspects | Personality Traits; Cognitive & Capability Profile | We split personality and cognition because they have different theoretical bases. |
| Cultural and Social Context | Social Identity, Relationships & Community; Narrative Identity & Life History | Useful for cultural grounding and lived context. |
| Relationships and Social Networks | Social Identity, Relationships & Community | Direct match. |
| Career and Work Identity | Life Context & Constraints; Cognitive & Capability Profile; Domain-Specific Overlays | Can become a professional identity submodule. |
| Education and Learning | Demographics & Population Grounding; Cognitive & Capability Profile; Life Context & Constraints | Education is both background and capability. |
| Hobbies, Interests, and Lifestyle | Behavioral Patterns & Preferences | Direct match. |
| Lifestyle and Daily Routine | Behavioral Patterns & Preferences | Direct match. |
| Core Values, Beliefs, and Philosophy | Values, Goals & Motivations; Worldview, Beliefs & Attitudes | We split values/goals from beliefs/attitudes. |
| Emotional and Relational Skills | Personality Traits; Cognitive & Capability Profile; Social Identity, Relationships & Community | Should be added as an explicit subcategory. |
| Media Consumption and Engagement | Behavioral Patterns & Preferences; Domain-Specific Overlays | Important for social simulation and recommender systems. |

## Attribute Construction Plan

### Step 1: Aggregate Candidate Pool

Collect candidate attributes from:

- Yuexing's 1K attributes;
- SCOPE;
- DeepPersona;
- Nemotron;
- PersonaHub;
- OASIS;
- PrimeX;
- WVS / GSS / ESS / Pew;
- Big Five / HEXACO / Facet MAP / IPIP;
- domain-specific benchmarks.

Output:

- a large candidate attribute pool;
- source metadata;
- initial category assignment.

### Step 2: Normalize

For each attribute, normalize:

- name;
- definition;
- category and subcategory;
- data type;
- allowed values or scale;
- aliases;
- source;
- theoretical basis;
- license notes;
- application relevance.

### Step 3: Deduplicate and Categorize

Merge near-duplicates and preserve aliases.

Examples:

- `political_leaning`, `political_orientation`, and `political_affiliation` should be inspected and either merged or separated by definition.
- `risk_aversion`, `risk_tolerance`, and `sensation_seeking` should be related but not automatically merged.
- `openness`, `curiosity`, `intellectual_curiosity`, and `need_for_cognition` should be graph-linked but not collapsed without checking theoretical meaning.

### Step 4: Grounding and Evidence

Each retained attribute should have at least one grounding source:

- validated psychological instrument;
- large-scale social survey;
- persona dataset;
- benchmark;
- domain literature;
- official population source.

Evidence level can be marked as:

- High: validated psychological scale or official survey variable;
- Medium: used in a peer-reviewed dataset / benchmark;
- Low: LLM-mined or generated attribute that still needs validation.

### Step 5: Attribute Graph

Construct a graph with relation types:

- `synonym_of`;
- `parent_of`;
- `subtype_of`;
- `correlates_with`;
- `negatively_correlates_with`;
- `conflicts_with`;
- `depends_on`;
- `domain_specific_to`;
- `grounded_by`.

This graph will help with deduplication, conflict detection, and domain-specific persona assembly.

## Recommended Output Structure

The final persona attribute system should have three layers:

### Core Persona Schema

Small set of cross-domain, high-value attributes.

Purpose:

- stable base persona;
- easy to inspect;
- useful across most simulations.

### Extended Attribute Pool

Large library of optional attributes, including fine-grained personality facets, beliefs, preferences, routines, and social context.

Purpose:

- richer personas;
- long-tail diversity;
- source-grounded expansion.

### Domain Modules

Task-specific attribute bundles.

Examples:

- finance: risk tolerance, financial literacy, time horizon, debt stress, trust in institutions;
- education: prior knowledge, learning style, self-efficacy, motivation, academic anxiety;
- health: health status, health literacy, care access, medication adherence, risk perception;
- recommender: taste profile, media consumption, novelty seeking, budget, brand sensitivity;
- political / social survey: ideology, institutional trust, religiosity, civic participation, social issue attitudes.

## Practical Rule

Top-level schema should be theory-driven.

Subcategories should be coverage-driven.

Individual attributes should be evidence-grounded.

DeepPersona helps with coverage. SCOPE helps with LLM-persona structure. Big Five, HEXACO, Facet MAP, Schwartz, WVS, GSS, PrimeX, Census, and IPUMS help with grounding.

## Short Summary

Our persona schema is based on:

- McAdams for overall personality architecture;
- Big Five / HEXACO / Facet MAP / IPIP for personality traits;
- Schwartz / WVS / GSS / PrimeX for values, beliefs, worldview, and attitudes;
- Social Identity Theory / Census / IPUMS / Nemotron for demographics and social context;
- Person-situation interaction / SCOPE for simulation logic.

DeepPersona should be used as a rich source of subcategories and candidate attributes, but not as the final theoretical taxonomy.
