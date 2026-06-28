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

The artifact handoff should follow the same curation flow used by the code:

```text
source raw data
  -> cleaned/normalized records
  -> local profile DB or user-history JSONL
  -> inferred/assigned persona fields
  -> validation or evaluation report
  -> packaged dataset or collaborator return archive
```

Upload the smallest useful reproducible artifact at each stage. Do not upload
dependency directories, local caches, credentials, or unredacted logs.

Use one HuggingFace dataset repository for migration artifacts, for example:

```text
hf://<org>/<matraix-artifacts-dataset>/matraix/
```

Keep the published URL column as `TODO` until each artifact is uploaded. After
upload, replace `TODO` with the actual HuggingFace file or directory URL and
update the module README that consumes that artifact.

### Source Snapshot: MatrAIx `origin/main`

Sizes below come from `MatrAIx-ai/MatrAIx@origin/main`
`e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`, inspected on 2026-06-27 with
`git ls-tree -r -l origin/main`.

| Priority | Source path | Approx. size | Suggested HuggingFace path | Published URL | Notes |
|---|---|---:|---|---|---|
| Required | `persona/attribute_pool/outputs/` | 402 MiB, 49 files | `matraix/persona/attribute_pool/outputs/` | TODO | Generated CSV/JSONL/GraphML outputs. Do not put these back into `main`. |
| Required | `persona/attribute_pool/dataset/scope_structured.jsonl` | 35 MiB | `matraix/persona/attribute_pool/sources/scope_structured.jsonl` | TODO | SCOPE structured input used by attribute-pool curation. |
| Required | `persona/datasets/bench-dev-2000/` | 12 MiB, 2,004 files | `matraix/persona/datasets/bench-dev-2000/` | TODO | Full generated persona benchmark cohort. PersonaBench `main` keeps only the tiny sample. |
| Required | `jobs/` | 64 MiB, 509 files | `matraix/jobs/historical/` | TODO | Historical run outputs, including trajectories, screenshots, recordings, and result JSON. |
| Optional | `docs/assets/persona-grounding-flow.png` | 1.6 MiB | `matraix/docs/assets/persona-grounding-flow.png` | TODO | Upload if docs need the original binary asset. |
| Optional | `docs/assets/matraix-architecture.png` | 1.1 MiB | `matraix/docs/assets/matraix-architecture.png` | TODO | Upload if docs need the original binary asset. |
| Defer | `adapters/**/uv.lock` and adapter fixtures | 11 MiB across 262 files | `matraix/adapters/source-fixtures/` | TODO | Prefer adapter-local regenerated locks. Upload only if a curated adapter PR requires exact source reproduction. |
| Defer | root `uv.lock` | 0.9 MiB | `matraix/root/uv.lock` | TODO | Keep out of clean main until dependency policy is explicit. |

Largest individual tracked files in `origin/main`:

| Source path | Approx. size |
|---|---:|
| `persona/attribute_pool/outputs/normalized/candidate_pool_raw_extended_normalized.jsonl` | 67 MiB |
| `persona/attribute_pool/outputs/step5_embedding_llm_dedup/embedding_retrieved_pairs.csv` | 50 MiB |
| `persona/attribute_pool/outputs/normalized/candidate_pool_raw_extended_normalized.csv` | 40 MiB |
| `persona/attribute_pool/dataset/scope_structured.jsonl` | 35 MiB |
| `persona/attribute_pool/outputs/candidate_pool_raw_extended.jsonl` | 32 MiB |
| `persona/attribute_pool/outputs/step3_dedup_categorize/candidate_assignments_high_quality.jsonl` | 28 MiB |
| `persona/attribute_pool/outputs/normalized/candidate_pool_high_quality_normalized.jsonl` | 23 MiB |
| `persona/attribute_pool/outputs/candidate_pool_raw_extended.csv` | 21 MiB |
| `jobs/appSim-example-computer-use-macos-local/macos-notification-preferences__kkygzz8/agent/recording.mp4` | 6 MiB |
| `jobs/appSim-example-web-cocoa-local/books-interest-cocoa__cARWDzg/result.json` | 4 MiB |

### Local Side Artifacts

