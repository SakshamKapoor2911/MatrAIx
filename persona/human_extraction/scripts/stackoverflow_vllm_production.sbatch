#!/bin/bash
#SBATCH --job-name=so-vllm-production
#SBATCH --account=torch_pr_543_general
#SBATCH --comment="preemption=yes;requeue=true"
#SBATCH --gres=gpu:1
#SBATCH --constraint=h200
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --output=/scratch/yl6586/slurm_logs/slurm-%x-%j.out
#SBATCH --error=/scratch/yl6586/slurm_logs/slurm-%x-%j.err

set -euo pipefail

WORKDIR=/scratch/yl6586/MatrAIx
SCRIPT="$WORKDIR/persona/human_extraction/scripts/extract_personas_stackoverflow_vllm_v2.py"
SURVEY_ROOT="$WORKDIR/persona/human_extraction/data/stackoverflow_survey"
OUTPUT="$SURVEY_ROOT/extraction_stackoverflow_v2_2025.jsonl"
IMAGE=/scratch/yl6586/containers/vllm-v0.19.0.sif

HF_CACHE=/scratch/yl6586/.cache/huggingface
export HF_HOME="$HF_CACHE"
export HF_HUB_CACHE="$HF_CACHE"
export VLLM_CACHE_ROOT=/scratch/yl6586/.cache/vllm
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

# Avoid inheriting an expired temporary path from the shell that submits the job.
if [[ -n "${SLURM_TMPDIR:-}" ]]; then
    export APPTAINER_TMPDIR="$SLURM_TMPDIR"
else
    unset APPTAINER_TMPDIR
fi

for required_file in "$IMAGE" "$SCRIPT" "$SURVEY_ROOT/2025/results_2025_completeness_60.csv" "$SURVEY_ROOT/2025/stackoverflow_column_mapping_2025.csv"; do
    if [[ ! -f "$required_file" ]]; then
        echo "ERROR: Required file not found: $required_file" >&2
        exit 1
    fi
done

mkdir -p "$HF_CACHE" "$VLLM_CACHE_ROOT" "$(dirname "$OUTPUT")"
cd "$WORKDIR"

echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Image: $IMAGE"
echo "Output: $OUTPUT"
echo "Existing output rows: $(test -f "$OUTPUT" && wc -l < "$OUTPUT" || echo 0)"
nvidia-smi

# Each batch makes 45 same-schema chunk-outer calls; compatible V2 rows resume by row index.
apptainer exec \
  --nv \
  --pwd "$WORKDIR" \
  "$IMAGE" \
  /usr/bin/python3 \
  "$SCRIPT" \
  --year 2025 \
  --survey-root "$SURVEY_ROOT" \
  --execute \
  --batch-profiles 16 \
  --max-num-seqs 64 \
  --max-model-len 32768 \
  --max-tokens 8192 \
  --dtype bfloat16 \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --quantization none \
  --gpu-memory-utilization 0.90 \
  --download-dir "$HF_CACHE" \
  --output "$OUTPUT"

echo "Production run completed: $OUTPUT"
echo "Final output rows: $(wc -l < "$OUTPUT")"
