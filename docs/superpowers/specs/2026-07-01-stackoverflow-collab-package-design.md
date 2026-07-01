# StackOverflow Collaborator Package Support — Design

- **Date:** 2026-07-01
- **Owner:** @Qianfeng-Wen
- **Base:** stacked on PR #143 (`[codex] Add persona collaboration package tools`)
- **Branch:** `stackoverflow-collab-package` (created from PR #143 head)

## Context

PR #143 adds owner-side tools that slice large local datasets into
self-contained collaborator packages (`.tar.gz` with `tasks.jsonl`,
`dimensions.json`, `collab_kit/`, checksummed manifests). A collaborator
unpacks the archive, runs `./run_assignment.sh` on their own Claude/Codex
subscription to attribute persona dimensions with evidence quotes, and returns
`results.jsonl`, which the owner validates and merges with
`scripts/merge_collab_results.py`.

Two sources exist: Wikipedia person profiles (`wiki`) and Amazon Reviews 2023
user histories (`amazon`). This design adds a third source: Stack Overflow
user posting histories, at **package-pipeline parity with amazon** (exporter,
package builder, evidence mapping, wrapper, owner DB, solver support, tests,
docs). The amazon-style downstream extraction/evaluation suite is explicitly
out of scope for this iteration.

## Decisions already made

| decision | choice |
|---|---|
| Scope | Package pipeline only (no downstream extraction/eval) |
| Data source | HF `MatrAIx2026/MatrAIx2026` → `StackExchange_Persona/<year>/stackoverflow_persona_batch_*.parquet` |
| Schema access | Dataset is gated; design against a documented assumed schema with strict exporter validation; verify against real files before merge |
| Delivery | Branch stacked on PR #143; PR to `main` marked blocked-by #143 |
| Architecture | Shared fold module: move source-neutral fold/truncation machinery out of the amazon builder; both builders import it |

## 1. Data flow and identity

```
HF StackExchange_Persona/<year>/stackoverflow_persona_batch_*.parquet
   │  scripts/export_hf_stackoverflow_user_histories.py   (owner, one-time)
   ▼
user_histories.jsonl.gz   {"user_id": "...", "post_count": N, "posts": [...]}
   │  scripts/make_stackoverflow_package.sh HISTORIES 0:100 alice
   │  └─ scripts/make_stackoverflow_collab_package.py
   ▼
SO_0_100_alice.tar.gz
   │  collaborator: ./run_assignment.sh  (their own subscription)
   ▼
results.jsonl ──► scripts/merge_collab_results.py   (unchanged, source-agnostic)
```

Identity strings (fixed constants in the SO builder):

| field | value |
|---|---|
| `source` | `stackoverflow_persona` |
| `task_id` | `stackoverflow_persona:<user_id>` |
| `qid` | `so_user:<user_id>` |
| `title` | `Stack Overflow user <user_id>` |
| `source_url` | `stackexchange://stackoverflow/user/<user_id>` (pseudo-URL, mirrors amazon) |
| assignment id prefix | `SO_<start>_<end>` |
| default dataset id | `matraix_stackoverflow_persona_v1` |
| protocol id | `stackoverflow_persona_inference_v1` |

## 2. Exporter: `scripts/export_hf_stackoverflow_user_histories.py`

Lists repo files with `huggingface_hub.list_repo_files`, filters
`StackExchange_Persona/<year>/stackoverflow_persona_batch_*.parquet` for the
requested years, downloads each shard with `hf_hub_download`, reads it with
`pyarrow`, and writes one normalized JSONL row per user.

**Normalized output row** (the contract the package builder consumes):

```json
{
  "user_id": "12345",
  "post_count": 42,
  "posts": [
    {
      "post_id": "987",
      "post_type": "question",
      "timestamp": 1700000000,
      "date": "2023-11-14",
      "tags": ["python", "pandas"],
      "title": "How do I ...",
      "text": "post body ...",
      "score": 12,
      "accepted": null,
      "site": "stackoverflow"
    }
  ]
}
```

Posts are sorted by timestamp ascending. Users are emitted in `--user-ids`
input order, or under `--all-users` sorted by numeric `user_id` when every id
is numeric (lexicographic otherwise), so output is deterministic.

**Schema assumption (VERIFY BEFORE MERGE).** The artifact is gated and its
parquet schema is unverified. The normalizer is a table-driven alias map that
accepts either shape:

- per-user rows: a user id column plus a nested list column of posts;
- per-post rows: one post per row grouped by owner id.

Column aliases (first match wins): user id `user_id | owner_user_id |
OwnerUserId | account_id`; post id `post_id | Id`; type `post_type |
PostTypeId` (map `1`→`question`, `2`→`answer`, other/missing→`post`);
timestamp `timestamp | creation_date | CreationDate` (epoch seconds or ms, or
ISO date string); tags `tags | Tags` (list, or `<a><b>` / comma string —
parsed); title `title | Title`; body `text | body | Body` (HTML tags stripped
when present); score `score | Score`; accepted `accepted | is_accepted |
accepted_answer` (bool or null).

If no user-id alias or no recognizable post shape is found, the exporter
fails with an error listing the columns it actually saw next to the aliases
it knows, so adapting to the real schema is a one-line alias-table fix.

CLI: `--user-ids FILE` (text/markdown with numeric ids, or JSONL with
`user_id`) or `--all-users`; `--years 2011,2019` (default: every year folder
present); `--min-posts N` (default 0); `--max-users N` (0 = all);
`--output PATH` (`.gz` supported); `--repo-id`, `--artifact-prefix`,
`--token` (defaults from `configs/stackexchange_persona.json`, overridable
via `STACKEXCHANGE_PERSONA_REPO_ID` / `STACKEXCHANGE_PERSONA_ARTIFACT_PREFIX`
env vars, mirroring the amazon exporter).

## 3. Shared fold module: `scripts/history_package_common.py`

Source-neutral machinery moved out of `make_amazon_collab_package.py`
(logic unchanged, names de-underscored):

| new public name | moved from (amazon builder) |
|---|---|
| `FOLD_TEXT_SEPARATOR`, `FOLD_TRUNCATION_MARKER` | module constants |
| `compact_text(value, max_chars)` | `_compact_text` |
| `sorted_by_time(items, timestamp_of)` | `_sorted_reviews` generalized: takes a `timestamp_of` callable |
| `spread_across_time(items, max_items)` | `_spread_across_time` |
| `build_cv_fold_texts(rendered_items, effective_cv_folds, id_field)` | fold assembly loop in `build_task`; `id_field="review_ids"` for amazon, `"post_ids"` for SO — amazon task shape stays byte-identical |
| `render_fold(fold_id, total_folds, rendered_item_texts)` | `_render_fold`, taking pre-rendered item strings |
| `join_fold_texts(fold_texts)` | `_profile_text` |
| `limit_fold_texts_for_profile(fold_texts, max_chars, effective_min_support)` | `_limit_fold_texts_for_profile` + private truncation helpers |
| `require_positive(name, value)` | `_require_positive` |
| `normalize_timestamp`, `timestamp_to_date` | generic copies (20 lines) so SO code does not import the amazon inference module |
| `load_evidence_mapping`, `category_matches`, `supported_schema_categories`, `filter_supported_dimensions` | generic copies of the ~30-line filter from `infer_amazon_review_dimensions.py` |

`make_amazon_collab_package.py` is updated mechanically to import these; its
CLI, behavior, task output, and its **existing imports from
`infer_amazon_review_dimensions.py` stay untouched** (that 3k-line imported
module is not modified). The duplicated 50 lines between the common module
and the amazon inference module are accepted for now and flagged for cleanup
after #143 merges. The existing amazon test passing unchanged is the
regression proof for the move.

## 4. Package builder: `scripts/make_stackoverflow_collab_package.py`

Mirrors the amazon builder's structure and CLI:

- Validates each history row: non-empty `user_id`; `posts` list; a usable
  post has non-empty `title` or `text`; **≥ 2 usable posts required**.
- Sorts posts by timestamp, spreads to `--max-posts-per-user` (default 90).
- Renders each post as:

  ```
  [p0001]
  date: 2023-11-14
  type: question
  tags: python, pandas
  title: How do I ...
  score: 12
  accepted: n/a
  text: <body compacted to --max-post-text-chars, default 900>
  ```

  `accepted` renders `true`/`false` for answers and `n/a` otherwise; `tags`
  renders comma-joined or `(none)`; missing titles render `(untitled)`.
- Round-robins rendered posts into CV folds (`--cv-folds`, default 3;
  `--min-support-folds`, default 2; both capped per-task like amazon), builds
  `cv_fold_texts` with `post_ids`, applies shared truncation
  (`--max-profile-text-chars`, default 70000).
- Task fields: `global_idx, task_id, qid, title, source_url, profile_text,
  source, user_id, post_count, selected_post_count, tags` (sorted distinct
  tags across selected posts — analog of amazon's `categories`), `cv_folds,
  effective_cv_folds, min_support_folds, cv_fold_texts, input_sha256`
  (sha256 of the canonical task payload minus `input_sha256`).
- Dimensions: default scope `stackoverflow_supported` via
  `configs/stackoverflow_evidence_mapping.json`; `--all-dimensions` sends the
  full catalog. Assignment metadata mirrors amazon's fields (with
  `max_posts_per_user`, `max_post_text_chars`).
- Package assembly reuses `make_collab_package.py` public helpers unchanged
  (`prepare_out_dir`, `copy_collab_kit`, `copy_root_launcher`, `write_jsonl`,
  `write_package_manifest`, `build_archive`) plus an SO-specific worker
  README (`write_stackoverflow_worker_readme`).

## 5. Evidence mapping: `configs/stackoverflow_evidence_mapping.json`

Same schema as `amazon_review_evidence_mapping.json`. Categories reference
real catalog category names (1339-dim `persona/dimensions.json`):

| id | inferability | schema_categories |
|---|---|---|
| `technical_expertise` | allowed_from_behavior | `Skills: Programming`, `Skills: Tools`, `Expertise: Skills`, `Expertise: Domains`, `Professional: Industry`, `Professional: Role`, `Professional: Career` |
| `topic_interests` | allowed_from_behavior | `Interests: Topics`, `Interests: Hobbies`, `Expertise: Domains`, `Learning: Academic` |
| `problem_solving_style` | allowed_from_behavior | `Risk & Decision`, `Behavior: Preferences`, `Personality: Big Five`, `Personality: Character` |
| `learning_behavior` | allowed_from_behavior | `Learning: Style`, `Learning: Academic`, `Behavior: Habits`, `Behavior: Time` |
| `communication_style` | allowed_from_language | `Linguistic: Communication`, `Linguistic: Language`, `Learning: Style`, `Personality: Big Five`, `Personality: Character` |
| `values_and_motivations` | allowed_from_behavior | `Values & Motivation`, `Worldview: Beliefs`, `Personality: Character` |
| `work_context` | allowed_from_behavior | `Behavior: Work`, `Behavior: Habits` |
| `explicit_self_statements` | direct_only | `Demographic:*`, `Health:*`, `Professional:*`, `Learning: Academic`, `Personality: Relationships`, `Worldview: Beliefs` |

`skip_by_default_schema_categories`: `External: Datasets`, `State: Emotional`,
`Narrative Identity & Life History` (same as amazon). `direct_only_note`
mirrors amazon's: demographic/health/occupation/geography/identity attributes
require explicit quoted self-statements; technical engagement must not be
converted into sensitive identity labels.

## 6. collab_kit changes (surgical)

`wiki_collab/collab_kit/solver.py` only:

- Fold-routing gate becomes duck-typed: `if profile.get("cv_fold_texts"):`
  replaces `if profile.get("source") == "amazon_reviews_2023":`. Wiki tasks
  carry no `cv_fold_texts`, so wiki behavior is unchanged; amazon and SO both
  route through fold voting. `_fold_profiles` and the `min_support_folds`
  read are already source-agnostic.
- `merge_amazon_fold_fields` is renamed `merge_fold_fields`;
  `merge_amazon_fold_fields = merge_fold_fields` stays as an alias.
- `build_prompt` selects opening + rules by `source`:
  - `stackoverflow_persona` opening: "You are extracting persona-attribution
    fields from a Stack Overflow user's public posting history."
  - SO rules: evidence must be quoted from the post titles/bodies/tags in
    `profile_text` (not outside knowledge); skill/expertise/interest
    inference from demonstrated posting behavior is allowed; demographic,
    health, financial, or other sensitive attributes require direct
    self-statements — otherwise `null`/`unsupported`.

No changes to `harness.py`, `assignment_runner.py`, `backends.py`,
`conformance.py`, schemas, or `run_assignment.sh` — verified source-agnostic.

## 7. Owner DB: `wiki_collab/stackoverflow_collab.py` + `scripts/build_stackoverflow_collab_db.py`

Mirrors the `amazon_collab.py` / `build_amazon_collab_db.py` pair (same
`profiles` SQLite schema so `merge_collab_results.py --db` works), with one
deliberate difference: the DB row's `task_id`/`qid` use the **same
convention as package tasks** (`stackoverflow_persona:<user_id>` /
`so_user:<user_id>`), keyed by `user_id` rather than row index, so merge
identity checks match what collaborators echo back.

> Note: PR #143's amazon DB stores `task_id = "amazon_user:<global_idx>"`
> while amazon packages emit `task_id = "amazon_reviews_2023:<user_id>"` — a
> latent identity-check mismatch. We do not replicate it; it will be reported
> as review feedback on #143 (not fixed in this branch).

The SO DB uses its own `profiles` schema WITHOUT an `input_sha256` column.
`merge_collab_results.py` checks that column against the results' echoed task
hash whenever present (column-presence-gated check, lines 91–93 and 211–221).
Package-task hashes are parameter-dependent (computed from the rendered
task payload), while a stored raw-payload hash would be parameter-independent
— so the two can never match. To avoid this mismatch the raw fingerprint is
stored as `source_payload_sha256` for owner-side audits; the absence of
`input_sha256` causes merge to skip the hash check entirely. Merge
compatibility (task_id/qid identity checks passing, hash check skipped) is
proven by `test_stackoverflow_merge_accepts_package_results_with_db`, which
builds a package and DB from the same histories file, synthesizes a conformant
`results.jsonl`, and asserts `merge_collab_results.main` returns 0.

## 8. Wrapper, config, docs

- `scripts/make_stackoverflow_package.sh`: mirrors `make_amazon_package.sh` —
  `USER_HISTORIES START:END [worker_id] [supported|all]`, env overrides
  `STACKOVERFLOW_DATASET_ID`, `MATRIX_DIMENSIONS`,
  `MATRIX_PACKAGE_CACHE_ROOT`, `MATRIX_PACKAGE_OUT_ROOT`; computes dataset
  sha256; calls the SO builder; prints the archive path. No private machine
  paths; `bash -n` clean.
- `configs/stackexchange_persona.json`: source config (repo id, artifact
  prefix, year-partitioned layout, format, persona_relevance, note that the
  schema assumption is pending verification against the gated artifact).
- `README.md`: new "Stack Overflow Packages" section (export → package →
  send), including the gated-dataset note and `huggingface-cli login`.

## 9. Tests (added to `tests/unit/matraix/test_persona_collab_packages.py`)

1. `test_stackoverflow_collab_package_builds_extractable_archive` — synthetic
   user with 2 posts; asserts `source == "stackoverflow_persona"`,
   `effective_cv_folds == 2`, `cv_fold_texts` uses `post_ids`, archive
   contains `tasks.jsonl` / `README.md` / `collab_kit/conformance.py`.
2. `test_hf_stackoverflow_exporter_writes_normalized_user_histories` —
   monkeypatched shard listing/reading; covers both per-post-row and
   per-user-row parquet shapes and the alias mapping (`OwnerUserId`,
   `PostTypeId`, HTML-tagged body, `<a><b>` tag string).
3. `test_solver_routes_fold_tasks_through_fold_voting` — monkeypatched
   `_attribute_single_pass`; asserts an SO task with `cv_fold_texts` merges
   per-fold outputs (and a wiki task does not).
4. `test_package_owner_scripts_document_portable_data_inputs` — extended with
   the SO wrapper/exporter/config (no `/data2/`, no usernames, `SCRIPT_DIR`
   pattern, config repo id).

Existing wiki/amazon tests must pass unchanged after the shared-module move.

Validation commands (mirroring #143's):

```
python3 -B -m pytest tests/unit/matraix/test_persona_collab_packages.py -q
bash -n persona/existing_data_curation/scripts/make_stackoverflow_package.sh
python3 -m py_compile persona/existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py \
  persona/existing_data_curation/scripts/make_stackoverflow_collab_package.py \
  persona/existing_data_curation/scripts/history_package_common.py \
  persona/existing_data_curation/wiki_collab/stackoverflow_collab.py
```

## 10. Out of scope / follow-ups

- Downstream extraction/evaluation workflows (amazon has
  `amazon/extraction/`, `amazon/evaluation/`) — future iteration.
- Verifying the parquet schema against the real gated artifact — required
  before this branch merges; the alias table makes the fix small.
- Reporting the amazon DB `task_id` mismatch on #143.
- De-duplicating the evidence-filter/timestamp helpers between
  `history_package_common.py` and `infer_amazon_review_dimensions.py` after
  #143 merges.
