# Task 1 Data Construction Readiness Audit

Last checked: 2026-06-22 after `git fetch --all --prune` and `git pull --ff-only` on `main`.
Tracking issue: https://github.com/MatrAIx-ai/MatrAIx/issues/66

This is a small, self-contained audit for Persona Task 1. It does not try to redesign the whole schema. The goal is to identify the first concrete steps we can take toward real-data-based persona construction and cleaning.

## Current Facts

- `personas/dimensions+new.json` has schema version `2.0`, `targetDimensions=1339`, and `1339` actual dimensions.
- The current schema has `39` categories.
- `personas/dimension_constraints.json` records `115` sparse incompatibility rules.
- `personas/validators/schema_validator.py` validates required dimension fields and deprecated-field removal.
- ACS PUMS variables are curated as source material, but no ACS PUMS weighted-resampling skeleton generator was found on `main`.
- Amazon review inference work is active in #64 and `origin/amazon-evidence-profile-modal`, with emphasis on evidence profiles, temporal split, and stronger validation.

## What Task 1 Asks For

From `personas/PLAN.md`, the relevant Task 1 steps are:

1. Create a population-grounded demographic skeleton from real data.
2. Coarsen fields only to behaviorally meaningful levels.
3. Expand structured skeletons into narrative personas without overriding facts.
4. Emit schema-conformant personas with provenance.
5. Validate marginal fidelity, joint fidelity, diversity, and behavioral sensitivity.

## What We Can Do Now

We can make progress without changing the schema or generating large persona files.

### 1. Define a minimal real-data record contract

For any real-data source, each constructed persona or intermediate profile should keep:

- `source_id` and source name;
- source time window or reference year;
- hashed source record/user id;
- selected evidence ids or row ids;
- schema dimension ids and values;
- confidence or support level;
- notes for omitted or unsupported fields.

### 2. Define cleaning checks before generation

Before LLM narrative expansion, real-data-derived profiles should pass:

- schema value validity: every value must match `dimensions+new.json`;
- incompatibility checks from `dimension_constraints.json`;
- provenance presence for every inferred field;
- temporal split for behavior data so construction evidence does not leak into evaluation;
- sensitive-attribute guardrails so demographics, health, family, identity, or private traits are not inferred from weak stereotypes.

### 3. Pick a small first real-data path

The smallest useful paths are:

- ACS PUMS for demographic skeletons, because Task 1 explicitly calls for it;
- Amazon reviews for behavior-grounded evidence profiles, because #64 already defines concrete review-selection and validation concerns.

This audit does not choose between them. It only records that both paths need the same basic construction contract and cleaning checks.

## Acceptance Criteria for This Issue

This issue is complete when the audit note:

- records the current schema and validation facts from `main`;
- summarizes the Task 1 steps that matter for real-data construction;
- defines a minimal real-data record/provenance contract;
- lists practical cleaning checks that can be applied before generation;
- identifies ACS PUMS and Amazon reviews as the nearest concrete real-data paths;
- does not change `dimensions+new.json`, generated persona YAML files, curation scripts, or inference pipelines.

## Candidate Follow-Up Tasks

These should be separate issues or PRs, not requirements for this audit.

1. Implement a 100-row ACS PUMS demographic skeleton prototype.
2. Add a small schema-conformance cleaner for real-data-derived profiles.
3. Add evidence-quote validation for Amazon review inference outputs.
4. Define a small temporal split protocol for behavior-grounded data.
5. Decide which cleaned fields should be included in PersonaBench v1 prompts.

## Not a Blocker

`personas/Jun20_1k_persona_description` has inconsistent artifacts on `main`: `INDEX.md` describes 1,000 individual YAML files, while `README.md` and `personas.yaml` describe a 10-persona combined sample and `origin/main` has zero `ID*.yaml` files. The 1,000 individual YAMLs exist on `origin/codex/wiki-persona-seed-pipeline` and `origin/environment/oasis`.

This should be reconciled separately, but it does not block real-data construction readiness.
