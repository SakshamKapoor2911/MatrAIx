#!/usr/bin/env bash
# agent_entrypoint_thin.sh — thin social-media agent (shared-vLLM-pool topology).
#
# Unlike agent_entrypoint.sh (which boots a private vLLM per container), this
# agent runs NO model of its own. It is a lightweight HTTP client that talks to:
#   - a shared vLLM server (one of the pool, picked by the orchestrator), and
#   - the shared platform (the social world).
# This is what lets us run FAR more agents than GPUs (64-128+), since dozens of
# thin agents share a handful of vLLM servers.
#
#   [ this container ]        [ pod host ]
#   agent loop  ───────────▶  vLLM pool member  (LLM_BASE_URL)
#               ───────────▶  platform :8000     (PLATFORM_URL)
#
# Env (set by the orchestrator):
#   PERSONA_PATH, PLATFORM_URL, LLM_BASE_URL, LLM_MODEL, NUM_STEPS,
#   STEP_DELAY_S, CLUSTER_AGENT_ID, AGENT_ID, OUTPUT_PATH
set -uo pipefail

AGENT_ID="${AGENT_ID:-0}"
echo "[agent ${AGENT_ID}] thin client -> llm=${LLM_BASE_URL:-unset} platform=${PLATFORM_URL:-unset} model=${LLM_MODEL:-unset}"

# Wait until the shared vLLM endpoint is reachable (the pool may still be
# loading when this agent starts).
base="${LLM_BASE_URL%/v1}"
for i in $(seq 1 150); do
    if curl -fsS "${base}/health" >/dev/null 2>&1; then
        echo "[agent ${AGENT_ID}] vLLM pool endpoint healthy"
        break
    fi
    sleep 4
done

export OUTPUT_PATH="${OUTPUT_PATH:-/app/output/trajectory_${AGENT_ID}.json}"
python3 -m environments.oasis.agents.entrypoint
echo "[agent ${AGENT_ID}] done (status $?)"
