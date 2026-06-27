# Persona Existing-Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the MatrAIx persona existing-data curation pipeline into PersonaBench so maintainers can generate, clean, validate, package, and merge Wikipedia-derived persona data and Amazon Reviews 2023 persona evidence without dumping raw artifacts into `main`.

**Architecture:** Keep pipeline code under `persona/curation/existing_data/` and tests under `tests/persona/curation/existing_data/`. Preserve the MatrAIx worker-package contract, but update imports and default paths from old `personas/` to PersonaBench `persona/`. Treat large raw data, generated profile DBs, worker archives, and curated-persona outputs as external artifacts tracked by `migration/matraix/README.md`.

**Tech Stack:** Python 3.12, stdlib JSON/JSONL/gzip/sqlite/tarfile, pytest, Ruff, optional OpenAI API calls through HTTP/curl, optional Modal/HuggingFace integration in a later PR.

---

## Source Provenance

Use the local MatrAIx source branch as the authoritative source because it
contains the latest Amazon fold-voting and evidence-preservation fixes.

- Source repo: `/data2/zonglin/persona_ai/MatrAIx`
- Source branch: `codex/amazon-review-collab-integration`
- Source HEAD: `87fe1dafb fix: preserve amazon min support fold texts`
- Source base: `MatrAIx-ai/MatrAIx@origin/main e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`

Carry the following local, uncommitted docs from the source worktree:

- `personas/existing_data_curation/wiki_collab/collab_kit/README.md`
- `personas/existing_data_curation/wiki_collab/collab_kit/RESULTS_JSONL_README.md`

Do not carry untracked archives, SQLite files, raw datasets, worker outputs, or
`__pycache__` files from the MatrAIx worktree.

## Target File Structure

Create this target module layout:

```text
persona/curation/existing_data/
  README.md
  .gitignore
  manifests/
  protocols/
  scripts/
  wiki_collab/
  worker_kit/
  samples/
  examples/
```

Tests should use:

```text
tests/persona/curation/existing_data/
```

The new module should not install as a package through `pyproject.toml`.
Pipeline scripts should add the repository root to `sys.path` when needed, as
the source scripts already do. This keeps the tools repo-local and avoids
publishing experimental curation APIs as stable package surface.

## Explicit Exclusions

Exclude these from git and record them as external artifacts:

- `personas/existing_data_curation/curated_personas/`
- `personas/existing_data_curation/raw/`
- `personas/existing_data_curation/outputs/`
- `personas/existing_data_curation/logs/`
- top-level `raw/amazon_reviews_2023/`
- `*.sqlite`, `*.db`, `*.tar.gz`, generated `results.jsonl`, generated
  `tasks.jsonl`, generated progress/failure JSONL files
- `wiki_collab/frontend/dist/`
- `wiki_collab/frontend/node_modules/`
- all `__pycache__/` and `*.pyc`

Small fixtures are allowed when they support tests or docs:

- `examples/wikipedia_persona_seed_entities_sample.jsonl`
- `examples/prism_alignment_conversations_dimension_candidates_sample.jsonl`
- `samples/amazon_reviews_2023/candidate_users_top100.jsonl`
- `samples/amazon_reviews_2023/persona_dimension_inference/pilot_2users_dpc100_readable.md`
- `wiki_collab/collab_kit/sample/*`

## Path Rewrite Rules

Apply these rewrites consistently:

```text
personas.existing_data_curation -> persona.curation.existing_data
personas/existing_data_curation -> persona/curation/existing_data
tests/personas/existing_data_curation -> tests/persona/curation/existing_data
personas/dimensions+new.json -> persona/schema/dimensions.json
personas/dimensions+new_pre_dedup.json -> external artifact or source-only note
```

When a script needs a schema path default, use:

```python
DEFAULT_SCHEMA_PATH = REPO_ROOT / "persona" / "schema" / "dimensions.json"
```

When a script needs an existing-data base directory, use:

```python
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BASE_DIR.parents[2]
```

For scripts copied into `persona/curation/existing_data/scripts/`, this makes
`REPO_ROOT` resolve to the repository root.

## PR 1: Existing-Data Source And Wiki Foundation

This PR establishes the module and verifies the non-Amazon wiki/source path.

