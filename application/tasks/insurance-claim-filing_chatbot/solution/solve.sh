#!/bin/bash
set -euo pipefail

API_BASE="http://chat-sim:8000"

curl -sS -X POST "${API_BASE}/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, I need some help."}'

curl -sS -X POST "${API_BASE}/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{"message": "Can you tell me more about that?"}'

mkdir -p /app/output
curl -sS "${API_BASE}/v1/conversation" -o /app/output/transcript.json
python3 -m json.tool /app/output/transcript.json > /dev/null
