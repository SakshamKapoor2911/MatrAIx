FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/input /app/output

COPY product_brief.md /app/input/product_brief.md
COPY survey_questions.md /app/input/survey_questions.md
