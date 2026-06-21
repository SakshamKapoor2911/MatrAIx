# GitHub Issues Template — Copy & Paste to Create

Use these templates to create GitHub Issues for the deduplication work and team coordination.

---

## Issue 1: Phase 1.1 — Delete SynthLabs Placeholders (33 dimensions)

**Title**: `[dedup:p1.1] Delete 33 SynthLabs placeholder dimensions`

**Labels**: `dedup:`, `team:persona`, `priority:p0`, `help-wanted`

**Milestone**: (none, or create "Dedup Phase 1: Cleanup" if not exists)

**Body**:
```markdown
## Problem
33 SynthLabs placeholder dimensions have value=['Unknown'] and contribute zero variance. They should be deleted.

## Impact
- Clutters schema with dead weight
- Blocks Phase 2 and downstream work
- Blocking Env & App teams from integration

## What to do
1. Find all dimensions with `contrib_id == "synthlab_*"` in `personas/dimensions+new.json`
2. Verify exactly 33 dimensions match
3. Delete them from the JSON
4. Commit: "Delete 33 SynthLabs placeholder dimensions (zero variance)"
5. Push to PR

## Acceptance Criteria
- [ ] All 33 dimensions deleted from JSON
- [ ] JSON is valid (`jq . dimensions+new.json`)
- [ ] Verification: `jq '[.[] | select(.contrib_id | startswith("synthlab_"))] | length'` returns 0
- [ ] PR created and assigned

## Effort
1 hour

## Related
- See: [IMPLEMENTATION_TRACKING.md](docs/deduplication/IMPLEMENTATION_TRACKING.md#task-11-delete-33-synthlabs-placeholders)
- Blocks: #[TBD Phase 1.2], #[TBD Phase 2]
```

---

## Issue 2: Phase 1.2 — Merge Marital Status Duplicates

**Title**: `[dedup:p1.2] Merge marital_status duplicates (keep demo_*, delete wiki_*)`

**Labels**: `dedup:`, `team:persona`, `priority:p0`

**Milestone**: (same as Phase 1.1)

**Body**:
```markdown
## Problem
Marital status is measured twice: `demo_marital_status` and `wiki_marital_status`. Same construct.

## Solution
Keep `demo_marital_status` (core demographic), delete `wiki_marital_status` (redundant).

## What to do
1. Locate `wiki_marital_status` in `personas/dimensions+new.json`
2. Verify `demo_marital_status` exists and is identical
3. Delete `wiki_marital_status`
4. Commit: "Merge marital_status duplicates (keep demo_*, delete wiki_*)"
5. Push to PR

## Acceptance Criteria
- [ ] `wiki_marital_status` deleted
- [ ] `demo_marital_status` still present
- [ ] JSON is valid
- [ ] Verification: `jq '.[] | select(.id | contains("marital"))'` returns 1 dimension

## Effort
30 minutes

## Related
- See: [IMPLEMENTATION_TRACKING.md](docs/deduplication/IMPLEMENTATION_TRACKING.md#task-12-merge-marital-status-duplicates)
- Depends on: #[TBD Phase 1.1] (can parallelize)
- Blocks: #[TBD Phase 1.3], #[TBD Phase 2]
```

---

## Issue 3: Phase 1.3 — Update Code References

**Title**: `[dedup:p1.3] Update code references to deleted dimensions`

**Labels**: `dedup:`, `team:persona`, `priority:p0`

**Milestone**: (same as Phase 1.1)

**Body**:
```markdown
## Problem
After Phase 1.1 & 1.2, code may still reference deleted dimensions. Need to clean up.

## What to do
1. Search codebase for references to `synthlab_*` and `wiki_marital_status`
   ```bash
   grep -r "synthlab_" . --include="*.py" --include="*.ipynb" --include="*.md"
   grep -r "wiki_marital_status" . --include="*.py" --include="*.ipynb" --include="*.md"
   ```
2. For each reference found, update or remove
3. Commit: "Update references to deleted dimensions"
4. Push to PR

## Expected
Likely 0-5 references (these were placeholders, rarely used).

## Acceptance Criteria
- [ ] All references to deleted dims found
- [ ] All references removed or updated
- [ ] grep shows no results for deleted dims
- [ ] PR describes each change

## Effort
1 hour

## Related
- See: [IMPLEMENTATION_TRACKING.md](docs/deduplication/IMPLEMENTATION_TRACKING.md#task-13-update-code-references)
- Depends on: #[TBD Phase 1.1], #[TBD Phase 1.2]
- Blocks: #[TBD Phase 1.4]
```

---

## Issue 4: Phase 1.4 — Validate & Test Phase 1 Changes

**Title**: `[dedup:p1.4] Validate Phase 1 deletions (test suite + spot-check)`

**Labels**: `dedup:`, `team:persona`, `priority:p0`, `type:qa`

**Milestone**: (same as Phase 1.1)

**Body**:
```markdown
## Problem
After deletions, need to verify nothing broke.

## What to do
1. Run full persona generation test suite
   ```bash
   cd personas && python -m pytest tests/ -v
   ```
2. Generate 20 random personas and inspect for errors
3. Spot-check specific personas: ID0001, ID0100, ID0500, ID1000
4. Commit: "Validate Phase 1 changes"
5. Push to PR

## Acceptance Criteria
- [ ] All existing tests pass
- [ ] No errors in test output
- [ ] 20 sample personas generated correctly
- [ ] Spot-check personas look valid (no missing data, reasonable values)
- [ ] PR summarizes validation

## Effort
1 hour

## Related
- See: [IMPLEMENTATION_TRACKING.md](docs/deduplication/IMPLEMENTATION_TRACKING.md#task-14-validation--testing)
- Depends on: #[TBD Phase 1.3]
- Blocks: Phase 1 Merge (→ Phase 2)
```