**Files:**
- Create: `persona/curation/existing_data/.gitignore`
- Create: `persona/curation/existing_data/README.md`
- Create: `persona/curation/existing_data/manifests/*.json`
- Create: `persona/curation/existing_data/scripts/extract_enwiki_pages.py`
- Create: `persona/curation/existing_data/scripts/derive_wikipedia_person_text.py`
- Create: `persona/curation/existing_data/scripts/build_enwiki_person_dataset.py`
- Create: `persona/curation/existing_data/scripts/build_enwiki_qid_labels.py`
- Create: `persona/curation/existing_data/scripts/build_wikidata_person_attributes.py`
- Create: `persona/curation/existing_data/scripts/build_wiki_profile_db.py`
- Create: `persona/curation/existing_data/scripts/fetch_wikipedia_persona_seeds.py`
- Create: `persona/curation/existing_data/wiki_collab/core.py`
- Create: `persona/curation/existing_data/wiki_collab/results.py`
- Create: `persona/curation/existing_data/examples/wikipedia_persona_seed_entities_sample.jsonl`
- Test: `tests/persona/curation/existing_data/test_wiki_collab_core.py`
- Test: `tests/persona/curation/existing_data/test_wiki_collab_dataset.py`
- Test: `tests/persona/curation/existing_data/test_wiki_collab_results.py`

- [ ] **Step 1: Copy source files with path rewrite**

  Use a small copy script from the shell, then inspect the diff:

  ```bash
  python3 - <<'PY'
  from pathlib import Path
  import shutil

  src_root = Path("/data2/zonglin/persona_ai/MatrAIx")
  dst_root = Path(".")
  pairs = [
      ("personas/existing_data_curation/.gitignore", "persona/curation/existing_data/.gitignore"),
      ("personas/existing_data_curation/README.md", "persona/curation/existing_data/README.md"),
      ("personas/existing_data_curation/examples/wikipedia_persona_seed_entities_sample.jsonl", "persona/curation/existing_data/examples/wikipedia_persona_seed_entities_sample.jsonl"),
      ("personas/existing_data_curation/wiki_collab/core.py", "persona/curation/existing_data/wiki_collab/core.py"),
      ("personas/existing_data_curation/wiki_collab/results.py", "persona/curation/existing_data/wiki_collab/results.py"),
      ("personas/existing_data_curation/scripts/extract_enwiki_pages.py", "persona/curation/existing_data/scripts/extract_enwiki_pages.py"),
      ("personas/existing_data_curation/scripts/derive_wikipedia_person_text.py", "persona/curation/existing_data/scripts/derive_wikipedia_person_text.py"),
      ("personas/existing_data_curation/scripts/build_enwiki_person_dataset.py", "persona/curation/existing_data/scripts/build_enwiki_person_dataset.py"),
      ("personas/existing_data_curation/scripts/build_enwiki_qid_labels.py", "persona/curation/existing_data/scripts/build_enwiki_qid_labels.py"),
      ("personas/existing_data_curation/scripts/build_wikidata_person_attributes.py", "persona/curation/existing_data/scripts/build_wikidata_person_attributes.py"),
      ("personas/existing_data_curation/scripts/build_wiki_profile_db.py", "persona/curation/existing_data/scripts/build_wiki_profile_db.py"),
      ("personas/existing_data_curation/scripts/fetch_wikipedia_persona_seeds.py", "persona/curation/existing_data/scripts/fetch_wikipedia_persona_seeds.py"),
  ]
  manifest_dir = src_root / "personas/existing_data_curation/manifests"
  for src in sorted(manifest_dir.glob("*.json")):
      pairs.append((str(src.relative_to(src_root)), f"persona/curation/existing_data/manifests/{src.name}"))
  test_names = [
      "test_wiki_collab_core.py",
      "test_wiki_collab_dataset.py",
      "test_wiki_collab_results.py",
  ]
  for name in test_names:
      pairs.append((f"tests/personas/existing_data_curation/{name}", f"tests/persona/curation/existing_data/{name}"))
  for src_rel, dst_rel in pairs:
      src = src_root / src_rel
      dst = dst_root / dst_rel
      dst.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy2(src, dst)
      if dst.suffix in {".py", ".md", ".sh", ".json"}:
          text = dst.read_text(encoding="utf-8")
          text = text.replace("personas.existing_data_curation", "persona.curation.existing_data")
          text = text.replace("personas/existing_data_curation", "persona/curation/existing_data")
          text = text.replace("tests/personas/existing_data_curation", "tests/persona/curation/existing_data")
          text = text.replace("personas/dimensions+new.json", "persona/schema/dimensions.json")
          dst.write_text(text, encoding="utf-8")
  PY
  ```

- [ ] **Step 2: Add package markers for repo-local imports**

  Create empty `__init__.py` files:

  ```bash
  touch persona/curation/existing_data/__init__.py
  touch persona/curation/existing_data/scripts/__init__.py
  touch persona/curation/existing_data/wiki_collab/__init__.py
  touch tests/persona/curation/existing_data/__init__.py
  ```

