FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY harbor_api/openbb_mcp_server.py /app/harbor_api/openbb_mcp_server.py

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

CMD ["python", "-m", "harbor_api.openbb_mcp_server", "--host", "0.0.0.0", "--port", "8001", "--tool-discovery"]
