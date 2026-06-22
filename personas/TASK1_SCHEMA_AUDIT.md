# Task 1 Real-Data Construction Requirements

Tracking issue: https://github.com/MatrAIx-ai/MatrAIx/issues/66

Last checked: 2026-06-22 on `main`.

## Scope

This is a small Task 1 note focused on real-data persona construction and cleaning. It does not redesign the schema, add dimensions, generate personas, or modify pipeline code.

## Current Facts

- `personas/dimensions+new.json` has `1339` dimensions across `39` categories.
- `personas/dimension_constraints.json` has `115` incompatibility rules.
- `personas/validators/schema_validator.py` validates dimension file structure.
- ACS PUMS variables are curated, but no weighted-resampling demographic skeleton generator was found on `main`.
- Amazon review inference is active in #64 and `origin/amazon-evidence-profile-modal`.

## Existing Definitions to Reuse

- `personas/CONTRIBUTION_GUIDE.md` defines `source_origin` metadata for dimension provenance.
- Issue #64 proposes schema-mapped inference outputs with `dimension_id`, `value`, `confidence`, `evidence_review_ids`, `evidence_quotes`, and `reasoning`.
- Issue #64 also requires temporal split, text-rich evidence selection, deduped reviews, and stronger evidence validation.

## Requirements

### 1. Real-data records must preserve provenance

Each real-data-derived persona record or intermediate profile should keep:

- source name and source id;
- source time window or reference year;
- hashed source record or user id;
- evidence ids or source row ids;
- schema dimension id and value;
- confidence or support level;
- omitted or unsupported fields.

### 2. Cleaning must happen before narrative generation

Before LLM narrative expansion, records should pass:

- schema value validation against `dimensions+new.json`;
- incompatibility checks against `dimension_constraints.json`;
- evidence/provenance presence checks;
- temporal split checks for behavioral data;
- sensitive-attribute guardrails for demographics, health, family, identity, and private traits.

### 3. Initial real-data paths should stay small

The nearest practical paths are:

- ACS PUMS: demographic skeleton construction.
- Amazon reviews: behavior-grounded evidence profiles.

This issue only records shared requirements for those paths. Implementation should happen in separate follow-up issues or PRs.

## Minimal Sample

```json
{
  "record_id": "amazon_user_profile_0001",
  "source_origin": {
    "source_id": "amazon_reviews_2023",
    "source_name": "Amazon Reviews 2023",
    "source_type": "review_history",
    "time_window": "2018-2023",
    "source_record_hash": "sha256:..."
  },
  "construction_split": {
    "persona_construction": "2018-2021",
    "evaluation_holdout": "2022-2023"
  },
  "inferred_attributes": [
    {
      "dimension_id": "topic_books",
      "value": "Passionate",
      "confidence": 0.86,
      "evidence_ids": ["review_123", "review_456"],
      "evidence_quotes": ["I read this series every year"],
      "reasoning": "Repeated long-form book reviews support a strong books interest."
    }
  ],
  "unsupported_fields": [
    {
      "dimension_id": "demo_marital_status",
      "reason": "No direct evidence; do not infer from product categories."
    }
  ]
}
```

## Acceptance Criteria

This issue is complete when this note:

- states the minimal provenance and evidence requirements;
- states the minimal cleaning requirements before generation;
- includes one concrete sample record;
- references the existing provenance and Amazon inference discussions;
- does not change schema data, generated persona files, or pipeline code.

## Follow-Up Candidates

1. Prototype a 100-row ACS PUMS demographic skeleton.
2. Add a schema-conformance cleaner for real-data-derived profiles.
3. Add evidence-quote validation for Amazon review inference outputs.
4. Define a temporal split protocol for behavior-grounded data.
5. Decide which cleaned fields should be included in PersonaBench v1 prompts.