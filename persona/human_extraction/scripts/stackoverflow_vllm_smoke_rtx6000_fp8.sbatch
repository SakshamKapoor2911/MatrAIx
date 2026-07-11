#!/bin/bash
#SBATCH --job-name=so-vllm-rtx-fp8-smoke
#SBATCH --account=torch_pr_543_general
#SBATCH --gres=gpu:1
# Verify the live feature with: sinfo -N --Format=Features,Gres,NodeList | grep -i -E 'rtx|6000'
#SBATCH --constraint=rtxpro6000
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=01:00:00
#SBATCH --output=/scratch/yl6586/slurm_logs/slurm-%x-%j.out
#SBATCH --error=/scratch/yl6586/slurm_logs/slurm-%x-%j.err

set -euo pipefail

WORKDIR=/scratch/yl6586/MatrAIx
SCRIPT="$WORKDIR/persona/human_extraction/scripts/extract_personas_stackoverflow_vllm.py"
OUTPUT="$WORKDIR/persona/human_extraction/data/stackoverflow_survey/smoke_vllm_rtx6000_fp8_2025_${SLURM_JOB_ID}.jsonl"

# Reuse the existing image first. The preflight below exits before model loading
# if its CUDA/PyTorch build cannot use the RTX Pro 6000.
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

echo "Running RTX Pro 6000 and container compatibility preflight..."
apptainer "${APPTAINER_ARGS[@]}" /usr/bin/python3 - <<'PY'
import torch
import vllm

if not torch.cuda.is_available():
    raise RuntimeError(
        "CUDA is not available inside the container; the image CUDA build may "
        "be incompatible with the node driver"
    )

properties = torch.cuda.get_device_properties(0)
name = properties.name
capability = torch.cuda.get_device_capability(0)
memory_gib = properties.total_memory / 1024**3

print(f"torch={torch.__version__}")
print(f"vllm={vllm.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"gpu={name}")
print(f"compute_capability={capability[0]}.{capability[1]}")
print(f"gpu_memory_gib={memory_gib:.1f}")

if "RTX PRO 6000" not in name.upper():
    raise RuntimeError(f"Expected an RTX Pro 6000, but Slurm exposed {name!r}")
if capability < (12, 0):
    raise RuntimeError(
        f"Expected compute capability 12.0 or newer, got {capability[0]}.{capability[1]}"
    )
if memory_gib < 90:
    raise RuntimeError(f"Expected about 96 GiB of GPU memory, got {memory_gib:.1f} GiB")
PY

apptainer "${APPTAINER_ARGS[@]}" \
  /usr/bin/python3 \
  "$SCRIPT" \
  --year 2025 \
  --start-row 0 \
  --limit 1 \
  --execute \
  --model Qwen/Qwen3.6-35B-A3B-FP8 \
  --batch-profiles 1 \
  --max-model-len 32768 \
  --max-num-seqs 64 \
  --dtype bfloat16 \
  --tensor-parallel-size 1 \
  --quantization none \
  --gpu-memory-utilization 0.90 \
  --download-dir "$HF_HUB_CACHE" \
  --output "$OUTPUT"

echo "RTX Pro 6000 FP8 smoke test completed: $OUTPUT"
