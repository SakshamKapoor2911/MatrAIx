# Construction-Axis Review for Top-100 Literature

Scope: first taxonomy axis only, using the construction-source categories in `taxonomy_construction_technique.md`. I reviewed the existing `papers_top100_taxonomy_coding.csv` against the local merged metadata and updated only clear construction-source corrections. I did not change objective-axis definitions or taxonomy definition files.

## Corrections Made

- [Synthetic Founders](https://arxiv.org/abs/2509.02605): changed from Trace-Grounded Personas to Model-Generated Personas. The local abstract uses interview data as a docking benchmark, while the synthetic founder/investor personas are described as AI-generated.
- [Synonymix](https://arxiv.org/abs/2603.28066): changed from Model-Generated Personas to Trace-Grounded Personas. The local abstract says the method constructs a unigraph from multiple life-story personas, so the bridge case is grounded in prior persona/life-story traces unless full text shows those life stories were model-invented.
- [PersonaBOT](https://arxiv.org/abs/2505.17156): changed from Trace-Grounded Personas to Authored Archetypes. The local abstract points to verified VCE customer personas and customer segment information rather than direct reconstruction from raw person-level traces.
- [ScioMind](https://arxiv.org/abs/2605.13725): kept Trace-Grounded Personas but narrowed subtype and notes to corpus-grounded dynamic profiles. The abstract says profiles come from a corpus-grounded retrieval pipeline, but the corpus granularity still needs follow-up.
- [Restoring Heterogeneity](https://arxiv.org/abs/2604.06663): changed from Unclear / Not Persona Generation to Population-Sampled Personas. The local abstract clearly anchors simulated heterogeneity in U.S. climate-opinion survey data and audience segmentation identifiers.

## Category Counts

Post-correction counts across 100 records:

| Category | Count |
|---|---:|
| Authored Archetypes | 8 |
| Model-Generated Personas | 17 |
| Population-Sampled Personas | 15 |
| Trace-Grounded Personas | 16 |
| Unclear - needs full-text check | 8 |
| Not Persona Generation / adjacent | 36 |

Confidence summary: 64 high, 28 medium, 8 low. There are 35 records still marked `needs_followup=yes`; I left these as follow-up rather than guessing beyond local metadata.

## Do the Four Construction Categories Work?

Yes. The four construction-technique categories cover the top-100 corpus without needing a fifth source family. The main pressure points are hybrids, but they can be handled with subtypes and boundary notes:

- Population scaffold plus value, personality, or narrative enrichment remains Population-Sampled Personas when census/survey/population structure carries the validity claim.
- Person-level traces plus later population calibration remains Trace-Grounded Personas when individual evidence is the starting point.
- LLM-generated personas evaluated against human data should remain Model-Generated Personas unless the human data directly anchors persona construction.
- Authored customer, design, or expert personas remain Authored Archetypes when the source artifact is a human-created persona or segment rather than raw trace reconstruction.

The large adjacent/out-of-scope group is expected because many top-100 hits study persona steering, role-playing evaluation, bias, default assistant personas, or synthetic survey responses without a clear persona-construction method in local metadata. The smaller `Unclear - needs full-text check` group should be manually reviewed before final screening decisions.

## High-Confidence Exemplars

- [Persona Generators](https://arxiv.org/abs/2602.03545): Model-Generated Personas. LLM-mutated generator programs expand small context descriptions into synthetic persona populations.
- [LLM Generated Persona is a Promise with a Catch](https://arxiv.org/abs/2503.16527): Model-Generated Personas. Critiques ad hoc LLM-generated personas.
- [When LLMs Imagine People](https://arxiv.org/abs/2602.00044): Model-Generated Personas. Audits open-ended persona brainstorming by LLMs.
- [PERSONA: A Reproducible Testbed for Pluralistic Alignment](https://arxiv.org/abs/2407.17387): Population-Sampled Personas. Census-derived synthetic user profiles.
- [HACHIMI](https://arxiv.org/abs/2603.04855): Population-Sampled Personas. Theory-aligned, quota-controlled synthetic student population with stratified sampling.
- [German General Social Survey Personas](https://arxiv.org/abs/2511.21722): Population-Sampled Personas. Survey-derived persona prompt collection.
- [Synthia](https://arxiv.org/abs/2507.14922): Trace-Grounded Personas. Personas grounded in real social-media data.
- [SCOPE framework](https://arxiv.org/abs/2601.07110): Trace-Grounded Personas. Built from a 141-item sociopsychological protocol collected from participants.
- [Population-Aligned Persona Generation](https://arxiv.org/abs/2509.10127): Trace-Grounded Personas. Starts from long-term social-media data and then aligns via importance sampling.
- [PersonaCite](https://arxiv.org/abs/2601.22288): Trace-Grounded Personas. Voice-of-customer artifacts are retrieved and cited during persona interaction.

## Important Boundary Cases

- [Culturally Grounded Personas](https://arxiv.org/abs/2601.22396): currently Population-Sampled Personas, medium confidence. Keep as follow-up because local metadata suggests World Values Survey variables, but full text is needed to determine whether these are sampled records or cultural condition labels.
- [Evaluating Cultural Adaptability](https://arxiv.org/abs/2408.06929): currently Trace-Grounded Personas, medium confidence. The abstract mentions 7,286 participants and shared demographic traits; follow-up should decide whether prompts are individual participant profiles or aggregate demographic/nationality conditions.
- [ASPIRE](https://doi.org/10.1145/3708319.3733685): currently Trace-Grounded Personas, medium confidence. It pairs each human participant with a digital twin based on demographic profile, so it is person-indexed, but full text should verify whether enough person-level evidence is used beyond demographics.
- [Sycamore](https://arxiv.org/abs/2605.08630): currently Trace-Grounded Personas, medium confidence. It includes both ungrounded LLM personas and personas constrained by voice-of-customer artifacts; cite it as a mixed-condition study rather than a pure family exemplar.
- [PersonaBOT](https://arxiv.org/abs/2505.17156): now Authored Archetypes, medium confidence. Recommended handling: keep as authored/verified customer-persona anchored unless full text shows raw interviews or logs directly drive each generated persona.
- [Synonymix](https://arxiv.org/abs/2603.28066): now Trace-Grounded Personas, medium confidence. Recommended handling: label as a group-abstraction bridge from life-story personas; verify whether source life stories are human-authored, trace-derived, or model-generated.
- [Restoring Heterogeneity](https://arxiv.org/abs/2604.06663): now Population-Sampled Personas, medium confidence. Recommended handling: include as a segment-level population/survey construction case, while noting it may not generate rich individual personas.
- [ScioMind](https://arxiv.org/abs/2605.13725): currently Trace-Grounded Personas, medium confidence. Recommended handling: keep needs_followup because local metadata says corpus-grounded retrieval but not whether the corpus is person-level.

## Recommended Handling

Keep the four source categories exactly as defined. Add or preserve subtypes for bridge cases rather than creating new categories: `population-calibrated traces`, `survey-segmented silicon samples`, `group abstraction from life-story personas`, `verified customer personas`, and `corpus-grounded dynamic profiles`. For rows where the abstract only says "synthetic personas" or "persona-conditioned" without source detail, keep `needs_followup=yes` and avoid upgrading confidence.
