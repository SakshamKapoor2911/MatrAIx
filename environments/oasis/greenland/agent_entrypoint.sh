#!/usr/bin/env bash
# agent_entrypoint.sh — boots ONE self-contained social-media agent container.
#
# Each agent container runs its OWN vLLM server internally (its private "brain"),
# then runs the OASIS agent loop against (a) that local vLLM and (b) the SHARED
# platform service that lives on the pod host. This is the "LLM inside each
# container" topology: the only thing shared across agents is the social platform.
#
#   [ this container ]                         [ pod host ]
#   vLLM :$VLLM_PORT  <--- agent loop --->     platform :8000  (shared world state)
#
# Env (set by the orchestrator when it `docker run`s this image):
#   PERSONA_PATH     persona YAML to embody (path inside the image)
#   PLATFORM_URL     shared platform, e.g. http://127.0.0.1:8000
#   LLM_MODEL        HF model id for this agent's private vLLM (default Qwen/Qwen3-4B)
#   VLLM_PORT        local port for the in-container vLLM (default 8100)
#   GPU_MEM_UTIL     vLLM --gpu-memory-utilization (default 0.40 -> ~2 agents/GPU)
#   VLLM_MAX_LEN     vLLM --max-model-len (default 4096)
#   NUM_STEPS        simulation steps for this agent (default 20)
#   AGENT_ID         integer index (for logs / output naming)
#   OUTPUT_PATH      trajectory json (default /app/output/trajectory_${AGENT_ID}.json)
set -uo pipefail

VLLM_PORT="${VLLM_PORT:-8100}"
LLM_MODEL="${LLM_MODEL:-Qwen/Qwen3-8B}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.40}"
VLLM_MAX_LEN="${VLLM_MAX_LEN:-4096}"
AGENT_ID="${AGENT_ID:-0}"

# CDI injects the real driver libcuda.so.1 into /usr/lib64, but this image's
# LD_LIBRARY_PATH doesn't include it, so torch/vLLM can't find the driver
# ("Failed to infer device type"). We removed the CDI update-ldcache hook (it
# mounts /proc, which the pod forbids), so prepend /usr/lib64 here instead.
export LD_LIBRARY_PATH="/usr/lib64:${LD_LIBRARY_PATH:-}"

echo "[agent ${AGENT_ID}] booting private vLLM: model=${LLM_MODEL} port=${VLLM_PORT} gpu_mem=${GPU_MEM_UTIL}"

# 1. Launch this agent's private vLLM in the background.
#    (base image ships python3, not python)
# Tool calling: the OASIS agent loop drives actions via OpenAI tool calls, so
# vLLM must run with auto tool choice + a parser. Qwen3/Qwen2.5 use the "hermes"
# parser. Override with TOOL_CALL_PARSER for other model families.
TOOL_CALL_PARSER="${TOOL_CALL_PARSER:-hermes}"
python3 -m vllm.entrypoints.openai.api_server \
    --model "${LLM_MODEL}" \
    --port "${VLLM_PORT}" \
    --gpu-memory-utilization "${GPU_MEM_UTIL}" \
    --max-model-len "${VLLM_MAX_LEN}" \
    --enable-auto-tool-choice \
    --tool-call-parser "${TOOL_CALL_PARSER}" \
    --no-enable-log-requests \
    > "/tmp/vllm_agent_${AGENT_ID}.log" 2>&1 &
VLLM_PID=$!

# 2. Wait for the private vLLM to become healthy (model load can take minutes).
echo "[agent ${AGENT_ID}] waiting for vLLM health on 127.0.0.1:${VLLM_PORT} ..."
for i in $(seq 1 150); do
    if curl -fsS "http://127.0.0.1:${VLLM_PORT}/health" >/dev/null 2>&1; then
        echo "[agent ${AGENT_ID}] vLLM healthy after ${i} checks"
        break
    fi
    if ! kill -0 "${VLLM_PID}" 2>/dev/null; then
        echo "[agent ${AGENT_ID}] FATAL: vLLM died during startup. Last log lines:"
        tail -20 "/tmp/vllm_agent_${AGENT_ID}.log"
        exit 3
    fi
    sleep 4
done

if ! curl -fsS "http://127.0.0.1:${VLLM_PORT}/health" >/dev/null 2>&1; then
    echo "[agent ${AGENT_ID}] FATAL: vLLM never became healthy. Last log lines:"
    tail -20 "/tmp/vllm_agent_${AGENT_ID}.log"
    exit 3
fi

# 3. Point the agent loop at its private vLLM and run.
export LLM_BASE_URL="http://127.0.0.1:${VLLM_PORT}/v1"
export LLM_API_KEY="${LLM_API_KEY:-no-key}"
export LLM_MODEL
export OUTPUT_PATH="${OUTPUT_PATH:-/app/output/trajectory_${AGENT_ID}.json}"

echo "[agent ${AGENT_ID}] starting OASIS agent loop -> platform=${PLATFORM_URL:-unset}"
python3 -m environments.oasis.agents.entrypoint
STATUS=$?

echo "[agent ${AGENT_ID}] agent loop exited (status ${STATUS}); stopping private vLLM"
kill "${VLLM_PID}" 2>/dev/null || true
exit "${STATUS}"
