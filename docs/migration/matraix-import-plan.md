# MatrAIx Import Plan

This plan guides imports from `MatrAIx-ai/MatrAIx` into PersonaBench.

## Current State

- MatrAIx main at inspection time: `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`.
- PersonaBench migration provenance was merged in PR #125.
- Raw migration PRs are available as screening artifacts, but most should not
  be merged directly.

## Merge Policy

Use the migration PRs as source material. Do not merge snapshot PRs into main
unless the explicit goal is to archive a source tree.

Recommended handling:

- `#2-#60`: main commit stack. Use as provenance and source material. Do not
  merge wholesale if curating into the module layout.
- `#61`: open PR #128 diff. Candidate for a curated Persona import after the
  persona module skeleton is in place.
- `#62-#92`: open or closed source PR snapshots. Screen and curate manually.
- `#93`: full main snapshot. Keep as reference; do not merge together with
  curated imports.
- `#94-#124`: merged PR snapshots. Mostly duplicate source material already in
  main. Screen only.
- `#125`: provenance manifest. Already merged.

## Recommended Import Waves

### Wave 0: Architecture and contribution guardrails

Create module READMEs, contribution guidance, and migration logs. This prevents
future imports from landing at repository root.

### Wave 1: Persona core

Import schema, dimensions, validators, and curation scripts. Avoid large raw
outputs and generated artifacts.

Primary sources:

- `#48`
- `#52`
- `#98`
- `#99`
- `#103`
- `#108`
- `#109`
- `#112`
- `#116`
- `#119`

### Wave 2: PersonaBench tasks and annotation tooling

Import persona adherence tasks, grounding specs, and annotation tools.

Primary sources:

- `#45`
- `#46`
- `#47`
- `#51`
- `#57`
- `#61`
- `#121`

### Wave 3: Application examples

Import runnable scenarios that consume personas. Keep fixtures small and move
application metrics into `application/`.

Primary sources:

- `#43`
- `#45`
- `#56`
- `#62`
- `#66`
- `#68`
- `#70`
- `#71`
- `#73`
- `#74`
- `#76`

### Wave 4: Environment runtime

Import only the runtime pieces needed by curated persona and application tasks.
Do not bring in every adapter by default.

Primary sources:

- `#36`
- `#42`
- `#52`
- `#53`
- `#54`
- `#55`
- `#58`
- `#59`
- `#60`

### Wave 5: Data curation and larger datasets

Import scripts, manifests, and small samples. Put large outputs in external
storage or Git LFS only after a maintainer decision.

Primary sources:

- `#64`
- `#65`
- `#67`
- `#72`
- `#75`
- `#77`
- `#78`
- `#79`
- `#80`
- `#83`
- `#84`
- `#87`
- `#88`
- `#104-#110`
