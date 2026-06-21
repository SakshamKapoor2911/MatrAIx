# Deduplication Implementation Tracker

**Live status of Phase 1 and Phase 2 consolidation work**

**Last updated**: 2026-06-21  
**Next update**: Daily (or as progress is made)

---

## 📊 Summary

| Phase | Status | Total Dims | Deadline | Est. Time | Blocker(s) |
|-------|--------|-----------|----------|-----------|-----------|
| **Phase 1** | ⏳ Not started | 34 → delete | Jun 28 | 4 hrs | None (owner needed) |
| **Phase 2** | 🔒 Blocked | 21 → consolidate | Jul 5 | 2.5 hrs | Phase 1 merge |
| **Testing & Merge** | ⏳ Waiting | — | Jul 5 | 2 hrs | Phase 2 complete |

---

## 🚀 Phase 1: Critical Cleanup (Delete 34 dimensions)

**Status**: NOT STARTED  
**Owner**: [OPEN - ASSIGN ASAP]  
**Deadline**: Jun 28 (1 week)  
**Est. time**: ~4 hours (can parallelize across 2-3 people)  
**Risk**: VERY LOW (only deleting placeholders, no consolidation)  
**Related GitHub Issue**: [TBD]

### Task 1.1: Delete 33 SynthLabs Placeholders

**What**: Remove all dimensions with `value=['Unknown']` from SynthLabs (contrib_id: synthlab_*)

**File**: `/home/yuexing/MatrAIx/personas/dimensions+new.json`

**Status**:
- [ ] Owner assigned
- [ ] PR created: [TBD]
- [ ] Deletions made in JSON
- [ ] Verified: exactly 33 removed
- [ ] Commit: "Delete 33 SynthLabs placeholder dimensions (zero variance)"
- [ ] PR passed review: [TBD]

**Validation**:
```bash
# Before
jq '[.[] | select(.contrib_id == "synthlab_*")] | length' dimensions+new.json
# Expected: 33

# After
jq '[.[] | select(.contrib_id == "synthlab_*")] | length' dimensions+new.json
# Expected: 0
```

**Who to assign**: Anyone comfortable with JSON editing + git

---

### Task 1.2: Merge Marital Status Duplicates

**What**: Keep `demo_marital_status` (core demographic), delete `wiki_marital_status`

**Why**: Same construct, measured twice. Core demographic version is the source of truth.

**File**: `/home/yuexing/MatrAIx/personas/dimensions+new.json`

**Status**:
- [ ] Owner assigned
- [ ] PR created: [TBD]
- [ ] `wiki_marital_status` deleted from JSON
- [ ] Verified: `demo_marital_status` still present
- [ ] Commit: "Merge marital_status duplicates (keep demo_*, delete wiki_*)"
- [ ] PR passed review: [TBD]

**Validation**:
```bash
# Before
jq '.[] | select(.id | contains("marital"))' dimensions+new.json
# Expected: 2 (demo_marital_status, wiki_marital_status)

# After
jq '.[] | select(.id | contains("marital"))' dimensions+new.json
# Expected: 1 (demo_marital_status only)
```

**Who to assign**: Same person as 1.1 or someone else (can parallelize)

---

### Task 1.3: Update Code References

**What**: Search codebase for references to deleted dimensions, update code

**Files to check**: `personas/**/*.py`, `personas/**/*.ipynb`, `*.py` (scripts), docs

**Status**:
- [ ] Owner assigned
- [ ] Grep search completed: [results TBD]
  ```bash
  grep -r "synthlab_" /home/yuexing/MatrAIx --include="*.py" --include="*.ipynb"
  grep -r "wiki_marital_status" /home/yuexing/MatrAIx --include="*.py" --include="*.ipynb"
  ```
- [ ] All references identified
- [ ] All references updated or removed
- [ ] PR created: [TBD]
- [ ] Commit: "Update references to deleted dimensions"
- [ ] PR passed review: [TBD]

**Expected findings**: 0-5 references (these dims were placeholders, unlikely to be used)

