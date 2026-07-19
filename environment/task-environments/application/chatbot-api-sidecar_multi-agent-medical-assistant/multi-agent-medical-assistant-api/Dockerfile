FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic

COPY medical_http.py medical_server.py ./

CMD ["python", "-m", "uvicorn", "medical_server:app", "--host", "0.0.0.0", "--port", "8000"]
