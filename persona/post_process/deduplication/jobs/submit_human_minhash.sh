#!/bin/bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx}"
PYTHON_BIN="${PYTHON_BIN:-/n/home08/xiaominli/.conda/envs/env05/bin/python}"
RUN_TAG="${RUN_TAG:-human_minhash_20260719}"
CONCURRENCY="${CONCURRENCY:-50}"
THRESHOLD="${THRESHOLD:-0.95}"
TOTAL_TARGET="${TOTAL_TARGET:-8400000000}"

DEDUP_ROOT="$REPO_ROOT/persona/post_process/deduplication"
SIGNATURE_DIR="$DEDUP_ROOT/results/$RUN_TAG/signatures"
DEDUP_OUTPUT_DIR="$DEDUP_ROOT/results/$RUN_TAG/dedup_threshold_${THRESHOLD}"
MANIFEST_DIR="$DEDUP_ROOT/jobs/manifests/$RUN_TAG"
MANIFEST="$MANIFEST_DIR/human_tasks.jsonl"
mkdir -p "$SIGNATURE_DIR" "$DEDUP_OUTPUT_DIR" "$MANIFEST_DIR" "$DEDUP_ROOT/jobs/sbatch_logs"

PYTHONPATH="$REPO_ROOT" "$PYTHON_BIN" "$DEDUP_ROOT/build_human_manifest.py" \
  --output-dir "$SIGNATURE_DIR" \
  --out "$MANIFEST"

cd "$DEDUP_ROOT/jobs"
scan_job=$(sbatch --parsable \
  --job-name=human_minhash \
  --array="0-464%$CONCURRENCY" \
  --export="ALL,REPO_ROOT=$REPO_ROOT,PYTHON_BIN=$PYTHON_BIN,MANIFEST=$MANIFEST" \
  "$DEDUP_ROOT/jobs/scan_human_minhash.job")
merge_job=$(sbatch --parsable \
  --job-name=human_lsh_merge \
  --dependency="afterok:$scan_job" \
  --export="ALL,REPO_ROOT=$REPO_ROOT,PYTHON_BIN=$PYTHON_BIN,MANIFEST=$MANIFEST,OUTPUT_DIR=$DEDUP_OUTPUT_DIR,THRESHOLD=$THRESHOLD,TOTAL_TARGET=$TOTAL_TARGET" \
  "$DEDUP_ROOT/jobs/merge_human_minhash.job")

cat > "$MANIFEST_DIR/submission.json" <<JSON
{
  "run_tag": "$RUN_TAG",
  "scan_job": "$scan_job",
  "scan_tasks": 465,
  "concurrency": $CONCURRENCY,
  "merge_job": "$merge_job",
  "threshold": $THRESHOLD,
  "num_perm": 64,
  "bands": 8,
  "total_target": $TOTAL_TARGET,
  "manifest": "$MANIFEST",
  "signature_dir": "$SIGNATURE_DIR",
  "dedup_output_dir": "$DEDUP_OUTPUT_DIR"
}
JSON
cat "$MANIFEST_DIR/submission.json"