# PR and Review Management Setup

**How MatrAIx handles pull requests, code reviews, and auto-merge**

---

## Current Configuration (2026-06-21)

### ✅ CODEOWNERS (Active)

```
personas/       @YuexingHao
environments/   @JianhengHou
applications/   @ShirleyHuang11
docs/           @XiaominLi1998
* (global)      @YuexingHao
```

**What this means**:
- When a PR touches `personas/`, @YuexingHao is auto-requested for review
- When a PR touches `environments/`, @JianhengHou is auto-requested
- When a PR touches `applications/`, @ShirleyHuang11 is auto-requested
- When a PR touches `docs/`, @XiaominLi1998 is auto-requested
- For any other changes, @YuexingHao is the fallback

---

## ⏳ Pending Setup (You Need to Do)

### 1. Branch Protection Rules (15 min)

**What**: Require approvals + status checks before merging to `main`

**Steps**:
1. Go to GitHub: MatrAIx → Settings → Branches
2. Click "Add rule" for `main` branch
3. Follow the checklist in `.github/BRANCH_PROTECTION_CHECKLIST.md`
4. Save

**Key settings**:
- ✅ Require PR before merge
- ✅ Require CODEOWNERS review (already have file)
- ✅ Require status checks (1+ passing)
- ✅ Auto-merge enabled (optional, but recommended)

**See**: [BRANCH_PROTECTION_SETUP.md](BRANCH_PROTECTION_SETUP.md)

### 2. Status Checks / CI (Optional but Recommended)

**What**: Automated tests/lint that must pass before merging

**Examples**:
- `pytest` for unit tests
- `pylint` for code quality
- `black` for formatting

**How to set up**:
1. Create `.github/workflows/tests.yml` (GitHub Actions)
2. Add pytest + lint steps
3. Once workflow runs, check will appear in branch protection settings

