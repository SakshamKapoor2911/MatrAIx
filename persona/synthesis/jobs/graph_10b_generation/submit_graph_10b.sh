#!/bin/bash
# Submit a SLURM array for Full DAG graph persona generation.
# Defaults: 100 shards x 100M rows = 10B rows.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$SCRIPT_DIR"
mkdir -p sbatch_logs

PARTITION="${PARTITION:-seas_compute}"
CPUS_PER_TASK="${CPUS_PER_TASK:-48}"
MEM="${MEM:-128G}"
TIME="${TIME:-0-06:00}"
TOTAL_SHARDS="${TOTAL_SHARDS:-100}"
ROWS_PER_SHARD="${ROWS_PER_SHARD:-100000000}"
ARRAY_CONCURRENCY="${ARRAY_CONCURRENCY:-20}"
BASE_SEED="${BASE_SEED:-420000}"
BATCH_SIZE="${BATCH_SIZE:-25000}"
WORKERS="${WORKERS:-$CPUS_PER_TASK}"
RUN_TAG="${RUN_TAG:-full_dag_10b_$(date +%Y%m%d_%H%M%S)}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$REPO_ROOT/persona/synthesis/generated/$RUN_TAG}"
PYTHON_BIN="${PYTHON_BIN:-python}"

array_end=$((TOTAL_SHARDS - 1))
array_spec="0-${array_end}%${ARRAY_CONCURRENCY}"

echo "=== Submit Full DAG generation ==="
echo "repo=$REPO_ROOT"
echo "partition=$PARTITION"
echo "cpus_per_task=$CPUS_PER_TASK"
echo "workers=$WORKERS"
echo "mem=$MEM"
echo "time=$TIME"
echo "total_shards=$TOTAL_SHARDS"
echo "rows_per_shard=$ROWS_PER_SHARD"
echo "total_rows=$((TOTAL_SHARDS * ROWS_PER_SHARD))"
echo "array_concurrency=$ARRAY_CONCURRENCY"
echo "base_seed=$BASE_SEED"
echo "batch_size=$BATCH_SIZE"
echo "output_root=$OUTPUT_ROOT"
echo "array=$array_spec"

mkdir -p "$OUTPUT_ROOT" "$OUTPUT_ROOT/shards" "$OUTPUT_ROOT/manifests"

sbatch \
  --partition="$PARTITION" \
  --cpus-per-task="$CPUS_PER_TASK" \
  --ntasks=1 \
  --mem="$MEM" \
  --time="$TIME" \
  --array="$array_spec" \
  --job-name="FDAG10B" \
  --export=ALL,REPO_ROOT="$REPO_ROOT",OUTPUT_ROOT="$OUTPUT_ROOT",ROWS_PER_SHARD="$ROWS_PER_SHARD",BASE_SEED="$BASE_SEED",BATCH_SIZE="$BATCH_SIZE",WORKERS="$WORKERS",PYTHON_BIN="$PYTHON_BIN" \
  generate_graph_shard.job
