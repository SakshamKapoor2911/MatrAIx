# CODEOWNERS Troubleshooting

**Why is "Require review from Code Owners" greyed out?**

---

## Quick Fixes (Try These First)

### 1. Clear Browser Cache & Refresh
- Hard refresh GitHub page: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Close settings and reopen
- This fixes 80% of "greyed out" issues

### 2. Verify Users Have Access
The users in CODEOWNERS must be **members** of the repository:

```
GitHub → MatrAIx → Settings → Collaborators and teams
```

Check that these users have access:
- @YuexingHao
- @JianhengHao
- @ShirleyHuang11
- @XiaominLi1998

If any are missing → Invite them first (Settings → Invite collaborator)

### 3. Verify CODEOWNERS File Syntax

GitHub requires the file at: `.github/CODEOWNERS`

Check syntax:
```bash
# Lines should be: path @username @username2
# Example:
personas/ @YuexingHao
environments/ @JianhengHao
```

Common syntax errors that break it:
- ❌ Wrong path (e.g., `persona/` instead of `personas/`)
- ❌ Invalid username format (e.g., `@ username` with space)
- ❌ No @ symbol
- ❌ Trailing spaces

---

## If Refresh Doesn't Work

### Option A: Use GitHub Teams (More Reliable)

If individual usernames keep failing, use GitHub Teams instead:

**Step 1**: Create teams in organization
```
GitHub → Organization Settings → Teams → New team
```

Create:
- `@MatrAIx-ai/persona-team` → add @YuexingHao
- `@MatrAIx-ai/environment-team` → add @JianhengHao
- `@MatrAIx-ai/application-team` → add @ShirleyHuang11
- `@MatrAIx-ai/docs-team` → add @XiaominLi1998

**Step 2**: Update CODEOWNERS to use teams
```
personas/ @MatrAIx-ai/persona-team
environments/ @MatrAIx-ai/environment-team
applications/ @MatrAIx-ai/application-team
docs/ @MatrAIx-ai/docs-team
* @YuexingHao
```

**Step 3**: Commit and push

### Option B: Add Users to a Read-Only Group

Some organizations require users to be in a "Team" rather than just collaborators:

```
GitHub → Organization Settings → Teams → Select team
→ Click "Members"
→ Add the users
```

---

## Verification Checklist

Before trying to enable CODEOWNERS again, verify:

- [ ] All 4 users have **Write** access to the repository (not just Read)
- [ ] CODEOWNERS file is at `.github/CODEOWNERS` (not `.githubignore` or other location)
- [ ] File syntax is correct (each line: `path @user`)
- [ ] No trailing spaces in file
- [ ] File is committed and pushed to `main` branch
- [ ] Browser cache cleared (hard refresh)
- [ ] CODEOWNERS setting is on a fresh browser tab

---

## After You've Done the Above

1. **Close branch protection settings** (if still open)
2. **Wait 5 minutes** (GitHub sometimes needs time to index CODEOWNERS)
3. **Go back to**: Settings → Branches → [main] protection rule
4. **Check if "Require review from Code Owners" is now enabled**

If still greyed out → Scroll down and look for an error message (GitHub shows it sometimes)

---

## If All Else Fails

**Temporary Workaround**: Skip the CODEOWNERS checkbox for now

1. **Enable these instead**:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (set to: 2)
   - ✅ Dismiss stale pull request approvals
   - ✅ Require status checks to pass
   - ✅ Allow auto-merge

2. **Manual process** (instead of auto-request):
   - When someone opens a PR touching `personas/`, manually request @YuexingHao
   - When PR touches `environments/`, manually request @JianhengHao
   - Etc.

3. **Come back to CODEOWNERS** once the greyed-out issue is resolved

---

## GitHub Docs

- [CODEOWNERS Official Docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
- [Teams in Organizations](https://docs.github.com/en/organizations/organizing-members-into-teams)

---

## Common Causes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Greyed out, no error message | Browser cache | Hard refresh (Ctrl+Shift+R) |
| Greyed out, error shown | CODEOWNERS syntax error | Check file format |
| Greyed out, users added | Users lack Write access | Give them Write permissions |
| Not auto-requesting | File not found/not on main | Verify committed + pushed |
| Wrong users requested | Path match issue | Test with a PR (see exact matches) |

---

**Still stuck?** Check the error message GitHub shows under the setting, or ask @YuexingHao in repo Discussions.

---

**Last updated**: 2026-06-21
