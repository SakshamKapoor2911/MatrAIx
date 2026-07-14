FROM ubuntu:24.04

COPY install-claude-code.sh /tmp/install-claude-code.sh
RUN sed -i 's/\r$//' /tmp/install-claude-code.sh && bash /tmp/install-claude-code.sh && rm /tmp/install-claude-code.sh

ENV PATH="/root/.local/bin:${PATH}"
WORKDIR /app
