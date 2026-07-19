# Constraint-based vs Graph-based Sampler Quality Report

Repository storage note: the JSONL files referenced below were generated for
readable qualitative analysis, but are not kept as committed artifacts. The
retained sample artifacts are the compact `.codes` files plus their
`.codes.schema.json` sidecars in this directory.

## 1. Evaluation setup
- Input package: `sampler_comparison_1000_20260702.zip`.
- Sample size: 1000 personas for each sampler, seed 42.
- Compared outputs: `constraint_based_1000.jsonl` and `full_dag_forward_1000.jsonl`.
- The analysis below treats generation quality as: schema coverage, internal consistency, dependency realism, diversity, compactness/runtime, and downstream usability.
## 2. Executive conclusion
The graph-based sampler is the better candidate for the final persona pool because it encodes a much richer persona state, exposes explicit dependency structure, and produces more conditionally shaped distributions. It moves the generator from a flat core-profile sampler to a full persona-state sampler. However, the graph version should not be treated as fully production-ready without a lightweight consistency repair layer. It still produces local contradictions in long-tail nodes, especially when demographic variables, life-stage variables, and newly added life-experience/demographic-detail attributes are sampled jointly.

The constraint-based sampler is cleaner and faster for the old 82-field schema. Its validation violations are zero, and its samples are easy to inspect. But quality is limited by shallow coverage and weak semantic coupling. Many fields look independently or near-independently sampled, so the resulting persona often feels like a bag of attributes rather than a coherent person.
## 3. Basic comparison
| Dimension | Constraint-based | Graph-based | Interpretation |
|---|---:|---:|---|
| Samples | 1000 | 1000 | Matched sample size. |
| Fields per sample | 82 | 1224 | Graph emits 14x+ more attributes. |
| Shared fields | 82 | 82 | Graph is a strict superset of the old core schema. |
| JSONL file size | 2,796,378 bytes | 38,796,803 bytes | Graph JSONL is much larger because it emits 1224 attributes. |
| Compact code output | 82,000 bytes + 22,921 byte schema | 1,224,000 bytes + 301,307 byte schema | Codes format solves most storage overhead. |
| Runtime | 0.030s | 0.623s JSONL / 0.848s codes | Graph is slower but still fast for 1000 samples. |
| Avg. per-field entropy | 2.45 bits | 1.77 bits | Graph has lower average entropy because many nodes are conditionally concentrated. |
| Avg. unique values per field | 5.82 | 4.86 | Graph contains many low-cardinality trait/skill nodes. |

## 4. Coverage and expressiveness
### Constraint-based sampler
The constraint version covers the old core persona profile: demographics, language, professional background, intent/context, and cognitive/communication style. This is useful for lightweight testing and debugging, but it cannot represent fine-grained user capabilities, attitudes, interests, habits, programming skills, academic familiarity, health profile, values, or domain-specific expertise.

### Graph-based sampler
The graph version preserves all 82 old fields and adds 1142 additional nodes. The schema groups these into 35 categories. The largest categories are expertise domains, media interests, topic interests, cultural interests, tool skills, worldview/belief nodes, general skills, language/communication, professional industry, Big Five/personality, hobbies, values, programming skills, sports, food, habits, preferences, and life-experience variables. This makes the graph sampler much more suitable for persona-faithfulness experiments because many downstream behaviors can be grounded in explicit attributes rather than inferred from a small profile.

Top graph schema categories by node count:

| Category | Node count |
|---|---:|
| Expertise: Domains | 144 |
| Interests: Media | 81 |
| Interests: Topics | 78 |
| Interests: Culture | 74 |
| Skills: Tools | 69 |
| Worldview: Beliefs | 67 |
| Expertise: Skills | 64 |
| Linguistic: Language | 53 |
| Professional: Industry | 51 |
| Personality: Big Five | 50 |
| Interests: Hobbies | 50 |
| Values & Motivation | 46 |
| Skills: Programming | 44 |
| Interests: Sports | 40 |
| Linguistic: Communication | 37 |

## 5. Distribution realism on shared core fields
The two samplers differ strongly even on the 82 shared fields. The constraint sampler is closer to balanced/uniform coverage, while the graph sampler produces conditionally skewed distributions. This is generally desirable if the DAG encodes world-like priors, but it also makes bias/coverage auditing more important.

