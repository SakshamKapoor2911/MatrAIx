# Candidate Pool Normalization Method

Last updated: 2026-06-19

## Purpose

This document explains the Step 2 normalization process for the persona attribute candidate pool.

Step 2 takes the raw extended candidate pool from Step 1 and converts heterogeneous source records into a consistent, reviewable schema. The goal is not to remove duplicates yet. The goal is to make each candidate easier to compare, deduplicate, categorize, ground, and connect in the later attribute graph.

Normalization is implemented in:

- `normalize_candidate_pool.py`

The normalized outputs are written to:

- `candidate_pool_outputs/normalized/candidate_pool_raw_extended_normalized.csv`
- `candidate_pool_outputs/normalized/candidate_pool_high_quality_normalized.csv`
- `candidate_pool_outputs/normalized/normalization_report.md`
- `candidate_pool_outputs/normalized/normalization_source_summary.csv`

ACS support files are produced by:

- `build_acs_curated_variables.py`
- `dataset/acs_pums/PUMS_Data_Dictionary_2024.csv`
- `dataset/acs_pums/acs_pums_curated_variables.csv`

## Input Files

The script reads:

- `candidate_pool_outputs/candidate_pool_raw_extended.csv`
- `candidate_pool_outputs/candidate_pool_high_quality.csv`

The raw extended file contains all candidates from Step 1. The high-quality file contains the curated subset used as the primary review pool.

## Output Principle

Normalization preserves every input row. It does not merge attributes.

Each row receives additional normalized fields:

- canonical label and name;
- normalized top-level category;
- normalized subcategory;
- inferred data type;
- measurement level;
- source family;
- quality tier;
- license risk;
- deduplication keys;
- aliases;
- review flags;
- application relevance.

This makes Step 3 easier because exact duplicates, near duplicates, aliases, conflicts, and related constructs can be detected with more consistent metadata.

## Why Normalize Before Deduplication

Different sources describe similar concepts in different forms.

Examples:

- `political_leaning`, `political_orientation`, and `party_affiliation` may be related but are not always identical.
- `risk_aversion`, `risk_tolerance`, and `sensation_seeking` are related risk constructs but should not be automatically merged.
- `openness`, `curiosity`, `intellectual_curiosity`, and `need_for_cognition` overlap conceptually but come from different theories and measurement traditions.

Normalization creates comparable labels, categories, source families, and dedup keys while preserving original source distinctions.

## Normalized Fields

### `canonical_label`

A cleaned version of the source label.

Examples:

- removes repeated suffixes such as `.1`;
- normalizes encoding artifacts where possible;
- preserves the human-readable wording.

### `canonical_name`

A machine-friendly snake_case identifier derived from `canonical_label`.

Example:

- `Political Orientation` -> `political_orientation`

### `normalized_primary_category`

The corrected top-level category using our 10-category persona schema:

1. Demographics & Population Grounding
2. Life Context & Constraints
3. Personality Traits
4. Values, Goals & Motivations
5. Worldview, Beliefs & Attitudes
6. Cognitive & Capability Profile
7. Behavioral Patterns & Preferences
8. Social Identity, Relationships & Community
9. Narrative Identity & Life History
10. Domain-Specific Overlays

### `normalized_subcategory`

A cleaned and source-aware subcategory.

Examples:

- `Facet MAP personality facets`
- `IPIP personality items`
- `Schwartz values`
- `sociodemographic attitudes`
- `domain labels and expertise areas`
- `hobbies interests and lifestyle`

### `normalized_definition`

A standardized definition. If the source already provides a useful definition, it is preserved. Otherwise, the script creates a light definition from the label, category, and subcategory.

### `normalized_data_type`

An inferred data type. Common values include:

- `likert_self_report_item`
- `psychometric_construct`
- `theory_construct`
- `ordinal_survey_item`
- `ordinal_or_binary_survey_item`
- `categorical`
- `multi_select`
- `free_text`
- `dataset_schema_field`
- `domain_label`
- `unknown_or_source_defined`

### `measurement_level`

The broad measurement type:

- `nominal`
- `ordinal`
- `construct`
- `free_text`
- `source_defined`

### `normalized_value_schema_json`

A JSON object describing the value structure where known.

For example, IPIP items are normalized as Likert-style self-report items with a standard agreement/accuracy scale.

Official survey variables without value labels are marked as source-defined and flagged for later codebook lookup.

### `source_family`

A broader source grouping:

- `psychometric`
- `official_population_survey`
- `official_survey`
- `research_dataset`
- `persona_dataset`
- `llm_mined`
- `local_project`
- `validated_theory`
- `other`

### `quality_tier`

Derived from the Step 1 inclusion tier:

- `A`: validated psychometric scale, official survey variable, or theory construct;
- `B`: peer-reviewed dataset, curated local schema, or dataset field;
- `C`: LLM-mined or automatically extracted candidate requiring review.

### `license_risk`

A coarse flag for downstream reuse risk:

- `low`
- `medium`
- `medium_high`
- `unknown`

This is not legal advice. It is a review signal.

### `dedup_key_strict`

A strict key based on normalized category and canonical label.

Use it for exact or near-exact duplicate detection.

### `dedup_key_loose`

A looser token-based key that removes common stopwords and sorts salient tokens.

Use it for candidate duplicate clusters that need human or semantic review.

### `alias_candidates_json`

A list of possible aliases derived from:

- original label;
- source-provided name;
- original source ID;
- canonical name.

### `review_flags_json`

Flags that indicate why a candidate needs special attention.

Common flags:

