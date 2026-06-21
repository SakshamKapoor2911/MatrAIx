# Team Assignments & Responsibilities

**Last updated**: 2026-06-21  
**Review frequency**: Weekly (every Monday)

---

## Coordination Hub

| Role | Name | GitHub | Slack | Responsibilities |
|------|------|--------|-------|------------------|
| **Project Lead** | Yuexing | @yuexing | @yuexing | Overall coordination, publication, dedup oversight |
| **Persona Team Lead** | [TBD] | — | — | Dimensions, personas, schema |
| **Environment Team Lead** | [TBD] | — | — | Execution, evaluation, harnesses |
| **Application Team Lead** | [TBD] | — | — | Tasks, scenarios, domain logic |

**Action**: Fill in team leads by **June 28**. Volunteers?

---

## Team: 🧬 Persona

**Focus**: Schema design, persona generation, dimension management

| Task | Owner | Status | Deadline | Notes |
|------|-------|--------|----------|-------|
| **Dedup Phase 1: SynthLabs cleanup** | [ASSIGN] | Not started | Jun 28 | Delete 33 placeholders, merge marital_status. 2 hrs. |
| **Dedup Phase 1: Code references** | [ASSIGN] | Not started | Jun 28 | Grep codebase, update references, test suite. 1 hr. |
| **Dedup Phase 1: Validation** | [ASSIGN] | Not started | Jun 28 | Run persona generation tests, spot-check 20 personas. 1 hr. |
| **Dedup Phase 2: Big Five consolidation** | [ASSIGN] | Waiting on Phase 1 | Jul 5 | Consolidate 15 Big Five alt sources. 1 hr. |
| **Dedup Phase 2: Expertise overlap** | [ASSIGN] | Waiting on Phase 1 | Jul 5 | Consolidate expertise/academic. Document distinction. 30 min. |
| **Dedup Phase 2: Testing** | [ASSIGN] | Waiting on Phase 1 | Jul 5 | Full validation suite. 1 hr. |
| **Persona generation**: Scale 1K → larger | [ASSIGN] | Not started | Aug 31 | Improve generation pipeline, quality checks, distribution |
| **Documentation**: Update personas/README | [ASSIGN] | Not started | Jul 15 | Clarify schema post-dedup, add examples |

### Current Bottleneck
Phase 1 is **not started**. We need 1-2 owners to take this on **this week**. This unblocks Phase 2 and all downstream work.

---

## Team: 🌐 Environment

**Focus**: Execution environments, evaluation harnesses, agent infrastructure

| Task | Owner | Status | Deadline | Notes |
|------|-------|--------|----------|-------|
| **Design doc**: Environment requirements | [TBD] | Not started | Jul 15 | What agents need to run, evaluate, trace |
| **Basic environment**: Survey/chatbot | [TBD] | Not started | Aug 31 | Simple execution + basic evaluation |
| **Telemetry**: Trace collection | [TBD] | Not started | Aug 31 | Logs, metrics, structured traces |
| **Integration**: Link with Persona team | [TBD] | Blocked | Jul 5 | Once dimensions stable (after Phase 2) |

### Dependency
Waiting on **Persona team Phase 2 merge** before full integration work.

---

## Team: 🧪 Application

**Focus**: Tasks, scenarios, domain-specific simulations

| Task | Owner | Status | Deadline | Notes |
|------|-------|--------|----------|-------|
| **Design doc**: Task taxonomy | [TBD] | Not started | Jul 15 | What scenarios will we simulate? |
| **Sample tasks**: Healthcare scenario | [TBD] | Not started | Aug 31 | Proof-of-concept domain task |
| **Sample tasks**: Financial scenario | [TBD] | Not started | Aug 31 | Second domain for validation |
| **Evaluation**: Task-level metrics | [TBD] | Not started | Aug 31 | How do we measure task completion? |
| **Integration**: Link with Environment | [TBD] | Blocked | Aug 15 | Once Environment team has basics |

### Dependency
Waiting on **Environment team basics** before integration.

---

## Cross-Team Coordination

### Communication
- **Async**: GitHub Discussions (daily check-in recommended)
  - `📋 Weekly Standups` — Mon 9am: What did you do? What's next? Blockers?
  - `❓ Design Questions` — Any time: Major decisions, feedback needed
  - `🚨 Blockers` — Any time: What's stopping you?
- **Sync (optional)**: Weekly 30-min call (Fridays, 3pm if useful)

### Dependency Management
- **Phase 1 dedup** must merge before Phase 2 starts
- **Phase 2 dedup** must merge before Environment/Application deep integration
- **Environment basics** unlock Application work
- All must converge by **Aug 15** for paper deadline

### Escalation
If blocked → post to `🚨 Blockers` discussion → Yuexing responds within 24h

---

## Assignments Tracking

### Phase 1 Dedup (Due Jun 28)

**Task 1.1: Delete placeholders + merge marital_status**
- Owner: [OPEN]
- Status: Not started
- PR: [TBD]
- Effort: 2 hrs
- GitHub Issue: [TBD]

**Task 1.2: Code references**
- Owner: [OPEN]
- Status: Not started
- Effort: 1 hr
- GitHub Issue: [TBD]

**Task 1.3: Validation & testing**
- Owner: [OPEN]
- Status: Not started
- Effort: 1 hr
- GitHub Issue: [TBD]

### Phase 2 Dedup (Due Jul 5, blocked on Phase 1)

**Task 2.1: Big Five consolidation**
- Owner: [OPEN]
- Status: Waiting
- Effort: 1 hr
- GitHub Issue: [TBD]

**Task 2.2: Expertise/academic overlap**
- Owner: [OPEN]
- Status: Waiting
- Effort: 30 min
- GitHub Issue: [TBD]

**Task 2.3: Full testing**
- Owner: [OPEN]
- Status: Waiting
- Effort: 1 hr
- GitHub Issue: [TBD]

---

## How to Request Assignment

1. **Looking for work?** Check tasks marked `[OPEN]` above
2. **Want to volunteer?** Leave a comment here or in the GitHub Issue
3. **Can't do assigned work?** Update status and reassign ASAP

---

## Skills Matrix (Optional)

Use this to match skills to tasks:

| Person | Python | Schema | Testing | Docs | GitHub |
|--------|--------|--------|---------|------|--------|
| Yuexing | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| [Name 2] | — | — | — | — | — |
| [Name 3] | — | — | — | — | — |

(Fill in as team joins)

---

## Quick Links

- **Dedup analysis**: `/home/yuexing/MatrAIx/DEDUP_QUICK_REFERENCE.md`
- **GitHub Issues**: [MatrAIx Issues](https://github.com/[your-org]/MatrAIx/issues)
- **GitHub Discussions**: [MatrAIx Discussions](https://github.com/[your-org]/MatrAIx/discussions)
- **Project board** (optional): [Kanban](https://github.com/[your-org]/MatrAIx/projects/1)

---

**Next update**: 2026-06-28 (Phase 1 status check)
