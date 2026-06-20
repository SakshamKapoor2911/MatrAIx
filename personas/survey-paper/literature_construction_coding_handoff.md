# Literature Coding Handoff: Four-Way Source Taxonomy

## Task

Systematically categorize the stored literature in `personas/survey-paper/literature/` using the four-way construction-source taxonomy in `personas/survey-paper/taxonomy_construction_technique.md`.

Do not write the survey paper. Produce a coding artifact and a short summary of category patterns, ambiguous cases, and recommended follow-up checks.

## Source Files

Use these local files first:

- `personas/survey-paper/literature/papers_merged_top100.csv`
- `personas/survey-paper/literature/papers_merged_top100.jsonl`
- `personas/survey-paper/literature/corpus_summary.md`
- `personas/survey-paper/taxonomy_construction_axis.md`

For paper claims, always include a link using `url`, `doi`, `arxiv_id`, or `pdf_url`. Do not reference a paper without a link.

## Four Source Categories

1. **Authored Archetypes**
   - Human-designed persona types.
   - Code here when personas are primarily crafted by experts, designers, stakeholders, user researchers, or manual qualitative synthesis.

2. **Model-Generated Personas**
   - LLM-invented persona distributions.
   - Code here when personas are substantially invented by the model from broad prompts, labels, or weak constraints.

3. **Population-Sampled Personas**
   - Top-down draws from population structure.
   - Code here when persona records are sampled, weighted, synthesized, fused, or calibrated from census, surveys, panels, synthetic population models, or other target-population distributions.

4. **Trace-Grounded Personas**
   - Bottom-up reconstructions from person-level evidence.
   - Code here when personas are reconstructed from interviews, logs, social media, behavioral histories, user profiles, longitudinal records, or digital-twin traces.

## Coding Fields To Produce

Create or update a CSV in `personas/survey-paper/literature/` named:

`papers_top100_taxonomy_coding.csv`

Columns:

```text
id
title
year
url
source_category
source_subtype
objective_tags
anchor_source
evidence_quote_or_abstract_basis
confidence
boundary_notes
needs_followup
```

Use these category values exactly:

```text
Authored Archetypes
Model-Generated Personas
Population-Sampled Personas
Trace-Grounded Personas
Unclear - needs full-text check
Not Persona Generation / adjacent
```

Use `confidence` values:

```text
high
medium
low
```

## Objective Tags

Add one or more semicolon-separated tags when visible from metadata/abstract:

```text
density matching
joint-structure preservation
quota/stratified balance
support coverage
stress/edge-case testing
individual fidelity
behavioral calibration
narrative enrichment
design communication
bias/harm audit
role-playing evaluation
not applicable
unclear
```

## Boundary Rules

1. Classify by the anchor source, not by the final prompt format.
2. If an LLM only verbalizes structured data, classify by the structured data source.
3. If a method starts from a population scaffold and adds psychometrics, style, or narrative detail, code **Population-Sampled Personas** with an enrichment subtype.
4. If a method starts from individual traces and later reweights/calibrates to population targets, code **Trace-Grounded Personas** with subtype `population-calibrated traces`.
5. If the paper mainly evaluates persona following, role-play behavior, or alignment without constructing personas, code `Not Persona Generation / adjacent` unless a clear persona construction method is described.
6. If local metadata is insufficient to determine whether the paper constructs personas, code `Unclear - needs full-text check` and set `needs_followup` to `yes`.
7. If multiple sources are genuinely co-equal, choose the source that carries the main validity claim and explain the ambiguity in `boundary_notes`.
8. Always include links in summaries and examples.

## Known Anchor Examples

- [NVIDIA Nemotron-Personas-USA](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA): **Population-Sampled Personas**, census/ACS-grounded and narratively enriched.
- [German General Social Survey Personas](https://arxiv.org/abs/2511.21722): **Population-Sampled Personas**, survey-derived.
- [PERSONA: A Reproducible Testbed for Pluralistic Alignment](https://arxiv.org/abs/2407.17387): **Population-Sampled Personas**, procedurally generated from US census data.
- [LLM Generated Persona is a Promise with a Catch](https://arxiv.org/abs/2503.16527): **Model-Generated Personas**, critiques ad hoc LLM-generated personas.
- [When LLMs Imagine People](https://arxiv.org/abs/2602.00044): **Model-Generated Personas**, open-ended persona generation audit.
- [Synthia](https://arxiv.org/abs/2507.14922): **Trace-Grounded Personas**, social-media-grounded.
- [The Need for a Socially-Grounded Persona Framework for User Simulation](https://arxiv.org/abs/2601.07110): **Trace-Grounded Personas**, participant-protocol-grounded SCOPE personas.
- [Population-Aligned Persona Generation for LLM-based Social Simulation](https://arxiv.org/abs/2509.10127): **Trace-Grounded Personas**, subtype `population-calibrated traces`, or mark as bridge case because trace-derived narratives are aligned to psychometric population distributions.
- [Persona Generators](https://arxiv.org/abs/2602.03545): code the construction source based on full text if possible; objective tag should include `support coverage`.

## Deliverable Summary

After coding, provide:

1. Count of papers per category.
2. 5-10 high-confidence exemplars with links.
3. Ambiguous boundary cases with links and recommended coding.
4. Whether the four-way taxonomy seems sufficient for the top-100 corpus.
