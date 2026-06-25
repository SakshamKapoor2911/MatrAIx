FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic

COPY harbor_api/__init__.py /app/harbor_api/__init__.py
COPY harbor_api/medical_http.py /app/harbor_api/medical_http.py
COPY harbor_api/medical_server.py /app/harbor_api/medical_server.py

CMD ["python", "-m", "uvicorn", "harbor_api.medical_server:app", "--host", "0.0.0.0", "--port", "8000"]
