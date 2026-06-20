# Literature Coding Handoff: Objective Axis

## Task

Systematically classify the stored literature in `personas/survey-paper/literature/` using the objective-axis taxonomy in `personas/survey-paper/taxonomy_objective_axis.md`.

Do not rewrite the survey paper. Do not edit the construction-technique taxonomy. This task concerns only what each paper's persona set, persona method, or persona use is meant to accomplish.

## Source Files

Use these local files first:

- `personas/survey-paper/taxonomy_objective_axis.md`
- `personas/survey-paper/literature/papers_top100_taxonomy_coding.csv`
- `personas/survey-paper/literature/papers_merged_top100.csv`
- `personas/survey-paper/literature/papers_merged_top100.jsonl`

For paper claims, always include a link using `url`, `doi`, `arxiv_id`, or `pdf_url`. Do not reference a paper without a link.

## Objective Categories

Use these objective values exactly, semicolon-separated when multiple apply:

```text
Population Representation
Coverage and Stress Testing
Individual Fidelity
Behavioral Calibration
Design Communication
Bias and Harm Auditing
Agent / Model Evaluation
Unclear - needs full-text check
Not applicable
```

## Output File

Create or update:

`personas/survey-paper/literature/papers_top100_objective_axis_coding.csv`

Columns:

```text
id
title
year
url
source_category
objective_categories
objective_basis
confidence
boundary_notes
needs_followup
```

Use `source_category` from `papers_top100_taxonomy_coding.csv` if available.

Use confidence values:

```text
high
medium
low
```

## Coding Rules

1. Objective labels are multi-label. Assign all objectives clearly supported by title, abstract, local coding, or local metadata.
2. Do not infer objectives only because a method could support them.
3. If a paper is not about persona generation but uses personas for role-play, steering, alignment, safety, or capability analysis, code **Agent / Model Evaluation** rather than `Not applicable`.
4. Use `Not applicable` only when the paper appears unrelated to persona objectives after reading local metadata.
5. Use `Unclear - needs full-text check` when local metadata does not reveal the objective.
6. Map old tags as follows when supported:
   - `density matching`, `joint-structure preservation`, `quota/stratified balance` -> **Population Representation**
   - `support coverage`, `stress/edge-case testing` -> **Coverage and Stress Testing**
   - `individual fidelity` -> **Individual Fidelity**
   - `behavioral calibration` -> **Behavioral Calibration**
   - `design communication` -> **Design Communication**
   - `bias/harm audit` -> **Bias and Harm Auditing**
   - `role-playing evaluation` -> **Agent / Model Evaluation**
   - `narrative enrichment` -> do not code directly; map to another objective only if the purpose is clear.
7. Always include paper links in the summary.

## Deliverable Summary

After coding, provide:

1. Count of papers per objective category. Because this is multi-label, counts may sum above 100.
2. 5-10 high-confidence exemplars with links.
3. Ambiguous boundary cases with links and recommended handling.
4. A short assessment of whether the seven objective categories cover the corpus.

