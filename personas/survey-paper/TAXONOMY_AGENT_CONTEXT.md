# Taxonomy Agent Context

This file is the handoff context for a new taxonomy-focused discussion.

## Goal

Help decide the final taxonomy definition for a survey paper on synthetic persona generation for LLM agents.

The user wants a taxonomy that is:

- simple enough to leave an impression
- centered on method families
- focused on how personas are constructed
- useful for arguing that narrative vividness is not population validity
- compatible with the paper's emphasis on marginal validity, joint validity, and enactment validity

## Files To Read First

1. `personas/survey-paper/taxonomy_options.md`
2. `personas/survey-paper/PLAN.md`
3. `personas/survey-paper/literature/papers_merged_top100.csv`
4. `personas/survey-paper/literature/corpus_summary.md`

## Curated Literature Folder

The curated paper corpus is in `personas/survey-paper/literature/`.

Important files:

- `papers_merged_top100.csv`: spreadsheet-friendly index of the top 100 candidate papers.
- `papers_merged_top100.jsonl`: canonical flexible metadata records, one JSON object per paper.
- `papers_arxiv.jsonl`: arXiv search results before final merge.
- `papers.jsonl`: Semantic Scholar search results before final merge.
- `search_log.md` and `search_log_arxiv.md`: reproducible search-query logs.
- `corpus_summary.md`: short corpus summary and notes.

Use these local files as the first source of truth for candidate papers and taxonomy examples. Prefer `rg` for quick title/keyword lookup and `Import-Csv` or JSONL line inspection for structured metadata.

Useful local retrieval patterns:

```powershell
rg -i "population|survey|persona|synthetic|joint|coverage|psychometric" personas\survey-paper\literature
Import-Csv personas\survey-paper\literature\papers_merged_top100.csv | Select-Object title,year,url
Get-Content personas\survey-paper\literature\papers_merged_top100.jsonl -TotalCount 5
```

If more detail is needed for a specific paper, use the `url`, `doi`, or `arxiv_id` fields from the CSV/JSONL to retrieve the paper from arXiv, DOI landing pages, Semantic Scholar, or official venue pages. When current details matter or the local record is insufficient, browse the web and cite the source used.

For arXiv papers, the PDF and abstract URLs usually follow:

```text
https://arxiv.org/abs/<arxiv_id>
https://arxiv.org/pdf/<arxiv_id>
```

Do not rely only on memory for paper claims. Tie taxonomy examples back to the curated records whenever possible.

When referencing papers, always include a link. Use the local `url`, `doi`, `arxiv_id`, or `pdf_url` fields from the curated records to provide a clickable source link.

## Current Working Taxonomy

The current working taxonomy for the first axis is a four-family construction-source / construction-technique taxonomy. See `taxonomy_construction_technique.md` for the full definition and coding rules.

1. Authored Archetypes
2. Model-Generated Personas
3. Population-Sampled Personas
4. Trace-Grounded Personas

The taxonomy should be used with a second, cross-cutting objective axis for density matching, joint-structure preservation, support coverage, stress testing, individual fidelity, behavioral calibration, narrative enrichment, design communication, and bias/harm auditing.

Do not treat Coverage-Optimized Sets as a top-level construction-source family. Treat coverage as a design objective.

## Current Working Objective Axis

The current working taxonomy for the second axis is in `taxonomy_objective_axis.md`.

Objective families:

1. Population Representation
2. Coverage and Stress Testing
3. Individual Fidelity
4. Behavioral Calibration
5. Design Communication
6. Bias and Harm Auditing
7. Agent / Model Evaluation

Narrative enrichment is treated as a means rather than a top-level objective. Role-playing evaluation, persona following, persona steering, and capability or safety testing under persona conditioning are treated as Agent / Model Evaluation.

## Core Conceptual Commitments

### Persona generation is the object

This survey is not primarily about role-playing agents or agent architectures. It is about how persona distributions are specified, sampled, grounded, validated, and audited.

### Joint validity is central

The motivating failure case is an LLM-generated persona such as an 8-year-old with college education. This is not a fluency failure; it is a joint-validity failure.

The paper should distinguish:

1. Marginal validity: one-dimensional distributions match the target population.
2. Joint validity: dependencies and constraints across attributes are preserved.
3. Enactment validity: the LLM behaves consistently with the persona after conditioning.

### Persona validity is not behavioral fidelity

A statistically coherent persona can still be ignored or misused by the LLM. Conversely, an LLM may match some aggregate outcomes from a crude prompt by relying on stereotypes or memorized regularities. These should be treated as different claims.

### Use-relative fidelity

All synthetic-persona simulations are imperfect, but some are useful. The required fidelity depends on downstream use:

- brainstorming
- UX/product ideation
- robustness testing
- role-play/training
- survey simulation
- policy/social simulation
- digital twins

The taxonomy should make it easy to state which generation methods are appropriate for which uses.

## Positioning Against Existing RPLA Survey

From Persona to Personalization classifies personas by the identity being enacted:

1. Demographic Persona
2. Character Persona
3. Individualized Persona

This survey should classify methods by where the persona distribution comes from and how it is constructed.

Potential sentence:

> Whereas role-playing-agent surveys classify personas by the identity being enacted, this survey classifies persona-generation methods by the source and construction logic of the persona distribution.

## Handoff Instruction

Do not start writing the paper. Debate taxonomy only. The concrete deliverable is a proposed final taxonomy definition and a short rationale the user can accept, reject, or revise.
