# AutoPersona

**Owner / proposer:** Ziyan Wang


## 0. Idea

A persona schema should be **learned from causal evidence**, not hand-designed and then validated. MatrAIx can use the simulator's *interventional* access — the ability to `do(factor)` that observational human data lacks — to identify which persona factors causally drive behavior in a target task, and to evolve the persona constitution toward the **smallest set of factors that is causally sufficient to reproduce the task's behavioral variation**.

The optimization objective is **support coverage under a bounded fidelity loss**: induce the full range of behaviors a real population would plausibly exhibit (coverage), without producing behaviors no real person would (fidelity), over a causally-pruned schema (minimality). The deliverable is therefore a *method* and the evidence behind it, not a static persona database.



## 1. Contribution and Novelty


**C1 — Causal factor attribution in the interactive, multi-turn setting.** ACE-Align (2601.12962) defines an attribute causal effect `CE = p(Y|do(A=1),Z) − p(Y|do(A=0),Z)` but estimates it from single-turn option probabilities (MCQ-style). The open problem is the interactive case: in a multi-turn rollout the factor *also shapes the trajectory*, so endpoints are not comparable and naive sensitivity is confounded. C1 defines and efficiently estimates the causal effect of a structured persona factor on multi-turn behavioral outcomes.

**C2 — Causal attribution as the engine of schema learning, not just measurement.** Recent work *diagnoses* that persona effects are weak or entangled — "Stable Behavior, Limited Variation" (2604.28048) finds gender has no measurable effect and political orientation negligible effect; "From Single to Societal" (2511.11789) shows persona-induced bias is confounded by cross-persona interactions — but none closes the loop. C2 turns the diagnostic into a causal feature/representation-selection procedure that yields a minimal, task-conditioned schema and a principled keep/merge/drop rule.

**C3 — A principled objective and a sample-efficient optimizer.** Persona Generators (2602.03545) evolves generator code for response diversity with a scalar fitness, trading away fidelity. C3 replaces this with (i) **support coverage under a stratified, observability-matched fidelity constraint** (§5.5–5.8), and (ii) a **GEPA-style reflective optimizer** (2507.19457) whose mutation signal is the causal factor→behavior matrix in natural language, not a scalar. GEPA's Pareto search and ~35× rollout efficiency over RL matter because behavioral rollouts are the dominant cost.

**Positioning.** vs Persona Generators — causal-attribution-driven minimal *schema* learning under a coverage-under-fidelity objective, not diversity-of-responses. vs ACE-Align — multi-turn interactive identification used to *evolve the generator*, not single-turn measurement aligned to ground truth. vs ODYSSIM (2606.14199) — an orthogonal, composable layer (a schema, not trained weights). vs the "limited variation" diagnoses — the diagnosis becomes the optimization signal.



## 2. Fit with the current MatrAIx plan

The Persona plan already has the backbone (Task 1 schema → Task 2 construction → Task 3 filtering/eval → Task 4 PersonaBench → Task 5 Train → Task 6 human validation → Task 7 release). Two existing items are exactly where AutoPersona plugs in, *upgraded from descriptive to causal*:

- **Task 1 §4 (behavioral-sensitivity probe)** — vary one axis, rank which axes move behavior. We make this a *causal* estimate with an explicit identification argument, and the ranked list becomes the engine driving schema coarsening rather than a one-off heuristic.
- **Task 3 (persona-factor analysis)** — which attributes shift action distributions. We supply the estimand, the probes, and the keep/merge/drop rule behind that matrix.

The missing layer is the optimization loop connecting schema design to downstream behavior:

```text
constitution σ → generator G_σ → multi-turn rollouts in target environments
   → causal factor→behavior matrix (the novel signal)
   → GEPA reflective update (support coverage under fidelity constraint)
   → smaller, causally-sufficient constitution σ′
```



## 3. Problem framing: heterogeneity as support coverage

A persona system is **homogeneous** when many profiles produce the same behavior: different personas share the assistant register, demographic variation does not change choices, agents are uniformly cooperative, and outcomes are driven by the base model rather than the persona. At 8.3B scale this is the central risk — millions of nominally distinct personas that are behaviorally identical.

