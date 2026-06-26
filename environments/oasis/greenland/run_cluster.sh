#!/usr/bin/env bash
# run_cluster.sh — bring up the full OASIS multi-agent Docker sim ON the pod.
#
# Shared-vLLM-pool topology (many more agents than GPUs):
#   - PLATFORM container (the social world) on host port 8000
#   - vLLM POOL: NUM_GPUS servers (1/GPU) on ports VLLM_BASE_PORT..+NUM_GPUS-1
#   - DASHBOARD (host process) on DASH_PORT — live web view
#   - ORCHESTRATOR (host process) spawns N THIN agent containers that round-robin
#     the pool and pace their steps (STEP_DELAY_S) so the sim runs ~1 hour.
#
# Prereq: rootless Docker + CDI GPU ready (scripts/greenland-instance-setup.sh docker).
# Run on the Greenland instance from the repo root (~/MatrAIx).
#
# Usage:
#   environments/oasis/greenland/run_cluster.sh up [N_AGENTS] [N_STEPS] [MODEL]
#   environments/oasis/greenland/run_cluster.sh build|platform|pool|dashboard|orchestrate|down|status
set -uo pipefail

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-$HOME/.docker/run}"
export PATH="/usr/bin:$PATH"
export DOCKER_HOST="${DOCKER_HOST:-unix://$HOME/.docker/run/docker.sock}"

REPO_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_DIR"

PLATFORM_IMAGE="oasis-platform:latest"
AGENT_IMAGE="oasis-agent:latest"

N_AGENTS="${2:-64}"
N_STEPS="${3:-30}"
MODEL="${4:-Qwen/Qwen3-8B}"
NUM_GPUS="${NUM_GPUS:-8}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.90}"
STEP_DELAY_S="${STEP_DELAY_S:-90}"          # 30 steps x ~90s pacing -> roughly an hour
LAUNCH_STAGGER_S="${LAUNCH_STAGGER_S:-0.5}"
VLLM_BASE_PORT="${VLLM_BASE_PORT:-8200}"
DASH_PORT="${DASH_PORT:-8500}"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_DIR/environments/oasis/output}"
PLATFORM_URL="http://127.0.0.1:8000"
CONDA="source \$HOME/miniconda3/etc/profile.d/conda.sh 2>/dev/null && conda activate matraix 2>/dev/null || true"

require_docker() {
    docker info >/dev/null 2>&1 || { echo "✗ rootless Docker not reachable. Run: scripts/greenland-instance-setup.sh docker"; exit 1; }
}

build() {
    require_docker
    # `docker build` RUN steps fail on this pod (/proc ban) -> build via run+commit.
    echo ">> Building images via run+commit (pod-safe)..."
    bash environments/oasis/greenland/build_images.sh all
}

platform() {
    require_docker
    mkdir -p "$OUTPUT_DIR"
    # kill any stale platform process (rm -f can hang) then remove
    for P in $(ps -eo pid,cmd | grep "platform.server" | grep -v grep | awk '{print $1}'); do kill -9 "$P" 2>/dev/null; done
    docker rm -f oasis-platform >/dev/null 2>&1 || true
    # Fresh DB: agent_id=i -> user_id=i+1 (graph alignment) only holds on a clean table.
    rm -f "$OUTPUT_DIR/simulation.db" 2>/dev/null || true
    echo ">> Starting platform on :8000 (fresh db)..."
    docker run -d --name oasis-platform --init --pid=host --network host \
        -e DB_PATH=/app/output/simulation.db -e RECSYS_TYPE=random -e MAX_REC_POSTS=50 -e PORT=8000 \
        -v "$OUTPUT_DIR:/app/output" "$PLATFORM_IMAGE" >/dev/null
    for i in $(seq 1 30); do
        curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 && { echo ">> ✓ platform healthy"; return 0; }
        sleep 2
    done
    echo "✗ platform unhealthy"; docker logs --tail 30 oasis-platform; exit 1
}

