FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

WORKDIR /app

# Pre-install browser-use for faster trials; agent install() can upgrade if missing.
RUN pip install --no-cache-dir "browser-use>=0.5" playwright==1.49.1

RUN mkdir -p /app/input /app/output
