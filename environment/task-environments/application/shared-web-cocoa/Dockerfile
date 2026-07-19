# Upstream sandbox:latest is amd64-only today; pin platform so Apple Silicon hosts
# can build via Docker Desktop emulation (slower than native arm64).
FROM --platform=linux/amd64 ghcr.io/agent-infra/sandbox:latest

WORKDIR /app

# CocoaAgent + Playwright (oracle). Task container *is* the AIO Sandbox (localhost:8080).
RUN git clone --depth 1 https://github.com/cocoabench/cocoa-agent.git /opt/cocoa-agent-src \
    && /opt/python3.12/bin/python3 -m pip install --no-cache-dir \
       -r /opt/cocoa-agent-src/requirements.txt \
       openai anthropic colorama agent-sandbox playwright \
    && /opt/python3.12/bin/python3 -m playwright install chromium \
    && ln -sfn /opt/cocoa-agent-src /opt/cocoa-agent \
    && ln -sf /opt/python3.12/bin/python3 /usr/local/bin/python \
    && ln -sf /opt/python3.12/bin/python3 /usr/local/bin/python3

RUN mkdir -p /app/input /app/output
