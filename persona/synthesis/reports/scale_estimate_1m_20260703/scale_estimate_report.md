# Full DAG 1M Generation Scale Estimate

Date: 2026-07-03

This note records the current 1M-persona compressed generation run, the observed node environment, and projected requirements for a ~10B-persona generation job.

## Status

Generated a 1M-row Full DAG graph-based sample in compressed `codes.gz` format.

```text
Output directory:
persona/synthesis/reports/scale_estimate_1m_20260703/

Tracked note:
scale_estimate_report.md

Temporary generated data under ignored `tmp/`:
tmp/full_dag_graph_1M.codes.gz
tmp/full_dag_graph_1M.codes.gz.schema.json
tmp/rendered_probe_2.jsonl
```

The `tmp/` directory is intentionally ignored by git. It keeps large generated
data and disposable rendered probes near the report without making them part of
the committed artifact set.

Generation command:

```bash
python persona/synthesis/scripts/sample_personas.py \
  --n 1000000 \
  --seed 42 \
  --workers 8 \
  --batch-size 25000 \
  --compress gzip \
  --out persona/synthesis/reports/scale_estimate_1m_20260703/tmp/full_dag_graph_1M.codes.gz
```

Renderer smoke test:

```bash
python persona/synthesis/scripts/render_personas.py \
  --codes persona/synthesis/reports/scale_estimate_1m_20260703/tmp/full_dag_graph_1M.codes.gz \
  --sample 2 \
  --seed 7 \
  --mode both \
  --max-clauses-per-bucket 3 \
  --out persona/synthesis/reports/scale_estimate_1m_20260703/tmp/rendered_probe_2.jsonl
```

Renderer note: `--sample` was updated to use streaming reservoir sampling, so it no longer materializes the whole input before sampling from large codes files.

## Current Node Environment

This run was performed on a login node, **not a dedicated compute node**.

```text
hostname: boslogin07.rc.fas.harvard.edu
nproc visible to shell: 1
lscpu CPU count on host: 32
CPU model: Intel(R) Xeon(R) Gold 6426Y
threads per core: 1
cores per socket: 16
sockets: 2
memory total: ~1.0 TiB
memory available at check time: ~812 GiB
filesystem: /n/netscratch
filesystem size: 4.0P
filesystem available at check time: ~532T
filesystem use: 88%
```

Important caveat: because this was not run inside a proper compute allocation, the observed throughput should be treated as a conservative/login-node estimate. It should not be used as the final production benchmark for a 10B run.

## 1M Run Results

Sampler metadata:

```text
samples: 1,000,000
format: codes
emitted_nodes: 1,290
workers requested: 8
workers used: 8
batch_size: 25,000
batches: 40
packing: nibble
compression: gzip
row_bytes before gzip: 645
elapsed_seconds: 104.2884
```

Measured output size:

```text
codes bytes: 403,977,643
schema bytes: 325,739
compressed bytes/persona: 403.98
throughput: ~9,589 rows/s
```

## Compute Node 1M Re-run

This follow-up benchmark was run on a SLURM compute node allocation. The node
hardware has 48 CPUs, but the active allocation only granted 1 CPU, so the
sampler was run with `--workers $(nproc) = 1` to fully use the allocated CPU
without oversubscribing the job.

```text
hostname: holy7c24609.rc.fas.harvard.edu
partition: seas_compute
SLURM job: 27676197
allocation: NumCPUs=1, NumTasks=1, CPUs/Task=1, memory=128G
Cpus_allowed_list: 0
nproc visible to shell: 1
lscpu CPU count on host: 48
CPU model: Intel(R) Xeon(R) Platinum 8268 CPU @ 2.90GHz
memory total visible to shell: ~188 GiB
memory available at check time: ~181 GiB
filesystem: /n/netscratch
filesystem available at check time: ~531T
filesystem use: 88%
```

Generation command:

