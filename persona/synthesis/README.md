# Persona Synthesis

This module owns the Persona Full DAG and the small runtime needed to sample,
validate, audit, and inspect synthetic persona assignments.

## What Is Committed

```text
persona/synthesis/
  graph/full_dag.json                  Canonical full graph artifact.
  sampler/                             Importable graph IO, sampler, validation, and audit code.
  scripts/                             Reproducible sampling, decoding, rendering, and QC entry points.
  jobs/                                SLURM job templates for large-scale graph generation.
  docs/                                Method and QC notes.
  reports/full_dag_quality_10000.md    Committed 10,000-sample quality report.
  reports/sampler_comparison_1000_20260702/
                                      Constraint baseline vs Full DAG comparison artifacts.
  reports/combinatorial_vs_graph_100_20260703/
                                      Legacy combinatorial baseline vs Full DAG quality review.
  visualization/full_dag_overview.html Static graph visualization.
```

Only one graph JSON is committed. The upstream desktop release contained two
JSON serializations with the same parsed graph content; this repo keeps the
compact one and gives it the stable domain name `full_dag.json`.

The graph-based Full DAG sampler is the primary generation path. The earlier
standalone combinatorial Persona8B sampler directory was removed to avoid two
competing generation surfaces. Its 100-sample comparison artifact is retained
only as historical baseline evidence under `reports/`.

## Graph Shape

The Full DAG is a typed persona proposal graph for a global 13+ general
population. Static validation is computed from the JSON arrays instead of
trusting metadata.

Current graph counts:

| Item | Count |
| --- | ---: |
| Emitted persona attributes | 1,290 |
| Internal latent/helper nodes | 18 |
| Total graph nodes | 1,308 |
| Directed proposal edges | 6,999 |
| Full CPT overlays | 54 |
| Full CPT rows | 17,645 |
| Conditional masks | 524 |
| Hard-zero masked values | 569 |
| External/proxy nodes | 0 |

The current graph is the v4.4 developer-extension Full DAG. Placeholder external
dataset dimensions, benchmark-adapter dimensions, provenance/source fields, and
duplicate source-proxy fields are removed from the committed graph. The
conditional-mask set includes soft cross-module consistency packs: language
budgets (`lang_*` proficiency vs `multilingualism`), cultural nativeness
budgets (`cult_*` vs `region`), duplicated-variable couplings
(`neurotype`/`health_neurodivergence`, `demo_disability_status` vs
sensory/mobility health), and pairwise guards for relationship
status/length/history, LinkedIn activity, academic institution/field, veteran
status vs military history, accessibility, and driving skill/status. Developer
and coding-agent attributes are included as emitted persona attributes. Default
samples emit 1,290 actual persona attributes. The remaining `emit:false` nodes
are internal latent/helper nodes used by the proposal model, not output persona
attributes.

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

## Rendering Semantics

`persona/schema/dimensions.json` is the canonical emitted-attribute schema for
the graph sampler and includes deterministic rendering metadata for every
emitted attribute:

- `phrase` maps an attribute value to a short natural-language clause.
- `defaultValue` marks low-salience values that the renderer can omit.
- `renderConvention` records the schema-level rendering convention.

The graph sampler itself emits structured attributes or compact integer codes.
Natural-language persona descriptions are produced as a separate rendering pass
with `scripts/render_personas.py`. This keeps the generated artifact compact and
lets downstream users choose attributes, text, or both on demand.

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

Because every emitted attribute currently has at most 16 values, the writer
nibble-packs two codes per byte (schema `format_version: 2`, `packing:
"nibble"`), which halves the artifact while keeping a fixed `row_bytes` stride
for random row access. The decoder still reads unpacked `format_version: 1`
artifacts such as the committed comparison samples.

Pass `--compress gzip` to trade random access for another ~1.6x of space. Each
batch becomes an independent gzip member, so parallel generation and
deterministic output bytes are preserved, and the decoder streams the
concatenated members transparently:

```bash
uv run python persona/synthesis/scripts/sample_personas.py \
  --n 1000000 \
  --seed 42 \
  --workers 8 \
  --batch-size 25000 \
  --compress gzip \
  --out /tmp/personas_1000000.codes.gz
```

Decode compact codes back to JSONL or CSV when a text artifact is needed:

```bash
uv run python persona/synthesis/scripts/decode_persona_codes.py \
  --codes /tmp/personas_1000000.codes \
  --out /tmp/personas_1000000.jsonl \
  --format jsonl
```

Render graph-generated attributes or compact codes into deterministic
natural-language persona descriptions when human inspection or prompt material is
needed:

```bash
uv run python persona/synthesis/scripts/render_personas.py \
  --jsonl /tmp/personas_100.jsonl \
  --mode text \
  --count 5
```

For saved compact codes, render directly from the codes file and schema sidecar:

