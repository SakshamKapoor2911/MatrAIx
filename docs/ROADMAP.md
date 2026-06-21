# MatrAIx Roadmap

**Vision**: Build large-scale persona-based agent simulations for testing ideas before deploying to the real world.

**Long-term goal**: 8.3 billion synthetic personas (planet-scale simulation).

---

## Stage 1: Minimal Stack (Current — Summer 2026)

### Completed ✅
- Persona schema (1,388 dimensions, 37 categories)
- Initial persona dataset (1,000 curated personas)
- Basic analysis and deduplication assessment

### In Progress 🔄
- **Q2 2026 (Now)**: Dimension cleanup (deduplication)
  - Phase 1: Delete placeholders + merge duplicates (34 dims, ~2 hrs)
  - Phase 2: Consolidate Big Five alt sources + expertise overlap (21 dims, ~1.5 hrs)
- **Q3 2026**: Paper 1 — Survey of agent personas and user simulation
  - Coverage of existing datasets, methods, benchmarks, challenges
  - Literature review + analysis

### Planned ⏳
- **Q3 2026**: Paper 2 — MatrAIxPersona & MatrAIxPersonaBench
  - Schema design, data generation, quality filtering, evaluation
  - Persona-conditioned agents as simulated users
- **Q3 2026**: First persona-adherence benchmark
- **Q3 2026**: Simple telemetry and basic trace collection

---

## Stage 2: Core Dataset & Benchmark (Late 2026 — 2027)

### Goals
- Release **MatrAIxPersona-8B** (8 billion personas)
- Release **MatrAIxPersonaTrain** (training subset)
- Release **MatrAIxPersonaBench** (persona-adherence evaluation)
- Add domain-specific subsets (healthcare, finance, etc.)
- Automatic evaluation pipeline

### Key Activities
- Persona generation at scale (infrastructure, quality checks)
- Benchmark expansion (multi-domain, challenging cases)
- Dataset documentation and versioning
- Community feedback and iteration

---

## Stage 3: Environment Expansion (2027)

### Goals
- Web environment (browser automation, form filling)
- Long-horizon tasks (multi-turn conversations, planning)
- Memory-enabled agents (persistent state across interactions)
- Multi-agent interaction (agents interacting with each other)
- Cost/friction simulation (user friction, switching costs)

### Key Activities
- Task library expansion
- Agent persistence and memory research
- Environment robustness testing
- Integration with external systems (APIs, web)

---

## Stage 4: Simulated Society (2027+)

### Goals
- Planet-scale simulation (8.3 billion personas)
- Social graphs and relationships
- Group interactions and consensus
- Information diffusion
- Synthetic communities and institutions

### Key Activities
- Multi-agent simulation infrastructure
- Social network modeling
- Aggregate behavior analysis
- Society-level evaluation metrics

---

## 2026 Target Milestones

| Milestone | Target | Owner | Blocker(s) |
|-----------|--------|-------|-----------|
| **Dedup Phase 1** | Jun 21 - Jun 28 | Persona Team | None |
| **Dedup Phase 2** | Jun 28 - Jul 5 | Persona Team | Phase 1 merged |
| **Paper 1 first draft** | Jul 31 | Yuexing + team | Dedup complete |
| **Paper 2 draft outline** | Aug 15 | Yuexing + team | Paper 1 structure clear |
| **Persona-8B generation plan** | Aug 31 | Persona Team | Phase 2 complete |
| **Both papers finalized** | Sep 30 | Yuexing + team | Community feedback |

---

## Dependencies & Critical Path

```
Dedup Phase 1 (2 hrs)
    ↓
Dedup Phase 2 (1.5 hrs, validation required)
    ↓
Paper 1 — Survey (research, writing)
    ↓
Paper 2 outline & structure
    ↓
Environment & Application teams can work in parallel
    ↓
Final papers + benchmarks (end of summer)
```

**Critical items that cannot be shortened**:
- Phase 1 & 2 must complete before large-scale generation
- Paper drafts need community review before finalization
- Benchmarks need validation before release

---

## Open Research Questions

1. **Persona adherence**: How do we best measure if agents stay "in character"?
2. **Long-horizon consistency**: Do LLM agents maintain personas over extended interactions?
3. **Predictive validity**: Can simulated user preferences predict real user behavior?
4. **Multi-agent dynamics**: How do personas interact with each other?
5. **Memory & evolution**: Should personas learn/change over time?

---

## Success Criteria (End of Summer 2026)

- [ ] Both papers submitted (or close to submission)
- [ ] Deduplication complete and merged
- [ ] MatrAIxPersona-1K validated and published
- [ ] First benchmark showing persona adherence
- [ ] Documentation clear enough for external contributors
- [ ] At least 10 external collaborators engaged
- [ ] Community feedback collected for Stage 2

---

## How to Use This Roadmap

- **Project managers**: Use milestones to track progress
- **Contributors**: See which stage aligns with your interests
- **Team leads**: Identify your dependencies and blockers
- **Decision makers**: Understand long-term vision and trade-offs

---

**Last updated**: 2026-06-21  
**Next review**: 2026-07-05 (post Phase 1)  
**Questions?** Open a GitHub Discussion or reach out to Yuexing
