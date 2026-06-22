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
- `origin/amazon-evidence-profile-modal` adds `amazon_review_evidence_mapping.json`, whose broad evidence categories include `product_interests`, `consumption_preferences`, `expertise_signals`, `behavioral_habits`, `decision_style`, `values_and_motivations`, `explicit_self_statements`, and `communication_style`.

## Sources Used for Local ACS/PUMS Prototype

- Task 1 plan: `personas/PLAN.md`, especially the ACS PUMS weighted-resampling skeleton section.
- ACS PUMS access page: https://www.census.gov/programs-surveys/acs/microdata/access.html
- ACS PUMS documentation page: https://www.census.gov/programs-surveys/acs/microdata/documentation.html
- Wyoming 2024 ACS 1-Year person records: `csv_pwy.zip` from https://www2.census.gov/programs-surveys/acs/data/pums/2024/1-Year/
- Wyoming 2024 ACS 1-Year housing records: `csv_hwy.zip` from the same Census FTP directory.
- 2024 ACS PUMS data dictionary: `PUMS_Data_Dictionary_2024.csv`.
- 2024 ACS PUMS code lists: `ACSPUMS2024CodeLists.xls`.

These raw Census files are stored only under `personas/existing_data_curation/raw/acs_pums_2024_1yr/`, which is gitignored.

Local prototype status:

- downloaded one state, Wyoming, for a small local test;
- sampled 1,000 age-13+ person records with `PWGTP` weighted sampling with replacement;
- joined person records to housing records by `SERIALNO`;
- generated local ignored files `wy_1000_weighted_skeleton.jsonl` and `wy_1000_weighted_skeleton_summary.json`;
- no narrative expansion was run;
- mappings are draft only and should be reviewed before reuse.

## Needs Review

The local prototype intentionally marks uncertain mappings instead of treating them as final. These are the current review points:

| Area | Current prototype behavior | Why review is needed |
| --- | --- | --- |
| `urbanicity` | Left unsupported for all 1,000 records. | `PUMA` alone is not enough; needs a PUMA-to-urbanicity or similar geographic crosswalk. |
| `domain` | Draft mapped from broad `INDP` industry ranges. | Industry ranges are coarse and may not match MatrAIx domain semantics. |
| `role_function` | Draft mapped from broad `OCCP` occupation ranges. | Occupation codes need a reviewed SOC/occupation crosswalk before use. |
| `demo_children_count` | Draft mapped from housing `NOC`. | Household children count may not equal the sampled person's own children; derivation needs care. |
| `primary_language` | Draft mapped from `LANP`, `LANX`, and household `HHL`. | Some `LANP` codes are not in MatrAIx language values; household language may not equal person language. |
| Sensitive demographics | Mapped only from explicit ACS fields. | Downstream behavior-grounded sources should not infer these from weak behavioral signals. |

Recommended reviewers: Task 1 schema owners for domain semantics, ACS/PUMS owner for Census variable interpretation, and Amazon/behavior-grounded owners for evidence and leakage requirements.

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

This sample is aligned with the `source_origin` pattern in `CONTRIBUTION_GUIDE.md` and the Amazon review inference shape discussed in #64 / `origin/amazon-evidence-profile-modal`.

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
  "evidence_profile": {
    "evidence_items": [
      {
        "evidence_id": "ev_001",
        "category": "product_interests",
        "claim": "The reviewer repeatedly engages with books and long-form reading.",
        "review_ids": ["review_123", "review_456"],
        "evidence_quotes": ["I read this series every year"],
        "confidence": 0.86
      }
    ],
    "unsupported_or_blocked": [
      {
        "topic": "marital status",
        "reason": "No explicit self-statement in review evidence."
      }
    ]
  },
  "inferred_attributes": [
    {
      "dimension_id": "topic_books",
      "value": "Passionate",
      "confidence": 0.86,
      "evidence_review_ids": ["review_123", "review_456"],
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

## Local Prototype Gaps

The local Wyoming prototype still leaves these fields unsupported or partially unsupported:

- `urbanicity`: unsupported for all 1,000 records; needs a PUMA-to-urbanicity crosswalk.
- `domain`: unsupported for 236 records; current INDP-based mapping is broad and draft.
- `role_function`: unsupported for 226 records; current OCCP-based mapping is broad and draft.
- `demo_children_count`: unsupported for 37 records; housing/person derivation needs review.
- `primary_language`: unsupported for 12 records; unmapped `LANP` codes need review against MatrAIx language values.