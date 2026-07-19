#!/bin/bash
set -euo pipefail

API_BASE="http://support-api:8000"

curl -sS -X POST "${API_BASE}/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, my order #4521 was supposed to arrive Tuesday but still has not shown up. Can you help?"}'

curl -sS -X POST "${API_BASE}/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{"message": "Thanks. The shipping address should still be correct. What does tracking show right now?"}'

mkdir -p /app/output
curl -sS "${API_BASE}/v1/conversation" -o /app/output/transcript.json
python3 -m json.tool /app/output/transcript.json > /dev/null
