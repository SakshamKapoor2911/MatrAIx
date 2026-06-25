FROM python:3.12-bookworm

COPY install-claude-code.sh /tmp/install-claude-code.sh
RUN bash /tmp/install-claude-code.sh && rm /tmp/install-claude-code.sh
COPY chatbot_client.py /app/chatbot_client.py
COPY chatbot_controller.py /app/chatbot_controller.py
RUN mkdir -p /app/input /app/output

ENV PATH="/root/.local/bin:${PATH}"
WORKDIR /app