```bash
uv run python persona/synthesis/scripts/render_personas.py \
  --codes /tmp/personas_1000000.codes.gz \
  --sample 100 \
  --mode both \
  --out /tmp/personas_100.rendered.jsonl
```

`--mode attrs` writes raw `{id: value}` dictionaries, `--mode text` writes only
the rendered description, and `--mode both` writes JSONL records containing
`index`, `text`, and `attrs`. The renderer caps each thematic bucket by default
to keep descriptions readable; pass `--max-clauses-per-bucket 0` to render all
non-default clauses.

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

Parallel generation splits the requested count into deterministic seed shards.
Uncompressed codes shards are written by workers directly into their row
offsets of the output file (no merge pass); compressed codes shards are
concatenated as gzip members in batch order; jsonl/csv shards use temporary
files merged in batch order. The underlying forward-sampling semantics are
unchanged.

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
  vectorized within each node, so a single huge batch allocates large
  `(values x N)` work buffers. Large jobs should use shards.
- Shard seeds are derived deterministically from `--seed`, and shard bytes land
  in batch order, so repeated runs with the same arguments produce the same
  output bytes regardless of worker count.
- JSONL/CSV materialization is still more expensive than integer-coded sampling.
  Keep committed/generated sample artifacts in `codes` format unless a
  human-readable debug file is explicitly needed.

Benchmarks on the same 28-core machine, before and after the compiled-plan
sampler rewrite (v4.4 graph, seed 42, 8 workers, 25k-row shards):

| Mode | Count | Output | Before | After |
| --- | ---: | ---: | ---: | ---: |
| No-save | 1,000,000 | none | 42.6s (23.5k/s) | 6.6s (150.6k/s) |
| Saved codes | 1,000,000 | 1.29GB → 645MB + 318KB schema | 45.9s | 7.7s |
| Saved codes `--compress gzip` | 1,000,000 | 408MB + 318KB schema | n/a | 9.0s |
| Single-process `sample_indices` | 20,000 | in-memory | 5.1s (3.9k/s) | 0.7s (27.7k/s) |

With 24 workers the no-save rate reaches ~205k rows/s on the same machine.

## Scaling To Billions Of Rows

Generation cost is linear in rows and embarrassingly parallel across shards, so
multi-billion-row jobs are mostly a storage decision. At the current 1,290
emitted attributes, projected artifact sizes and single-machine times for
8 billion personas:

| Artifact | Bytes/row | 8B-row size | Time at ~205k rows/s |
| --- | ---: | ---: | ---: |
| Codes (packed, default) | 645 | 5.2TB | ~11h |
| Codes + `--compress gzip` | ~408 | ~3.3TB | ~12h |
| Legacy unpacked codes | 1,290 | 10.3TB | n/a |

For jobs that size, split the run into independent invocations (for example
80 x 100M rows), each with its own `--seed` and `--out` file. Every invocation
is deterministic and restartable on its own, files stay below filesystem and
tooling limits, and invocations can run on different machines concurrently.
Peak RAM stays bounded by `--batch-size` per worker (a few hundred MB each), so
`--workers` can be set to the core count.

For SLURM/cluster runs, use the CPU-only job templates in
`jobs/graph_10b_generation/`. The recommended production shape is compressed
`codes.gz` shards under the ignored `persona/synthesis/generated/` directory,
for example `100 x 100M` rows for a 10B run. Start with a small dry run and a
single 100M-shard benchmark before submitting the full array:

```bash
cd persona/synthesis/jobs/graph_10b_generation
TOTAL_SHARDS=1 \
ROWS_PER_SHARD=100000000 \
ARRAY_CONCURRENCY=1 \
CPUS_PER_TASK=24 \
WORKERS=24 \
TIME=0-06:00 \
RUN_TAG=full_dag_test_100m \
./submit_graph_10b.sh
```

See [10B cluster generation plan](jobs/graph_10b_generation/README.md) for the
full shard layout, storage estimate, and monitoring commands.

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
  constraint-based generator and an earlier Full DAG forward-sampler snapshot.
  The same directory keeps the source comparison samples only in compact code format:
  `constraint_based_1000.codes`, `constraint_based_1000.codes.schema.json`,
  `full_dag_forward_1000.codes`, `full_dag_forward_1000.codes.schema.json`, and
  `summary.json`. The JSONL renderings used during analysis are intentionally
  not committed.
- [100-sample combinatorial vs graph quality report](reports/combinatorial_vs_graph_100_20260703/quality_report.md)
  records a small local comparison between a legacy combinatorial baseline
  sample and the current Full DAG graph sample. Its conclusion is that the graph
  sampler is the better realistic persona-generation direction because it
  produces sparse, human-scaled expertise/skill/tool/language profiles, while
  the combinatorial baseline is mostly useful for coverage and stress testing.
- [Graph visualization](visualization/full_dag_overview.html) is an
  interactive static HTML view of the full graph: 1,290 emitted persona
  attributes, 18 latent/helper nodes, and 6,999 directed proposal edges. X
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
