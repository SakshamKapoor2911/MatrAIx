# Contributing to PersonaBench

PersonaBench is built by three teams — **Persona**, **Application**, and
**Environment**. This guide covers workflow (Issues, Discussions, PRs), where
each team works in the repo, and how contribution is recognized.

## Contribution flow

1. **Choose your team(s)** — read the team docs below. One PR can touch multiple
   teams; tag every team involved.
2. **Open or pick an Issue** — Issues are for todos, task proposals, and bugs.
   The **creator** tags `team: persona|environment|application`. Either **assign
   yourself** and start work, or leave it open for someone else to claim in a
   comment.
3. **Log progress in Discussions** — Discussions are for your contribution
   history (design notes, experiments, weekly updates). Keep one long-lived
   thread; append dated posts. Do not use Issues for this.
4. **One Issue per PR** — every PR must link the Issue it implements
   (`Fixes #123`). Drive-by PRs without a linked Issue are closed. You may also
   link your Discussion thread in the PR body.
5. **Write the PR clearly** — what changed, why, how you tested. Link the Issue;
   use `git commit -s`.
6. **Merge** — CI must pass. At least **one** approval from a maintainer or the
   relevant team reviewer is required before merge.

Org members: branch on this repo. Everyone else: **fork** and PR from your fork.

Questions: [Discord](https://discord.gg/vruP88PTZ) ·
[Google Form](https://forms.gle/hwEHng5HGWRqcJue9).

### Teams — paths and where to start

| Team | Main paths | Start here |
|------|------------|------------|
| **Persona** | `persona/` | [docs/personas/README.md](docs/personas/README.md) |
| **Application** | `application/` | [application/README.md](application/README.md) · [QUICKSTART.md](application/QUICKSTART.md) |
| **Environment** | `environment/`, `configs/jobs/`, Cockpit, harbor view | [environment/README.md](environment/README.md) |

Running simulations: [choosing-an-agent.md](application/choosing-an-agent.md).

---

## Contributing points

**How contribution is recognized**

- **Task work** — Persona bench tasks, application tasks, and runnable examples:
  **count and quality** of merged work in the repo. **Only merged task PRs count.**
- **Everything else** — research, schema, datasets, infra, agents, etc.:
  **effort** as reviewed by team reviewers and maintainers, primarily from your
  **Discussion** thread and linked PRs.

| Team | Contribution area | Recognized by |
|------|-------------------|---------------|
| **Persona** | Persona survey and related-work research | Effort |
| | Dataset curation | Effort |
| | Dimension and persona schema | Effort |
| | Persona bench task design (grounding) | Effort |
| | Persona bench task curation | Task count & quality |
| **Environment** | Runtime infrastructure, agents, execution planes | Effort |
| | Persona / application task pipelines | Task count & quality |
| | Cockpit, harbor view, run inspection | Effort |
| **Application** | Application task development (scenarios, metrics, verifiers) | Task count & quality |
| | Research or demo development | Effort |

---

## Modules

| Module | Owns | Does not own |
| --- | --- | --- |
| `persona/` | Persona schema, attributes, curated datasets, curation scripts, adherence tasks | Runtime drivers, product scenarios, checked-in job outputs |
| `application/` | Survey/chat/web/os-app scenarios, metrics, tasks, task specs | Persona source datasets, runtime engines |
| `environment/` | Harbor runtime, persona agents, job recipes, Cockpit, harbor view, execution backends | Persona schema decisions, application-specific research claims |
| `packages/` | Reusable libraries used by multiple modules | One-off scripts or generated outputs |

## PR expectations

Every PR should include:

- The module or modules it touches.
- The source issue, when applicable.
- A short explanation of why the change belongs in that module.
- Test or validation commands that were run.
- Any generated data policy decision, especially for large files.

## What not to merge

Do not merge raw migration snapshot directories such as `MatrAIx/`,
`MatrAIx_PR_*`, `MatrAIx_CLOSED_PR_*`, or `MatrAIx_MERGED_PR_*`. Curate useful
code into the module layout instead.

Do not check in large generated job output by default. Prefer small fixtures
under the owning module, or external storage — see
[migration/matraix/README.md](migration/matraix/README.md).

## Basics

- **License:** Apache 2.0. No confidential data, PII, or secrets in the repo.
- **Setup:** see [README.md — Installation](README.md#installation).

## Migration workflow

When importing from MatrAIx:

1. Find the source PR or commit in `migration/matraix/`.
2. Decide which module owns the useful content.
3. Move only the curated files into that module.
4. Add or update module docs.
5. Run the narrowest useful validation.
6. Record the import in `docs/migration/matraix-merge-log.md`.
