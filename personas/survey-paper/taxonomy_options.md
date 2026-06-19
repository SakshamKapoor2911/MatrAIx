# Taxonomy Options for Discussion

Status: preliminary discussion draft, not settled.

## Option A: Method-Family Taxonomy

This taxonomy groups papers by the main construction procedure.

- Demographic prompting
- Role or character personas
- Survey-grounded synthetic respondents
- Psychometric and value-grounded personas
- Data-driven HCI personas
- Synthetic population and microsimulation personas
- LLM-generated open-ended personas
- Hybrid data-theory-LLM pipelines

Strength: easy for readers to understand.

Risk: method families blur together when a paper uses both structured sampling and LLM narrative expansion.

## Option B: Pipeline-Stage Taxonomy

This taxonomy groups choices by where they occur in the generation pipeline.

- Target population definition
- Persona schema design
- Data grounding and source selection
- Sampling and data fusion
- LLM narrative realization
- Agent deployment and memory construction
- Validation, calibration, and audit

Strength: aligns tightly with the paper's unit of analysis: persona generation as a procedure.

Risk: less compact as a related-work table because one paper may appear in multiple stages.

## Option C: Multidimensional Taxonomy

This taxonomy codes each paper along orthogonal dimensions.

- Grounding source: none, LLM prior, expert design, survey, census or microdata, behavioral traces, interviews, social media, mixed sources
- Representation: demographic vector, psychometric vector, role label, biography, memory bank, social graph position, policy or preference model
- Sampling logic: hand-authored, prompt enumeration, random generation, stratified sampling, weighted resampling, calibration, optimization, model-based synthesis, statistical matching
- Theoretical basis: none, HCI persona theory, psychometrics, cultural/value theory, social psychology, economics, microsimulation, agent-based modeling
- Validation target: distributional realism, internal consistency, behavioral fidelity, diversity/coverage, persona adherence, fairness/harm, robustness/reproducibility

Strength: most comprehensive and analytically clean.

Risk: heavier coding burden; needs a simple top-level map so readers do not get lost.

## My Current Recommendation

Use Option C as the underlying coding scheme, but present it through a simplified Option B pipeline figure. Option A can become the reader-facing related-work table.

This is intentionally not final. The key question for debate is whether the survey should foreground method families, pipeline stages, or multidimensional coding.