pool() {
    require_docker
    echo ">> Starting vLLM pool: $NUM_GPUS servers, model=$MODEL ..."
    VLLM_MAX_LEN="${VLLM_MAX_LEN:-4096}" BASE_PORT="$VLLM_BASE_PORT" AGENT_IMAGE="$AGENT_IMAGE" \
        bash environments/oasis/greenland/vllm_pool.sh up "$MODEL" "$NUM_GPUS" "$GPU_MEM_UTIL"
}

dashboard() {
    echo ">> Starting dashboard on :$DASH_PORT (host process)..."
    pkill -f "greenland/dashboard.py" 2>/dev/null || true
    bash -c "$CONDA; setsid nohup python environments/oasis/greenland/dashboard.py --port $DASH_PORT --platform-url $PLATFORM_URL > $OUTPUT_DIR/dashboard.log 2>&1 < /dev/null &"
    sleep 2
    echo ">> ✓ dashboard: tunnel with  ssh -p 1057 -L $DASH_PORT:127.0.0.1:$DASH_PORT greenland-user@localhost  then open http://127.0.0.1:$DASH_PORT"
}

orchestrate() {
    require_docker
    mkdir -p "$OUTPUT_DIR"
    echo ">> Orchestrating: $N_AGENTS thin agents x $N_STEPS steps, step_delay=${STEP_DELAY_S}s, model=$MODEL"
    bash -c "$CONDA; setsid nohup python environments/oasis/greenland/orchestrator_cluster.py \
        --personas-dir '$REPO_DIR/personas/Jun20_1k_persona_description' \
        --num-agents $N_AGENTS --num-steps $N_STEPS --step-delay-s $STEP_DELAY_S \
        --agent-image $AGENT_IMAGE --platform-url $PLATFORM_URL --llm-model '$MODEL' \
        --num-gpus $NUM_GPUS --vllm-base-port $VLLM_BASE_PORT --launch-stagger-s $LAUNCH_STAGGER_S \
        --output-dir '$OUTPUT_DIR' > $OUTPUT_DIR/orchestrator.log 2>&1 < /dev/null &"
    sleep 2
    echo ">> ✓ orchestrator launched (background). Log: $OUTPUT_DIR/orchestrator.log"
}

up() {
    build
    platform
    pool
    dashboard
    orchestrate
    echo ""
    echo ">> ✓ FULL SIM UP. Watch the dashboard; tail $OUTPUT_DIR/orchestrator.log for progress."
}

down() {
    require_docker
    echo ">> Stopping sim..."
    pkill -f "greenland/orchestrator_cluster.py" 2>/dev/null || true
    pkill -f "greenland/dashboard.py" 2>/dev/null || true
    docker ps -a --format '{{.Names}}' | grep -E '^oasis-(agent|vllm)-' | xargs -r docker rm -f
    for P in $(ps -eo pid,cmd | grep "platform.server" | grep -v grep | awk '{print $1}'); do kill -9 "$P" 2>/dev/null; done
    docker rm -f oasis-platform >/dev/null 2>&1 || true
    echo ">> ✓ cleaned up"
}

status() {
    require_docker
    echo "=== services ==="; docker ps --format '{{.Names}}\t{{.Status}}' | grep -E '^oasis-(platform|vllm)' || echo "(none)"
    echo "=== agents (state counts) ==="; docker ps -a --format '{{.State}}' | grep -c running | sed 's/^/running: /' ; \
        docker ps -a --format '{{.Names}} {{.State}}' | grep '^oasis-agent-' | awk '{print $2}' | sort | uniq -c
    echo "=== platform stats ==="; curl -fsS http://127.0.0.1:8000/stats 2>/dev/null || echo "(platform down)"
}

case "${1:-help}" in
    build) build ;;
    platform) platform ;;
    pool) pool ;;
    dashboard) dashboard ;;
    orchestrate) orchestrate ;;
    up) up ;;
    down) down ;;
    status) status ;;
    *) echo "Usage: $0 [up|build|platform|pool|dashboard|orchestrate|down|status] [N_AGENTS] [N_STEPS] [MODEL]" ;;
esac