- [ ] **Step 3: Verify wiki tests expose missing path fixes**

  Run:

  ```bash
  .venv/bin/pytest tests/persona/curation/existing_data/test_wiki_collab_core.py \
    tests/persona/curation/existing_data/test_wiki_collab_dataset.py \
    tests/persona/curation/existing_data/test_wiki_collab_results.py -q
  ```

  Expected first result: either pass, or fail only on stale `personas/` paths.
  Fix stale paths with explicit replacements, then rerun until the command
  exits 0.

- [ ] **Step 4: Verify lint for the imported subset**

  Run:

  ```bash
  .venv/bin/ruff check persona/curation/existing_data tests/persona/curation/existing_data
  ```

  Expected: exit 0. Fix import ordering or stale paths only.

- [ ] **Step 5: Commit PR 1**

  ```bash
  git add persona/curation/existing_data tests/persona/curation/existing_data
  git commit -m "feat: add persona existing-data wiki foundation"
  ```

## PR 2: Collaboration Packaging And Merge Tools

This PR makes collaborator packaging usable without Amazon.

**Files:**
- Create/modify: `persona/curation/existing_data/wiki_collab/collab_kit/**`
- Create: `persona/curation/existing_data/wiki_collab/run_assignment.sh`
- Create: `persona/curation/existing_data/wiki_collab/EMAIL_TEMPLATES.md`
- Create: `persona/curation/existing_data/scripts/make_collab_package.py`
- Create: `persona/curation/existing_data/scripts/make_package.sh`
- Create: `persona/curation/existing_data/scripts/make_wiki_assignments.py`
- Create: `persona/curation/existing_data/scripts/merge_collab_results.py`
- Create: `persona/curation/existing_data/scripts/merge_wiki_results.py`
- Create: `persona/curation/existing_data/scripts/audit_wiki_results.py`
- Create: `persona/curation/existing_data/scripts/validate_wiki_results.py`
- Create: `persona/curation/existing_data/worker_kit/run_range.py`
- Create: `persona/curation/existing_data/worker_kit/backends.py`
- Test: `tests/persona/curation/existing_data/test_collab_kit.py`
- Test: `tests/persona/curation/existing_data/test_assignment_runner.py`
- Test: `tests/persona/curation/existing_data/test_make_collab_package.py`
- Test: `tests/persona/curation/existing_data/test_merge_collab_results.py`
- Test: `tests/persona/curation/existing_data/test_worker_kit.py`

- [ ] **Step 1: Copy collab files and tests**

  Copy the listed files from MatrAIx using the same rewrite rules from PR 1.
  Also copy the source worktree-only file:

  ```text
  /data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/wiki_collab/collab_kit/RESULTS_JSONL_README.md
  ```

- [ ] **Step 2: Fix package builder constants**

  In `persona/curation/existing_data/scripts/make_collab_package.py`, ensure:

  ```python
  COLLAB_KIT_SRC = REPO_ROOT / "persona/curation/existing_data/wiki_collab/collab_kit"
  ROOT_LAUNCHER_SRC = REPO_ROOT / "persona/curation/existing_data/wiki_collab/run_assignment.sh"
  ```

- [ ] **Step 3: Keep worker package self-contained**

  Verify `copy_collab_kit()` excludes generated package state:

  ```python
  def _ignore_collab_kit(dir_path: str, names: list[str]) -> set[str]:
      ignored = {"__pycache__", ".pytest_cache"}
      ignored.update(name for name in names if name.endswith(".pyc"))
      ignored.update(name for name in names if name in {"results.jsonl", "results.jsonl.progress.jsonl"})
      return ignored
  ```

- [ ] **Step 4: Run collab packaging tests**

  ```bash
  .venv/bin/pytest \
    tests/persona/curation/existing_data/test_collab_kit.py \
    tests/persona/curation/existing_data/test_assignment_runner.py \
    tests/persona/curation/existing_data/test_make_collab_package.py \
    tests/persona/curation/existing_data/test_merge_collab_results.py \
    tests/persona/curation/existing_data/test_worker_kit.py -q
  ```

  Expected: exit 0.

- [ ] **Step 5: Commit PR 2**

  ```bash
  git add persona/curation/existing_data tests/persona/curation/existing_data
  git commit -m "feat: add persona collaboration packaging tools"
  ```

## PR 3: Amazon Reviews 2023 Pipeline

This PR adds Amazon evidence/profile generation and worker compatibility.

