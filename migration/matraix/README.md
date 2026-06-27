# MatrAIx Migration Provenance

This directory records provenance for the MatrAIx-to-PersonaBench migration. It is metadata-only and does not import code into `main`.

Files:

- `main_commits.tsv`: first-parent MatrAIx `main` commits, including source author/committer metadata and the PersonaBench migration PR/branch/commit mapping. Skipped commits are included with `migration_status=skipped`.
- `source_prs.tsv`: every MatrAIx GitHub PR and the PersonaBench PR that imported it as a snapshot or diff.
- `source_pr_commits.tsv`: commits inside every MatrAIx GitHub PR, including commit authors, emails, dates, subjects, and bodies where available from GitHub.

Important exclusions:

- `06a5450001128b696e4116176c5cf00a9a0734ae` was intentionally skipped because it removed legacy scaffold directories from the old MatrAIx main.
- `30e1e5a4992c8c207a6d49480d757b84121352bd` was skipped because it had an empty diff.

Generated from local migration reports under `/tmp/personabench_full_matraix_migration` and live GitHub PR metadata for `MatrAIx-ai/MatrAIx`.

## External Artifact Upload Checklist

Large generated datasets, raw source dumps, and job outputs should not be
committed to PersonaBench `main`. Upload these artifacts to HuggingFace or
another approved external storage location, then update module READMEs with the
published URLs.

Recommended HuggingFace layout:

```text
attribute_pool/outputs/
attribute_pool/sources/scope_structured.jsonl
existing_data_curation/curated_personas.tar.gz
existing_data_curation/raw/prism_alignment/
amazon_reviews_2023/
wiki_collab/A_10000_20000_worker.tar.gz
```

Primary upload targets:

Sizes and local paths below come from the local MatrAIx working copy inspected
on 2026-06-27. Some MatrAIx `origin/main` paths use `persona/...`, while local
large data artifacts are currently under `personas/...`.

| Priority | Local source path | Approx. size | Suggested HF path | Notes |
|---|---:|---:|---|---|
| Required | `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/outputs/` | 402 MiB | `attribute_pool/outputs/` | Generated attribute-pool CSV/JSONL/GraphML outputs. In `MatrAIx origin/main`, equivalent tracked paths appear under `persona/attribute_pool/outputs/`. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/dataset/scope_structured.jsonl` | 35 MiB | `attribute_pool/sources/scope_structured.jsonl` | SCOPE structured source data used by attribute-pool curation. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/curated_personas/` | 669 MiB | `existing_data_curation/curated_personas.tar.gz` | Directory contains 130,709 small files. Tar before upload. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/raw/prism_alignment/` | 211 MiB | `existing_data_curation/raw/prism_alignment/` | Raw PRISM alignment files: `metadata.jsonl`, `utterances.jsonl`, `conversations.jsonl`. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/raw/amazon_reviews_2023/` | 31 MiB | `amazon_reviews_2023/` | Amazon review curation artifacts, including `amazon_profiles.sqlite` and `persona_dimension_inference/user_histories.jsonl`. |
| Optional | `/data2/zonglin/persona_ai/MatrAIx/personas/A_10000_20000/` | 83 MiB | `wiki_collab/A_10000_20000/` | Wiki/Amazon collaboration package directory. |
| Optional | `/data2/zonglin/persona_ai/MatrAIx/A_10000_20000_worker.tar.gz` | 15 MiB | `wiki_collab/A_10000_20000_worker.tar.gz` | Worker package archive. Duplicate copy also exists under `personas/A_10000_20000/`. |
| Optional | `/data2/zonglin/persona_ai/MatrAIx/A_20000_30000_worker.tar.gz` | 16 MiB | `wiki_collab/A_20000_30000_worker.tar.gz` | Worker package archive. |
| Optional | `/data2/zonglin/persona_ai/MatrAIx/A_30000_40000_worker.tar.gz` | 16 MiB | `wiki_collab/A_30000_40000_worker.tar.gz` | Worker package archive. |
| Optional | `/data2/zonglin/persona_ai/MatrAIx/applications/recommendation_chatbot_eval/data/catalogs/game.parquet` | 5 MiB | `application/recommendation_chatbot_eval/data/catalogs/game.parquet` | Application-specific recommender catalog fixture. |

Not recommended for upload:

| Local path | Reason |
|---|---|
| `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/wiki_collab/frontend/node_modules/` | Reinstall from package lock instead of storing dependencies. |
| `/data2/zonglin/persona_ai/MatrAIx/applications/recommendation_chatbot_eval/frontend/node_modules/` | Reinstall from package lock instead of storing dependencies. |

Largest individual tracked/generated files observed during migration:

| Local source path | Approx. size |
|---|---:|
| `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/raw/prism_alignment/metadata.jsonl` | 81 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/outputs/normalized/candidate_pool_raw_extended_normalized.jsonl` | 67 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/raw/prism_alignment/utterances.jsonl` | 65 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/raw/prism_alignment/conversations.jsonl` | 58 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/outputs/step5_embedding_llm_dedup/embedding_retrieved_pairs.csv` | 50 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/outputs/normalized/candidate_pool_raw_extended_normalized.csv` | 40 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/A_10000_20000/A_10000_20000_worker/tasks.jsonl` | 40 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/dataset/scope_structured.jsonl` | 35 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/outputs/candidate_pool_raw_extended.jsonl` | 32 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/outputs/step3_dedup_categorize/candidate_assignments_high_quality.jsonl` | 28 MiB |

After upload, update the relevant module READMEs:

- `persona/curation/attribute_pool/README.md`
- `persona/datasets/README.md`
- future `persona/bench/` documentation
- future application-specific README files that need external fixtures
