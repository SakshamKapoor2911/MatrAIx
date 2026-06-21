# PR Review Checklist

Use this checklist when reviewing PRs for MatrAIx.

---

## For All PRs

- [ ] **Scope**: Does the PR do one thing well? (Avoid mega-PRs)
- [ ] **Title**: Clear, concise title matching the commit message style
- [ ] **Description**: Links to related issues (#XXX), explains why this change
- [ ] **Tests**: Includes test(s) or clear explanation why tests aren't needed
- [ ] **Docs**: Updates relevant documentation or admits what's missing
- [ ] **No breaking changes**: Or clear migration path if breaking

---

## For Deduplication PRs

- [ ] **Dimensions file**: JSON is valid (passes `jq`)
- [ ] **Deletions verified**: Exact count matches description
- [ ] **Code references**: All references to deleted dims removed or consolidated
- [ ] **No orphaned references**: Grep confirms no stray references
- [ ] **Test suite passes**: Full persona generation test suite green
- [ ] **Spot-check**: ~5-10 sample personas render correctly post-change
- [ ] **Commit message**: Notes dimension count before/after

---

## For Persona Generation PRs

- [ ] **Personas valid**: 20+ sample personas generated and inspected
- [ ] **Metadata preserved**: ID, created_at, source, dimensions intact
- [ ] **No data loss**: Personas post-change match expected structure
- [ ] **Performance**: No unexpected slowdown (profile if uncertain)
- [ ] **Backwards compatible**: Or clear migration path for existing personas

---

## For Documentation PRs

- [ ] **Clarity**: Readable to someone unfamiliar with the topic
- [ ] **Completeness**: Answers most common questions (or links to details)
- [ ] **Examples**: Includes examples or commands (when relevant)
- [ ] **Links**: Internal links work, external links are stable

---

## For Cross-Team PRs

- [ ] **Compatibility**: Doesn't break other teams' workflows
- [ ] **Team notification**: Tag relevant team in the PR (e.g., @persona-team)
- [ ] **Integration**: Clear how this integrates with other systems

---

## Approval Criteria

**Approve** if:
- All checks pass
- No outstanding concerns
- Scope is clear and contained

**Request changes** if:
- Critical issues (test failures, breaking changes without migration)
- Significant clarity gaps
- Schema violations

**Comment for future** if:
- Nice-to-have improvements that can be deferred
- Follow-up work suggested

---

## Red Flags

⚠️ **Don't merge if**:
- Tests are failing
- Deletes dimensions without verification
- Removes code references without checking impact
- Changes schema without team discussion
- Breaking changes undocumented

---

**Template for comments**:
```markdown
Great work on this! A few things:

1. [Specific comment]
2. [Specific comment]

Can you address these, or should we defer to a follow-up PR?
```

---

**Last updated**: 2026-06-21
