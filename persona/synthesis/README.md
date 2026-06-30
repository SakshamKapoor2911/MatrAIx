# Persona Synthesis

This module owns the Persona Full DAG and the small runtime needed to sample,
validate, audit, and inspect synthetic persona assignments.

## What Is Committed

```text
persona/synthesis/
  graph/full_dag.json                  Canonical full graph artifact.
  sampler/                             Importable graph IO, sampler, validation, and audit code.
  scripts/                             Reproducible CLI entry points.
  docs/                                Method and QC notes.
  reports/full_dag_quality_10000.md    Committed 10,000-sample quality report.
  visualization/full_dag_overview.html Static graph visualization.
```

Only one graph JSON is committed. The upstream desktop release contained two
JSON serializations with the same parsed graph content; this repo keeps the
compact one and gives it the stable domain name `full_dag.json`.

## Graph Shape

The Full DAG is a typed persona proposal graph for a global 13+ general
population. Static validation is computed from the JSON arrays instead of
trusting metadata.

Current graph counts:

| Item | Count |
| --- | ---: |
| Schema attributes | 1,339 |
| Default emitted attributes | 1,230 |
| Hidden schema attributes | 109 |
| Latent/helper graph nodes | 18 |
| Total graph nodes | 1,357 |
| Directed proposal edges | 6,937 |
| Full CPT overlays | 53 |
| Full CPT rows | 13,491 |
| Conditional masks | 95 |

Total graph nodes are the 1,339 canonical persona schema attributes plus 18
latent/helper nodes used by the proposal model. Some source-proxy and audit-only
schema attributes are marked with `emit:false`; the default sampler uses those
nodes internally but hides them from emitted persona JSON, so default samples
emit 1,230 attributes.

## Sampling Semantics

The sampler is a vectorized forward sampler over
`proposal_view.topological_order`.

Each node starts with its base prior `P0(X_i)`. Pairwise directed CPDs, full CPT
overlays, and conditional masks then modify the proposal distribution:

```text
log q_i(v) = log P0_i(v)
           + gamma_i * sum_pairwise w_e [log P_e(v | x_p) - log P0_i(v)]
           + gamma_i * sum_full_cpt w_c [log P_c(v | x_pa) - log P0_i(v)]
```

The shrinkage term is:

```text
gamma_i = 1 / max(1, sqrt(sum_j weight_j^2))
```

This keeps dense parent sets from over-sharpening a node distribution. Full CPTs
can mark `replace_pairwise_parent_edges=true`; when they do, the sampler skips
the corresponding pairwise parent edges for the same target to avoid double
counting.

Conditional masks are applied after the proposal distribution is normalized:

- `bad_values` with `bad_value_multiplier=0` are hard guards.
- `downweight_values` are soft penalties.
- `preferred_values` with `penalize_values_outside_preferred_set=true` are
  applicability gates.

The graph should be read as a sampled-proposal model, not learned causal ground
truth.

## Usage

Validate the graph:

```bash
uv run python persona/synthesis/scripts/validate_graph.py
```

Sample personas:

```bash
uv run python persona/synthesis/scripts/sample_personas.py \
  --n 1000 \
  --seed 42 \
  --out /tmp/personas_1000.jsonl
```

Generate larger batches with process-level shard concurrency:

```bash
uv run python persona/synthesis/scripts/sample_personas.py \
  --n 100000 \
  --seed 42 \
  --workers 8 \
  --batch-size 12500 \
  --out /tmp/personas_100000.jsonl
```

Parallel generation splits the requested count into deterministic seed shards,
writes temporary shard files, merges them in batch order, and deletes the
temporary files before returning. The underlying forward-sampling semantics are
unchanged.

Generate the committed 10,000-sample quality report:

```bash
uv run python persona/synthesis/scripts/generate_quality_report.py \
  --n 10000 \
  --seed 42
```

Generate the committed visualization:

```bash
uv run python persona/synthesis/scripts/render_graph_visualization.py
```

Open the generated visualization directly:

```bash
open persona/synthesis/visualization/full_dag_overview.html
```

If your browser or automation blocks local `file://` access, serve the repo
from a local HTTP server instead:

```bash
python -m http.server 8765
open http://localhost:8765/persona/synthesis/visualization/full_dag_overview.html
```

Use the Python API:

```python
from persona.synthesis.sampler import (
    DEFAULT_GRAPH_PATH,
    PersonaForwardSampler,
    SamplingConfig,
)

sampler = PersonaForwardSampler(DEFAULT_GRAPH_PATH, SamplingConfig(seed=42))
samples = sampler.sample(10)
```

## Quality Artifacts

- [10,000-sample quality report](reports/full_dag_quality_10000.md) records
  static graph validation, sampling time, end-to-end report time, consistency
  audit results, and focus-node marginal drift.
- [Graph visualization](visualization/full_dag_overview.html) is an
  interactive static HTML view of the full graph: 1,339 schema attributes, 18
  latent/helper nodes, and 6,937 directed proposal edges. X position follows
  topological order; Y position groups nodes into category lanes. It supports
  search, category filtering, degree filtering, hidden/helper toggling, edge
  toggling, pan/zoom, and hover/click node inspection.
- [Visualization instructions](visualization/README.md) document how to
  regenerate, open, and verify the graph view.

The quality report intentionally does not commit the 10,000 sampled personas.
It commits only aggregate audit results and timing.

## Caveats

- The graph currently has no 0-12 age brackets, so it is a global 13+ scaffold.
- `domain` and `role_function` should be read as background or field context,
  not necessarily current employment for every persona.
- Marginal drift from priors is expected for non-root nodes because pairwise
  edges, full CPTs, and masks intentionally condition later fields on earlier
  fields.
- Hard consistency issues in the report should be treated as blockers. Strong
  and soft issues are triage signals for future graph refinement.
