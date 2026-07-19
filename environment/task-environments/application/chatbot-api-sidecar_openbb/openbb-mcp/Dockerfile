FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY run_openbb_mcp.py .

RUN python -m pip install --no-cache-dir --upgrade pip wheel && \
    python -m pip install --no-cache-dir \
      openbb-mcp-server \
      openbb-crypto \
      openbb-bls \
      openbb-ecb \
      openbb-econdb \
      openbb-economy \
      openbb-equity \
      openbb-etf \
      openbb-federal-reserve \
      openbb-fixedincome \
      openbb-fred \
      openbb-index \
      openbb-imf \
      openbb-news \
      openbb-oecd \
      openbb-technical \
      openbb-tmx \
      openbb-yfinance

EXPOSE 8001

CMD ["python", "run_openbb_mcp.py", "--host", "0.0.0.0", "--port", "8001", "--tool-discovery"]
