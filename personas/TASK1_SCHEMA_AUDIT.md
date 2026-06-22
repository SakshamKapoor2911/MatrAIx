# Task 1 Schema Audit

Last checked: 2026-06-22 after `git fetch --all --prune` and `git pull --ff-only` on `main`.

Tracking issue: https://github.com/MatrAIx-ai/MatrAIx/issues/66

This note summarizes the current status of Persona Task 1: Schema & Domain Design. It is a small coordination artifact, not a replacement for `PLAN.md` or the schema files.

## Current Facts

- `personas/dimensions+new.json` is on schema version `2.0`.
- `targetDimensions` is `1339` and the actual dimension count is `1339`.
- The current schema has `39` distinct categories.
- `personas/dimension_constraints.json` exists and records `115` sparse incompatibility rules.
- `personas/validators/schema_validator.py` exists and validates required dimension fields plus deprecated field removal.
- ACS PUMS is present as a curated source through `personas/existing_data_curation/manifests/acs_pums_curated_variables.json` and `personas/attribute_pool/scripts/build_acs_curated_variables.py`.
- No ACS PUMS weighted-resampling demographic skeleton generator was found on `main`.

## Task 1 Intent

Task 1 asks the team to settle the schema before downstream construction, filtering, and benchmarking. The practical requirements are:

- organize personas around 4-5 major aspects, including basic demographics;
- keep attributes tied to target domains and tasks instead of over-exploring;
- build each domain slice with a small owner group;
- assemble personas by combining slices into one profile;
- reuse prior attribute sets where possible;
- prototype a population-grounded demographic slice from ACS PUMS using weighted resampling;
- validate marginal fidelity, joint fidelity, diversity/collapse, and behavioral sensitivity.

## Current Category Inventory

| Category | Count |
| --- | ---: |
| Behavior: Habits | 30 |
| Behavior: Preferences | 34 |
| Behavior: Time | 3 |
| Behavior: Work | 2 |
| Demographic: Core | 27 |
| Demographic: Cultural | 2 |
| Demographic: Family | 2 |
| Demographic: Geographic | 1 |
| Demographic: Geography | 1 |
| Demographic: Life Events | 25 |
| Expertise: Domains | 144 |
| Expertise: Skills | 64 |
| External: Datasets | 94 |
| Health: Fitness | 2 |
| Health: Lifestyle | 2 |
| Health: Physical | 25 |
| Interests: Culture | 74 |
| Interests: Food | 35 |
| Interests: Hobbies | 50 |
| Interests: Media | 81 |
| Interests: Sports | 40 |
| Interests: Topics | 78 |
| Learning: Academic | 38 |
| Learning: Style | 1 |
| Linguistic: Communication | 37 |
| Linguistic: Language | 53 |
| Personality: Big Five | 56 |
| Personality: Character | 34 |
| Personality: MBTI | 2 |
| Personality: Relationships | 4 |
| Professional: Career | 6 |
| Professional: Industry | 52 |
| Professional: Role | 1 |
| Risk & Decision | 7 |
| Skills: Programming | 44 |
| Skills: Tools | 69 |
| State: Emotional | 5 |
| Values & Motivation | 46 |
| Worldview: Beliefs | 68 |

## Draft Mapping to 5 Major Aspects

This is a working map for discussion. Some categories can belong to more than one aspect depending on the task; those should be marked as core, overlay, or source-only before large-scale generation.

| Major aspect | Candidate categories |
| --- | --- |
| Demographics & Background | Demographic: Core; Demographic: Cultural; Demographic: Family; Demographic: Geographic; Demographic: Geography; Demographic: Life Events; Professional: Career; Professional: Industry; Professional: Role |
| Psychology & Personality | Personality: Big Five; Personality: Character; Personality: MBTI; Personality: Relationships; Values & Motivation; Worldview: Beliefs; Risk & Decision; State: Emotional |
| Communication & Cognition | Linguistic: Communication; Linguistic: Language; Learning: Academic; Learning: Style; Expertise: Domains; Expertise: Skills; Skills: Programming; Skills: Tools |
| Preferences & Interests | Interests: Culture; Interests: Food; Interests: Hobbies; Interests: Media; Interests: Sports; Interests: Topics; Behavior: Preferences; Health: Fitness; Health: Lifestyle |
| Behavior & History | Behavior: Habits; Behavior: Time; Behavior: Work; Health: Physical; Demographic: Life Events; External: Datasets |

Open mapping questions:

- `External: Datasets` should likely be treated as a source/provenance layer or review bucket, not a final persona aspect.
- `Health: Physical` can be life context, preference/behavior context, or a health-domain overlay depending on release scope.
- `Expertise: Domains`, `Learning: Academic`, and `Skills:*` need a core-vs-overlay decision for task-specific benchmarks.
- `State: Emotional` may be a dynamic interaction-state field rather than a stable persona attribute.

## What Looks Done

- A rich schema exists and is internally valid at the required-field level.
- The current dimension count matches the public PersonaBench v1 number: 1,339.
- Major aspect language exists in `personas/README.md`.
- A first set of incompatibility constraints exists.
- ACS PUMS variables have been curated as candidate grounding attributes.

## Main Gaps

- No single source-of-truth map from the 39 current categories to the 4-5 major aspects.
- No explicit core-vs-domain-overlay designation.
- No ACS PUMS weighted-resampling skeleton generator on `main`.
- No marginal or joint fidelity report for a demographic skeleton.
- No behavioral-sensitivity probe tying coarsening decisions to observed agent behavior.
- No provenance contract for generated skeletons beyond source metadata in dimensions and curation docs.

## Minimal Next Steps

1. Confirm the 5 major aspects and approve or edit the draft category mapping above.
2. Mark each category as one of: core, domain overlay, dynamic state, source/provenance, or review bucket.
3. Prototype a 100-row ACS PUMS demographic skeleton with provenance fields, even before full narrative generation.
4. Run simple marginal checks for the prototype: age, sex/gender, education, occupation, income, marital status, household, geography, language, nativity/citizenship.
5. Select a tiny behavioral-sensitivity probe with 3-5 tasks and 3-5 demographic axes to test whether current binning is behaviorally meaningful.

## Not a Blocker

`personas/Jun20_1k_persona_description` has inconsistent artifacts on `main`: `INDEX.md` describes 1,000 individual YAML files, while `README.md` and `personas.yaml` describe a 10-persona combined sample and `origin/main` has zero `ID*.yaml` files. The 1,000 individual YAMLs exist on `origin/codex/wiki-persona-seed-pipeline` and `origin/environment/oasis`.

This should be reconciled, but it does not block Task 1. Task 1 can proceed from the schema and grounding audit above.