| Field | Constraint-based dominant values | Graph-based dominant values | Quality reading |
|---|---|---|---|
| `age_bracket` | 55-64 14.4%, 18-24 14.3%, 25-34 14.3%, 35-44 14.3%, 45-54 14.3% | 25-34 15.6%, 35-44 14.8%, 55-64 11.7%, 45-54 10.6%, 5-12 10.5% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `region` | Latin America 10.8%, Oceania 10.7%, North America 10.7%, Southeast Asia 10.6%, South Asia 10.5% | South Asia 22.9%, East Asia 20.3%, Sub-Saharan Africa 18.4%, Southeast Asia 8.6%, Latin America 7.5% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `primary_language` | Bengali 10.0%, Portuguese 9.7%, German 9.1%, Hindi 8.7%, Mandarin 8.5% | English 20.9%, Mandarin 20.3%, Hindi 10.1%, Spanish 9.9%, Swahili 7.2% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `english_proficiency` | Fluent (C1-C2) 21.5%, Native 21.4%, Basic (A1-A2) 20.2%, Intermediate (B1-B2) 18.6%, None 18.3% | None 39.4%, Basic (A1-A2) 17.2%, Intermediate (B1-B2) 16.1%, Fluent (C1-C2) 13.9%, Native 13.4% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `domain` | Hospitality 8.1%, Public Sector 7.9%, Finance & Economics 7.9%, Manufacturing 7.5%, Software & AI 6.8% | Agriculture 23.7%, Manufacturing 12.8%, Business & Management 10.2%, Education 8.0%, Hospitality 7.1% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `subject_specialty` | Comparative literature 7.6%, Molecular biology 7.3%, Curriculum design 7.1%, Structural engineering 7.0%, Constitutional law 6.7% | Electrical work 27.2%, Agronomy 15.9%, Operations 14.2%, Culinary arts 11.4%, Curriculum design 5.6% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `highest_education` | Vocational / cert 21.8%, Bachelor's 21.0%, Secondary 19.9%, Master's 16.5%, Doctorate 12.7% | Secondary 35.6%, No formal 21.0%, Primary 19.7%, Bachelor's 9.8%, Vocational / cert 7.4% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `seniority` | Student / intern 26.8%, Mid 16.0%, Senior 14.5%, Entry 13.3%, Retired 10.6% | Student / intern 37.7%, Entry 18.3%, Mid 14.3%, Senior 10.4%, Retired 9.9% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `years_experience` | 0-2 38.9%, 3-5 17.6%, 11-20 17.1%, 6-10 15.7%, 20+ 10.7% | 0-2 43.8%, 11-20 17.4%, 20+ 15.0%, 6-10 13.1%, 3-5 10.7% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `life_stage` | Student 21.9%, Career change 16.3%, Early career 15.9%, Empty nester 14.2%, Parent of young kids 11.5% | Student 33.5%, Mid-life 21.9%, Early career 14.0%, Career change 12.7%, Retirement 7.5% | Graph is more prior-shaped; constraint is more coverage-balanced. |
| `tech_savviness` | Comfortable 22.4%, Avoidant 21.7%, Digital native 19.5%, Reluctant 18.3%, Cautious adopter 18.1% | Comfortable 30.6%, Cautious adopter 23.2%, Reluctant 19.2%, Avoidant 13.6%, Digital native 13.4% | Graph is more prior-shaped; constraint is more coverage-balanced. |

## 6. Internal consistency checks
I applied rule-based sanity checks to the generated samples. These checks are not a full validator; they are diagnostic probes for obvious cross-field contradictions.

| Check | Constraint count | Constraint rate | Graph count | Graph rate |
|---|---:|---:|---:|---:|
| `minor_parenting_journey_implausible` | 0 | 0.0% | 248 | 24.8% |
| `monolingual_native_english_nonenglish_primary` | 63 | 6.3% | 1 | 0.1% |
| `native_english_with_nonenglish_primary_language` | 200 | 20.0% | 1 | 0.1% |
| `retired_seniority_without_retirement_stage` | 0 | 0.0% | 45 | 4.5% |
| `software_ai_with_low_tech_savviness` | 24 | 2.4% | 12 | 1.2% |
| `teen_nonstudent_life_stage` | 0 | 0.0% | 5 | 0.5% |

### Main consistency observations
- Constraint-based has fewer contradiction types mostly because it has fewer fields. The largest visible issue is language consistency: `english_proficiency = Native` often appears with a non-English `primary_language`, sometimes together with `multilingualism = Monolingual`.
- Graph-based almost eliminates the language inconsistency, which suggests the DAG dependencies are doing useful work. The rate drops from 20.0% to 0.1% for native-English/non-English-primary conflicts.
- Graph-based introduces new contradiction surfaces because it samples many more life-history and demographic-detail nodes. Examples include child/teen samples with implausible parenting journeys, retired seniority not always aligned with retirement life stage, and some child samples with non-child-compatible role/function details.
- These graph issues look repairable. They are not evidence that the DAG approach is worse; they are evidence that extra emitted nodes need either stronger parent links, hard masks, or a post-sampling repair pass.