```bash
python persona/synthesis/scripts/sample_personas.py \
  --n 1000000 \
  --seed 42 \
  --workers "$(nproc)" \
  --batch-size 25000 \
  --compress gzip \
  --out persona/synthesis/reports/scale_estimate_1m_20260703/tmp/full_dag_graph_1M_compute_holy7c24609_w1.codes.gz
```

Sampler metadata:

```text
samples: 1,000,000
format: codes
emitted_nodes: 1,290
workers requested: 1
workers used: 1
batch_size: 25,000
batches: 40
parallel: false
packing: nibble
compression: gzip
elapsed_seconds: 100.6257
```

Measured output size and throughput:

```text
codes bytes: 403,977,643
schema bytes: 325,711
compressed bytes/persona: 403.98
throughput: ~9,938 rows/s
wall time from /usr/bin/time: 1:41.76
CPU utilization: 95%
maximum resident set size: 236,724 KB (~231 MiB)
```

Projected 10B generation time at this 1-CPU compute allocation throughput:

```text
10,000,000,000 / 9,938 rows/s = ~1,006,239 sec
= ~279.5 hours
= ~11.6 days
```

This re-run confirms the compressed output density from the first 1M run, but it
does not measure full-node parallel throughput because the allocation was only
granted 1 CPU. For a true parallel compute-node estimate, request a multi-core
allocation such as `--cpus-per-task 24` or `--cpus-per-task 48`, then run with
`--workers $(nproc)` inside that allocation.

## 10B Projection From This Run

Projected storage for 10B rows using this exact compressed `codes.gz` density:

```text
10B rows * 403.98 bytes/row = 4,039,776,430,000 bytes
Decimal TB: ~4.04 TB
Binary TiB: ~3.67 TiB
```

Projected generation time if the same login-node throughput held:

```text
10,000,000,000 / 9,589 rows/s = ~1,042,884 sec
= ~289.7 hours
= ~12.1 days
```

This is the conservative estimate from the current non-compute-node run.

## Expected Compute-Node Estimate

The README benchmark for the optimized Full DAG sampler reports roughly:

```text
~205k rows/s on a 24-worker run
```

At that throughput, 10B rows would take:

```text
10,000,000,000 / 205,000 rows/s = ~48,780 sec
= ~13.6 hours
```

With compressed saving overhead, a realistic compute-node estimate is likely closer to:

```text
~15-18 hours per 10B rows on a strong single node
```

Actual performance depends on CPU allocation, filesystem I/O, gzip throughput, and whether the job receives enough cores. A real production benchmark should be run inside a SLURM compute allocation, not on `boslogin07`.

## Storage Planning

Recommended primary storage format:

```text
Full DAG packed codes + gzip
```

Expected final storage:

```text
~4.04 TB for 10B rows, based on the 1M run
```

Recommended provisioned space:

```text
6-8 TB minimum for codes.gz only
12-16 TB if also producing a secondary Parquet/analytics copy
20 TB+ if storing rendered text or string-heavy Parquet
```

Do not store 10B rendered text personas as the primary artifact. Render text lazily from codes for samples or downstream prompt-material subsets.

## Recommended 10B Job Layout

Use sharded jobs rather than one monolithic output.

Good layouts:

```text
100 shards x 100M rows
200 shards x 50M rows
```

Estimated compressed shard size:

```text
100M rows * 403.98 bytes/row = ~40.4 GB per shard
50M rows * 403.98 bytes/row = ~20.2 GB per shard
```

Example shard command:

```bash
python persona/synthesis/scripts/sample_personas.py \
  --n 100000000 \
  --seed 420001 \
  --workers 24 \
  --batch-size 25000 \
  --compress gzip \
  --out /path/to/graph_10B_shards/shard_0001.codes.gz
```

For SLURM, prefer submitted batch jobs over interactive allocation for the full 10B run. Interactive allocation is useful for benchmarking 1M-10M rows and checking actual throughput on the target partition.

## Parquet Recommendation

Do not use Parquet as the primary generation artifact unless downstream analytics require it immediately.

Recommended approach:

```text
Primary artifact: codes.gz shards + schema sidecars
Secondary artifact: optional Parquet subsets or selected columns
```

Reasoning:

- `codes.gz` is compact and deterministic.
- It is easy to shard and restart.
- It avoids storing 1,290 repeated string columns.
- Parquet is better for downstream Spark/Arrow analytics, not necessarily for the smallest primary store.

If Parquet is needed, store integer/dictionary-coded columns rather than expanded strings.

## Current Recommendation

1. Keep the 1M run as the empirical login-node baseline.
2. Treat the `holy7c24609` compute-node re-run as a 1-CPU allocation benchmark, not as full-node parallel performance.
3. Run a 10M compressed benchmark inside a multi-core compute allocation with `--workers $(nproc)` set to the allocated CPU count.
4. Use that multi-core compute-node benchmark to choose shard size and job array count.
5. For 10B, generate `codes.gz` shards first.
6. Keep local benchmark data, rendered probes, and temporary decoded files under
  each report's ignored `tmp/` directory.
7. Render or convert to Parquet only for samples, subsets, or analytics workflows.

## 48-CPU Dry Run Submission

After confirming `seas_compute` has many 48+ CPU nodes available, the cluster
generation templates were adjusted to default to 48 CPUs per shard job and 20
concurrent array tasks for production-scale runs.

Submitted dry run:

```bash
cd persona/synthesis/jobs/graph_10b_generation
TOTAL_SHARDS=2 \
ROWS_PER_SHARD=1000000 \
ARRAY_CONCURRENCY=2 \
CPUS_PER_TASK=48 \
WORKERS=48 \
TIME=0-01:00 \
RUN_TAG=full_dag_dryrun_2m_w48 \
./submit_graph_10b.sh
```

SLURM job:

```text
job_id: 27692367
array: 0-1%2
partition: seas_compute
rows_per_shard: 1,000,000
total_rows: 2,000,000
cpus_per_task: 48
workers: 48
```

Scheduler status confirmed both shards received 48 CPUs and started on separate
compute nodes:

```text
27692367_0  RUNNING  AllocCPUS=48  Node=holy7c24211
27692367_1  RUNNING  AllocCPUS=48  Node=holy7c24305
```

Final dry-run status:

```text
27692367_0  COMPLETED  AllocCPUS=48  Elapsed=00:00:21  Node=holy7c24211
27692367_1  COMPLETED  AllocCPUS=48  Elapsed=00:00:24  Node=holy7c24305
```

Per-shard sampler manifest throughput:

```text
shard_0000: 1,000,000 rows in 8s  -> ~125,000 rows/s, 403.979 bytes/row
shard_0001: 1,000,000 rows in 9s  -> ~111,111 rows/s, 403.979 bytes/row
```

The SLURM elapsed time includes job startup and cleanup overhead; the manifest
elapsed time is the sampling command itself. The important result is that the
jobs really did receive 48 CPUs, unlike the earlier 1-CPU compute allocation.

When this dry run finishes, inspect the manifests under:

```text
persona/synthesis/generated/full_dag_dryrun_2m_w48/manifests/
```

If throughput is good and both shards validate, the next recommended step is a
single 100M-shard benchmark with `CPUS_PER_TASK=48`, then the full 10B array with
`TOTAL_SHARDS=100`, `ROWS_PER_SHARD=100000000`, and `ARRAY_CONCURRENCY=20`.

## 100M Shard Benchmark Submission

A single production-sized 100M shard benchmark was submitted after the 48-CPU
dry run completed successfully.

```bash
cd persona/synthesis/jobs/graph_10b_generation
TOTAL_SHARDS=1 \
ROWS_PER_SHARD=100000000 \
ARRAY_CONCURRENCY=1 \
CPUS_PER_TASK=48 \
WORKERS=48 \
TIME=0-06:00 \
RUN_TAG=full_dag_test_100m_w48 \
./submit_graph_10b.sh
```

SLURM job:

```text
job_id: 27692686
partition: seas_compute
rows: 100,000,000
cpus_per_task: 48
workers: 48
expected compressed output: ~40.4 GB
output_root: persona/synthesis/generated/full_dag_test_100m_w48
```

If this benchmark completes cleanly, use its manifest elapsed time and output
size as the production estimate for choosing `ARRAY_CONCURRENCY` for the full
10B submission.

Final 100M benchmark result:

```text
status: COMPLETED
SLURM elapsed: 00:09:34
sampler elapsed from manifest: 428s
rows: 100,000,000
codes bytes: 40,397,144,381
compressed bytes/persona: 403.971
sampler throughput: ~233,645 rows/s
node: holy7c24211
sha256: 7bc401d3ed18fe81dbb4e20fe365a7273d2ee90c2ce2cabd940f0c504e4e57b9
```

This validates the planned production shard size: one 48-CPU job can generate a
100M-row compressed shard of about 40.4GB in under 10 minutes wall time on this
test. If 20 such shards run concurrently and filesystem bandwidth holds, a
100-shard 10B run would require roughly 5 waves. A naive wall-time projection is
about 50 minutes plus scheduler and I/O variability, but a more conservative
planning window is still a few hours because 20 simultaneous 40GB writers may
stress shared storage.

Monitoring helper added:

```bash
cd persona/synthesis/jobs/graph_10b_generation
./monitor_generation.sh full_dag_test_100m_w48 27692686
```

The monitor prints `squeue`, `sacct`, output size, shard counts, manifest
summary, estimated in-progress rows from shard file sizes, and recent sbatch log
tails. Future shard jobs also print periodic `PROGRESS` lines with current file
size and estimated rows while sampling is running.

## Full 10B Production Run Submission

Submitted the full 10B run using the validated 48-CPU shard plan:

```bash
cd persona/synthesis/jobs/graph_10b_generation
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

SLURM job:

```text
job_id: 27698932
array: 0-99%20
partition: seas_compute
total_rows: 10,000,000,000
rows_per_shard: 100,000,000
shards: 100
concurrency: 20
cpus_per_task: 48
workers: 48
output_root: persona/synthesis/generated/full_dag_10b_20260703
```

Initial scheduler status confirmed 20 concurrent shards started immediately,
each with 48 allocated CPUs; the remaining 80 were pending only because of the
array concurrency limit.

Progress snapshot at 2026-07-03 16:49 ET:

```text
running: first wave mostly finishing; shard 20 from second wave already started
completed/visible shard files: 20 x ~40.397GB codes.gz
schema files visible: 19
manifest files visible: 1
output directory size: ~759GB
completed rows in manifests: 100,000,000
visible shard-file rows: ~2,000,000,000
```

Interpretation: the first 20-shard wave has produced the expected final shard
files, but most tasks are still completing schema/sha256/manifest cleanup. Since
each wave is roughly 20 shards, the full run should complete in about 5 waves if
I/O remains healthy. Based on the 100M benchmark and the first wave, the active
ETA is approximately 45-60 minutes from submission, with storage expected around
4.04TB final and higher transient space while temporary shard directories and
final gzip files coexist.

Final production run status:

```text
status: COMPLETED
job_id: 27698932
code shard files: 100
schema sidecars: 100
manifest files: 100
missing shard ids: none
total rows from manifests: 10,000,000,000
total compressed codes bytes: 4,039,709,140,901
average compressed bytes/persona: 403.971
sum of per-shard sampler seconds: 46,872
aggregate rows per sampler-second: ~213,347
directory size from du -sh: 3.7T
```

The final output is under:

```text
persona/synthesis/generated/full_dag_10b_20260703/
  shards/      100 x .codes.gz plus 100 x .schema.json
  manifests/   100 x .manifest.json
```

Each shard contains 100M personas in compressed Full DAG codes format. The run
completed without missing shard ids, and all array tasks reported `COMPLETED` in
SLURM accounting. The final decimal storage footprint is approximately 4.04TB;
`du -sh` reports 3.7T in binary/display units.