- `review_low_evidence_or_llm_mined`
- `review_deeppersona_auto_extraction`
- `domain_label_not_standalone_attribute`
- `domain_specific_not_core_by_default`
- `needs_value_schema_or_codebook_lookup`
- `auto_augmented_values_review`
- `label_too_generic_review`
- `free_text_should_be_structured_before_final_schema`

### `needs_review`

Boolean value derived from whether the row has any review flags.

### Boolean Helper Fields

The script also creates:

- `is_questionnaire_item`
- `is_construct`
- `is_dataset_field`
- `is_domain_label`
- `is_generated_or_mined`

These make filtering easier.

### `application_relevance`

A broad application signal, such as:

- `general_personality_and_behavior_simulation`
- `survey_social_science_policy_and_alignment`
- `motivation_preference_and_decision_simulation`
- `education_workflow_task_capability_simulation`
- `recommender_consumer_media_and_daily_behavior`
- `population_grounding_sampling_and_fairness_analysis`
- `domain_specific_module_selection`

## Source-Specific Normalization Rules

### Psychometric Sources

Sources:

- IPIP
- Facet MAP
- BFI-2
- HEXACO

Rules:

- map to `Personality Traits` by default;
- preserve psychometric source names;
- infer `likert_self_report_item` for IPIP items;
- infer `psychometric_construct` for scales, facets, and domains;
- assign high quality tier when the source is validated or public-domain psychometric material.

Exception:

- `Need for Cognition` can be treated as a cognitive style and may be cross-linked to personality in Step 3.

### Value and Motivation Sources

Sources:

- Schwartz Theory of Basic Values
- Self-Determination Theory

Rules:

- map to `Values, Goals & Motivations`;
- infer `theory_construct`;
- retain high evidence level.

### Official Survey Sources

Sources:

- ACS PUMS curated variables
- GSS
- WVS

Rules:

- treat ACS as an official population-grounding layer, not as a behavioral determinant;
- map ACS variables into demographics, life context, capability, and social/family context;
- normalize ACS fields as `official_population_numeric_variable`, `official_population_categorical_variable`, `official_population_binary_variable`, or `official_population_ordinal_variable`;
- map survey variables/questions into the 10-category schema using keywords and source sections;
- infer survey item types when possible;
- mark variables without value labels as `needs_value_schema_or_codebook_lookup`;
- preserve source IDs and raw category paths for grounding.

### Research Datasets

Sources:

- Apple ML-PrimeX

Rules:

- map worldview/opinion questions to `Worldview, Beliefs & Attitudes`;
- map PI-18 Primal World Beliefs items to `primal world beliefs`;
- mark explanation fields as belief explanations;
- keep license risk visible because PrimeX has non-commercial/no-derivatives terms.

### Persona Dataset Sources

Sources:

- SCOPE-Persona
- Nemotron-Personas-USA
- OASIS

Rules:

- map SCOPE facets to the corresponding theoretical categories;
- map Nemotron demographic/geographic fields to population grounding;
- map Nemotron skills to capability;
- map Nemotron hobbies/sports/arts/travel/culinary fields to behavioral preferences;
- map OASIS MBTI to personality traits, profession to domain overlay, and interested topics to behavioral preferences.

### DeepPersona Auto-Extractions

Rules:

- use DeepPersona top-level categories as subcategory hints;
- remap them into our 10-category schema;
- flag all DeepPersona auto-extracted attributes for review;
- do not treat them as high-quality final attributes without grounding.

Examples:

- `Media Preferences` -> `Behavioral Patterns & Preferences`
- `Analytical Skills` -> `Cognitive & Capability Profile`
- `Sensitivity` -> `Personality Traits`
- `Guidance` -> `Social Identity, Relationships & Community`

### PersonaHub Domain Labels

Rules:

- map all sampled PersonaHub domain labels to `Domain-Specific Overlays`;
- infer `domain_label`;
- flag as `domain_label_not_standalone_attribute`;
- do not treat domain labels as standalone persona attributes until they are converted into domain modules or expertise attributes.

Example:

- `Aerospace Engineering` is not itself a general persona attribute. It is a domain/expertise label that may support a future professional or domain-specific module.

## Review Philosophy

Normalization is conservative.

It does not assume that similar words mean the same construct.

For example:

- `risk_aversion`
- `risk_tolerance`
- `sensation_seeking`

These should be related in the graph, but not automatically merged. They share a risk theme, but measure different mechanisms:

- avoidance of uncertainty;
- capacity to tolerate loss or volatility;
- desire for stimulation and novelty.

Step 3 should create relations such as:

- `negatively_correlates_with`
- `related_to`
- `domain_specific_to`

but should not collapse them into one generic `risk_preference` attribute.

## Step 2 QA Checks

The normalization script checks:

- row count preservation;
- duplicate candidate IDs;
- empty canonical labels;
- unknown normalized categories;
- category changes from Step 1;
- data type counts;
- review flag counts.

Current output:

- raw extended normalized rows: 28,463;
- high-quality normalized rows: 9,935;
- duplicate candidate IDs: 0;
- empty canonical labels: 0;
- unknown normalized categories: 0.

## Next Step

Step 3 should use the normalized outputs to perform:

- exact duplicate detection;
- loose duplicate clustering;
- alias consolidation;
- source priority selection;
- relation graph construction;
- final category/subcategory review.

The main inputs for Step 3 are:

- `dedup_key_strict`
- `dedup_key_loose`
- `canonical_name`
- `normalized_primary_category`
- `normalized_subcategory`
- `source_family`
- `quality_tier`
- `review_flags_json`
