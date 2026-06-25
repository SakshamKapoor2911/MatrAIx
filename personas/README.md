# 🧬 Team 1: Persona

> Part of [MatrAIx](../README.md). The Persona team builds the foundation of the MatrAIx simulated population.

This team focuses on constructing, curating, validating, and benchmarking large-scale persona datasets.

## 🎯 Goals

The main goal is to build a diverse and scalable persona database, tentatively called:

```text
MatrAIxPersona-8B
```

This database will contain synthetic and semi-synthetic persona profiles that can be used to instantiate persona-affiliated agents.

## 🏗️ Persona Construction

Personas may be constructed through multiple complementary approaches:

1. **Fully synthetic persona generation.** Generate diverse persona profiles from scratch using LLMs, structured templates, demographic priors, and controlled diversity constraints.

2. **Synthetic personas seeded by real human profiles.** Use real-world human profile distributions, public demographic statistics, survey data, or anonymized behavioral patterns as seeds for generating more realistic synthetic personas.

3. **Personas built from existing persona datasets.** Adapt, clean, expand, and normalize existing persona-style datasets into the MatrAIx format.

4. **Domain-specific persona generation.** Build persona subsets for specific application domains, such as education, finance, gaming, healthcare, e-commerce, developer tools, AI assistants, or enterprise software.

5. **Longitudinal personas with memory.** Extend static persona profiles into persistent agents with evolving memory, preferences, and behavioral history.

## 📦 Core Artifacts

The Persona team maintains three main artifacts: the full database and two high-quality core subsets derived from it.

### 🧱 Persona Structure

Rather than a flat list of traits, we organize each persona around a few **major aspects**, and give each aspect its own set of attributes / dimensions. A working starting point is four to five aspects:

| Aspect | Example dimensions / attributes |
|--------|---------------------------------|
| 👤 **Demographics & Background** | age, gender, location, occupation, education, income bracket, household, life stage, cultural background |
| 🧠 **Psychology & Personality** | Big Five traits, risk tolerance, openness to new tools, patience, skepticism, motivation drivers, values |
| 💬 **Communication & Cognition** | tone, verbosity, formality, language/literacy level, attention span, technical fluency, learning style |
| ❤️ **Preferences & Interests** | hobbies, brand affinities, product likes/dislikes, price sensitivity, aesthetic taste, content preferences |
| 🔁 **Behavior & History** | decision-making style, purchase/usage patterns, churn triggers, daily routine, memory & past interactions |

The exact aspects and dimensions are an open design question (and a contribution area). The goal is a schema rich enough that an agent conditioned on a persona behaves like a coherent, complete individual — not a one-line caricature.

### 🗃️ 1. MatrAIxPersona-8B

The full persona database.

Each persona should ideally include:

- a unique persona ID
- structured metadata
- a natural-language profile
- behavioral traits
- communication style
- preference dimensions
- domain-specific attributes
- optional memory fields
- optional social graph information

Example format (abbreviated — a real persona is much richer across all aspects):

```markdown
# Persona ID: mx_persona_000001

## Metadata
locale: en-US | segment: graduate_student | created: 2026-05-10
tags: [productivity, ai-tools, indie-games, fitness]

## Demographics & Background
- Age: 24 | Gender: female | Location: Seattle, WA
- Occupation: graduate student (HCI) | Education: pursuing MSc
- Income: low / student budget | Household: shared apartment, 2 roommates
- Life stage: early-career, time-rich but cash-constrained
- ...

## Psychology & Personality
- Big Five: high openness, high conscientiousness, moderate introversion
- Risk tolerance: low–moderate | Skeptical of marketing claims
- Motivated by: saving time, learning, feeling in control
- Values: privacy, transparency, evidence over hype
- ...

## Communication & Cognition
- Tone: direct, concise, detail-oriented
- Technical fluency: high | Reads docs before asking for help
- Attention span: short for onboarding, long for things she cares about
- Learning style: hands-on, example-driven
- ...

## Preferences & Interests
- Likes: clean interfaces, keyboard shortcuts, dark mode, free trials
- Dislikes: long onboarding flows, forced account creation, paywalls up front
- Interests: productivity tools, AI assistants, indie games, fitness tracking
- Price sensitivity: high | Prefers freemium with clear upgrade value
- ...

## Behavior & History
- Decision style: compares 2–3 options before adopting anything
- Adoption: tries new tools if setup is < 5 minutes
- Churn triggers: too many accounts, unclear value, intrusive notifications
- Past interactions: abandoned 2 note-taking apps during signup last month
- ...

## Goals & Current Context
- Looking for a lightweight tool to organize research notes
- Recently switched laptops; wary of re-setting up her whole workflow
- ...
```

### 🎓 2. MatrAIxPersonaTrain

A high-quality core subset for model training and agent development.

This subset should contain personas that are:

- internally consistent
- sufficiently detailed
- diverse across key dimensions
- easy to parse and condition on
- useful for training persona-following models
- suitable for fine-tuning, preference learning, or agent behavior modeling

Possible uses:

- persona-conditioned model training
- synthetic dialogue generation
- user behavior modeling
- agent instruction tuning
- memory and self-consistency training

### 📊 3. MatrAIxPersonaBench

A benchmark subset for evaluating **persona simulation quality** — i.e. how well an agent conditioned on a persona actually *behaves* in line with that persona's profile.

The core idea: for a given persona, we **generate tasks that target specific aspects/dimensions of the profile** (demographics, personality, preferences, behavior, etc.), have the agent perform them, and check whether the resulting behavior is consistent with what the profile implies. Each profile attribute becomes something testable.

Each benchmark persona should include:

- the persona profile
- a set of tasks, each tied to one or more profile aspects/dimensions
- the expected behavior or behavioral constraints implied by the profile
- automatic and/or human evaluation criteria (a "ground truth" derived from the profile)

The benchmark tests whether an agent can:

- **adhere to the profile** — its choices reflect the persona's stated preferences, values, and constraints
- preserve personality and communication style across contexts
- make decisions that are plausible for that specific persona
- avoid contradicting core persona facts (demographics, background, hard constraints)
- stay consistent across multi-turn interactions and different domains

Example benchmark task:

```markdown
Persona aspect tested: Preferences & Interests + Psychology (risk-averse, low financial literacy)

Persona:
A budget-conscious first-time investor with low financial literacy and
moderate risk aversion.

Task:
Evaluate two onboarding flows for a fintech app and choose one.

Expected behavior (derived from profile):
- Prefers the flow with clear, jargon-free explanations
- Expresses concern about risk and asks for educational guidance
- Is hesitant to commit money before understanding the product

Evaluation:
- adherence: did the choice and reasoning match the expected behavior?
- consistency: were preferences stable if asked again / rephrased?
- no contradiction: did it stay low-literacy and risk-averse throughout?
```

## 🤝 Contributing

- persona schema design
- persona generation pipelines
- persona validation tools
- domain-specific persona subsets
- persona consistency benchmarks

## 📥 Existing Data Curation

For curated ingestion scripts and manifests of external persona datasets (Nemotron, PersonaHub, OASIS, ML-PRIMEX), see [existing_data_curation/README.md](existing_data_curation/README.md).
