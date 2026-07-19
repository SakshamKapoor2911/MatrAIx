# Full DAG 10B Cluster Generation Plan

This folder contains CPU-only SLURM templates for generating large Full DAG persona shards.

## Files

```text
generate_graph_shard.job   One SLURM array task = one compressed codes shard.
submit_graph_10b.sh        Wrapper that submits an array of shard jobs.
monitor_generation.sh      One-command progress view for a run and optional job id.
RUN_FULL_DAG_10B_20260703.md
                            Completed 10B production run record.
HF_UPLOAD_PERSONA8B_1B_20260704.md
                            Hugging Face upload record for the 1B subset.
```

The generated personas are stored as compressed graph `codes.gz` files, not rendered text.
Rendering and Parquet conversion should happen later for samples, subsets, or downstream analytics.

## Recommended Storage Location

Default output root:

```text
persona/synthesis/generated/<RUN_TAG>/
```

Example:

```text
persona/synthesis/generated/full_dag_10b_20260703_153000/
  shards/
    full_dag_100000000_shard_0000.codes.gz
    full_dag_100000000_shard_0000.codes.gz.schema.json
    ...
  manifests/
    full_dag_100000000_shard_0000.manifest.json
    ...
```

`persona/synthesis/generated/` should stay git-ignored. This keeps large generated artifacts out of version control while keeping them near the graph/sampler code.

## Empirical Size Estimate

From the 1M compressed run:

```text
1M codes.gz size: 403,977,643 bytes
compressed bytes/persona: ~403.98
```

Projected 10B storage:

```text
10B x 403.98 bytes = ~4.04 TB decimal = ~3.67 TiB binary
```

Recommended free space:

```text
6-8 TB    codes.gz only
12-16 TB  codes.gz plus secondary Parquet/analytics copy
20 TB+    if storing expanded text/string-heavy artifacts
```

## Shard Layout

Default submission:

```text
100 shards x 100M rows = 10B rows
```

Estimated shard size:

```text
100M rows -> ~40.4 GB compressed codes.gz
50M rows  -> ~20.2 GB compressed codes.gz
```

The default array concurrency is 20 jobs at a time, with 48 CPUs per shard job.
This is intentionally aggressive because `seas_compute` usually has many CPU
nodes. Reduce `ARRAY_CONCURRENCY` if `/n/netscratch` write load becomes the
bottleneck or if the scheduler leaves too many jobs pending.

## First: Multi-core Benchmark

Your earlier compute-node rerun only had 1 allocated CPU, so it measured single-core throughput. Before launching 10B, request a multi-core CPU allocation or submit a small benchmark.

Interactive benchmark example:

```bash
salloc -p seas_compute -n 1 --cpus-per-task=48 --mem=128gb -t 0-02:00
```

Inside the allocation:

```bash
cd /n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx
nproc
python persona/synthesis/scripts/sample_personas.py \
  --n 10000000 \
  --seed 42 \
  --workers "$(nproc)" \
  --batch-size 25000 \
  --compress gzip \
  --out persona/synthesis/reports/scale_estimate_1m_20260703/tmp/full_dag_graph_10M_compute_w$(nproc).codes.gz
```

If `nproc` still prints `1`, the allocation did not grant multiple CPUs. Fix that before relying on parallel speed estimates.

## Submit A Small Dry Run

From this folder:

```bash
cd /n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx/persona/synthesis/jobs/graph_10b_generation
```

Submit 2 shards x 1M rows:

```bash
TOTAL_SHARDS=2 \
ROWS_PER_SHARD=1000000 \
ARRAY_CONCURRENCY=2 \
CPUS_PER_TASK=48 \
WORKERS=48 \
TIME=0-01:00 \
RUN_TAG=full_dag_dryrun_2m \
./submit_graph_10b.sh
```

Expected output:

```text
persona/synthesis/generated/full_dag_dryrun_2m/
  shards/*.codes.gz
  shards/*.codes.gz.schema.json
  manifests/*.manifest.json
```

