FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip wheel && \
    python -m pip install --no-cache-dir fastapi "uvicorn[standard]>=0.27"

COPY harbor_api/router_server.py /app/harbor_api/router_server.py

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "harbor_api.router_server:app", "--host", "0.0.0.0", "--port", "8000"]
