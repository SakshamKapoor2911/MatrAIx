FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt /tmp/backend-requirements.txt
COPY harbor_api/finance-requirements.txt /tmp/finance-requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip wheel && \
    python -m pip install --no-cache-dir \
      -r /tmp/backend-requirements.txt \
      -r /tmp/finance-requirements.txt

COPY . /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "harbor_api.server:app", "--host", "0.0.0.0", "--port", "8000"]
