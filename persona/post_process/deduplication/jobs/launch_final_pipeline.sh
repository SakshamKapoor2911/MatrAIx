#!/bin/bash
# Submit the final pipeline after both calibration summaries exist.
set -euo pipefail
R="${REPO_ROOT:-/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx}"; P="${PYTHON_BIN:-/n/home08/xiaominli/.conda/envs/env05/bin/python}"; D="$R/persona/post_process/deduplication"
H="$D/results/human_minhash_20260719/dedup_threshold_0.95/summary.json"; Q="$D/results/projection_pilot_10b_20260719/summary.json"; O="$D/results/final_8_4b_20260719"; mkdir -p "$O" "$D/jobs/sbatch_logs"
TARGET=$(jq -r '8400000000 - .dedup_kept_rows' "$H")
PROJECTION=$($P -c 'import json,sys; s=json.load(open(sys.argv[1])); t=int(sys.argv[2]); eligible=[p for p in s["projections"] if p["estimated_unique_signatures"] >= t*1.005]; print(min(eligible,key=lambda p:p["width"])["id"])' "$Q" "$TARGET")
export_common="ALL,REPO_ROOT=$R,PYTHON_BIN=$P"
materialize=$(sbatch --parsable --job-name=dedup_materialize --array=0-99%20 --export="$export_common,OUTPUT=$O/materialized,PROJECTION=$PROJECTION,CONFIG=$D/projection_config.json" "$D/jobs/materialize_synthetic.job")
reduce=$(sbatch --parsable --job-name=dedup_reduce --dependency=afterok:$materialize --array=0-255%32 --export="$export_common,INPUT=$O/materialized,OUTPUT=$O/reduced" "$D/jobs/reduce_synthetic.job")
select=$(sbatch --parsable --job-name=dedup_select --dependency=afterok:$reduce --export="$export_common,INPUT=$O/reduced,TARGET=$TARGET,OUTPUT=$O/cutoff.json" "$D/jobs/select_synthetic_cutoff.job")
bitmap=$(sbatch --parsable --job-name=dedup_bitmap --dependency=afterok:$select --array=0-99%50 --export="$export_common,REDUCED=$O/reduced,CUTOFF=$O/cutoff.json,OUTPUT=$O/bitmaps" "$D/jobs/build_synthetic_bitmap.job")
summary=$(sbatch --parsable --job-name=dedup_final --dependency=afterok:$bitmap --export="$export_common,SYNTHETIC=$O/bitmaps,HUMAN=$H,OUTPUT=$O/summary.json,TOTAL_TARGET=8400000000" "$D/jobs/summarize_final.job")
jq -n --arg projection "$PROJECTION" --argjson target "$TARGET" --arg materialize "$materialize" --arg reduce "$reduce" --arg select "$select" --arg bitmap "$bitmap" --arg summary "$summary" '{projection:$projection,synthetic_target:$target,materialize_job:$materialize,reduce_job:$reduce,select_job:$select,bitmap_job:$bitmap,summary_job:$summary}' | tee "$O/submission.json"