# Persona Full DAG Quality Report

## Run

- Graph: `persona/synthesis/graph/full_dag.json`
- Samples: 10,000
- Seed: 42
- Generated at: 2026-07-03T01:55:03+00:00
- Python: 3.13.14
- Platform: macOS-15.6-arm64-arm-64bit-Mach-O

## Timing

| Step | Time |
| --- | ---: |
| Load and compile sampler | 0.4284s |
| Static validation | 0.2783s |
| Sample integer-coded DAG rows | 1.5726s |
| Marginal audit | 0.0077s |
| Consistency audit | 1.3706s |
| End-to-end report runtime | 3.6577s |

Sampling throughput: 6359.0 samples/sec.
End-to-end throughput: 2734.0 samples/sec.

## Static Graph Validation

- Validation passed: `true`
- Nodes: 1,242
- Emitted nodes: 1,224
- Directed proposal edges: 6,830
- Full CPT overlays: 54
- Full CPT rows: 17,645
- Conditional masks: 172
- Missing refs: 0
- Duplicate node ids: 0
- Duplicate directed pairs: 0
- Cycle-free: `true`
- Topological dependency violations: 0

## Consistency Audit

- Personas with hard issues: 0 (0.00%)
- Personas with hard or strong issues: 0 (0.00%)
- Personas with any flagged issue: 15 (0.15%)
- Severity issue counts: `{"soft": 15}`
- Group issue counts: `{"finance": 15}`

Top consistency rules:

| Rule | Severity | Group | Count | Share |
| --- | --- | --- | ---: | ---: |
| `unbanked_mobile_wallet_or_crypto_payment` | soft | finance | 15 | 0.15% |

## Focus-Node Marginal Drift

TVD is total variation distance between the sample marginal and the node prior.

| Node | TVD vs prior | Top sampled values |
| --- | ---: | --- |
| `seniority` | 0.1390 | Student / intern: sample 39.13%, prior 34.00%; Entry: sample 18.59%, prior 10.00%; Mid: sample 14.42%, prior 17.00%; Retired: sample 9.48%, prior 18.30% |
| `role_function` | 0.1214 | Operations: sample 31.26%, prior 28.75%; Engineering: sample 11.01%, prior 11.25%; Sales / GTM: sample 9.54%, prior 10.00%; Research: sample 7.99%, prior 2.50% |
| `english_proficiency` | 0.1062 | None: sample 39.03%, prior 29.00%; Basic (A1-A2): sample 18.28%, prior 18.00%; Intermediate (B1-B2): sample 15.03%, prior 17.00%; Fluent (C1-C2): sample 14.81%, prior 14.50% |
| `life_stage` | 0.1017 | Student: sample 35.49%, prior 30.00%; Mid-life: sample 20.29%, prior 19.00%; Early career: sample 13.28%, prior 13.00%; Career change: sample 10.97%, prior 8.00% |
| `demo_children_count` | 0.0611 | None: sample 55.00%, prior 60.00%; 3+ children: sample 12.39%, prior 11.00%; 2 children: sample 12.02%, prior 12.00%; Adult children: sample 11.20%, prior 6.50% |
| `highest_education` | 0.0519 | Secondary: sample 36.72%, prior 36.00%; Primary: sample 21.60%, prior 24.50%; No formal: sample 20.49%, prior 16.50%; Bachelor's: sample 7.15%, prior 8.00% |
| `years_experience` | 0.0376 | 0-2: sample 44.79%, prior 42.00%; 11-20: sample 17.25%, prior 18.00%; 20+: sample 13.97%, prior 13.00%; 6-10: sample 12.83%, prior 14.00% |
| `demo_employment_status` | 0.0300 | Student: sample 33.34%, prior 33.00%; Full-time: sample 24.28%, prior 24.50%; Homemaker: sample 11.13%, prior 8.50%; Retired: sample 9.48%, prior 10.50% |
| `tech_savviness` | 0.0198 | Comfortable: sample 29.55%, prior 28.00%; Cautious adopter: sample 24.22%, prior 25.00%; Reluctant: sample 18.03%, prior 18.00%; Digital native: sample 14.80%, prior 16.00% |
| `domain` | 0.0168 | Agriculture: sample 23.31%, prior 24.00%; Manufacturing: sample 12.13%, prior 12.00%; Business & Management: sample 10.10%, prior 10.00%; Education: sample 7.51%, prior 7.00% |
| `region` | 0.0150 | South Asia: sample 25.39%, prior 25.23%; East Asia: sample 18.70%, prior 19.41%; Sub-Saharan Africa: sample 17.04%, prior 16.85%; Southeast Asia: sample 8.34%, prior 8.78% |
| `age_bracket` | 0.0149 | 25-34: sample 14.58%, prior 14.50%; 5-12: sample 13.55%, prior 13.00%; 35-44: sample 13.26%, prior 13.30%; 45-54: sample 11.12%, prior 11.50% |
| `primary_language` | 0.0125 | English: sample 21.13%, prior 21.50%; Mandarin: sample 19.76%, prior 20.50%; Hindi: sample 10.73%, prior 10.50%; Spanish: sample 9.99%, prior 10.00% |
| `demo_ethnicity_broad` | 0.0122 | South Asian: sample 25.22%, prior 25.00%; East Asian: sample 19.77%, prior 20.50%; Black / African: sample 14.29%, prior 14.50%; White / European: sample 10.96%, prior 10.50% |
| `demo_religion_affiliation` | 0.0119 | Christian: sample 29.01%, prior 28.80%; Muslim: sample 26.16%, prior 25.60%; Hindu: sample 15.21%, prior 14.90%; None: sample 9.14%, prior 9.30% |
| `urbanicity` | 0.0074 | Rural: sample 35.24%, prior 34.50%; Dense urban: sample 24.13%, prior 24.50%; Suburban: sample 20.97%, prior 21.00%; Small town: sample 18.18%, prior 18.50% |
| `socioeconomic_band` | 0.0062 | Lower-middle: sample 33.17%, prior 33.00%; Low income: sample 33.14%, prior 33.50%; Middle: sample 21.95%, prior 21.50%; Upper-middle: sample 9.25%, prior 9.50% |
| `gender_identity` | 0.0056 | Man: sample 50.23%, prior 49.80%; Woman: sample 49.04%, prior 49.50%; Self-described: sample 0.33%, prior 0.20%; Non-binary: sample 0.26%, prior 0.30% |

## Interpretation

- The static graph checks are structural checks over the committed JSON.
- The sampling audit is stochastic and should be compared with the seed and sample count.
- Marginal drift from priors is expected for non-root nodes because pairwise edges, full CPTs, and masks intentionally condition later fields on earlier fields.
- Hard consistency issues should be treated as blockers. Strong and soft issues are triage signals for graph refinement.
