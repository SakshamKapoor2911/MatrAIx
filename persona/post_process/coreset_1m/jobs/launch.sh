#!/bin/bash
set -euo pipefail
R="${REPO_ROOT:-/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx}"
P="${PYTHON_BIN:-/n/home08/xiaominli/.conda/envs/env05/bin/python}"
HF="${HF_BIN:-/n/home08/xiaominli/.conda/envs/env05/bin/hf}"
D="$R/persona/post_process/coreset_1m"
INPUT="$R/persona/post_process/unified_dataset/results/persona8b_8_4b_20260720"
CODEBOOK="$R/persona/synthesis/generated/full_dag_10b_20260703/shards/full_dag_100000000_shard_0000.codes.gz.schema.json"
OUTPUT="${OUTPUT:-$D/results/persona_1m_20260720}"
mkdir -p "$D/jobs/sbatch_logs" "$D/results"
cd "$D/jobs"
common="ALL,REPO_ROOT=$R,PYTHON_BIN=$P,HF_BIN=$HF,INPUT_ROOT=$INPUT,CODEBOOK=$CODEBOOK,OUTPUT=$OUTPUT,REPO_ID=MatrAIx2026/MatrAIx_Persona_1M_Public_Release"
build=$(sbatch --parsable --job-name=persona1m_build \
  --export="$common" "$D/jobs/build.job")
upload=""
if [[ -n "${HF_TOKEN_matraix:-${HF_TOKEN:-}}" ]]; then
  upload=$(sbatch --parsable --job-name=persona1m_upload \
    --dependency="afterok:$build" --export="$common" "$D/jobs/upload.job")
fi
printf '{"build_job":"%s","upload_job":%s,"authentication_required":%s,"output":"%s","repo":"%s"}\n' \
  "$build" "${upload:+\"$upload\"}" \
  "$(if [[ -z "$upload" ]]; then printf true; else printf false; fi)" \
  "$OUTPUT" "MatrAIx2026/MatrAIx_Persona_1M_Public_Release" \
  | sed 's/"upload_job":,/"upload_job":null,/' | tee "$D/results/submission.json"