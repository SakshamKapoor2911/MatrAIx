#!/bin/bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx}"
PYTHON_BIN="${PYTHON_BIN:-/n/home08/xiaominli/.conda/envs/env05/bin/python}"
RUN_TAG="${RUN_TAG:-full_filter_20260719}"
SYNTHETIC_CONCURRENCY="${SYNTHETIC_CONCURRENCY:-20}"
HUMAN_CONCURRENCY="${HUMAN_CONCURRENCY:-30}"

FILTER_ROOT="$REPO_ROOT/persona/post_process/quality_filter"
OUTPUT_ROOT="$FILTER_ROOT/results/$RUN_TAG"
MANIFEST_DIR="$FILTER_ROOT/jobs/manifests/$RUN_TAG"
JOB_FILE="$FILTER_ROOT/jobs/filter_shard.job"
SUMMARY_JOB_FILE="$FILTER_ROOT/jobs/summarize.job"

mkdir -p "$FILTER_ROOT/jobs/sbatch_logs" "$MANIFEST_DIR" "$OUTPUT_ROOT"
cd "$FILTER_ROOT/jobs"

PYTHONPATH="$REPO_ROOT" "$PYTHON_BIN" "$FILTER_ROOT/build_inventory.py" \
  --output-root "$OUTPUT_ROOT" \
  --manifest-dir "$MANIFEST_DIR"

synthetic_manifest="$MANIFEST_DIR/synthetic_tasks.jsonl"
human_manifest="$MANIFEST_DIR/human_tasks.jsonl"
synthetic_tasks=$(wc -l < "$synthetic_manifest")
human_tasks=$(wc -l < "$human_manifest")

synthetic_job=$(sbatch --parsable \
  --job-name=qf_synthetic \
  --array="0-$((synthetic_tasks - 1))%$SYNTHETIC_CONCURRENCY" \
  --export="ALL,REPO_ROOT=$REPO_ROOT,PYTHON_BIN=$PYTHON_BIN,MANIFEST=$synthetic_manifest" \
  "$JOB_FILE")
human_job=$(sbatch --parsable \
  --job-name=qf_human \
  --array="0-$((human_tasks - 1))%$HUMAN_CONCURRENCY" \
  --export="ALL,REPO_ROOT=$REPO_ROOT,PYTHON_BIN=$PYTHON_BIN,MANIFEST=$human_manifest" \
  "$JOB_FILE")
summary_out="$OUTPUT_ROOT/summary.json"
summary_job=$(sbatch --parsable \
  --job-name=qf_summary \
  --dependency="afterok:$synthetic_job:$human_job" \
  --export="ALL,REPO_ROOT=$REPO_ROOT,PYTHON_BIN=$PYTHON_BIN,SYNTHETIC_MANIFEST=$synthetic_manifest,HUMAN_MANIFEST=$human_manifest,SUMMARY_OUT=$summary_out" \
  "$SUMMARY_JOB_FILE")

cat > "$MANIFEST_DIR/submission.json" <<JSON
{
  "run_tag": "$RUN_TAG",
  "output_root": "$OUTPUT_ROOT",
  "synthetic_job": "$synthetic_job",
  "synthetic_tasks": $synthetic_tasks,
  "synthetic_concurrency": $SYNTHETIC_CONCURRENCY,
  "human_job": "$human_job",
  "human_tasks": $human_tasks,
  "human_concurrency": $HUMAN_CONCURRENCY,
  "summary_job": "$summary_job",
  "summary_out": "$summary_out"
}
JSON

cat "$MANIFEST_DIR/submission.json"