# Contributing to PersonaBench

PersonaBench accepts focused PRs. A PR can touch more than one module, but it
must explain the boundary crossing in the PR body.

Feature work, migrations, and policy changes should go through pull requests.
Do not push directly to `main` for reviewable work. At least one reviewer
approval is expected before merge; once GitHub branch protection or rulesets are
available for this private repository, that expectation should be enforced by
GitHub.

## Modules

| Module | Owns | Does not own |
| --- | --- | --- |
| `persona/` | Persona schema, attributes, curated datasets, persona curation scripts, persona adherence tasks | Runtime drivers, product scenarios, checked-in job outputs |
| `application/` | Survey/chat/web/product scenarios, application metrics, application task fixtures | Persona source datasets, runtime engines |
| `environment/` | Harbor/runtime code, persona agent adapters, job recipes, viewer backend, execution backends | Persona schema decisions, application-specific research claims |
| `apps/` | Repo-local tool frontends such as the `harbor view` UI | Generated builds, datasets, task definitions |
| `packages/` | Reusable libraries used by multiple modules | One-off scripts or generated outputs |

## PR Expectations

Every PR should include:

- The module or modules it touches.
- The source issue or migration source, when applicable.
- A short explanation of why the change belongs in that module.
- Test or validation commands that were run.
- Any generated data policy decision, especially for large files.

Every non-trivial PR should also link the prior issue, discussion, design note,
or source migration record that explains why the work exists. Small mechanical
fixes can be self-contained, but the PR body still needs enough context for a
reviewer to understand the intent.

## Issues And Status Tracking

Use GitHub Issues for task tracking and contributor progress logs. Do not add
per-person `StatusUpdate/*.md` files to the repository.

Keep each task issue focused on a concrete bug, feature, migration, dataset, or
documentation change. Link the issue from the PR body, and use closing keywords
only when the PR is intended to resolve that task issue.

For substantial research, dataset, benchmark, evaluation, or multi-PR work,
open a long-lived issue titled `Status Update - <Your Name>`. Use it as a
running log for dated updates, motivation, design decisions, current status,
open questions, blockers, outputs, and next steps. Keep this issue open while
you are active on the project.

When a PR relates to your status-update issue, reference it with a plain mention
such as `#123` or `ref #123`. Do not use auto-closing keywords such as
`fixes #123`, `closes #123`, or `resolves #123` for status-update issues.

## Issue Labels

Apply lightweight labels when opening issues so work stays filterable:

- Team labels: `team: persona`, `team: environment`, `team: application`.
- Type labels: `status-update`, `task`, `bug`, `enhancement`,
  `documentation`, `question`.
- Contributor labels: `good first issue`, `help wanted`.

At minimum, use one team label and one type label when they apply. Maintainers
can adjust labels during triage.

## AI-Assisted Contributions

AI-assisted drafts, code, and documentation are acceptable when a human
contributor has reviewed them carefully and takes responsibility for the final
change.

Do not submit bulk, low-signal, or unreviewed generated changes. In particular,
avoid PRs that are mostly generated text or code without a clear purpose,
module owner, validation evidence, and human editing. Reviewers may close or
request a rewrite for generated submissions that add noise, duplicate existing
work, or cannot be validated.

## Safety, Licensing, And Data

PersonaBench is distributed under the MIT License. By contributing, you confirm
that your changes can be redistributed under that license.

Before opening a PR, check that the change contains:

- No secrets, credentials, private keys, or local `.env` values.
- No confidential, proprietary, employer-owned, client-owned, or collaborator
  material unless there is explicit permission to publish it.
- No PII, PHI, or regulated personal data in code, tests, prompts, logs,
  fixtures, screenshots, or generated outputs.
- No third-party code, data, prompts, or model weights with incompatible or
  unclear redistribution terms.

Datasets, external artifacts, and model-derived resources need clear
provenance. Add or update the owning README, manifest, or datasheet-style note
with the source, original license, collection method, preprocessing, intended
use, and redistribution limits. Models or model weights need equivalent
model-card-style documentation before they can be reviewed for inclusion.

Prefer permissive dependencies such as MIT, BSD, Apache-2.0, ISC, or MPL-2.0.
Flag GPL, AGPL, non-commercial, share-alike, gated, or unknown licenses in the
PR body instead of quietly adding them.

Reviewers may ask for signed-off commits (`git commit -s`) when contributor
authorization or provenance needs an explicit audit trail.

## Authorship And Research Records

For substantial research, dataset, benchmark, or evaluation work, keep a short
written record in the relevant module docs, PR body, or linked status-update
issue. Capture the motivation, design choices, experiment configuration,
outputs, blockers, and next steps. Credit collaborators who materially shaped
the work through ideas, review, datasets, or implementation.

Clear records make the migration auditable and help future paper or release
authorship discussions rely on concrete contributions rather than memory.

## What Not To Merge

Do not merge raw migration snapshot directories such as:

- `MatrAIx/`
- `MatrAIx_PR_*`
- `MatrAIx_CLOSED_PR_*`
- `MatrAIx_MERGED_PR_*`

Those are screening artifacts. Curate the useful code into the module layout
instead.

Do not check in large generated job output by default. Prefer small fixtures
under the owning module, or external storage for large datasets and run logs.

## Migration Workflow

When importing from MatrAIx:

1. Find the source PR or commit in `migration/matraix/`.
2. Decide which module owns the useful content.
3. Move only the curated files into that module.
4. Add or update module docs.
5. Run the narrowest useful validation.
6. Record the import in `docs/migration/matraix-merge-log.md`.
