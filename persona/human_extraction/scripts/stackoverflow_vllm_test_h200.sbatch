#!/bin/bash
#SBATCH --job-name=so-vllm-test-h200
#SBATCH --account=torch_pr_543_general
#SBATCH --comment="preemption=yes;requeue=true"
#SBATCH --gres=gpu:1
#SBATCH --constraint=h200
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=01:00:00
#SBATCH --output=/scratch/yl6586/slurm_logs/slurm-%x-%j.out
#SBATCH --error=/scratch/yl6586/slurm_logs/slurm-%x-%j.err
#SBATCH --mail-type=FAIL,END
#SBATCH --mail-user=yl6586@nyu.edu

set -euo pipefail

YEAR=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --year)
      YEAR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$YEAR" ]]; then
  echo "Error: --year flag is required."
  exit 1
fi


WORKDIR=/scratch/yl6586/MatrAIx
SCRIPT="$WORKDIR/persona/human_extraction/scripts/extract_personas_stackoverflow_vllm_v3.py"
SURVEY_ROOT="$WORKDIR/persona/human_extraction/data/stackoverflow_survey"
case "$YEAR" in
  2023) SURVEY_FILE="$SURVEY_ROOT/2023/results_2023_completeness_60.csv" ;;
  2024) SURVEY_FILE="$SURVEY_ROOT/2024/results_2024_completeness_60_attention.csv" ;;
  2025) SURVEY_FILE="$SURVEY_ROOT/2025/results_2025_completeness_60.csv" ;;
  *)
    echo "Error: unsupported year: $YEAR"
    exit 1
    ;;
esac
OUTPUT="$SURVEY_ROOT/extraction_stackoverflow_v3_h200_${YEAR}_${SLURM_JOB_ID}.jsonl"
IMAGE=/scratch/yl6586/containers/vllm-v0.19.0.sif

HF_CACHE=/scratch/yl6586/.cache/huggingface
export HF_HOME="$HF_CACHE"
export HF_HUB_CACHE="$HF_CACHE"
export VLLM_CACHE_ROOT=/scratch/yl6586/.cache/vllm
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1
export TOKENIZERS_PARALLELISM=true
export PYTHONUNBUFFERED=1

# Avoid inheriting an expired temporary path from the shell that submits the job.
if [[ -n "${SLURM_TMPDIR:-}" ]]; then
    export APPTAINER_TMPDIR="$SLURM_TMPDIR"
else
    unset APPTAINER_TMPDIR
fi


mkdir -p "$HF_CACHE" "$VLLM_CACHE_ROOT" "$(dirname "$OUTPUT")"
cd "$WORKDIR"

# random start row
LINE_COUNT=$(wc -l < "$SURVEY_FILE")
START_ROW=$(shuf -i "0-$((LINE_COUNT - 5000))" -n 1)

echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Image: $IMAGE"
echo "Output: $OUTPUT"
echo "Random start row: $START_ROW (CSV lines: $LINE_COUNT)"
echo "Existing output rows: $(test -f "$OUTPUT" && wc -l < "$OUTPUT" || echo 0)"
nvidia-smi

apptainer exec \
  --nv \
  --pwd "$WORKDIR" \
  "$IMAGE" \
  /usr/bin/python3 \
  "$SCRIPT" \
  --year "$YEAR" \
  --survey-root "$SURVEY_ROOT" \
  --start-row "$START_ROW" \
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
