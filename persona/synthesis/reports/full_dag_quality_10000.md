# Persona Full DAG Quality Report

## Run

- Graph: `persona/synthesis/graph/full_dag.json`
- Samples: 10,000
- Seed: 42
- Generated at: 2026-07-03T13:35:06+00:00
- Python: 3.12.7
- Platform: Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.35

## Timing

| Step | Time |
| --- | ---: |
| Load and compile sampler | 0.5667s |
| Static validation | 0.3746s |
| Sample integer-coded DAG rows | 0.3938s |
| Marginal audit | 0.0117s |
| Consistency audit | 1.6037s |
| End-to-end report runtime | 2.9505s |

Sampling throughput: 25394.7 samples/sec.
End-to-end throughput: 3389.3 samples/sec.

## Static Graph Validation

- Validation passed: `true`
- Nodes: 1,308
- Emitted nodes: 1,290
- Directed proposal edges: 6,999
- Full CPT overlays: 54
- Full CPT rows: 17,645
- Conditional masks: 524
- Missing refs: 0
- Duplicate node ids: 0
- Duplicate directed pairs: 0
- Cycle-free: `true`
- Topological dependency violations: 0

## Consistency Audit

- Personas with hard issues: 0 (0.00%)
- Personas with hard or strong issues: 0 (0.00%)
- Personas with any flagged issue: 16 (0.16%)
- Severity issue counts: `{"soft": 16}`
- Group issue counts: `{"finance": 16}`

Top consistency rules:

| Rule | Severity | Group | Count | Share |
| --- | --- | --- | ---: | ---: |
| `unbanked_mobile_wallet_or_crypto_payment` | soft | finance | 16 | 0.16% |

## Focus-Node Marginal Drift

TVD is total variation distance between the sample marginal and the node prior.

| Node | TVD vs prior | Top sampled values |
| --- | ---: | --- |
| `seniority` | 0.1369 | Student / intern: sample 38.98%, prior 34.00%; Entry: sample 18.60%, prior 10.00%; Mid: sample 14.11%, prior 17.00%; Retired: sample 9.80%, prior 18.30% |
| `role_function` | 0.1225 | Operations: sample 31.46%, prior 28.75%; Engineering: sample 10.59%, prior 11.25%; Sales / GTM: sample 9.97%, prior 10.00%; Research: sample 7.68%, prior 2.50% |
| `life_stage` | 0.1006 | Student: sample 35.39%, prior 30.00%; Mid-life: sample 19.43%, prior 19.00%; Early career: sample 13.19%, prior 13.00%; Retirement: sample 12.21%, prior 10.00% |
| `english_proficiency` | 0.0983 | None: sample 38.03%, prior 29.00%; Basic (A1-A2): sample 17.91%, prior 18.00%; Intermediate (B1-B2): sample 15.33%, prior 17.00%; Fluent (C1-C2): sample 15.30%, prior 14.50% |
| `demo_children_count` | 0.0596 | None: sample 55.72%, prior 60.00%; 3+ children: sample 12.40%, prior 11.00%; 2 children: sample 11.86%, prior 12.00%; Adult children: sample 11.06%, prior 6.50% |
| `highest_education` | 0.0494 | Secondary: sample 36.23%, prior 36.00%; No formal: sample 20.76%, prior 16.50%; Primary: sample 20.69%, prior 24.50%; Bachelor's: sample 8.08%, prior 8.00% |
| `years_experience` | 0.0446 | 0-2: sample 45.05%, prior 42.00%; 11-20: sample 16.55%, prior 18.00%; 20+: sample 14.41%, prior 13.00%; 6-10: sample 12.99%, prior 14.00% |
| `demo_employment_status` | 0.0318 | Student: sample 33.23%, prior 33.00%; Full-time: sample 23.35%, prior 24.50%; Homemaker: sample 11.00%, prior 8.50%; Retired: sample 9.80%, prior 10.50% |
| `tech_savviness` | 0.0197 | Comfortable: sample 29.18%, prior 28.00%; Cautious adopter: sample 24.44%, prior 25.00%; Reluctant: sample 18.26%, prior 18.00%; Digital native: sample 14.59%, prior 16.00% |
| `domain` | 0.0168 | Agriculture: sample 23.31%, prior 24.00%; Manufacturing: sample 12.13%, prior 12.00%; Business & Management: sample 10.10%, prior 10.00%; Education: sample 7.51%, prior 7.00% |
| `region` | 0.0150 | South Asia: sample 25.39%, prior 25.23%; East Asia: sample 18.70%, prior 19.41%; Sub-Saharan Africa: sample 17.04%, prior 16.85%; Southeast Asia: sample 8.34%, prior 8.78% |
| `age_bracket` | 0.0149 | 25-34: sample 14.58%, prior 14.50%; 5-12: sample 13.55%, prior 13.00%; 35-44: sample 13.26%, prior 13.30%; 45-54: sample 11.12%, prior 11.50% |
| `demo_ethnicity_broad` | 0.0144 | South Asian: sample 25.22%, prior 25.00%; East Asian: sample 20.07%, prior 20.50%; Black / African: sample 15.10%, prior 14.50%; White / European: sample 11.02%, prior 10.50% |
| `demo_religion_affiliation` | 0.0135 | Christian: sample 29.75%, prior 28.80%; Muslim: sample 25.21%, prior 25.60%; Hindu: sample 15.15%, prior 14.90%; None: sample 9.40%, prior 9.30% |
| `primary_language` | 0.0131 | English: sample 22.13%, prior 21.50%; Mandarin: sample 19.74%, prior 20.50%; Hindi: sample 10.47%, prior 10.50%; Spanish: sample 9.92%, prior 10.00% |
| `urbanicity` | 0.0074 | Rural: sample 35.24%, prior 34.50%; Dense urban: sample 24.13%, prior 24.50%; Suburban: sample 20.97%, prior 21.00%; Small town: sample 18.18%, prior 18.50% |
| `socioeconomic_band` | 0.0062 | Lower-middle: sample 33.17%, prior 33.00%; Low income: sample 33.14%, prior 33.50%; Middle: sample 21.95%, prior 21.50%; Upper-middle: sample 9.25%, prior 9.50% |
| `gender_identity` | 0.0056 | Man: sample 50.23%, prior 49.80%; Woman: sample 49.04%, prior 49.50%; Self-described: sample 0.33%, prior 0.20%; Non-binary: sample 0.26%, prior 0.30% |

## Interpretation

- The static graph checks are structural checks over the committed JSON.
- The sampling audit is stochastic and should be compared with the seed and sample count.
- Marginal drift from priors is expected for non-root nodes because pairwise edges, full CPTs, and masks intentionally condition later fields on earlier fields.
- Hard consistency issues should be treated as blockers. Strong and soft issues are triage signals for graph refinement.