## Submit A 100M Test

This is a realistic single-shard test for final shard size.

```bash
TOTAL_SHARDS=1 \
ROWS_PER_SHARD=100000000 \
ARRAY_CONCURRENCY=1 \
CPUS_PER_TASK=48 \
WORKERS=48 \
TIME=0-06:00 \
RUN_TAG=full_dag_test_100m \
./submit_graph_10b.sh
```

If this finishes quickly and produces a ~40GB shard, the 10B plan is ready.

## Submit 10B

Default 10B submission:

```bash
TOTAL_SHARDS=100 \
ROWS_PER_SHARD=100000000 \
ARRAY_CONCURRENCY=20 \
CPUS_PER_TASK=48 \
WORKERS=48 \
MEM=128G \
TIME=0-06:00 \
RUN_TAG=full_dag_10b_20260703 \
./submit_graph_10b.sh
```

Alternative gentler I/O plan:

```bash
TOTAL_SHARDS=200 \
ROWS_PER_SHARD=50000000 \
ARRAY_CONCURRENCY=20 \
CPUS_PER_TASK=48 \
WORKERS=48 \
MEM=128G \
TIME=0-06:00 \
RUN_TAG=full_dag_10b_20260703_50m \
./submit_graph_10b.sh
```

## Runtime Expectations

Observed single-CPU throughput:

```text
~9.6k-9.9k rows/s
10B at this speed: ~11.6-12.1 days
```

README optimized benchmark:

```text
~205k rows/s at 24 workers
10B no-save at this speed: ~13.6 hours
10B compressed save estimate: ~15-18 hours
```

With 48-worker shard jobs and 20 shards running concurrently, the cluster-level
throughput could be substantially higher than a single-node benchmark if
filesystem bandwidth keeps up. Treat the 48-worker/20-concurrent default as an
aggressive production setting after the dry run confirms allocations and I/O.

Practical expectation depends on whether `seas_compute` grants the requested CPUs and how `/n/netscratch` handles concurrent gzip writes.

## Monitoring

Useful commands:

```bash
squeue -u "$USER"
sacct --format=JobID,JobName%30,Partition,NodeList,AllocCPUS,State,ExitCode,Elapsed,Start,End
find persona/synthesis/generated/<RUN_TAG>/shards -name '*.codes.gz' | wc -l
du -sh persona/synthesis/generated/<RUN_TAG>
```

Preferred one-command monitor:

```bash
cd persona/synthesis/jobs/graph_10b_generation
./monitor_generation.sh <RUN_TAG> <SLURM_JOB_ID>
```

Example:

```bash
./monitor_generation.sh full_dag_test_100m_w48 27692686
```

The monitor prints scheduler state, output size, shard/schema counts, manifest
summary, estimated in-progress rows from shard file sizes, and recent sbatch log
tails.

Future shard jobs also print periodic `PROGRESS` lines to their `.out` logs while
the sampler is running. The lines include current output bytes and estimated rows
based on the measured compressed density. Adjust the interval with:

```bash
MONITOR_INTERVAL=30 ./submit_graph_10b.sh
```

Each completed shard writes a manifest containing row count, seed, output bytes, sha256, elapsed time, hostname, and SLURM job metadata.

## Resume Behavior

`generate_graph_shard.job` skips a shard if both the `.codes.gz` and `.schema.json` already exist and are non-empty. This makes failed arrays restartable: resubmitting the same `RUN_TAG`, shard count, and row count will only run missing shards.

## Notes

- Use CPU partition `seas_compute`; no GPU is needed.
- Request CPUs with `--cpus-per-task`, not only `-n 1`.
- Set `WORKERS` equal to allocated CPUs, usually `$(nproc)` inside an allocation or `CPUS_PER_TASK` at submission.
- Keep primary artifacts as `codes.gz`; render text lazily with `persona/synthesis/scripts/render_personas.py`.
- Convert to Parquet only for selected columns/subsets or analytics workflows.