The target is not maximum randomness, and — importantly — not maximum coverage of *trait* space (the Persona Generators objective, which can produce diverse traits with behaviorally unrealistic personas). The target is **coverage of the task's behavior space under a fidelity constraint**: the population should induce the range of behaviors that occur or could plausibly occur in the task (skeptical users challenging claims, low-literacy users asking for clarification, impatient users abandoning, privacy-sensitive users withholding data, adversarial-but-task-preserving users probing safety), and each persona should behave as a real person with those factors would. §5 makes this precise.



## 4. Persona Constitution

A small set of factor families every generator must respect, with rules for when factors are active, how they interact, and how they are evaluated.

### 4.1 Factor families

| Family | Role | Example factors |
|---|---|---|
| Baseline identity | Population grounding | age, region, language, education, occupation, income, household |
| Sociopsychological | Stable preferences / personality | Big Five, values, risk tolerance, trust, skepticism, patience |
| Capability / resource | What the persona can do | domain expertise, literacy, technical fluency, time, money, device |
| Communication / cognition | How it interacts | verbosity, tone, learning style, attention span, ambiguity tolerance |
| Preference / history | Persistent behavioral priors | product preferences, churn triggers, prior experience, brand trust |
| Interaction state | Session-local dynamics | mood, urgency, frustration, goal clarity, trust in the target system |
| Persona policy | Behavioral control layer | cooperative, reluctant, confused, adversarial, privacy-protective, impatient |
| Environment / task binding | What matters here | task objective, action space, observation space, eval metrics |
| Theory-grounded constraints | Domain validity | budget, incentive compatibility, health/safety/legal, bounded rationality |

### 4.2 Design principle: causal sufficiency, not completeness

A factor earns a place in the **core** schema only if it is causally load-bearing somewhere in the target task distribution. Everything else is a task-specific overlay (relevant in some scenarios) or dropped. Population importance alone does not justify a *behavioral* factor: Nemotron-grade demographic realism is retained as a grounding layer (§8) without every demographic field being a behavioral factor.

### 4.3 Task-conditioned relevance map

Each scenario declares primary vs secondary factors and the behavioral signals it expects. This is the prior the causal loop refines (the loop may promote or demote factors based on measured effects).

```yaml
scenario: ai_support_assistant_redteam
environment_type: chatbot
primary_persona_factors: [trust_level, patience, frustration_tolerance,
                          technical_fluency, ambiguity_tolerance,
                          adversarialness, privacy_sensitivity]
secondary_persona_factors: [age, language_proficiency, device_context, prior_context]
expected_behavioral_signals: [asks_clarification, challenges_unsupported_claims,
                              abandons_task, attempts_prompt_injection,
                              escalates_to_human, repeats_question,
                              refuses_to_share_personal_data]
```



## 5. Problem formulation

### 5.1 Setup

A persona is a pair: structured factors `f = (f_1, …, f_m)` and a narrative `x = Narr(f)` produced by the LLM expansion step. An agent `A_θ` conditioned on `(f, x)` interacts with a target system `S` in environment `E` over a horizon, producing a trajectory `τ` and behavioral outcomes `b(τ)` (binary signals such as *abandoned* / *refused-data* / *attempted-injection*, plus continuous summaries such as turn count, clarification rate, satisfaction).

### 5.2 Causal estimands

For factor `f_j` and a value contrast `a → a′`:

- **Average causal effect (ACE)**, marginalizing other factors over the population prior `π`:
  `ACE_j(a→a′) = E_{f_{-j}∼π}[ E[b | do(f_j=a′), f_{-j}] − E[b | do(f_j=a), f_{-j}] ]`.
- **Controlled direct effect (CDE)**: the same with `f_{-j}` held at a reference `c` (one persona, one knob). The one-factor perturbation probe is the CDE; the ACE is its population-marginal version.




### 5.3 Objective: support coverage under bounded fidelity loss