---

## Issue 5: Design — Environment Team Requirements

**Title**: `[design] Environment team: execution & evaluation requirements`

**Labels**: `type:design`, `team:environment`, `priority:p1`, `help-wanted`

**Milestone**: (create "Design & Roadmap" if not exists)

**Body**:
```markdown
## Problem
Environment team doesn't have clear requirements yet. Need design doc.

## Scope
Define what the environment layer needs to:
- Execute agents (run inference, handle context)
- Evaluate agents (measure persona adherence, task completion)
- Collect telemetry (traces, metrics)
- Support different agent backends (GPT, LLMs, etc.)

## What to do
1. Write design doc (2-4 pages) covering above
2. Post to Discussions for feedback
3. Iterate based on feedback
4. Create this issue to track acceptance

## Deliverable
Design doc: `environments/DESIGN.md` (or link in environments/README.md)

## Acceptance Criteria
- [ ] Defines what agents need at runtime
- [ ] Defines evaluation metrics
- [ ] Defines telemetry/tracing format
- [ ] Lists dependencies (Persona team schema)
- [ ] Feedback incorporated from Discussions

## Effort
4-6 hours (design + iteration)

## Timeline
Due: Jul 15

## Related
- See: [ROADMAP.md](docs/ROADMAP.md)
- Depends on: Persona Phase 2 merge (schema must be stable)
- Blocks: Environment implementation work
```

---

## Issue 6: Design — Application Team Task Taxonomy

**Title**: `[design] Application team: task taxonomy & scenarios`

**Labels**: `type:design`, `team:application`, `priority:p1`, `help-wanted`

**Milestone**: (create "Design & Roadmap" if not exists)

**Body**:
```markdown
## Problem
Application team doesn't have clear task/scenario requirements yet. Need design doc.

## Scope
Define what scenarios we'll simulate:
- Which domains (healthcare, finance, e-commerce, etc.)?
- What types of tasks (survey, chatbot, decision-making)?
- What evaluation criteria?
- How do personas affect outcomes?

## What to do
1. Write task taxonomy (2-3 pages)
2. Propose 2-3 pilot scenario domains
3. Post to Discussions for feedback
4. Create this issue to track acceptance

## Deliverable
Task taxonomy: `applications/TAXONOMY.md` (or link in applications/README.md)

## Acceptance Criteria
- [ ] Defines task types and domains
- [ ] Proposes 2-3 pilot scenarios
- [ ] Explains how personas matter
- [ ] Lists dependencies (Environment basics)
- [ ] Feedback incorporated from Discussions

## Effort
4-6 hours (design + iteration)

## Timeline
Due: Jul 15

## Related
- See: [ROADMAP.md](docs/ROADMAP.md)
- Depends on: Environment team design (must know what env provides)
- Blocks: Application implementation work
```

---

## Issue 7: Team Coordination — Assign Team Leads

**Title**: `[admin] Assign Environment & Application team leads`

**Labels**: `type:admin`, `priority:p0`, `help-wanted`

**Body**:
```markdown
## Problem
Environment and Application teams don't have designated leads yet. Blocking coordination.

## Action
Identify or recruit:
- 1 Environment team lead (owns execution/evaluation infrastructure)
- 1 Application team lead (owns tasks/scenarios)

## Deliverable
Update [TEAM_ASSIGNMENTS.md](docs/TEAM_ASSIGNMENTS.md) with names + GitHub handles.

## Acceptance Criteria
- [ ] Environment lead identified
- [ ] Application lead identified
- [ ] Names added to TEAM_ASSIGNMENTS.md
- [ ] Leads aware of responsibilities
- [ ] Announced in Discussions

## Timeline
Due: Jun 28

## Related
- See: [TEAM_ASSIGNMENTS.md](docs/TEAM_ASSIGNMENTS.md)
- Blocks: All downstream team work
```

---

## How to Use This Template

1. **Copy each "Issue" section** (Title, Labels, Body)
2. **Go to GitHub**: MatrAIx repository → Issues → New Issue
3. **Paste the title** in the Title field
4. **Add labels** (create if not exists)
5. **Paste the body** in the Description field
6. **Assign** to someone or leave unassigned if open
7. **Create issue**
8. **Update this doc** with the issue number (#XXX)

---

## Creating Labels

Before creating issues, create these labels (if not exists):

| Label | Color | Description |
|-------|-------|-------------|
| `dedup:` | purple | Dimension deduplication work |
| `team:persona` | blue | Persona team work |
| `team:environment` | green | Environment team work |
| `team:application` | orange | Application team work |
| `priority:p0` | red | Critical blocker |
| `priority:p1` | yellow | High priority |
| `priority:p2` | grey | Medium priority |
| `type:design` | navy | Design/architecture doc |
| `type:qa` | lime | Quality assurance |
| `type:admin` | grey | Administrative/coordination |
| `help-wanted` | green | Seeking contributors |
| `blocker` | red | Blocks other work |

---

**Last updated**: 2026-06-21  
**Instructions**: Copy-paste to GitHub Issues, update numbers as you create them
