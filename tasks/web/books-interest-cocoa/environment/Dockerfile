FROM ghcr.io/agent-infra/sandbox:latest

WORKDIR /app

# CocoaAgent + Playwright (oracle). Task container *is* the AIO Sandbox (localhost:8080).
RUN git clone --depth 1 https://github.com/cocoabench/cocoa-agent.git /opt/cocoa-agent-src \
    && /opt/python3.12/bin/pip install --no-cache-dir \
       -r /opt/cocoa-agent-src/requirements.txt \
       agent-sandbox playwright \
    && /opt/python3.12/bin/playwright install chromium \
    && ln -sfn /opt/cocoa-agent-src /opt/cocoa-agent \
    && ln -sf /opt/python3.12/bin/python3 /usr/local/bin/python \
    && ln -sf /opt/python3.12/bin/python3 /usr/local/bin/python3

RUN mkdir -p /app/input /app/output
