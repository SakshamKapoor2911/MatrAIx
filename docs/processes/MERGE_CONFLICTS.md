# Merge Conflict Resolution Guide

**How to avoid and resolve merge conflicts in MatrAIx**

---

## Prevention

### Coordinate Before Touching Shared Files

**High-conflict files** (always coordinate):
- `personas/dimensions+new.json` — schema definition
- `personas/ID0001-ID1000/*.yaml` — persona definitions

**Lower-conflict files** (coordinate if working on same area):
- `environments/`, `applications/` — own your area
- `docs/` — can usually merge cleanly (fork-merge strategy)

### Communication Strategy

Before starting work that touches `dimensions+new.json` or persona files:
1. Post to Discussions: `📋 Weekly Standups` — "I'm working on [task]"
2. Check [TEAM_ASSIGNMENTS.md](../TEAM_ASSIGNMENTS.md) — is someone else on this?
3. If conflict risk > 0%, open a GitHub Issue and discuss approach

---

## Resolving Conflicts

### 1. Pull & Identify Conflicts

```bash
cd /home/yuexing/MatrAIx
git fetch origin
git pull origin main
# Git will report: "CONFLICT (content merge)"
```

### 2. Check the Conflict

```bash
git status
# Shows: "both modified: dimensions+new.json" (example)
```

### 3. View Conflict Markers

```bash
git diff dimensions+new.json | head -50
# Markers:
# <<<<<<< HEAD           (your version)
# [your changes]
# =======
# [their changes]
# >>>>>>> origin/main
```

### 4. Resolve Conflict

**For JSON files** (dimensions+new.json):
```bash
# Option A: Keep yours
git checkout --ours dimensions+new.json

# Option B: Keep theirs
git checkout --theirs dimensions+new.json

# Option C: Manual merge (recommended)
# Use a JSON editor to combine both versions
```

**For Markdown files** (docs, README):
```bash
# Manually edit the file, remove conflict markers
# Combine changes logically
# Test that markdown renders correctly
```

**For code files** (Python):
```bash
# Manually edit, test thoroughly
# Run test suite to verify no breakage
```

### 5. Validate Post-Merge

```bash
# For JSON:
jq . personas/dimensions+new.json > /dev/null && echo "Valid JSON"

# For Python:
python -m pytest tests/ -v

# For docs:
# Just check rendering in your viewer
```

### 6. Complete the Merge

```bash
git add .
git commit -m "Resolve merge conflict: [description]"
git push origin main  # or your branch
```

---

## Common Scenarios

### Scenario 1: Both You & Someone Else Deleted Different Dimensions

**Conflict**: Both deleted, git can't merge

**Resolution**:
1. Check `git log --oneline` to understand both deletions
2. Verify both deletions are intended (check related PRs)
3. Confirm final dimension count matches both expectations
4. Resolve to reflect both deletions

```bash
git checkout --ours dimensions+new.json
# (or --theirs, depending on which has both deletions)
```

### Scenario 2: Both You & Someone Else Modified Same Dimension

**Conflict**: Different changes to same dimension object

**Resolution**:
1. Manually open JSON in editor
2. Identify the dimension: `"id": "..."` (use find)
3. Merge both changes into single definition
4. Validate with `jq .[] | select(.id == "...");`

```json
// BEFORE (conflict)
<<<<<<< HEAD
{
  "id": "foo",
  "value": [1, 2, 3],  // YOUR change
  "description": "old"
}
=======
{
  "id": "foo",
  "value": [1, 2, 3],
  "description": "new"   // THEIR change
}
>>>>>>> origin/main

// AFTER (resolved)
{
  "id": "foo",
  "value": [1, 2, 3],
  "description": "new"   // Keep the better description
}
```

### Scenario 3: Documentation Merge

**Conflict**: Both added content to same doc file

**Resolution**:
1. Manually edit the file
2. Remove conflict markers `<<<<`, `====`, `>>>>`
3. Combine content logically (chronological, thematic, etc.)
4. Check markdown renders

```markdown
// BEFORE
<<<<<<< HEAD
## Your Section
Content...
=======
## Their Section
Content...
>>>>>>> origin/main

// AFTER (combine both)
## Your Section
Content...

## Their Section
Content...
```

---

## When to Ask for Help

**Post to Discussions** if:
- Conflict is in `dimensions+new.json` and affects many dimensions
- You're unsure which version is "correct"
- Conflict seems like a bug (both should work together)
- Manual merge is getting complex

**@ mention** the original PR author to discuss.

---

## Tools That Help

### Merge Tool: `meld` (visual diff)
```bash
git mergetool --tool=meld
# Opens visual 3-way merge (left=theirs, middle=merged, right=ours)
```

### Check Merge Without Committing
```bash
git merge origin/main --no-commit --no-ff
git status  # Review changes
git merge --abort  # Back out if needed
```

### Validate After Merge
```bash
# For JSON
jq . personas/dimensions+new.json > /dev/null && echo "✓ Valid"

# For Python
python -m pytest tests/test_persona_generation.py -v

# For docs
# Just visually scan the file
```

---

## Best Practices

1. **Communicate early**: Tell team before you start large changes
2. **Commit small**: Smaller commits = easier to merge
3. **Test before pushing**: Don't push code you haven't tested
4. **Pull frequently**: `git pull origin main` often reduces conflicts
5. **When stuck**: Ask in Discussions, don't force-push

---

## Escalation Path

1. **Can't resolve?** Post to Discussions with conflict markers
2. **Urgent?** Tag @Yuexing or team lead
3. **Still stuck?** Pair program with someone to resolve together

---

**Last updated**: 2026-06-21
