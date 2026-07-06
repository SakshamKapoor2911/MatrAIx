# Full DAG 10B Production Run Record

Date: 2026-07-03

This file records the completed 10B Full DAG persona generation run launched from this SLURM job template directory.

## Run Summary

```text
status: COMPLETED
run_tag: full_dag_10b_20260703
slurm_job_id: 27698932
partition: seas_compute
array: 0-99%20
total_rows: 10,000,000,000
rows_per_shard: 100,000,000
shards: 100
array_concurrency: 20
cpus_per_task: 48
workers_per_shard: 48
memory_per_task: 128G
time_limit: 0-06:00
```

Generation command:

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

Output root:

```text
persona/synthesis/generated/full_dag_10b_20260703/
```

The output directory is intentionally ignored by git via `persona/synthesis/generated/`.

## Final Dataset Layout

```text
persona/synthesis/generated/full_dag_10b_20260703/
  shards/
    100 x full_dag_100000000_shard_NNNN.codes.gz
    100 x full_dag_100000000_shard_NNNN.codes.gz.schema.json
  manifests/
    100 x full_dag_100000000_shard_NNNN.manifest.json
```

Each shard contains 100M personas in compressed Full DAG codes format.

```text
code shard files: 100
schema sidecars: 100
manifest files: 100
missing shard ids: none
rows per shard: 100,000,000
total rows from manifests: 10,000,000,000
attributes per row: 1,290
shape per schema: (100000000, 1290)
```

## Storage Format

The primary artifact stores structured attributes as compact integer codes, not rendered persona text.

```text
format: codes.gz
packing: nibble
compression: gzip
rendered text stored: no
```

The schema sidecar for each shard maps integer codes back to attribute value strings. Rendered text should be produced lazily from these codes for samples or downstream prompt-material subsets with `persona/synthesis/scripts/render_personas.py`.

## Final Size

```text
total compressed codes bytes: 4,039,709,140,901
average compressed bytes/persona: 403.970914
decimal TB: 4.0397 TB
binary TiB: 3.6741 TiB
du -sh display: 3.7T
```

Per-shard compressed size range:

```text
min shard bytes: 40,396,968,494
max shard bytes: 40,397,174,913
avg shard bytes: ~40,397,091,409
```

## Performance

```text
sum of per-shard sampler seconds: 46,872
aggregate rows per sampler-second: ~213,347
```

The observed per-shard sampler throughput was generally around 190k-250k rows/s on 48 allocated CPUs, with variation by node and filesystem behavior. Because 20 shards ran concurrently, cluster-level wall time was far shorter than the sum of shard runtimes.

## Monitoring

Monitor command used during the run:

```bash
cd persona/synthesis/jobs/graph_10b_generation
./monitor_generation.sh full_dag_10b_20260703 27698932
```

The monitor reports scheduler state, output directory size, shard/schema counts, manifest summaries, estimated in-progress rows, and sbatch log tails.

## Validation Performed

Final consistency check:

```text
codes: 100
schemas: 100
manifests: 100
rows: 10,000,000,000
missing shard ids: none
```

SLURM accounting showed all array tasks completed. The generated data remains ignored by git, while this run record is intended to be tracked.

## Notes

- This run used CPU only; no GPU was required.
- The output is already compressed with gzip and nibble-packed codes.
- Do not convert the full 10B to rendered text as a primary artifact.
- Parquet should be considered a secondary analytics format for selected columns/subsets, not the canonical generated artifact.