**Who to assign**: Someone good at searching/cleanup

---

### Task 1.4: Validation & Testing

**What**: Run test suite, spot-check personas, ensure nothing broke

**Status**:
- [ ] Owner assigned
- [ ] Persona generation test suite runs: [status TBD]
  ```bash
  cd /home/yuexing/MatrAIx/personas
  python -m pytest tests/ -v
  # or: python tests/test_persona_generation.py
  ```
- [ ] All tests pass
- [ ] Spot-check: Generate 20 random personas, inspect (no errors, reasonable data)
- [ ] Manual review: Check ID0001–ID0010, ID0500, ID1000 render correctly
- [ ] Commit & PR: "Validate Phase 1 changes"
- [ ] PR passed review: [TBD]

**Expected**: All tests pass, all personas valid, no complaints.

**Who to assign**: QA person or someone detail-oriented

---

### Phase 1 Merge Criteria

- [ ] All 4 tasks above complete
- [ ] All PRs reviewed & approved
- [ ] All tests passing
- [ ] No open comments on any PR
- [ ] Ready to merge to main

**Merge date target**: Jun 28

**Merge checklist**:
- [ ] Squash commits (optional, but recommended for clarity)
- [ ] Write merge commit message: "Phase 1: Delete 33 SynthLabs placeholders + merge marital_status"
- [ ] Merge to main
- [ ] Tag: `v1.1-dedup-phase1` (optional, for reference)
- [ ] Announce in Discussions: `📋 Weekly Standups`

---

## 🔒 Phase 2: Consolidation (Consolidate 21 dimensions)

**Status**: BLOCKED (waiting on Phase 1 merge)  
**Owner**: [OPEN - to be assigned]  
**Deadline**: Jul 5  
**Est. time**: ~2.5 hours  
**Risk**: MEDIUM (consolidation, not just deletion)  
**Depends on**: Phase 1 must be merged first  
**Related GitHub Issue**: [TBD]

### Task 2.1: Big Five Alternative Sources Consolidation

**What**: Keep `neo_big5_*` (primary), consolidate `pandora_big5_*` + `bfi2_domain_*` + `ipip_*` references

**Why**: Measuring personality 4 ways (Big5, IPIP, BFI-2, Pandora). These are all Big5. Consolidate to single system.

**What to keep**: 
- `neo_big5_*` (56 dimensions) — theoretical foundation, keep all

**What to consolidate**:
- `pandora_big5_*` (X dimensions) → merge into neo_big5
- `bfi2_domain_*` (X dimensions) → merge into neo_big5
- `ipip_*` (X dimensions) → merge into neo_big5
- **Total savings**: 15 dimensions

**Status**:
- [ ] Owner assigned
- [ ] Audit completed: Find all non-neo Big5 dimensions
- [ ] Consolidation plan reviewed in Discussions (gather feedback)
- [ ] PR created: [TBD]
- [ ] Consolidation made in JSON
- [ ] Code references updated
- [ ] Validation passed
- [ ] PR review complete: [TBD]

**Who to assign**: Personality/psychology expert preferred, but Python skills enough

---

### Task 2.2: Expertise vs. Academic Overlap

**What**: Clarify distinction between `Expertise: Domains` (143 dims) and `Learning: Academic` (32 dims). Consolidate overlap.

**Why**: "Subject matter expertise" and "academic knowledge" are different, but some overlap exists (e.g., "Biology", "Mathematics").

**What to keep**:
- All 143 Expertise domains (each independent, needed for granularity)
- Subset of Academic (only non-overlapping, ~26 dims)

**What to consolidate**: ~6 dimensions where Academic duplicates Expertise

**Status**:
- [ ] Owner assigned
- [ ] Overlap identified: Academic dims that duplicate Expertise domains
- [ ] Consolidation plan: Which Academic to keep? Which to remove?
- [ ] Plan reviewed in Discussions (gather feedback)
- [ ] PR created: [TBD]
- [ ] Consolidation made in JSON
- [ ] Code references updated
- [ ] Validation passed
- [ ] PR review complete: [TBD]