**See**: [BRANCH_PROTECTION_SETUP.md](BRANCH_PROTECTION_SETUP.md#setting-up-ciStatus-checks)

---

## Workflow for Team Members

### Creating a PR

1. **Create feature branch** from `main`
   ```bash
   git checkout main && git pull
   git checkout -b feature/my-change
   ```

2. **Make changes and commit**
   ```bash
   git add .
   git commit -m "Clear description of change"
   ```

3. **Push to GitHub**
   ```bash
   git push origin feature/my-change
   ```

4. **Open PR**
   - GitHub shows a "Create Pull Request" button
   - Fill in title (clear, concise)
   - Fill in description (why this change, what it fixes)
   - Link related issues (#XXX)

5. **Wait for automatic actions**
   - CODEOWNERS reviewer auto-requested
   - CI checks run automatically
   - Status appears in PR (✅ passing or ❌ failing)

### Reviewing a PR

1. **You're notified** (auto-requested via CODEOWNERS)
2. **Open the PR** and review:
   - Code quality (style, naming, structure)
   - Test coverage (are tests included?)
   - Documentation (is it documented?)
   - Architecture (does it fit the system?)
3. **Leave comments**
   - Click "Review changes"
   - Select "Approve" or "Request changes"
   - Add summary comment if needed
4. **The PR author addresses feedback**
5. **Once approved + CI passes, PR auto-merges** (if enabled) OR author clicks merge

### After Merge

- The feature branch is automatically deleted (GitHub option)
- Commit appears on `main` (squashed or merged based on settings)
- CI runs on `main` to verify nothing broke

---

## Approval Strategy

### For Code Changes (personas/, environments/, applications/)

**Minimum**: 1 approval from CODEOWNERS (the team member assigned to that folder)

**Recommended**: 2 approvals for larger changes

**How to request 2nd approval**:
- Manual: Ask in PR comment
- Semi-automatic: Create branch protection rule requiring 2 approvals for code folders
- Culture-based: Document in CONTRIBUTION.md that large changes need 2 reviews

### For Documentation Changes (docs/)

**Minimum**: 1 approval from @XiaominLi1998 (docs CODEOWNER)

**Exception**: Minor fixes (typos, links) can be merged faster if CI passes

---

## Managing Stalled PRs

### If a PR is stuck waiting for approval:

1. **Check why**: 
   - Reviewer hasn't seen it? → Tag them in a comment
   - Reviewer too busy? → Escalate to Yuexing
   - PR unclear? → Author should improve description

2. **Process**:
   - If > 3 days with no response → ping in Discussions
   - If > 1 week → Yuexing can approve on behalf of team lead

3. **Prevent blocking**:
   - Set team notifications to "All activity"
   - Check PR queue during weekly standups
   - Aim for 48-hour review turnaround

---

## Auto-Merge Workflow (Recommended)

**How it works**:
1. PR author clicks "Enable auto-merge" (Squash and merge)
2. System waits for all conditions:
   - All required approvals ✅
   - All status checks pass ✅
   - No conflicts with main ✅
3. Once all conditions met → PR automatically merges
4. Feature branch deleted automatically

**Why use it**:
- Faster iteration (no waiting for author to click merge)
- Consistent merge strategy (always squash = clean history)
- Reduces manual work

**When not to use**:
- If you want to review again before merge
- If PR is still getting feedback

---

## Handling Merge Conflicts

**If a PR has conflicts with main**:

1. **Author pulls latest main**:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Author resolves conflicts** in their editor

3. **Author pushes**:
   ```bash
   git push origin feature/my-change --force-with-lease
   ```

4. **Stale approvals are dismissed** (auto, by branch protection)

5. **Reviewer re-approves** (usually just a quick check)

**See**: [MERGE_CONFLICTS.md](processes/MERGE_CONFLICTS.md)

---

## Updating CODEOWNERS

**When to update**:
- New team member joins → add to relevant folder
- Team member leaves → remove from folders
- Ownership of folder changes → update reviewer

**How to update**:

1. **Edit `.github/CODEOWNERS`**
   ```
   personas/       @NewPersona
   environments/   @JianhengHou
   applications/   @ShirleyHuang11
   docs/           @XiaominLi1998
   * @YuexingHao
   ```

2. **Create PR and merge** (same as any other change)

3. **Announce in Discussions** (in `📋 Weekly Standups`)

**Example**:
```markdown
Updated CODEOWNERS: @NewPersona now owns personas/ folder.
They'll be auto-requested for PRs touching personas/.
```

---

## Best Practices

### For Authors
- [ ] Clear PR title and description
- [ ] Small, focused PRs (easier to review)
- [ ] Include tests with code changes
- [ ] Link related issues
- [ ] Respond to feedback promptly
- [ ] Enable auto-merge once approved + CI passes

### For Reviewers
- [ ] Check PR within 24-48 hours
- [ ] Leave constructive feedback
- [ ] Ask questions if unclear
- [ ] Approve when ready (don't ghost)
- [ ] Trust the author for minor changes

### For Maintainers (Yuexing)
- [ ] Monitor for stalled PRs
- [ ] Enforce review standards
- [ ] Unblock when needed
- [ ] Keep CODEOWNERS updated
- [ ] Document process changes

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| PR won't merge (blocked by check) | Check GitHub Actions logs. Fix code, push commit. Auto-retry happens. |
| Reviewer not notified | Check CODEOWNERS syntax. Try: `git check-attr codeowners <file>` |
| Need to merge urgently | Yuexing can bypass (admin only). Use sparingly. |
| Auto-merge not working | Verify all approvals + checks are green. Refresh page. |
| Conflict with main | Author rebases and force-pushes. Stale approvals dismissed. Re-review. |

---

## Next Steps

1. **Review this document** with the team
2. **Set up branch protection** (see `.github/BRANCH_PROTECTION_CHECKLIST.md`)
3. **Optionally set up CI** (see BRANCH_PROTECTION_SETUP.md)
4. **Test with a sample PR** (before enforcing on all PRs)
5. **Announce in Discussions** (explain the new workflow)

---

## Links

- [CODEOWNERS File](./.github/CODEOWNERS)
- [Branch Protection Setup](docs/BRANCH_PROTECTION_SETUP.md)
- [Branch Protection Checklist](./.github/BRANCH_PROTECTION_CHECKLIST.md)
- [PR Review Checklist](docs/PR_REVIEW_CHECKLIST.md)
- [Merge Conflict Resolution](docs/processes/MERGE_CONFLICTS.md)

---

**Last updated**: 2026-06-21  
**Owner**: Yuexing  
**Team**: @YuexingHao, @JianhengHou, @ShirleyHuang11, @XiaominLi1998
