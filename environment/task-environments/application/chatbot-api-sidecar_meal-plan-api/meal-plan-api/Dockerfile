FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py nutrition_data.py llm.py .

EXPOSE 8000

CMD ["python", "server.py"]