**Files:**
- Create: `persona/curation/existing_data/amazon_review_evidence_mapping.json`
- Create: `persona/curation/existing_data/amazon_reviews_2023_pool_stats.md`
- Create: `persona/curation/existing_data/manifests/amazon_reviews_2023.json`
- Create: `persona/curation/existing_data/protocols/amazon_review_persona_inference_v1/**`
- Create: `persona/curation/existing_data/scripts/analyze_amazon_reviews_2023.py`
- Create: `persona/curation/existing_data/scripts/fetch_amazon_reviews_2023.py`
- Create: `persona/curation/existing_data/scripts/infer_amazon_review_dimensions.py`
- Create: `persona/curation/existing_data/scripts/build_amazon_collab_db.py`
- Create: `persona/curation/existing_data/scripts/make_amazon_collab_package.py`
- Create: `persona/curation/existing_data/scripts/validate_amazon_results.py`
- Create: `persona/curation/existing_data/scripts/evaluate_amazon_persona_rating_holdout.py`
- Create: `persona/curation/existing_data/scripts/render_amazon_inference_report.py`
- Create: `persona/curation/existing_data/scripts/retrieve_amazon_user_histories.py`
- Create: `persona/curation/existing_data/wiki_collab/amazon_collab.py`
- Create: `persona/curation/existing_data/worker_kit/run_amazon_range.py`
- Create: `persona/curation/existing_data/samples/amazon_reviews_2023/**`
- Test: `tests/persona/curation/existing_data/test_amazon_review_core_unittest.py`
- Test: `tests/persona/curation/existing_data/test_amazon_collab_unittest.py`
- Test: `tests/persona/curation/existing_data/test_make_amazon_collab_package.py`

- [ ] **Step 1: Copy Amazon files from MatrAIx HEAD**

  Copy all listed files from source HEAD `87fe1dafb`, not from
  `origin/main`, because the latest fold-voting fixes live after the source
  main snapshot.

- [ ] **Step 2: Preserve fold-voting behavior**

  Confirm `collab_kit/solver.py` includes:

  ```python
  def merge_amazon_fold_fields(
      fold_outputs: list[list[dict[str, Any]]],
      dimensions: list[dict[str, Any]],
      *,
      min_support_folds: int,
      fold_count: int,
  ) -> list[dict[str, Any]]:
      ...
  ```

  Keep support threshold behavior from commits:

  - `92e017be3 feat: support amazon fold voting in collab solver`
  - `bb1ab0911 fix: preserve amazon fold support threshold`
  - `b51f424d9 fix: handle ambiguous amazon fold votes`
  - `e06a4950c fix: keep amazon fold evidence visible`
  - `87fe1dafb fix: preserve amazon min support fold texts`

- [ ] **Step 3: Update default paths**

  In `infer_amazon_review_dimensions.py`, set:

  ```python
  DEFAULT_SCHEMA_PATH = REPO_ROOT / "persona" / "schema" / "dimensions.json"
  DEFAULT_OUTPUT_PATH = (
      BASE_DIR
      / "raw"
      / "amazon_reviews_2023"
      / "persona_dimension_inference"
      / "inferred_dimensions.jsonl"
  )
  DEFAULT_EVIDENCE_MAPPING_PATH = BASE_DIR / "amazon_review_evidence_mapping.json"
  ```

  Keep generated output under `persona/curation/existing_data/raw/`, which is
  ignored by `.gitignore`.

- [ ] **Step 4: Run Amazon tests**

  ```bash
  .venv/bin/pytest \
    tests/persona/curation/existing_data/test_amazon_review_core_unittest.py \
    tests/persona/curation/existing_data/test_amazon_collab_unittest.py \
    tests/persona/curation/existing_data/test_make_amazon_collab_package.py -q
  ```

  Expected: exit 0. The Modal test must keep using its in-test stub and must
  not require the real `modal` package.

- [ ] **Step 5: Run mock package smoke**

  Create a tiny package from test histories and validate that the archive is
  produced without OpenAI credentials:

  ```bash
  .venv/bin/python persona/curation/existing_data/scripts/make_amazon_collab_package.py \
    --user-histories persona/curation/existing_data/samples/amazon_reviews_2023/candidate_users_top100.jsonl \
    --dimensions persona/schema/dimensions.json \
    --range 0:2 \
    --out-dir /tmp/personabench_amazon_collab_A0001 \
    --assignment-id A0001 \
    --worker-id smoke \
    --dataset-id amazon_reviews_2023_sample \
    --dataset-sha256 sample \
    --force
  ```

  Expected: command exits 0 and writes a `.tar.gz` next to the output
  directory. Do not commit the generated package.

- [ ] **Step 6: Commit PR 3**

  ```bash
  git add persona/curation/existing_data tests/persona/curation/existing_data
  git commit -m "feat: add amazon review persona pipeline"
  ```

