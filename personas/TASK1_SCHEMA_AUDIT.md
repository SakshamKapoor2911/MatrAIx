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

## Reviewable Acceptance Criteria

The tracking issue should not require every downstream implementation to land in the first PR. A practical review path is split into phases.

### Phase A: Documentation Alignment

The first PR should be considered complete when:

- this audit note is merged under `personas/`;
- it records the current schema facts, including 1,339 dimensions and 39 categories;
- it lists all 39 current categories with counts;
- it proposes a reviewable mapping from categories to 4-5 major aspects;
- it calls out unresolved classification questions rather than hiding them;
- it makes no changes to `dimensions+new.json`, generated persona artifacts, or pipeline code.

### Phase B: Category Decision Artifact

A follow-up PR or update should be considered complete when there is a single source of truth, in Markdown, JSON, or CSV, with one row per current category and at least these fields:

- `category`;
- `major_aspect`;
- `schema_role`: one of `core`, `domain_overlay`, `dynamic_state`, `source_provenance`, or `review_bucket`;
- `prompt_inclusion`: one of `default`, `task_dependent`, `never_direct`, or `review`;
- `rationale`;
- `owner_or_reviewer`.

This artifact should explicitly resolve at least these categories or groups: `External: Datasets`, `State: Emotional`, `Health:*`, `Expertise:*`, `Learning:*`, and `Skills:*`.

### Phase C: ACS/PUMS Skeleton Scope

The ACS/PUMS work should be considered scoped when the team has documented:

- reference population and year;
- source access path, such as `folktables` or Census PUMS files;
- weighted-resampling key, including `PWGTP` or the relevant person weight;
- output fields for the demographic skeleton;
- provenance fields, including source, year, source row hash, and sampling weight;
- a 100-row prototype target or a linked follow-up implementation issue.

### Phase D: Validation and Behavioral Sensitivity Scope

The validation plan should be considered scoped when the team has documented:

- marginal checks for age, sex/gender, education, occupation, income, marital status, household, geography, language, and nativity/citizenship;
- at least two joint checks, such as age x education and occupation x income;
- a tiny behavioral-sensitivity probe with 3-5 tasks, 3-5 demographic axes, and cheap metrics;
- how the result affects coarsening decisions and PersonaBench prompt inclusion.

## Minimal Next Steps

1. Merge or review Phase A as a documentation-only PR.
2. Decide whether Phase B should be a Markdown table in this document or a machine-readable mapping file.
3. Assign owner(s) for Phase C ACS/PUMS skeleton scope.
4. Assign owner(s) for Phase D validation and behavioral-sensitivity scope.
5. Revisit issue #66 after Phase B to decide whether to split implementation into separate issues.

## Not a Blocker

`personas/Jun20_1k_persona_description` has inconsistent artifacts on `main`: `INDEX.md` describes 1,000 individual YAML files, while `README.md` and `personas.yaml` describe a 10-persona combined sample and `origin/main` has zero `ID*.yaml` files. The 1,000 individual YAMLs exist on `origin/codex/wiki-persona-seed-pipeline` and `origin/environment/oasis`.

This should be reconciled, but it does not block Task 1. Task 1 can proceed from the schema and grounding audit above.