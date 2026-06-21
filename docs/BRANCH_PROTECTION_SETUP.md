# Branch Protection & Auto-Merge Setup Guide

**How to configure GitHub branch protection rules for MatrAIx main branch**

---

## Overview

This guide walks you through setting up:
1. **Branch protection rules** (require approvals + checks)
2. **Auto-merge** (automatically merge when conditions are met)
3. **Status checks** (require passing tests/linting)
4. **CODEOWNERS** (auto-request reviewers) — ✅ Already done

---

## Current Team Structure

### CODEOWNERS (Already Updated ✅)

```
personas/       @YuexingHao
environments/   @JianhengHou
applications/   @ShirleyHuang11
docs/           @XiaominLi1998
* (global)      @YuexingHao
```

When a PR touches a folder, that folder's owner is **automatically requested** for review.

---

## Step 1: Enable Branch Protection Rule

**Go to**: GitHub Repository → Settings → Branches → Branch protection rules

### Create Rule for `main` Branch

1. Click **"Add rule"**
2. **Branch name pattern**: `main`
3. Configure the following settings (detailed below)

---

## Step 2: Configure Approval Requirements

**Require a pull request before merging**
- ✅ Check this box

**Require approvals**
- ✅ Check this box
- **Required number of approvals before merging**: Set based on type:
  - **For docs changes**: 1 approval (faster iteration)
  - **For code changes**: 2 approvals (more rigorous)
  - **Solution**: Use branch pattern rules (see below)

**Dismiss stale pull request approvals when new commits are pushed**
- ✅ Recommended (prevents approving old code)

**Require review from Code Owners**
- ✅ Check this box
- Automatically requests reviewers from CODEOWNERS file

**Restrict who can dismiss pull request reviews**
- ✅ Check this box (only you or admins can dismiss)

---

## Step 3: Require Status Checks to Pass

**Require status checks to pass before merging**
- ✅ Check this box

**Require branches to be up to date before merging**
- ✅ Recommended (keeps main clean)

**Status checks that must pass**:
- Add each CI/test check your repo runs. Examples:
  - `tests` (Python pytest)
  - `lint` (Code quality)
  - `build` (If applicable)
  
*Note*: You'll see available checks once you have CI set up.

---

## Step 4: Enable Auto-Merge

**Allow auto-merge**
- ✅ Check this box
- **Type**: "Squash and merge" (recommended for clean history)
  - Or "Create a merge commit" if you prefer

**How it works**:
- PR author clicks "Enable auto-merge"
- Once all conditions are met (approvals + checks pass), PR auto-merges

---

## Step 5: Additional Options (Optional)

**Require conversation resolution before merging**
- ✅ Recommended (all comments must be resolved)

**Require linear history**
- ✅ Optional (prevents messy merge commits)

**Allow force pushes**
- ❌ Not recommended for `main`

**Allow deletions**
- ❌ Not recommended for `main`

---

## Recommended Settings Summary

| Setting | Value | Why |
|---------|-------|-----|
| Require PR before merge | ✅ | Code review is mandatory |
| Require CODEOWNERS review | ✅ | Right people review right code |
| Require status checks | ✅ | Automated quality gates |
| Branches up to date | ✅ | Prevents conflicts/surprises |
| Auto-merge enabled | ✅ | Faster iteration (once approved) |
| Squash and merge | ✅ | Clean git history |
| Conversation resolution | ✅ | All feedback addressed |

---

## Two-Tier Approval Strategy

For **flexible approvals** (1 for docs, 2 for code), GitHub recommends using multiple branch rules:

### Rule 1: For Documentation (1 approval)
- **Branch name pattern**: `main`
- **Paths**: `docs/**`, `README.md`, `*.md`
- **Required approvals**: 1
- **Status checks**: Pass (basic)

### Rule 2: For Code (2 approvals)
- **Branch name pattern**: `main`
- **Paths**: `personas/**`, `environments/**`, `applications/**`
- **Required approvals**: 2
- **Status checks**: Pass (all)

*Note*: GitHub doesn't support per-path approval counts in a single rule. Use `CODEOWNERS` + 2 approvals globally, document that docs need only 1 (honor system), or use GitHub Actions to enforce.

---

## Setting Up CI/Status Checks

For status checks to work, you need CI configured. Quick setup options:

### GitHub Actions (Simplest)

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest
      - run: pylint personas/ environments/ applications/
```

Then the "tests" check will appear in branch protection settings.

---

## Workflow After Setup

### For PR Authors

1. Create PR (from feature branch)
2. Make changes, push commits
3. CODEOWNERS reviewers auto-requested
4. CI runs (tests, lint) automatically
5. Once approved + CI passes:
   - [ ] Author clicks "Enable auto-merge" (if using that)
   - OR manually click "Merge" button

### For Reviewers

1. Notified automatically (CODEOWNERS)
2. Review code in GitHub PR interface
3. Request changes or Approve
4. PR auto-merges once all conditions met

### For Yuexing (Maintainer)

- Monitor for stuck PRs (feedback not addressed, checks failing)
- Enforce culture: "merge when ready, review thoroughly"
- Update CODEOWNERS as team changes

---

## Troubleshooting

### "PR can't merge — missing approval"
- **Check**: Has folder owner approved?
- **CODEOWNERS**: Make sure it matches the file (see above)

### "CI check is not appearing"
- **Check**: Is CI workflow set up? See "Setting Up CI/Status Checks" above
- **Note**: Checks appear once workflow runs

### "Stale approval — what do I do?"
- **Setting**: "Dismiss stale approvals" is enabled
- **Action**: Author pushes a new commit → previous approvals dismissed → re-request approval

### "Can't enable auto-merge"
- **Check**: Do all approval + CI conditions pass?
- **Note**: Auto-merge button only appears once everything is green

---

## Manual Checklist Before Merging

Even with auto-merge, do a final review:

- [ ] PR title is clear
- [ ] Description explains why (not just what)
- [ ] Code follows project style
- [ ] Tests pass (green CI)
- [ ] No unresolved conversations
- [ ] CODEOWNERS approved
- [ ] Ready for production

---

## CODEOWNERS Reference (Current)

```
personas/       @YuexingHao
environments/   @JianhengHou
applications/   @ShirleyHuang11
docs/           @XiaominLi1998
* (global)      @YuexingHao
```

**Update when**:
- Team members join/leave
- Ownership of folders changes

**How to update**:
- Edit `.github/CODEOWNERS`
- PR the change
- Merge normally (doesn't require its own CODEOWNERS approval)

---

## Links & Resources

- [GitHub Docs: Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [GitHub Docs: CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Docs: Auto-merge](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request)

---

## Status Checklist

After completing setup:

- [ ] Branch protection rule created for `main`
- [ ] Require PR before merge: ✅
- [ ] Require CODEOWNERS review: ✅
- [ ] Require status checks: ✅
- [ ] Auto-merge enabled: ✅
- [ ] CODEOWNERS file updated: ✅ (done)
- [ ] CI/tests workflow created: (optional but recommended)

---

**Last updated**: 2026-06-21  
**Setup by**: Claude Code  
**Maintained by**: Yuexing + team leads
