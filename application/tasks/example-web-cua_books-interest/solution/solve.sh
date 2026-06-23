#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

cat > /app/output/book_interest.json <<'EOF'
{
  "title": "A Light in the Attic",
  "price_gbp": "£51.77",
  "interested": true,
  "reason": "I would consider this poetry collection at this price after browsing the catalog in the browser."
}
EOF