We treat coverage as the **primary objective** and fidelity as a **constraint**, rather than as co-equal terms in an additive score. Let `B_H` be the distribution of behaviors that real people from the target population produce in the task, with support `supp(B_H)`, and let `B_P` be the behavior distribution induced by the simulated population `P = G_σ`. There are two ways `B_P` can match `B_H`:

- *Density matching* aligns `B_P` with the density of `B_H`, concentrating mass on the modal user. It is the right objective when the simulation is used as a measurement instrument, but it leaves the tail — the rare users that drive failures — unexplored.
- *Support coverage* aligns the support of `B_P` with `supp(B_H)`, spanning the full range of plausible behaviors including the tail.

Coverage and fidelity are thus not opposing forces but two halves of matching the support: **coverage pushes `B_P` outward to reach the boundary of `supp(B_H)`; fidelity prevents `B_P` from placing mass outside it.** Persona Generators maximizes coverage with no support constraint and consequently places mass outside `supp(B_H)` (diverse but unrealistic); density matching stays inside but never reaches the boundary. Our objective is to reach the boundary without crossing it:


### 5.4 Fidelity is plausibility, not rationality

The constraint must enforce **plausibility** — "could a real person with factors `f` behave this way?" — not **rationality**. Constraining rationality would penalize realistic-but-irrational behavior (a confused user selecting the wrong option, an impatient user abandoning a beneficial flow, a low-literacy user making a poor financial choice), which are precisely the high-value coverage targets for stress-testing. Plausibility admits bounded-rational and irrational-but-human behavior while excluding the incoherent or non-human (a self-described novice who suddenly produces expert output; a budget-conscious persona that ignores price for no reason). This mirrors the LLM Economist construction (2507.15815), where realistic behavior required a *bounded-rational* objective — a rational core plus a satisfaction term — rather than rationality alone. Rationality (and domain theory) defines the support boundary only in normative domains such as economics, mechanism design, and safety-critical settings, where it enters as a hard constraint (§5.7, tier 1).





## 6.  Iteration

### 6.1 Why GEPA, not AlphaEvolve

GEPA (2507.19457) reflects on *trajectories* in natural language to diagnose failures and propose targeted edits, and maintains a Pareto front of candidate specs rather than a single global best, at ~35× fewer rollouts than RL. This fits AutoPersona on three counts: the object we optimize is a *spec* (the constitution + generation rules), a natural-language program in GEPA's domain; the feedback is rich (a causal factor→behavior matrix plus per-trajectory diagnoses), wasted if compressed to a scalar; and rollouts are expensive, so sample efficiency is first-order. AlphaEvolve-with-scalar-diversity (Persona Generators) is precisely what we differentiate from.

### 6.2 Loop sketch

```text
Input: initial constitution σ0, generator G0, target environments E,
       task/eval suite T, grounded reference B_H, theory/safety constraints H

For iteration k:
  1. instantiate G_{σk}; sample persona batch P_k (respecting tier-1 validity)
  2. run multi-turn rollouts in E, including paired-branch counterfactuals (§5.4)
  3. estimate the causal factor→behavior matrix (§5.2–5.4) + A1 leakage audit (§5.3)
  4. compute Cov, the tiered fidelity terms (§5.7), and |σ|
  5. GEPA reflection: feed the matrix + per-trajectory diagnoses as natural-language
     feedback; propose edits to {active factors, granularity, factor correlations,
     narrative rules, persona-policy rules, task-conditioned activation, sampling weights}
  6. keep the Pareto front over (Cov, Fid, −|σ|); stochastically expand from it
  7. write a short research note: what changed, what improved/regressed, what to try next

Output: minimal sufficient constitution σ*, generator G*, the causal matrix,
        PersonaBench tasks + eval rules, high-fidelity rollouts for PersonaTrain
```




## 7. Evaluation: the causal factor→behavior matrix

### 7.1 Example: Output object (per environment / task family)

