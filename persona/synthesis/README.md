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
  reports/sampler_comparison_1000_20260702/
                                      Constraint baseline vs Full DAG comparison artifacts.
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
| Emitted persona attributes | 1,224 |
| Internal latent/helper nodes | 18 |
| Total graph nodes | 1,242 |
| Directed proposal edges | 6,830 |
| Full CPT overlays | 54 |
| Full CPT rows | 17,645 |
| Conditional masks | 172 |
| Hard-zero masked values | 391 |
| External/proxy nodes | 0 |

The current graph is the v4.3 cleaned Full DAG. Placeholder external dataset
dimensions, benchmark-adapter dimensions, provenance/source fields, and duplicate
source-proxy fields were removed from the committed graph. Default samples emit
1,224 actual persona attributes. The remaining `emit:false` nodes are internal
latent/helper nodes used by the proposal model, not output persona attributes.

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

Sample personas and save compact integer codes by passing `--out`. This is the
default saved format:

```bash
uv run python persona/synthesis/scripts/sample_personas.py \
  --n 1000 \
  --seed 42 \
  --out /tmp/personas_1000.codes
```

The command writes the dense code matrix and a sidecar schema:

```text
/tmp/personas_1000.codes
/tmp/personas_1000.codes.schema.json
```

For larger saved batches, use process-level shard concurrency. Codes remain the
default format, so `--format codes` is optional:

```bash
uv run python persona/synthesis/scripts/sample_personas.py \
  --n 100000 \
  --seed 42 \
  --workers 8 \
  --batch-size 12500 \
  --out /tmp/personas_100000.codes
```

For million-row persistent outputs:

```bash
uv run python persona/synthesis/scripts/sample_personas.py \
  --n 1000000 \
  --seed 42 \
  --workers 8 \
  --batch-size 25000 \
  --out /tmp/personas_1000000.codes
```

The codes file stores one dense integer matrix. Values are 0-based codes for
the emitted attributes, and the sidecar schema maps each code back to its string
value:

```text
/tmp/personas_1000000.codes
/tmp/personas_1000000.codes.schema.json
```

Decode compact codes back to JSONL or CSV when a text artifact is needed:

```bash
uv run python persona/synthesis/scripts/decode_persona_codes.py \
  --codes /tmp/personas_1000000.codes \
  --out /tmp/personas_1000000.jsonl \
  --format jsonl
```

Direct JSONL/CSV sampling is still supported for small inspection runs, but it
should not be the default persistent artifact:

```bash
uv run python persona/synthesis/scripts/sample_personas.py \
  --n 100 \
  --seed 42 \
  --format jsonl \
  --out /tmp/personas_100.jsonl
```

Benchmark generation throughput without saving samples by omitting `--out`:

```bash
uv run python persona/synthesis/scripts/sample_personas.py \
  --n 1000000 \
  --seed 42 \
  --workers 8 \
  --batch-size 25000
```

Parallel generation splits the requested count into deterministic seed shards,
writes temporary shard files only when `--out` is provided, merges saved shards
in batch order, and deletes temporary files before returning. The underlying
forward-sampling semantics are unchanged.

Use the saved form when the generated personas are the artifact. Use the no-save
form when measuring sampler throughput or stress-testing generation. Saved JSONL
runs include JSON serialization, shard writes, and final shard merge time, and
they temporarily need enough disk for both shard files and the merged output.
Saved `codes` runs avoid per-row JSON serialization and write a much smaller
binary matrix plus a small schema file.

Sampler concurrency notes:

- Default sampling prunes hidden/source nodes that are not needed to produce the
  emitted attributes. Hidden parents that affect emitted attributes are still
  sampled.
- `--workers` controls process-level shard concurrency. Each shard uses an
  independent RNG stream. On POSIX systems, parallel runs compile the sampler
  once in the parent process and inherit it in forked workers to avoid repeated
  graph compilation during worker startup.
- `--batch-size` controls rows per shard. On the current Full DAG, `25,000` is
  a good default for large runs; `10,000` to `50,000` keeps peak memory bounded
  without materially changing throughput.
- Avoid one giant `sample_indices(N)` call for very large `N`. The sampler is
  vectorized within each node, so a single huge batch repeatedly allocates large
  `(N x values)` arrays. Large jobs should use shards.
- Shard seeds are derived deterministically from `--seed`, and shards are
  merged in batch order, so repeated runs with the same arguments produce the
  same output order.
- JSONL/CSV materialization is still more expensive than integer-coded sampling.
  Keep committed/generated sample artifacts in `codes` format unless a
  human-readable debug file is explicitly needed.

Recent benchmark on this graph:

| Mode | Count | Output | Time | Throughput |
| --- | ---: | ---: | ---: | ---: |
| No-save, 8 workers, 25k-row shards | 1,000,000 | none | 23.02s | 43.4k/s |
| Saved JSONL, 4 actual workers, 2.5k-row shards | 10,000 | 372MB | 1.95s | 5.1k/s |
| Saved codes, 4 actual workers, 2.5k-row shards | 10,000 | 12.3MB + 296KB schema | 1.32s | 7.6k/s |
| Saved codes, 8 workers, 25k-row shards | 1,000,000 | 1.23GB + 296KB schema | 25.17s | 39.7k/s |

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
- [Sampler comparison report](reports/sampler_comparison_1000_20260702/sampler_generation_quality_comparison.md)
  is a GPT Pro-authored qualitative review of 1,000 seed-42 samples from the old
  constraint-based generator and the current Full DAG forward sampler. The same
  directory keeps the source comparison samples only in compact code format:
  `constraint_based_1000.codes`, `constraint_based_1000.codes.schema.json`,
  `full_dag_forward_1000.codes`, `full_dag_forward_1000.codes.schema.json`, and
  `summary.json`. The JSONL renderings used during analysis are intentionally
  not committed.
- [Graph visualization](visualization/full_dag_overview.html) is an
  interactive static HTML view of the full graph: 1,224 emitted persona
  attributes, 18 latent/helper nodes, and 6,830 directed proposal edges. X
  position follows
  topological order; Y position groups nodes into category lanes. It supports
  search, category filtering, degree filtering, hidden/helper toggling, edge
  toggling, pan/zoom, and hover/click node inspection.
- [Visualization instructions](visualization/README.md) document how to
  regenerate, open, and verify the graph view.

The comparison report's main conclusion is that the Full DAG sampler should
replace the constraint-based generator as the primary sampler because it emits a
much richer persona state and explicit dependency structure. The report also
flags remaining long-tail consistency surfaces around age, parenting,
retirement, driving, and role/seniority, so treat it as qualitative review
context alongside the machine-readable `summary.json` and generated samples.

The quality report intentionally does not commit the 10,000 sampled personas.
It commits only aggregate audit results and timing.
