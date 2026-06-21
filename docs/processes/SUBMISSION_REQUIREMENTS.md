# Submission Requirements for Contributors

**What we expect in PRs, issues, and contributions to MatrAIx**

---

## For All Contributions

### Code Submissions
- [ ] Follows project style (see Contribution.md)
- [ ] Includes tests (if applicable)
- [ ] Passes linting / style checks
- [ ] No breaking changes (or clear migration path)
- [ ] Documented in relevant README or docs/

### Documentation Submissions
- [ ] Clear and concise
- [ ] Examples included (where helpful)
- [ ] Links to related docs
- [ ] No dead links

### Data Submissions
- [ ] Validates against schema
- [ ] Passes test suite
- [ ] Includes metadata (source, date, validation status)

---

## For Persona Data

- [ ] All required dimensions present
- [ ] Values are valid (match dimension spec)
- [ ] IDs are unique
- [ ] No invalid JSON
- [ ] Sample personas have been generated and spot-checked

---

## For Dimension Schema Changes

- [ ] Clear justification (issue #XXX)
- [ ] Backwards compatible (or migration plan)
- [ ] Existing personas still generate correctly
- [ ] All code references updated
- [ ] Test suite passes

---

## For Documentation

- [ ] Markdown is valid
- [ ] No dead internal links
- [ ] Appropriate detail level for audience
- [ ] Examples where helpful

---

## Review Process

1. **Submission**: Create PR with clear description
2. **CI checks**: Automated tests run
3. **Peer review**: Team member reviews for correctness + style
4. **Approval**: 1 approval from team lead required
5. **Merge**: Squash if lots of commits, merge to main

---

## Checklist for Submitters

Before submitting your PR:

- [ ] Commit message is clear and references issue #XXX
- [ ] All tests pass locally
- [ ] No new warnings or errors
- [ ] Documentation updated
- [ ] Ready for review (not draft)

---

**Last updated**: 2026-06-21

**See also**: [../PR_REVIEW_CHECKLIST.md](../PR_REVIEW_CHECKLIST.md), [Contribution.md](../../Contribution.md)
