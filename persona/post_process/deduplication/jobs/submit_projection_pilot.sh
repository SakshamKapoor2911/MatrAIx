#!/bin/bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx}"
PYTHON_BIN="${PYTHON_BIN:-/n/home08/xiaominli/.conda/envs/env05/bin/python}"
RUN_TAG="${RUN_TAG:-projection_pilot_10b_20260719}"
CONCURRENCY="${CONCURRENCY:-20}"
TARGET_ROWS="${TARGET_ROWS:-8397735907}"

DEDUP_ROOT="$REPO_ROOT/persona/post_process/deduplication"
CONFIG="$DEDUP_ROOT/projection_config.json"
OUTPUT_DIR="$DEDUP_ROOT/results/$RUN_TAG/sketches"
SUMMARY_OUT="$DEDUP_ROOT/results/$RUN_TAG/summary.json"
MANIFEST_DIR="$DEDUP_ROOT/jobs/manifests/$RUN_TAG"
mkdir -p "$OUTPUT_DIR" "$MANIFEST_DIR" "$DEDUP_ROOT/jobs/sbatch_logs"

cd "$DEDUP_ROOT/jobs"
scan_job=$(sbatch --parsable \
  --job-name=dedup_hll \
  --array="0-99%$CONCURRENCY" \
  --export="ALL,REPO_ROOT=$REPO_ROOT,PYTHON_BIN=$PYTHON_BIN,CONFIG=$CONFIG,OUTPUT_DIR=$OUTPUT_DIR" \
  "$DEDUP_ROOT/jobs/scan_projection_hll.job")
merge_job=$(sbatch --parsable \
  --job-name=dedup_hll_merge \
  --dependency="afterok:$scan_job" \
  --export="ALL,REPO_ROOT=$REPO_ROOT,PYTHON_BIN=$PYTHON_BIN,CONFIG=$CONFIG,OUTPUT_DIR=$OUTPUT_DIR,SUMMARY_OUT=$SUMMARY_OUT,TARGET_ROWS=$TARGET_ROWS" \
  "$DEDUP_ROOT/jobs/merge_projection_hll.job")

cat > "$MANIFEST_DIR/submission.json" <<JSON
{
  "run_tag": "$RUN_TAG",
  "scan_job": "$scan_job",
  "scan_tasks": 100,
  "concurrency": $CONCURRENCY,
  "merge_job": "$merge_job",
  "config": "$CONFIG",
  "output_dir": "$OUTPUT_DIR",
  "summary_out": "$SUMMARY_OUT",
  "synthetic_target_rows": $TARGET_ROWS
}
JSON
cat "$MANIFEST_DIR/submission.json"