## 7. Qualitative quality assessment
### Constraint-based sample quality
Strengths:
- Easy to read, debug, and validate.
- Generates compact profiles suitable for quick tests.
- The old core fields are consistently present and validation reports zero violations.

Weaknesses:
- Persona often feels synthetic because many attributes combine without enough causal/contextual glue.
- It has limited behavioral depth: e.g., it can say a user is risk-seeking or formal, but it cannot express the supporting values, habits, skills, topic attitudes, or domain familiarity that would make those behaviors robust.
- Some combinations are world-implausible, especially language-region-primary-language-proficiency combinations and domain/tech-skill combinations.

### Graph-based sample quality
Strengths:
- Much richer behavioral substrate. It can support persona faithfulness tests across knowledge, tools, programming ability, values, attitudes, preferences, habits, and communication style.
- Better dependency realism on several core axes. For example, age, life stage, seniority, education, language, and regional distributions are no longer flat.
- The code format is efficient enough for large-scale sampling despite the wide schema.

Weaknesses:
- Full JSONL is heavy and not human-readable at scale. For most pipelines, the compact code format plus schema should be the default artifact.
- Some long-tail nodes are under-constrained. The most important issue is not field-level validity, but cross-field coherence after adding many new nodes.
- The graph currently appears better at local parent-child dependency than global persona-level coherence. A persona can be plausible in many local neighborhoods while still having one or two globally strange attributes.

## 8. Recommendation
Use the graph-based sampler as the main generator, but add a small consistency layer before treating it as final production data. The recommended pipeline is:

1. Sample from the full DAG.
2. Apply hard masks for impossible or near-impossible combinations, especially age × education, age × parenting, age × driving, age × seniority, retirement × employment, language × English proficiency × multilingualism, and domain × skill/tech-savviness.
3. Apply a global persona coherence score or repair pass over high-impact nodes.
4. Emit compact codes as the canonical storage format and JSONL only for debugging/sample inspection.
5. Keep the 82 shared core fields as a regression-test slice, so future graph changes can be compared against the old generator.

## 9. Concrete fixes for graph sampler
| Priority | Fix | Rationale |
|---|---|---|
| High | Add hard age masks for education, children, parenting journey, driver status, and seniority. | Most obvious contradictions are age-conditioned. |
| High | Align `seniority = Retired`, `demo_employment_status = Retired`, and `life_stage = Retirement`. | Retirement should be a tightly coupled state cluster. |
| High | Treat `primary_language`, `english_proficiency`, and `multilingualism` as a constrained triad. | Graph already improves this; a hard final check can eliminate the remaining edge case. |
| Medium | Add domain-skill coherence edges, e.g., Software & AI should raise tech/programming familiarity. | Prevents domain labels from conflicting with capability/style labels. |
| Medium | Use category-level emission presets. | Some tasks need 82-core fields; others need full 1224-node persona state. |
| Medium | Add a graph-level QA dashboard. | Track contradiction rate, entropy, marginal drift, and top parent-child mutual information after each graph edit. |

## 10. Final judgment
For generation quality, graph-based is directionally better and should replace constraint-based as the main sampler. Constraint-based remains useful as a minimal baseline and smoke-test generator, but it is too shallow for realistic persona simulation. The graph sampler gives the right substrate for downstream persona behavior, especially when evaluating whether assigned attributes such as risk aversion, programming familiarity, skepticism, verbosity, or domain expertise actually transfer into generated behavior. The remaining work is mainly consistency repair, not a reason to return to the old constraint-only design.

## 11. Text explanation version
The constraint-based sampler is clean and fast, but it is essentially a shallow 82-field core-profile generator. It is good for debugging and lightweight coverage tests, but many samples look like independent attribute bundles rather than coherent people. The graph-based sampler is much stronger for realistic persona generation because it emits all old core fields plus more than one thousand additional attributes covering skills, interests, values, habits, attitudes, language, professional background, academic familiarity, programming ability, and personality structure. This makes it much more useful for persona-faithfulness evaluation, since downstream behavior can be conditioned on explicit supporting attributes rather than a small set of labels. The graph version also improves several dependency problems from the old generator, especially language consistency, where native-English/non-English-primary conflicts drop sharply. The main weakness is that the graph exposes many new contradiction surfaces: some long-tail demographic and life-history nodes are not yet sufficiently constrained, especially around age, parenting, retirement, driving, and role/seniority. My recommendation is to use the graph-based sampler as the primary generator, keep the constraint-based sampler as a baseline/smoke test, and add a lightweight post-sampling repair layer or hard masks for impossible combinations. Overall, the graph-based version is higher quality and more scalable, but it needs consistency validation before being treated as production-ready.
