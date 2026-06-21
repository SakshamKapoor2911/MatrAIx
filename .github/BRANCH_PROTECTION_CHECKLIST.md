# Branch Protection Implementation Checklist

**Quick reference for setting up GitHub branch protection rules**

---

## Pre-Setup

- [ ] All team members have GitHub accounts
- [ ] All team members have been invited to the repo
- [ ] You have admin access to the repo

---

## Step-by-Step Setup

### 1. Navigate to Branch Settings
```
GitHub → MatrAIx Repository → Settings → Branches
```

### 2. Create Rule for `main`
- [ ] Click "Add rule"
- [ ] Enter branch name pattern: `main`

### 3. Pull Request Requirements
- [ ] ✅ Require a pull request before merging
- [ ] ✅ Require approvals
  - [ ] Set to **2** for code changes
  - [ ] Set to **1** for docs-only changes (honor system)
- [ ] ✅ Dismiss stale pull request approvals when new commits are pushed
- [ ] ✅ Require review from Code Owners

### 4. Status Checks
- [ ] ✅ Require status checks to pass before merging
- [ ] ✅ Require branches to be up to date before merging
- [ ] Add specific checks (once CI is set up):
  - [ ] `tests` (or equivalent)
  - [ ] `lint` (or equivalent)

### 5. Auto-Merge
- [ ] ✅ Allow auto-merge
- [ ] Select merge method: **Squash and merge** (recommended)

### 6. Additional Protections
- [ ] ✅ Require conversation resolution before merging
- [ ] ✅ Restrict who can dismiss reviews (only admins)
- [ ] ❌ Do NOT allow force pushes
- [ ] ❌ Do NOT allow deletions

### 7. Save
- [ ] Click **"Create"** or **"Save changes"**

---

## Verify CODEOWNERS

- [ ] `.github/CODEOWNERS` file exists
- [ ] Contains entries for:
  - [ ] `personas/ @YuexingHao`
  - [ ] `environments/ @JianhengHou`
  - [ ] `applications/ @ShirleyHuang11`
  - [ ] `docs/ @XiaominLi1998`
  - [ ] `* @YuexingHao` (global fallback)

---

## Test It

Create a test PR to verify everything works:

- [ ] Create a test branch
- [ ] Make a small change (e.g., update README)
- [ ] Open PR to `main`
- [ ] Verify: CODEOWNERS reviewers auto-requested?
- [ ] Request approval from reviewer
- [ ] Verify: Can't merge without approval?
- [ ] Approve and merge
- [ ] Verify: Auto-merge works (if enabled)
- [ ] Check: Commit appears on main with squash?

---

## Team Communication

- [ ] Announce new review rules in Discussions
- [ ] Explain: "CODEOWNERS will auto-request your review for PRs touching your folder"
- [ ] Provide link: `docs/BRANCH_PROTECTION_SETUP.md`
- [ ] Remind: "Please review PRs promptly; auto-merge triggers once approved"

---

## Ongoing Maintenance

**Weekly**:
- [ ] Check for stalled PRs (stuck waiting for approval)
- [ ] Monitor CI failures

**When team changes**:
- [ ] Update `.github/CODEOWNERS`
- [ ] Announce in Discussions

**When CI changes**:
- [ ] Update branch protection to require new status checks
- [ ] Document in `docs/BRANCH_PROTECTION_SETUP.md`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| PR shows "Requires review from Code Owners" but no one is requested | Check CODEOWNERS syntax. Run: `git check-attr codeowners <file>` |
| Can't enable auto-merge | Verify all approvals & checks are passing |
| Reviewer not getting notified | Check CODEOWNERS email settings, team notifications |
| Need to override & merge immediately | Admins can bypass protections (use sparingly) |

---

## Quick Links

- [Full Setup Guide](../docs/BRANCH_PROTECTION_SETUP.md)
- [CODEOWNERS File](./.github/CODEOWNERS)
- [GitHub Branch Protection Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)

---

**Last updated**: 2026-06-21  
**Estimated setup time**: 15 minutes  
**Difficulty**: Easy
