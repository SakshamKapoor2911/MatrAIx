#!/usr/bin/env bash
# Pre-install Claude Code + runtime deps for persona-claude-code Docker tasks.
# Canonical copy for the Persona bench task tree; copy into each task's environment/
# dir so Harbor's Docker build context can COPY it.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    procps \
    python3 \
    python3-pip
rm -rf /var/lib/apt/lists/*

curl -fsSL https://downloads.claude.ai/claude-code-releases/bootstrap.sh | bash -s --
echo 'export PATH="/root/.local/bin:$PATH"' >> /root/.bashrc
export PATH="/root/.local/bin:$PATH"
claude --version

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh
export PATH="/root/.local/bin:$PATH"
uvx --version

mkdir -p /installed-agent /app/input /app/output
