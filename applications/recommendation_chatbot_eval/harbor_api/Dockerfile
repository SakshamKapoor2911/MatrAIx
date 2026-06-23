FROM --platform=linux/amd64 python:3.9-slim

ARG RECAI_COMMIT=0959ecb05b0794748426e73e6efc1b6b35ec433d

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TOKENIZERS_PARALLELISM=false \
    INTERECAGENT_CACHE_AGENT=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN if [ ! -d /app/recai/InteRecAgent/llm4crs ]; then \
      rm -rf /app/recai && \
      git clone https://github.com/microsoft/RecAI.git /app/recai && \
      cd /app/recai && \
      git checkout "${RECAI_COMMIT}"; \
    fi

RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir gdown "numpy<2" && \
    python -m pip install --no-cache-dir -r /app/recai/InteRecAgent/requirements.txt && \
    python -m pip install --no-cache-dir -r /app/backend/requirements.txt

RUN python /app/scripts/setup_resources.py

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "harbor_api.server:app", "--host", "0.0.0.0", "--port", "8000"]
