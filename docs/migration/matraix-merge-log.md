# MatrAIx Merge Log

This log records the curated migration from MatrAIx into PersonaBench.

## 2026-06-27

### Step 1: Merge provenance manifest

- PersonaBench PR: `#125`
- Title: `[matraix-migration] Add provenance manifest`
- Result: merged
- Merge commit: `ee9f9334f1badd9bd84b702817a634b82e778638`
- Previous `origin/main`: `29b951ca3285ec2456ee5dd61020c9d42617255f`
- New `origin/main`: `ee9f9334f1badd9bd84b702817a634b82e778638`
- Files added:
  - `migration/matraix/README.md`
  - `migration/matraix/main_commits.tsv`
  - `migration/matraix/source_pr_commits.tsv`
  - `migration/matraix/source_prs.tsv`
- Notes:
  - This was metadata only.
  - It preserves source commit and source PR authorship before curated imports.
  - No raw MatrAIx code was imported in this step.

### Step 2: Establish architecture guardrails

- Branch: `codex/architecture-guidance`
- Purpose: define module boundaries before importing code.
- Policy:
  - Do not merge raw snapshot directories into `main`.
  - Curate files into `persona/`, `application/`, or `environment/`.
  - Record every import source in this log.