The local MatrAIx working copy also contains untracked or branch-local data
under `/data2/zonglin/persona_ai/MatrAIx`. These are not clean-main source
imports, but they are useful to preserve externally before the migration
workspace is cleaned.

| Priority | Local source path | Approx. size | Suggested HuggingFace path | Published URL | Notes |
|---|---|---:|---|---|---|
| Required | `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/curated_personas/` | 669 MiB, 130,709 files | `matraix/local/personas/existing_data_curation/curated_personas.tar.gz` | TODO | Tar before upload; many tiny files. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/raw/prism_alignment/` | 211 MiB | `matraix/local/personas/existing_data_curation/raw/prism_alignment/` | TODO | Raw PRISM alignment files. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/outputs/` | 402 MiB | `matraix/local/personas/attribute_pool/outputs/` | TODO | Local path mirrors tracked `persona/attribute_pool/outputs/`. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/dataset/scope_structured.jsonl` | 35 MiB | `matraix/local/personas/attribute_pool/sources/scope_structured.jsonl` | TODO | Local path mirrors tracked `persona/attribute_pool/dataset/scope_structured.jsonl`. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/raw/amazon_reviews_2023/` | 31 MiB | `matraix/local/raw/amazon_reviews_2023/` | TODO | Amazon review curation artifacts. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl` | 16 MiB | `matraix/local/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl` | TODO | Full Amazon user histories consumed by `make_amazon_collab_package.py` and inference scripts. |
| Required | `/data2/zonglin/persona_ai/MatrAIx/raw/amazon_reviews_2023/amazon_profiles.sqlite` | 15 MiB | `matraix/local/amazon_reviews_2023/amazon_profiles.sqlite` | TODO | Local Amazon profile database for worker-range validation. |
| Required | `MatrAIx PR #125: personas/existing_data_curation/samples/amazon_reviews_2023/top_reviewers/` | 15 MiB, 5 files | `matraix/local/amazon_reviews_2023/top_reviewers/` | TODO | Top-10K rich-persona reviewer queue. PersonaBench `main` keeps the selector script and README instructions, not the generated CSV/JSONL/ID list. |
| Optional | `MatrAIx PR #72: applications/recommendation_chatbot_eval/data/` | 9.4 MiB, 339 files | `matraix/local/application/recommendation_chatbot_eval/data/` | TODO | Catalog parquet files and generated persona fixtures for the full recommender evaluation app. The clean main task uses a tiny task-local sidecar instead. |
| Optional | `/data2/zonglin/persona_ai/MatrAIx/applications/recommendation_chatbot_eval/data/catalogs/game.parquet` | 5 MiB | `matraix/local/application/recommendation_chatbot_eval/data/catalogs/game.parquet` | TODO | Application-specific recommender catalog fixture. |

Largest local side-artifact files:

| Local source path | Approx. size |
|---|---:|
| `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/raw/prism_alignment/metadata.jsonl` | 81 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/raw/prism_alignment/utterances.jsonl` | 65 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/raw/prism_alignment/conversations.jsonl` | 58 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/outputs/normalized/candidate_pool_raw_extended_normalized.jsonl` | 67 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/personas/attribute_pool/outputs/step5_embedding_llm_dedup/embedding_retrieved_pairs.csv` | 50 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl` | 16 MiB |
| `/data2/zonglin/persona_ai/MatrAIx/raw/amazon_reviews_2023/amazon_profiles.sqlite` | 15 MiB |

Do not upload dependency directories:

| Local path | Reason |
|---|---|
| `/data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/wiki_collab/frontend/node_modules/` | Reinstall from package metadata instead of storing dependency trees. |
| `/data2/zonglin/persona_ai/MatrAIx/applications/recommendation_chatbot_eval/frontend/node_modules/` | Reinstall from package metadata instead of storing dependency trees. |

### README Updates After Upload

After upload, update the relevant module READMEs with actual artifact URLs:

- `persona/curation/attribute_pool/README.md`
- `persona/datasets/README.md`
- `environment/adapters/<adapter-name>/README.md` for adapter-required data
- future `persona/bench/` documentation
- future application-specific README files that need external fixtures
