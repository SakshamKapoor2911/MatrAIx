FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

WORKDIR /app

# Web tasks: Playwright + Chromium for terminal-driven browsing scripts.
RUN pip install --no-cache-dir playwright==1.49.1

# CLI harnesses: shared terminal deps (curl/python/uv). Claude Code is pre-baked;
# Codex and Gemini CLI install via Harbor agent install() at trial start.
COPY install-claude-code.sh /tmp/install-claude-code.sh
RUN bash /tmp/install-claude-code.sh && rm /tmp/install-claude-code.sh

ENV PATH="/root/.local/bin:${PATH}"

RUN mkdir -p /app/input /app/output /installed-agent
