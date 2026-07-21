#!/bin/bash
set -euo pipefail

R="${REPO_ROOT:-/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx}"
P="${PYTHON_BIN:-/n/home08/xiaominli/.conda/envs/env05/bin/python}"
D="$R/persona/post_process/unified_dataset"
OUTPUT="${OUTPUT:-$D/results/persona8b_8_4b_20260720}"
MANIFEST="$R/persona/post_process/deduplication/jobs/manifests/human_minhash_20260719/human_tasks.jsonl"
DEDUP_DIR="$R/persona/post_process/deduplication/results/human_minhash_20260719/dedup_threshold_0.95"
SCHEMA="$R/persona/synthesis/generated/full_dag_10b_20260703/shards/full_dag_100000000_shard_0000.codes.gz.schema.json"
SURVEY="$R/persona/human_extraction/data/matraix_persona_1m_public_release/Real Human Survey/merged_personas_508.jsonl"
HUMAN_TASKS=$(wc -l < "$MANIFEST")
[[ "$HUMAN_TASKS" -eq 465 ]]

mkdir -p "$OUTPUT/data" "$OUTPUT/reports" "$D/jobs/sbatch_logs"
cd "$D/jobs"
common="ALL,REPO_ROOT=$R,PYTHON_BIN=$P,OUTPUT=$OUTPUT,SCHEMA=$SCHEMA"
synthetic=$(sbatch --parsable --job-name=persona8b_synthetic --array=0-99%25 \
  --export="$common" "$D/jobs/materialize_synthetic.job")
human=$(sbatch --parsable --job-name=persona8b_human --array=0-$((HUMAN_TASKS - 1))%50 \
  --export="$common,MANIFEST=$MANIFEST,DEDUP_DIR=$DEDUP_DIR" "$D/jobs/materialize_human.job")
survey=$(sbatch --parsable --job-name=persona8b_survey \
  --export="$common,SURVEY=$SURVEY" "$D/jobs/materialize_survey.job")
finalize=$(sbatch --parsable --job-name=persona8b_finalize \
  --dependency="afterok:$synthetic:$human:$survey" --export="$common" "$D/jobs/finalize.job")
upload=$(sbatch --parsable --job-name=persona8b_upload \
  --dependency="afterok:$finalize" \
  --export="$common,REPO_ID=MatrAIx2026/Persona8B,REVISION=unified-8.4b" \
  "$D/jobs/upload.job")

jq -n \
  --arg output "$OUTPUT" \
  --arg synthetic_job "$synthetic" \
  --arg human_job "$human" \
  --arg survey_job "$survey" \
  --arg finalize_job "$finalize" \
  --arg upload_job "$upload" \
  '{output:$output,synthetic_job:$synthetic_job,human_job:$human_job,survey_job:$survey_job,finalize_job:$finalize_job,upload_job:$upload_job,hf_repo:"MatrAIx2026/Persona8B",hf_revision:"unified-8.4b"}' \
  | tee "$OUTPUT/submission.json"