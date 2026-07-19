FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY finance_openbb.py finance_server.py ./

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "finance_server:app", "--host", "0.0.0.0", "--port", "8000"]
