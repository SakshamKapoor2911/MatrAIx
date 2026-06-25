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

COPY requirements.txt /tmp/backend-requirements.txt
COPY scripts/setup_resources.py /app/scripts/setup_resources.py

RUN git clone https://github.com/microsoft/RecAI.git /app/recai && \
    cd /app/recai && \
    git checkout "${RECAI_COMMIT}"

RUN python -m pip install --no-cache-dir --upgrade pip "setuptools<81" wheel && \
    python -m pip install --no-cache-dir gdown "numpy<2" && \
    grep -v -E '^(--extra-index-url|torch[<=>])' \
      /app/recai/InteRecAgent/requirements.txt > /tmp/recai-requirements-docker.txt && \
    python -m pip install --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu \
      "torch==1.13.1+cpu" \
      "torchvision==0.14.1+cpu" && \
    python -m pip install --no-cache-dir -r /tmp/recai-requirements-docker.txt && \
    python -m pip install --no-cache-dir \
      "setuptools<81" \
      "huggingface_hub>=0.14,<0.17" \
      "accelerate<0.20" \
      "transformers==4.27.4" && \
    python -m pip install --no-cache-dir -r /tmp/backend-requirements.txt

RUN python /app/scripts/setup_resources.py && \
    rm -f /all_resources.zip

COPY . /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "harbor_api.server:app", "--host", "0.0.0.0", "--port", "8000"]
