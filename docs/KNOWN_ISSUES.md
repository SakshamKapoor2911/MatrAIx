# Known Issues & Backlog

**Last updated**: 2026-06-21  
**Total open**: 4 blocking, 6 non-blocking  
**See also**: GitHub Issues (authoritative)

---

## 🚨 Blockers (Must fix before major milestones)

### 1. Dimension Deduplication Phase 1 Not Started
**Priority**: P0 (critical)  
**Type**: Schema cleanup  
**Impact**: Blocks Phase 2, environment integration, papers  
**Effort**: 4 hrs (3 tasks × parallel)  
**Assigned to**: [OPEN]  
**Related**: GitHub Issues [TBD]

**What needs to happen**:
- [ ] Delete 33 SynthLabs placeholder dimensions
- [ ] Merge marital_status duplicates (keep demo_*, delete wiki_*)
- [ ] Update all code references
- [ ] Run test suite
- [ ] Merge to main

**Why it blocks**: Phase 2 depends on Phase 1. Environment/Application teams can't finalize integration until schema is stable.

**Acceptance criteria**:
- All 33 placeholders deleted
- No dangling references in codebase
- Persona generation test suite passes
- Spot-check: 20 random personas generate correctly

---

### 2. Team Leads Not Assigned
**Priority**: P0  
**Type**: Coordination  
**Impact**: No clear ownership of Environment & Application teams  
**Effort**: ~5 min (decision)  
**Assigned to**: Yuexing  
**Related**: [TEAM_ASSIGNMENTS.md](./TEAM_ASSIGNMENTS.md)

**What needs to happen**:
- [ ] Identify or recruit Environment team lead
- [ ] Identify or recruit Application team lead
- [ ] Update [TEAM_ASSIGNMENTS.md](./TEAM_ASSIGNMENTS.md)
- [ ] Announce in Discussions

**Why it blocks**: Can't assign work to teams without leads.

---

### 3. GitHub Issues Not Created for Dedup Phase 1
**Priority**: P0  
**Type**: Project management  
**Impact**: No way to track or assign dedup work  
**Effort**: ~30 min  
**Assigned to**: Yuexing  
**Related**: See draft below

**What needs to happen**:
- [ ] Create GitHub Issue: "Delete SynthLabs placeholders (33 dims)"
- [ ] Create GitHub Issue: "Merge marital_status duplicates"
- [ ] Create GitHub Issue: "Update code references post-dedup"
- [ ] Create GitHub Issue: "Test & validate Phase 1"
- [ ] Label with `dedup:`, `team:persona`, `priority:p0`
- [ ] Link to [IMPLEMENTATION_TRACKING.md](./deduplication/IMPLEMENTATION_TRACKING.md)

---

### 4. Environment & Application Teams Have No Design Docs
**Priority**: P1  
**Type**: Design  
**Impact**: Teams spinning without direction  
**Effort**: 4-6 hrs (design + review)  
**Assigned to**: [TBD by team leads]  
**Related**: [ROADMAP.md](./ROADMAP.md)

**What needs to happen**:
- [ ] Environment: "What agents need to run & evaluate"
- [ ] Application: "What tasks & scenarios will we simulate?"
- [ ] Both posted to Discussions for feedback
- [ ] Design finalized by Jul 15

**Dependencies**: Unblocked, but Environment needs Persona Phase 2 before deep integration.

---

## ⚠️ Non-Blocking Issues (Important, but not urgent)

### 5. Persona Generation Pipeline Not Optimized
**Priority**: P1  
**Type**: Performance  
**Impact**: Scaling to 8B personas will be slow  
**Effort**: 8-12 hrs (profiling + optimization)  
**Assigned to**: [OPEN - Persona Team]  
**Target**: Aug 31

**Problem**: Current pipeline may have bottlenecks for large-scale generation.

**Action items**:
- [ ] Profile generation with 10K+ personas
- [ ] Identify slowest components
- [ ] Implement 3-5 optimizations
- [ ] Measure improvement

---

### 6. Dedup Phase 2 Needs Validation Plan
**Priority**: P1  
**Type**: Quality assurance  
**Impact**: Risk of breaking personas during consolidation  
**Effort**: 2 hrs (design)  
**Assigned to**: [OPEN - Persona Team]  
**Target**: Before Phase 2 implementation

