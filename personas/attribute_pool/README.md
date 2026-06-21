# Persona Attribute Candidate Pool

This folder contains the persona attribute aggregation, normalization, LLM-assisted deduplication, and final merged attribute outputs generated for the MatrAIx persona schema work.

## Key Outputs

- `outputs/candidate_pool_high_quality.csv`: aggregated high-quality candidate attribute pool before rule/LLM deduplication.
- `outputs/normalized/`: normalized candidate pool with canonical labels, categories, data types, quality tiers, and source metadata.
- `outputs/step3_dedup_categorize/`: rule-based deduplication and categorization outputs.
- `outputs/step4_llm_graph/`: graph preparation outputs and LLM adjudication candidate prompts.
- `outputs/step5_embedding_llm_dedup/llm_adjudicated_pairs.csv`: OpenAI LLM adjudication results for 7,000 candidate attribute pairs.
- `outputs/step5_embedding_llm_dedup/llm_confirmed_merges.csv`: high-confidence merge edges used for deduplication.
- `outputs/step5_embedding_llm_dedup/llm_graph_edges.csv`: relation edges that should remain separate nodes in the attribute graph.
- `outputs/step6_final_merged/final_merged_attributes.csv`: final deduplicated attribute set.
- `outputs/step6_final_merged/final_graph_edges.csv`: graph edges after duplicate nodes are merged.
- `dataset/`: source snapshots used by the attribute aggregation pipeline.

## Current Counts

- High-quality candidate attributes before deduplication: 9,935
- Step 3 canonical attributes before LLM merge: 9,504
- LLM-adjudicated candidate pairs: 7,000
- High-confidence merge edges: 429
- Final merged attributes: 9,123
- Final graph edges: 5,039

Only high-confidence `duplicate_of` / `alias_of` merge decisions are collapsed. Correlated, inverse, broader/narrower, conflict, review, and rejected pairs remain separate attributes and are represented as graph edges or review rows.

## Reproducibility

Scripts used to generate these artifacts are in `scripts/`. Method notes and theoretical-basis documents are in `docs/`.

This work belongs to the Persona layer because it defines persona schema attributes, source grounding, deduplication logic, and graph relations. Application scenarios consume this attribute pool but should not own it.
