# Full DAG Quality Control

Static validation checks:

- no duplicate node ids;
- no duplicate directed pairs;
- no missing source, target, CPT, or mask references;
- cycle-free dependency graph;
- valid topological order;
- normalized node priors, pairwise CPD rows, and full-CPT rows;
- source-proxy nodes marked `emit:false`.

Sampling audits track marginal drift for high-leverage nodes such as:

```text
region
age_bracket
urbanicity
socioeconomic_band
highest_education
tech_savviness
primary_language
demo_ethnicity_broad
demo_religion_affiliation
demo_employment_status
demo_children_count
```

Consistency audits check high-confidence contradictions, including:

```text
child/parent status mismatch
life_stage / children mismatch
minor adult-finance behavior
minor adult-work experience
primary_language / lang_* mismatch
unaffiliated + devout religion mismatch
blind + current-driver mismatch
low-tech + power-user developer tool mismatch
```

The release caveat still applies: the current graph does not add `Not
applicable` to `domain` or `role_function`, so non-working personas can still
carry concrete background or role labels.