**Problem**: Phase 2 (Big Five, expertise) has medium consolidation risk. Need clear validation strategy.

**Action items**:
- [ ] Design test matrix (which scenarios to validate?)
- [ ] Identify edge cases where Big Five/expertise matter
- [ ] Create automated checks
- [ ] Plan manual review (sample size?)

---

### 7. personas/README.md Needs Contributor Guide
**Priority**: P2  
**Type**: Documentation  
**Impact**: External contributors unclear on how to extend personas  
**Effort**: 3-4 hrs  
**Assigned to**: [OPEN - Persona Team lead]  
**Target**: Jul 15

**Missing content**:
- [ ] How to add a new dimension
- [ ] How to generate personas with custom dimensions
- [ ] Validation checklist for new dimensions
- [ ] Examples (demographics, personality, skills)

---

### 8. No Central Configuration System
**Priority**: P2  
**Type**: Infrastructure  
**Impact**: Hard to manage different persona configs for different experiments  
**Effort**: 4-6 hrs  
**Assigned to**: [OPEN]  
**Target**: Aug 15

**Problem**: Team members likely using different dimension subsets, filters, validation rules.

**Action items**:
- [ ] Design config file format (YAML? JSON?)
- [ ] Implement loader for personas with custom configs
- [ ] Create examples (e.g., "healthcare subset", "top 100 dims")
- [ ] Document usage

---

### 9. Telemetry & Tracing Not Defined
**Priority**: P1  
**Type**: Infrastructure (Environment team)  
**Impact**: Can't measure agent behavior, benchmark adherence  
**Effort**: 6-8 hrs (design + MVP)  
**Assigned to**: [TBD - Environment Team]  
**Target**: Aug 31

**Missing**:
- [ ] What to trace? (agent inputs, outputs, reasoning, decisions, errors)
- [ ] How to store? (JSON files, database, streaming)
- [ ] How to query? (analyze post-hoc, real-time dashboards)

---

### 10. Paper 1 (Survey) Has No Author Assignment
**Priority**: P0 (but far future)  
**Type**: Publication  
**Impact**: Survey paper deadline approaching (end of summer)  
**Effort**: 60+ hrs (research + writing)  
**Assigned to**: Yuexing (lead) + [TBD - 2-3 co-authors]  
**Target**: Jul 31 (first draft outline), Sep 30 (final)

**Scope**: Agent personas, user simulation, datasets, methods, benchmarks, open challenges.

---

## Issue Template (For Creating GitHub Issues)

Use this format when creating new issues:

```markdown
## Problem
[1-2 sentences describing the issue]

## Impact
- What breaks if this isn't fixed?
- Who is blocked?
- Does it block other work?

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Effort
[Estimate in hours]

## Related
- Depends on: [Issue #X, #Y]
- Blocks: [Issue #A, #B]

## Labels
- `priority:p0` or `p1` or `p2`
- `team:persona` or `team:environment` or `team:application`
- `type:` (e.g., `dedup`, `design`, `docs`, `perf`)
```

---

## Triage Rules

**P0 (Critical)**: Blocks publication, other work, or team coordination  
**P1 (High)**: Important for timeline, team progress, or quality  
**P2 (Medium)**: Nice-to-have, can defer to next sprint

---

## Quick Stats

| Category | Count | Est. Hours | Notes |
|----------|-------|-----------|-------|
| Blockers | 4 | 9 hrs | Must resolve this sprint |
| High priority | 3 | 18 hrs | Next sprint (1-2 weeks) |
| Medium priority | 3 | 12 hrs | Future sprints |
| **Total** | **10** | **39 hrs** | ~1 week of team effort |

---

## How to Report New Issues

1. **Check existing issues first** (GitHub Issues) to avoid duplicates
2. **Use the template above**
3. **Assign priority** (P0, P1, P2)
4. **Assign team** (persona, environment, application, or cross-team)
5. **Estimate effort** (in hours)
6. **Mention blockers** (what's this waiting for? what does this block?)
7. **Post to Discussions** if you want early feedback

---

**Last updated**: 2026-06-21  
**Next triage**: 2026-06-28 (Monday)  
**Responsible**: Yuexing (coord), team leads (per stream)
