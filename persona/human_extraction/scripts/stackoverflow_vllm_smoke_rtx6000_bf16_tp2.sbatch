#!/bin/bash
#SBATCH --job-name=so-vllm-rtx-bf16-tp2
#SBATCH --account=torch_pr_543_general
#SBATCH --comment="preemption=yes;requeue=true"
#SBATCH --gres=gpu:2
#SBATCH --constraint=rtx6000
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=01:00:00
#SBATCH --output=/scratch/yl6586/slurm_logs/slurm-%x-%j.out
#SBATCH --error=/scratch/yl6586/slurm_logs/slurm-%x-%j.err

set -euo pipefail

WORKDIR=/scratch/yl6586/MatrAIx
SCRIPT="$WORKDIR/persona/human_extraction/scripts/extract_personas_stackoverflow_vllm_v2.py"
OUTPUT="$WORKDIR/persona/human_extraction/data/stackoverflow_survey/smoke_vllm_v2_rtx6000_bf16_tp2_2025_${SLURM_JOB_ID}.jsonl"

# Reuse the existing image first. The preflight below exits before model loading
# if its CUDA/PyTorch build cannot use both RTX Pro 6000 GPUs.
IMAGE=/scratch/yl6586/containers/vllm-v0.19.0.sif

if [[ ! -f "$IMAGE" ]]; then
    echo "ERROR: Apptainer image not found: $IMAGE" >&2
    exit 1
fi

export HF_HOME=/scratch/yl6586/.cache/huggingface
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_XET_CACHE="$HF_HOME/xet"
export VLLM_CACHE_ROOT=/scratch/yl6586/.cache/vllm
export TMPDIR=/scratch/yl6586/.cache/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn

mkdir -p \
  "$HF_HOME" \
  "$HF_HUB_CACHE" \
  "$HF_XET_CACHE" \
  "$VLLM_CACHE_ROOT" \
  "$TMPDIR" \
  "$(dirname "$OUTPUT")" \
  /scratch/yl6586/slurm_logs
cd "$WORKDIR"

echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Image: $IMAGE"
echo "Output: $OUTPUT"
nvidia-smi

APPTAINER_ARGS=(
  exec
  --nv
  --bind /scratch:/scratch
  --pwd "$WORKDIR"
  "$IMAGE"
)

echo "Running two-GPU RTX Pro 6000 and container compatibility preflight..."
apptainer "${APPTAINER_ARGS[@]}" /usr/bin/python3 - <<'PY'
import torch
import vllm

if not torch.cuda.is_available():
    raise RuntimeError(
        "CUDA is not available inside the container; the image CUDA build may "
        "be incompatible with the node driver"
    )

device_count = torch.cuda.device_count()
print(f"torch={torch.__version__}")
print(f"vllm={vllm.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"visible_gpu_count={device_count}")

if device_count != 2:
    raise RuntimeError(f"Expected exactly 2 visible GPUs, got {device_count}")

for device_index in range(device_count):
    properties = torch.cuda.get_device_properties(device_index)
    name = properties.name
    capability = torch.cuda.get_device_capability(device_index)
    memory_gib = properties.total_memory / 1024**3

    print(f"gpu_{device_index}={name}")
    print(
        f"gpu_{device_index}_compute_capability="
        f"{capability[0]}.{capability[1]}"
    )
    print(f"gpu_{device_index}_memory_gib={memory_gib:.1f}")

    if capability < (12, 0):
        raise RuntimeError(
            f"Expected GPU {device_index} to have compute capability 12.0 or "
            f"newer, got {capability[0]}.{capability[1]}"
        )
    if memory_gib < 90:
        raise RuntimeError(
            f"Expected GPU {device_index} to have about 96 GiB of memory, "
            f"got {memory_gib:.1f} GiB"
        )
PY

# V2 runs all 45 manifest-defined schemas chunk-outer; one respondent bounds this GPU smoke.
apptainer "${APPTAINER_ARGS[@]}" \
  /usr/bin/python3 \
  "$SCRIPT" \
  --year 2025 \
  --start-row 0 \
  --limit 1 \
  --execute \
  --model Qwen/Qwen3.6-35B-A3B \
  --batch-profiles 1 \
  --max-model-len 32768 \
  --max-num-seqs 64 \
  --dtype bfloat16 \
  --tensor-parallel-size 2 \
  --distributed-executor-backend mp \
  --quantization none \
  --gpu-memory-utilization 0.90 \
  --download-dir "$HF_HUB_CACHE" \
  --output "$OUTPUT"

echo "Two-GPU RTX Pro 6000 BF16 smoke test completed: $OUTPUT"
