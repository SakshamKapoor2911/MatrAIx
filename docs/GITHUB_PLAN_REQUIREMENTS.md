# GitHub Plan Requirements for MatrAIx Features

**Important**: Some features we've set up require a GitHub Pro or organization plan.

---

## Current Status

✅ **Set up and ready on Free plan**:
- CODEOWNERS file created and documented
- Branch protection rules (basic setup)
- Documentation hub complete
- PR workflow guide written

⏳ **Requires GitHub Pro to fully enable**:
- Require CODEOWNERS review (branch protection)
- Auto-merge on PRs

---

## GitHub Plan Comparison

| Feature | Free | Pro | Team | Enterprise |
|---------|------|-----|------|-----------|
| Basic branch protection | ✅ | ✅ | ✅ | ✅ |
| Require pull requests | ✅ | ✅ | ✅ | ✅ |
| Require approvals | ✅ | ✅ | ✅ | ✅ |
| Require status checks | ✅ | ✅ | ✅ | ✅ |
| Dismiss stale approvals | ✅ | ✅ | ✅ | ✅ |
| **Require CODEOWNERS review** | ❌ | ✅ | ✅ | ✅ |
| **Auto-merge** | ❌ | ✅ | ✅ | ✅ |

---

## What You Have Right Now (Free Plan)

✅ **Working**:
- CODEOWNERS file (`.github/CODEOWNERS`) documents team ownership
- Basic branch protection (require PR + approvals)
- Status checks requirement
- Manual reviewer requests (you select reviewers manually when PR opens)

---

## What You'll Get After Upgrading to Pro

✅ **Additional**:
- **Automatic CODEOWNERS request**: When PR touches `personas/`, @YuexingHao auto-requested (no manual pinging)
- **Auto-merge**: PR auto-merges once approved + checks pass
- **Faster iteration**: No manual merge clicks, no manual reviewer requests

---

## Upgrade Path

When you're ready (can be any time):

1. **Go to**: GitHub → Your Account → Settings → Billing → Plans
2. **Upgrade to GitHub Pro**: $4/month
3. **Wait 5 minutes** for GitHub to re-index CODEOWNERS
4. **Go to**: MatrAIx repo → Settings → Branches → [main] rule
5. **Enable**: "Require review from Code Owners" ✅
6. **Enable**: "Allow auto-merge" ✅
7. **Save**

That's it! Full setup is live.

---

## For Now (Free Plan)

### Current Branch Protection (Ready to enable)

1. Go to: Settings → Branches → Add rule for "main"
2. Check these:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (set to: 2)
   - ✅ Dismiss stale pull request approvals
   - ✅ Require status checks to pass
   - ❌ "Require review from Code Owners" (greyed out - needs Pro)
   - ❌ "Allow auto-merge" (greyed out - needs Pro)
3. Save

### Manual Process (Until Pro upgrade)

When a PR opens:
- **If PR touches `personas/`** → Request review from @YuexingHao
- **If PR touches `environments/`** → Request review from @JianhengHao
- **If PR touches `applications/`** → Request review from @ShirleyHuang11
- **If PR touches `docs/`** → Request review from @XiaominLi1998
- **If multiple folders** → Request all relevant reviewers

Then merge manually after approval + CI passes.

---

## Timeline

**Now** (Free plan):
- Basic protection works
- Manual reviewer requests
- Manual merge

**Later** (Pro plan, $4/month):
- Auto-request reviewers
- Auto-merge
- Full professional setup

---

## Cost Estimate

| Plan | Cost | Best For |
|------|------|----------|
| **Free** | $0 | Solo projects, very small teams |
| **GitHub Pro** | $4/month | Individual developers, small teams |
| **GitHub Team** | $21/month | Teams (5-20 people) |
| **GitHub Enterprise** | Custom | Large organizations |

For MatrAIx with 4+ active contributors, **GitHub Pro ($4/month) is worth it** for the auto-request + auto-merge features.

---

## Recommendation

1. **Use free plan now** with manual reviewer requests (fully functional)
2. **Upgrade when budget allows** ($4/month for Pro)
3. **Everything is already set up** — just flip the switch when you upgrade

---

**See also**:
- [CODEOWNERS Troubleshooting](./CODEOWNERS_TROUBLESHOOTING.md)
- [PR & Review Management](./PR_AND_REVIEW_MANAGEMENT.md)
- [Branch Protection Setup](./BRANCH_PROTECTION_SETUP.md)

---

**Last updated**: 2026-06-21
