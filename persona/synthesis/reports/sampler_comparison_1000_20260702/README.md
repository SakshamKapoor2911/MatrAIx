# Sampler Comparison 1000

- Seed: `42`
- Count: `1000`

## Outputs

- Constraint-based compact codes: `constraint_based_1000.codes`
- Constraint-based compact code schema: `constraint_based_1000.codes.schema.json`
- Full DAG compact codes: `full_dag_forward_1000.codes`
- Full DAG compact code schema: `full_dag_forward_1000.codes.schema.json`
- Machine-readable summary: `summary.json`
- GPT Pro qualitative report: `sampler_generation_quality_comparison.md`

## Summary

| Sampler | Fields per sample | Time | File size | Notes |
| --- | ---: | ---: | ---: | --- |
| Constraint-based dev generator codes | 82 | 0.030s generation | 82,000 bytes + 22,921 schema bytes | validation violations: 0 |
| Full DAG forward sampler codes | 1224 | 0.848s | 1,224,000 bytes + 301,307 schema bytes | dtype uint8 |

The constraint-based generator is the older dev/core generator. The Full DAG sampler is the current graph-driven forward sampler.

`sampler_generation_quality_comparison.md` was written externally in GPT Pro
from readable JSONL renderings of the same seed-42 samples. It should be read as
a qualitative review rather than a validator: it recommends the Full DAG sampler
as the main generator because it has much broader coverage and explicit
dependency structure, while also calling out remaining consistency surfaces that
should be handled with masks, repair, or post-sampling validation.

Only compact code artifacts are kept in this directory. JSONL renderings were
used during the qualitative review for readability, but are intentionally not
committed because they duplicate the same samples at much larger size.
