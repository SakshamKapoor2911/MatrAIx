#!/usr/bin/env bash
# vllm_pool.sh — run a POOL of shared vLLM servers, one per GPU, on the pod.
#
# In the shared-pool topology, a handful of vLLM servers (one per A100) serve
# many thin agent containers. Each server is a --pid=host container with one
# CDI GPU, listening on its own host port (BASE_PORT + gpu_index).
#
# Usage (rootless docker env exported):
#   environments/oasis/greenland/vllm_pool.sh up   [MODEL] [NUM_GPUS] [GPU_MEM_UTIL]
#   environments/oasis/greenland/vllm_pool.sh down
#   environments/oasis/greenland/vllm_pool.sh status
set -uo pipefail
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-$HOME/.docker/run}"
export PATH="/usr/bin:$PATH"
export DOCKER_HOST="${DOCKER_HOST:-unix://$HOME/.docker/run/docker.sock}"

CMD="${1:-up}"
MODEL="${2:-Qwen/Qwen3-8B}"
NUM_GPUS="${3:-8}"
GPU_MEM_UTIL="${4:-0.90}"
BASE_PORT="${BASE_PORT:-8200}"
MAX_LEN="${VLLM_MAX_LEN:-4096}"
TOOL_PARSER="${TOOL_CALL_PARSER:-hermes}"
AGENT_IMAGE="${AGENT_IMAGE:-oasis-agent:latest}"   # reuse the vLLM-based image (has vllm + CUDA libs)

up() {
    echo ">> Starting vLLM pool: ${NUM_GPUS} servers, model=${MODEL}, mem=${GPU_MEM_UTIL}"
    # HF cache is shared via a host volume so each server reuses the same
    # downloaded weights instead of pulling its own copy.
    mkdir -p "$HOME/.cache/huggingface"
    for g in $(seq 0 $((NUM_GPUS-1))); do
        port=$((BASE_PORT + g))
        name="oasis-vllm-${g}"
        docker rm -f "$name" >/dev/null 2>&1 || true
        echo "   - $name on GPU $g, port $port"
        docker run -d --name "$name" --init --pid=host \
            --device "nvidia.com/gpu=${g}" --network host \
            -e LD_LIBRARY_PATH=/usr/lib64 \
            -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
            --entrypoint python3 \
            "$AGENT_IMAGE" \
            -m vllm.entrypoints.openai.api_server \
            --model "$MODEL" --port "$port" \
            --gpu-memory-utilization "$GPU_MEM_UTIL" \
            --max-model-len "$MAX_LEN" \
            --enable-auto-tool-choice --tool-call-parser "$TOOL_PARSER" \
            --no-enable-log-requests >/dev/null
    done
    echo ">> waiting for all ${NUM_GPUS} servers to report healthy (model load can take minutes)..."
    for g in $(seq 0 $((NUM_GPUS-1))); do
        port=$((BASE_PORT + g))
        for i in $(seq 1 150); do
            curl -fsS "http://127.0.0.1:${port}/health" >/dev/null 2>&1 && { echo "   ✓ GPU $g (:$port) ready"; break; }
            sleep 4
        done
    done
    echo ">> ✓ vLLM pool up. Endpoints: ${BASE_PORT}..$((BASE_PORT+NUM_GPUS-1))"
}

down() {
    echo ">> Stopping vLLM pool..."
    docker ps -a --format '{{.Names}}' | grep '^oasis-vllm-' | xargs -r docker rm -f
    echo ">> ✓ pool down"
}

status() {
    echo "=== vLLM pool ==="
    docker ps --format '{{.Names}}\t{{.Status}}' | grep '^oasis-vllm-' || echo "(none)"
    for g in $(seq 0 $((NUM_GPUS-1))); do
        port=$((BASE_PORT + g))
        printf "GPU %s (:%s) " "$g" "$port"
        curl -fsS "http://127.0.0.1:${port}/health" >/dev/null 2>&1 && echo "healthy" || echo "DOWN"
    done
}

case "$CMD" in
    up) up ;;
    down) down ;;
    status) status ;;
    *) echo "Usage: $0 [up|down|status] [MODEL] [NUM_GPUS] [GPU_MEM_UTIL]" ;;
esac