| Factor | Causal effect? | Direction | Standardized effect (CDE/ACE) | CI | A1 leak? | Keep / merge / drop |
|---|---|---|---:|---:|---|---|
| trust_level | yes | skeptical → more verification | 0.41 | tight | no | keep |
| privacy_sensitivity | yes | refuses unnecessary data | 0.55 | tight | no | keep |
| age | weak | older → slightly more cautious | 0.06 | wide | flag | coarsen / merge |
| region | none (this task) | — | ~0 | — | no | inactive overlay |
| horoscope_interest | none | — | 0 | tight | no | drop |



### 7.2 Probes

1. **CDE probe** — fix persona, intervene one factor, paired-branch rollouts, measure outcome contrast.
2. **ACE probe** — same, marginalizing other factors over `π`.
3. **Counterfactual persona pairs** — trusting/skeptical, patient/impatient, novice/expert, privacy/convenience — as paired branches sharing history.
4. **Factor & policy ablation** — remove a factor or the persona-policy layer; does behavior collapse to generic cooperation?
5. **Long-turn persistence** — does the effect survive 5 / 10 / 20 turns? (links to instruction-drift work, 2402.10962.)
6. **A1 leakage audit** — narrative probe for implied other-factor shifts across each contrast.
7. **Mechanistic (open-source only)** — persona-vector projection / attention as a secondary check that the factor is used (2507.21509).
...




## 8. Relationship to prior work

- **Nemotron-Personas** — population-grounded demographic baseline; kept as the grounding layer (the `B_H` reference for tier-2 fidelity), not as the behavioral schema. Demographics alone give limited behavioral heterogeneity (cf. 2604.28048).
- **SCOPE** — sociopsychological grounding; the stable middle layer of the constitution.
- **Persona Policies** — lightweight, interpretable behavioral control; adopted as first-class factors whose causal effect is measured like any other.
- **Persona vectors** (2507.21509) — mechanistic monitoring/control; the *secondary* attribution signal that can corroborate the behavioral causal estimate on open-source models.
- **ACE-Align** (2601.12962) — closest causal-attribution prior; single-turn MCQ, aligns model CE to data CE. We extend to multi-turn interactive identification and use the estimate to evolve a schema.
- **Persona Generators** (2602.03545) — diversity/coverage of responses via AlphaEvolve; we optimize the schema for support coverage under a fidelity constraint.
- **ODYSSIM** (2606.14199) — weight-level behavioral foundation model; orthogonal and composable.
- **"Stable Behavior, Limited Variation"** (2604.28048), **"From Single to Societal"** (2511.11789) — empirical motivation that many factors do not move behavior and that effects are confounded; we turn this into the optimization signal.
- **Behavioral-economics persona conditioning** (2508.18600) — evidence that low-dimensional grounded trait sets align LLM behavior to human distributions (Wasserstein); supports both the fidelity term and the minimality hypothesis.
- **GEPA** (2507.19457) — the reflective Pareto optimizer used in §6.
- **Theory-grounded constraints (bounded rationality)** — enter as tier-1 hard constraints and the constraint set `H`; realized as the Pareto-front shape (§6.3), not a slogan.



## 9. Experimental design

**Baselines.** B0 demographic-only (Nemotron-style, no sociopsychological/policy factors); B1 full schema (all families, fine granularity); B2 diversity-only loop (Persona-Generators-style, scalar trait-coverage fitness, no fidelity term)

**Hypotheses.**
- **H1 (minimality):** the causally-pruned schema `σ*` matches or exceeds the full schema B1 on `Cov` at a fraction of `|σ|` and rollout cost.
- **H2 (causal ≠ naive):** the keep/merge/drop decision under causal matching differs materially from naive sensitivity (−causal ablation) — the rigor *changes the answer*.
- **H3 (grounding):** the fidelity constraint prevents the diversity-without-realism drift of B2 / −fidelity, at a quantifiable cost in `Cov`.

**Metrics (with estimands).** effect = standardized CDE/ACE (§5.2); `Cov` = behavioral-embedding coverage of `supp(B_H)`; `Fid` = Wasserstein/calibration to the reference, aggregate level (§5.7 tier 2); `|σ|` = active factors × granularity; plus long-turn persistence, A1 leak rate, and judge–human agreement.