## PR 4: Optional Modal/HuggingFace Indexer

This PR adds heavy cloud indexing helpers without affecting the default install.

**Files:**
- Create: `persona/curation/existing_data/modal_amazon_user_index.py`
- Modify: `pyproject.toml`
- Test: extend `tests/persona/curation/existing_data/test_amazon_review_core_unittest.py`
- Docs: update `persona/curation/existing_data/README.md`

- [ ] **Step 1: Add optional dependency group**

  Modify `pyproject.toml`:

  ```toml
  amazon-modal = [
      "modal>=1.4.0",
      "datasets>=4.4.1",
      "huggingface-hub>=0.36.0",
      "pyarrow>=22.0.0",
  ]
  ```

- [ ] **Step 2: Copy `modal_amazon_user_index.py`**

  Copy from MatrAIx HEAD and apply the standard path rewrites. Keep the module
  import-safe under tests by preserving the existing Modal stub test pattern.

- [ ] **Step 3: Run targeted tests**

  ```bash
  .venv/bin/pytest tests/persona/curation/existing_data/test_amazon_review_core_unittest.py -q
  ```

  Expected: exit 0 without installing real Modal.

- [ ] **Step 4: Commit PR 4**

  ```bash
  git add pyproject.toml persona/curation/existing_data/modal_amazon_user_index.py tests/persona/curation/existing_data/test_amazon_review_core_unittest.py
  git commit -m "feat: add optional amazon modal indexer"
  ```

## PR 5: Docs, Artifact Handoff, And End-To-End Guide

This PR documents the full source-to-package workflow and all external data
slots.

**Files:**
- Modify: `README.md`
- Modify: `persona/curation/README.md`
- Modify: `persona/curation/existing_data/README.md`
- Modify: `persona/datasets/README.md`
- Modify: `migration/matraix/README.md`
- Modify: `docs/migration/matraix-merge-log.md`
- Modify: `docs/migration/matraix-parity-matrix.md`

- [ ] **Step 1: Add end-to-end pipeline overview**

  Document this canonical flow:

  ```text
  fetch/index source data
    -> normalize/clean records
    -> build local SQLite profile DB
    -> infer or assign persona dimensions
    -> validate outputs
    -> create collaborator package
    -> collaborator returns results.jsonl or result archive
    -> merge and audit results
    -> publish large generated artifacts externally
  ```

- [ ] **Step 2: Add external artifact table**

  Extend `migration/matraix/README.md` with:

  ```text
  /data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/curated_personas/
  /data2/zonglin/persona_ai/MatrAIx/personas/existing_data_curation/raw/prism_alignment/
  /data2/zonglin/persona_ai/MatrAIx/raw/amazon_reviews_2023/
  /data2/zonglin/persona_ai/MatrAIx/personas/A_10000_20000/
  /data2/zonglin/persona_ai/MatrAIx/A_*_worker.tar.gz
  ```

- [ ] **Step 3: Run docs/link checks**

  ```bash
  git diff --check
  python3 - <<'PY'
  from pathlib import Path
  for path in [
      Path("README.md"),
      Path("persona/curation/README.md"),
      Path("persona/curation/existing_data/README.md"),
      Path("persona/datasets/README.md"),
      Path("migration/matraix/README.md"),
  ]:
      assert path.exists(), path
  print("docs paths ok")
  PY
  ```

- [ ] **Step 4: Commit PR 5**

  ```bash
  git add README.md persona/curation/README.md persona/curation/existing_data/README.md persona/datasets/README.md migration/matraix/README.md docs/migration
  git commit -m "docs: document persona data curation pipeline"
  ```

## Verification Gate For Every PR

Run these before pushing any PR:

```bash
git diff --check
.venv/bin/ruff check persona/curation/existing_data tests/persona/curation/existing_data
.venv/bin/pytest tests/persona/curation/existing_data -q
```

For docs-only PRs, run:

```bash
git diff --check
.venv/bin/ruff check .
.venv/bin/pytest tests/ -q
```

Do not merge a PR unless GitHub CI passes.

## Self-Review

- Spec coverage: covers data generation, cleaning, package creation,
  collaborator validation/merge, and Amazon integration. Modal/HF indexing is
  separated because it introduces optional cloud dependencies.
- Placeholder scan: no implementation step depends on an unspecified path.
- Type consistency: target imports consistently use
  `persona.curation.existing_data`; target data paths consistently use
  `persona/curation/existing_data`.
- Scope check: this is intentionally split into five PRs because one PR would
  mix source parsing, worker UX, Amazon modeling, optional cloud indexing, and
  external artifact docs.