**Who to assign**: Someone who understands education/expertise modeling

---

### Task 2.3: Full Validation Suite

**What**: Run comprehensive testing post-consolidation. Higher bar than Phase 1.

**Status**:
- [ ] Owner assigned
- [ ] Test suite runs: [status TBD]
- [ ] All tests pass
- [ ] Spot-check: 30 random personas (Phase 2 is higher-risk, more validation)
- [ ] Edge case validation: Personas with high Expertise should still generate correctly
- [ ] Personas with Academic overlaps should consolidate gracefully
- [ ] PR created: "Validate Phase 2 changes"
- [ ] PR review complete: [TBD]

**Who to assign**: QA + testing specialist

---

### Phase 2 Merge Criteria

- [ ] All 3 tasks complete
- [ ] All PRs reviewed & approved
- [ ] Test suite passing (all tests)
- [ ] 30+ sample personas validated
- [ ] No open blockers
- [ ] Ready to merge to main

**Merge date target**: Jul 5

**Merge checklist**:
- [ ] Squash commits (optional)
- [ ] Merge commit: "Phase 2: Consolidate Big Five alt sources + expertise overlap"
- [ ] Merge to main
- [ ] Tag: `v1.2-dedup-phase2` (optional)
- [ ] Announce in Discussions
- [ ] Update [docs/CURRENT_STATE.md](../CURRENT_STATE.md): "Deduplication complete"

---

## 📋 Summary Progress

| Task | Status | Owner | PR | Deadline |
|------|--------|-------|----|----|
| **Phase 1.1**: Delete placeholders | ⏳ | [OPEN] | [—] | Jun 28 |
| **Phase 1.2**: Merge marital | ⏳ | [OPEN] | [—] | Jun 28 |
| **Phase 1.3**: Code refs | ⏳ | [OPEN] | [—] | Jun 28 |
| **Phase 1.4**: Validation | ⏳ | [OPEN] | [—] | Jun 28 |
| **Phase 1 Merge** | 🔒 Waiting | Yuexing | [—] | Jun 28 |
| **Phase 2.1**: Big Five | 🔒 Blocked | [OPEN] | [—] | Jul 5 |
| **Phase 2.2**: Expertise/Academic | 🔒 Blocked | [OPEN] | [—] | Jul 5 |
| **Phase 2.3**: Validation | 🔒 Blocked | [OPEN] | [—] | Jul 5 |
| **Phase 2 Merge** | 🔒 Blocked | Yuexing | [—] | Jul 5 |

---

## 🎯 Critical Path

```
Jun 21 ← You are here
  ↓
Jun 28 — Phase 1 complete (4 tasks, 4 hrs team time)
  ↓
Jul 5 — Phase 2 complete (3 tasks, 2.5 hrs team time)
  ↓
Jul 5+ — Environment/Application teams can integrate final schema
  ↓
Aug 31 — Papers ready for writing
```

**Critical bottleneck**: Phase 1 owner(s) need to start **this week**. All downstream work waits.

---

## 📝 How to Update This Tracker

1. **Owner**: Assign yourself to a task
2. **PR**: Add PR link when created
3. **Status**: Update checkbox as you progress
4. **Blocker**: If stuck, post to [KNOWN_ISSUES.md](../KNOWN_ISSUES.md) and @ mention team lead
5. **Merge**: Update summary table when PRs merge

---

## 🔗 Related Documents

- [FINDINGS_SUMMARY.txt](./FINDINGS_SUMMARY.txt) — Executive summary
- [DEDUP_QUICK_REFERENCE.md](./DEDUP_QUICK_REFERENCE.md) — Implementation guide
- [DEDUPLICATION_ANALYSIS.txt](./DEDUPLICATION_ANALYSIS.txt) — Full technical report
- [../KNOWN_ISSUES.md](../KNOWN_ISSUES.md) — Blockers and open issues

---

**Last updated**: 2026-06-21  
**Next update**: Daily or as progress changes  
**Contact**: Post to Discussions or @ Yuexing if blocked
